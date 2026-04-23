"""15code Verify — command-line entry point."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from verify_core import ScanConfig, ScanDepth, Scanner
from verify_core.branding import BRAND, cli_footer_banner
from verify_core.config import ProviderProtocol

app = typer.Typer(
    name="verify",
    help=(
        "15code Verify — detect LLM provider tampering (model substitution, "
        "token inflation, cache non-compliance).\n\nMade by 15code · https://15code.com"
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def _print_banner() -> None:
    console.print(Panel.fit(
        "[bold cyan]15code Verify[/bold cyan] — LLM provider integrity check\n"
        "[dim]by 15code · https://15code.com · free forever[/dim]",
        border_style="cyan", box=box.ROUNDED,
    ))


@app.command()
def scan(
    base_url: str = typer.Option(..., "--base-url", "-u", help="Third-party API base URL"),
    api_key: str = typer.Option(..., "--api-key", "-k", help="Third-party API key"),
    claimed_model: str = typer.Option(..., "--claimed-model", "-m", help="Model the provider claims to serve"),
    protocol: str = typer.Option("openai", "--protocol", "-p",
                                  help="API protocol: openai | anthropic"),
    depth: str = typer.Option("standard", "--depth", "-d",
                               help="Scan depth: quick | standard | deep"),
    output: Optional[Path] = typer.Option(None, "--output", "-o",
                                           help="Save full JSON report to file"),
    json_only: bool = typer.Option(False, "--json", help="Output JSON only, no pretty print"),
):
    """Run a one-shot integrity scan against a third-party LLM endpoint."""
    if not json_only:
        _print_banner()

    try:
        depth_enum = ScanDepth(depth.lower())
    except ValueError:
        console.print(f"[red]Invalid --depth '{depth}'. Use quick | standard | deep[/red]")
        raise typer.Exit(1)

    try:
        proto_enum = ProviderProtocol(protocol.lower())
    except ValueError:
        console.print(f"[red]Invalid --protocol '{protocol}'. Use openai | anthropic[/red]")
        raise typer.Exit(1)

    cfg = ScanConfig(
        base_url=base_url,
        api_key=api_key,  # SecretStr coerces
        claimed_model=claimed_model,
        protocol=proto_enum,
        depth=depth_enum,
    )

    report = None
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
        console=console, transient=not json_only,
    ) as progress:
        task = progress.add_task("Starting scan...", total=None)

        def cb(stage: str, p: float):
            progress.update(task, description=f"[cyan]{stage}[/cyan] ({p:.0%})")

        scanner = Scanner(cfg, on_progress=cb)
        try:
            report = asyncio.run(scanner.run_async())
        except Exception as e:
            progress.stop()
            console.print(f"[red]Scan failed:[/red] {e}")
            raise typer.Exit(2)

    if output:
        output.write_text(report.model_dump_json(indent=2))
        if not json_only:
            console.print(f"[green]Full report saved to[/green] {output}")

    if json_only:
        print(report.model_dump_json(indent=2))
        return

    _render_report(report)


def _render_report(report) -> None:
    tbl = Table(title=f"Scan {report.scan_id}", box=box.ROUNDED, border_style="cyan")
    tbl.add_column("Dimension", style="bold")
    tbl.add_column("Result")

    tbl.add_row("Target", report.base_url)
    tbl.add_row("Claimed Model", report.claimed_model)
    tbl.add_row("Trust Score",
                f"[bold]{report.trust_score}/100[/bold]  [dim]({report.verdict})[/dim]")

    if report.authenticity:
        a = report.authenticity
        ll = a.likely_model or "?"
        tbl.add_row(
            "🔍 Authenticity",
            f"claimed confidence: {a.confidence_is_claimed:.0%}  "
            f"|  most consistent with: [yellow]{ll}[/yellow] ({a.likely_model_confidence:.0%})",
        )
    if report.billing_audit:
        b = report.billing_audit
        infl = "⚠️  " if b.systematic_inflation else "✓ "
        tbl.add_row(
            "💰 Billing",
            f"{infl}input dev: {b.input_token_deviation_pct:+.1f}%  "
            f"output dev: {b.output_token_deviation_pct:+.1f}%  "
            f"(n={b.sample_count})",
        )
    if report.cache_audit:
        c = report.cache_audit
        status = "✓ supported" if c.cache_supported else "—  not observed"
        tbl.add_row("🗄️  Cache", status)
    if report.qos:
        q = report.qos
        tbl.add_row("⚡ QoS", f"TTFT p50: {q.ttft_ms_p50:.0f}ms  errors: {q.error_rate:.0%}")

    console.print(tbl)

    # findings
    all_findings = []
    for s in [report.authenticity, report.billing_audit, report.cache_audit, report.qos]:
        if s and getattr(s, "findings", None):
            all_findings.extend(s.findings)

    if all_findings:
        console.print("\n[bold]Findings:[/bold]")
        for f in all_findings:
            sev_colors = {"critical": "red", "warn": "yellow", "info": "blue", "ok": "green"}
            color = sev_colors.get(f.severity, "white")
            console.print(f"  [{color}][{f.severity.upper()}][/{color}] "
                          f"[bold]{f.title}[/bold]  [dim]{f.code}[/dim]")
            console.print(f"    {f.detail}")

    # Legal disclaimer
    console.print(f"\n[dim italic]{report.disclaimer}[/dim italic]")

    # 15code branded footer (rotating promo)
    console.print(cli_footer_banner("zh"))


@app.command()
def version():
    """Print version."""
    from verify_cli import __version__ as cli_v
    from verify_core import __version__ as core_v
    console.print(f"[bold cyan]{BRAND['name']}[/bold cyan]")
    console.print(f"  verify-cli  {cli_v}")
    console.print(f"  verify-core {core_v}")
    console.print(f"  [dim]by {BRAND['vendor']} · {BRAND['main_url']}[/dim]")


@app.command()
def about():
    """Learn more about 15code."""
    console.print(Panel.fit(
        f"[bold cyan]{BRAND['name']}[/bold cyan]\n"
        f"[dim]{BRAND['tagline_zh']}[/dim]\n\n"
        f"🏠 Main site    : [link]{BRAND['main_url']}[/link]\n"
        f"🔍 Verify       : [link]{BRAND['verify_url']}[/link]\n"
        f"📊 Leaderboard  : [link]{BRAND['leaderboard']}[/link]\n"
        f"📖 Docs         : [link]{BRAND['docs_url']}[/link]\n"
        f"\n"
        f"⭐ GitHub       : [link]{BRAND['github_url']}[/link]\n"
        f"🏷️  Latest rls   : [link]{BRAND['release_url']}[/link]\n"
        f"🐛 Issues       : [link]{BRAND['issues_url']}[/link]\n"
        f"💬 Discussions  : [link]{BRAND['discussions_url']}[/link]\n\n"
        "[cyan]想用一个信得过的 LLM API 服务？[/cyan]\n"
        f"[cyan]→ {BRAND['main_url']}[/cyan] — 统一 API 网关，按官方价计费，零套路\n"
        f"\n[dim]觉得工具有用？给 GitHub 点个 Star：{BRAND['github_url']}[/dim]",
        border_style="cyan", box=box.ROUNDED, title="About 15code",
    ))


if __name__ == "__main__":
    app()
