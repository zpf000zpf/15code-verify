"""FastAPI backend for 15code Verify SaaS.

Serves both the REST API and the static single-page HTML UI from one
process. Minimal memory footprint (~100 MB) so it co-exists happily
with the rest of the 15code stack on a 2 GB node.
"""
from __future__ import annotations

import asyncio
import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from verify_core import ScanConfig, ScanDepth, Scanner
from verify_core.config import ProviderProtocol
from verify_core.security import install_log_redaction, redact

install_log_redaction()

app = FastAPI(
    title="15code Verify API",
    version="0.1.0",
    description="Free LLM provider integrity checking service by 15code.",
)


# Defensive exception handler: prevent leaking API keys through pydantic errors
@app.exception_handler(Exception)
async def _safe_exception_handler(request, exc):
    from fastapi.responses import JSONResponse as _JSON
    msg = redact(str(exc))[:400]
    return _JSON(status_code=500, content={"error": "internal", "detail": msg})

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Locate static assets & download directory ────────────────────────────
_HERE = Path(__file__).resolve().parent
STATIC_DIR = _HERE / "static"
# Optional download directory for release artifacts (wheels, tarballs).
# Defaults to /opt/15code-verify/dist on the server; falls back to local.
DOWNLOAD_DIR = Path(os.getenv("VERIFY_DOWNLOAD_DIR", "/opt/15code-verify/dist"))


# Persistent scan registry (SQLite). Survives restarts.
from verify_api.store import ScanStore
_store = ScanStore()

# In-memory event queues (ephemeral — SSE only works while the worker is alive).
_events: dict[str, asyncio.Queue] = {}


class ScanCreateRequest(BaseModel):
    base_url: str
    api_key: str
    claimed_model: str
    protocol: str = "openai"
    depth: str = "standard"
    # Default-public (v1.1): scans are aggregated anonymously to the
    # public leaderboard unless explicitly set False. ToS discloses this.
    publish_to_leaderboard: bool = True
    vendor_display_name: str | None = None
    tos_accepted: bool = False


@app.get("/health")
async def health():
    return {"ok": True, "service": "15code-verify-api", "version": "0.1.0"}


@app.get("/v1/models")
async def list_supported_models():
    """List the 15code-offered models that this tool can audit."""
    from verify_core.catalog import get_catalog
    cat = get_catalog()
    return {
        "models": [
            {
                "id": m.id,
                "display_name": m.display_name,
                "family": m.family,
                "protocol": m.protocol,
                "tier": m.tier,
                "supports_cache": m.supports_cache,
                "input_price_per_mtok": m.input_price_per_mtok,
                "output_price_per_mtok": m.output_price_per_mtok,
            }
            for m in cat.all()
        ],
        "total": len(cat.all()),
        "scope_note": (
            "15code Verify 仅检测 15code 平台在售模型。这样我们可以为每个模型"
            "维护精确的 Ground-Truth 基线，提高识别准确度。"
        ),
        "15code_pricing_url": "https://15code.com/pricing",
    }


