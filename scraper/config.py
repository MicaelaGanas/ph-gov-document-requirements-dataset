"""Runtime scraper configuration (set from scrape.py / build.py CLI)."""

from __future__ import annotations

USE_BROWSER: bool = False
BROWSER_FALLBACK: bool = True

# Pause between HTTP requests (seconds) to respect official sites.
REQUEST_DELAY_SEC: float = 1.0

# Try Playwright first (or right after HTTP 403) for these hosts.
BROWSER_FIRST_HOSTS: frozenset[str] = frozenset(
    {
        "psa.gov.ph",
        "lto.gov.ph",
        "portal.lto.gov.ph",
        "pagibigfund.gov.ph",
        "gsis.gov.ph",
        "www.comelec.gov.ph",
        "comelec.gov.ph",
    }
)
