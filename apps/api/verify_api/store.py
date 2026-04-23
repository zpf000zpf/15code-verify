"""SQLite-backed scan registry. Replaces in-memory dict for durability across restarts.

Schema is minimal — we store scan metadata + the final report JSON blob.
API keys are NEVER persisted.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional


DEFAULT_DB = os.getenv("VERIFY_DB_PATH", "/opt/15code-verify/data/verify.db")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    scan_id        TEXT PRIMARY KEY,
    status         TEXT NOT NULL,          -- running | done | error
    claimed_model  TEXT,
    base_url       TEXT,
    trust_score    INTEGER,
    verdict        TEXT,
    created_at     REAL NOT NULL,
    updated_at     REAL NOT NULL,
    report_json    TEXT,
    error          TEXT,
    published      INTEGER DEFAULT 0       -- user-opt-in flag
);
CREATE INDEX IF NOT EXISTS idx_scans_created ON scans(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_published ON scans(published, created_at DESC);
"""


class ScanStore:
    def __init__(self, path: Optional[str] = None):
        self.path = Path(path or DEFAULT_DB)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create(self, scan_id: str, claimed_model: str, base_url: str, published: bool = False) -> None:
        now = time.time()
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO scans "
                "(scan_id,status,claimed_model,base_url,created_at,updated_at,published) "
                "VALUES (?,?,?,?,?,?,?)",
                (scan_id, "running", claimed_model, base_url, now, now, int(published)),
            )

    def mark_done(self, scan_id: str, report: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE scans SET status=?, trust_score=?, verdict=?, report_json=?, updated_at=? "
                "WHERE scan_id=?",
                ("done", report.get("trust_score"), report.get("verdict"),
                 json.dumps(report, ensure_ascii=False), time.time(), scan_id),
            )

    def mark_error(self, scan_id: str, error: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE scans SET status=?, error=?, updated_at=? WHERE scan_id=?",
                ("error", error[:2000], time.time(), scan_id),
            )

    def get(self, scan_id: str) -> Optional[dict[str, Any]]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM scans WHERE scan_id=?", (scan_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            if d.get("report_json"):
                try:
                    d["report"] = json.loads(d.pop("report_json"))
                except Exception:
                    d["report"] = None
            else:
                d["report"] = None
            d["published"] = bool(d.get("published", 0))
            return d

    def list_public(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT scan_id, claimed_model, trust_score, verdict, created_at "
                "FROM scans WHERE published=1 AND status='done' "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