@app.post("/v1/scan")
async def create_scan(body: ScanCreateRequest):
    if not body.tos_accepted:
        raise HTTPException(400, "tos_accepted must be true. See /docs/TERMS_OF_SERVICE.md")
    # Derive vendor display name from base_url host if publishing and not provided
    if body.publish_to_leaderboard and not body.vendor_display_name:
        try:
            from urllib.parse import urlparse
            body.vendor_display_name = urlparse(body.base_url).hostname or "unknown"
        except Exception:
            body.vendor_display_name = "unknown"

    scan_id = f"scan_{secrets.token_hex(6)}"
    try:
        cfg = ScanConfig(
            base_url=body.base_url,
            api_key=body.api_key,
            claimed_model=body.claimed_model,
            protocol=ProviderProtocol(body.protocol.lower()),
            depth=ScanDepth(body.depth.lower()),
            publish_to_leaderboard=body.publish_to_leaderboard,
            vendor_display_name=body.vendor_display_name,
            tos_accepted=True,
            scan_id=scan_id,
        )
    except Exception as e:
        raise HTTPException(422, f"Invalid config: {e}")

    q: asyncio.Queue = asyncio.Queue()
    _events[scan_id] = q
    _store.create(scan_id, body.claimed_model, body.base_url, published=body.publish_to_leaderboard)

    def cb(stage: str, p: float):
        q.put_nowait({"stage": stage, "progress": p})

    async def _worker():
        scanner = Scanner(cfg, on_progress=cb)
        try:
            report = await scanner.run_async()
            _store.mark_done(scan_id, report.model_dump(mode="json"))
            q.put_nowait({"stage": "done", "progress": 1.0})
        except Exception as e:
            _store.mark_error(scan_id, redact(str(e)))
            q.put_nowait({"stage": "error", "progress": 1.0, "error": redact(str(e))})
        finally:
            q.put_nowait(None)  # sentinel

    asyncio.create_task(_worker())
    return {"scan_id": scan_id, "status": "running"}


@app.get("/v1/scan/{scan_id}")
async def get_scan(scan_id: str):
    s = _store.get(scan_id)
    if not s:
        raise HTTPException(404, "scan not found")
    return s


@app.get("/r/{scan_id}")
async def share_report(scan_id: str):
    """Shareable public report page. Only scans where the user opted-in
    to publish_to_leaderboard=True are accessible here; others 404."""
    s = _store.get(scan_id)
    if not s or not s.get("published") or s.get("status") != "done":
        raise HTTPException(404, "Report not public or not found")
    # Just serve the SPA — it will call GET /v1/scan/{id} to render.
    idx = STATIC_DIR / "share.html"
    if idx.is_file():
        return FileResponse(idx)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/v1/scan/{scan_id}/events")
async def stream_events(scan_id: str):
    q = _events.get(scan_id)
    if q is None:
        raise HTTPException(404, "scan not found")

    async def gen():
        while True:
            evt = await q.get()
            if evt is None:
                break
            yield {"event": "progress", "data": JSONResponse(content=evt).body.decode()}

    return EventSourceResponse(gen())


@app.get("/v1/leaderboard")
async def leaderboard():
    """Aggregated public leaderboard (Phase 1 — data collection)."""
    return {
        "notice": (
            "Leaderboard is in Phase 1 (data collection). "
            "Public display begins after sufficient opt-in samples. "
            "See docs/LEADERBOARD_POLICY.md."
        ),
        "methodology_version": "v1.0",
        "vendors": [],
    }


# ── Download routes (release artifacts) ──────────────────────────────────
@app.get("/download/{name:path}")
async def download(name: str):
    """Serve a release artifact if it exists."""
    # Prevent path traversal
    if ".." in name or name.startswith("/"):
        raise HTTPException(400, "invalid path")
    p = DOWNLOAD_DIR / name
    if not p.is_file():
        raise HTTPException(404, f"artifact '{name}' not found")
    return FileResponse(p, filename=name)


# ── Simple public "docs" pages (ToS / Policy) ────────────────────────────
_DOC_PAGES = {
    "tos": STATIC_DIR / "tos.html",
    "policy": STATIC_DIR / "policy.html",
}


@app.get("/docs/{page}")
async def doc_page(page: str):
    f = _DOC_PAGES.get(page)
    if f and f.is_file():
        return FileResponse(f)
    raise HTTPException(404)


# ── Root: single-page HTML UI ────────────────────────────────────────────
@app.get("/")
async def root():
    idx = STATIC_DIR / "index.html"
    if idx.is_file():
        return FileResponse(idx)
    return PlainTextResponse(
        "15code Verify API is running. See /docs for OpenAPI, /v1/models for model list.",
        media_type="text/plain",
    )


@app.get("/robots.txt")
async def robots():
    return PlainTextResponse("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")


# mount static assets last (JS/CSS if we add any later)
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
