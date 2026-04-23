"""Centralized 15code branding — ads, links, and promotional content.

All software surfaces (CLI, Web, API, reports, Docker) read from here so
brand changes only need to be made in one place.
"""
from verify_core.branding.promo import (
    BRAND,
    cli_header_banner,
    cli_footer_banner,
    report_disclaimer_full,
    report_footer_html,
    get_promo_rotation,
    get_all_links,
)

__all__ = [
    "BRAND",
    "cli_header_banner",
    "cli_footer_banner",
    "report_disclaimer_full",
    "report_footer_html",
    "get_promo_rotation",
    "get_all_links",
]
