"""HTTP utilities for fetching government web pages."""

from __future__ import annotations

import logging
import time
from typing import Optional

import cloudscraper
import requests

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class FetchResult:
    __slots__ = ("url", "html", "status_code", "error", "method")

    def __init__(
        self,
        url: str,
        html: str = "",
        status_code: Optional[int] = None,
        error: str = "",
        method: str = "requests",
    ) -> None:
        self.url = url
        self.html = html
        self.status_code = status_code
        self.error = error
        self.method = method

    @property
    def ok(self) -> bool:
        return bool(self.html) and not self.error


def fetch_page(
    url: str,
    *,
    timeout: int = 30,
    retries: int = 2,
    use_cloudscraper: bool = True,
    use_browser: bool = False,
    browser_fallback: bool = True,
) -> FetchResult:
    """
    Fetch a page using requests/cloudscraper, optionally falling back to Playwright.

    Set `use_browser=True` to try Playwright first (for Cloudflare-protected sites).
    Set `browser_fallback=True` (default) to try Playwright after HTTP 403/503.
    """
    if use_browser:
        result = _fetch_browser(url)
        if result.ok:
            return result
        logger.info("Browser fetch failed for %s, trying HTTP: %s", url, result.error)

    last_error = ""
    clients: list[tuple[str, object]] = [("requests", requests)]
    if use_cloudscraper:
        clients.append(("cloudscraper", cloudscraper.create_scraper()))

    for attempt in range(retries + 1):
        client_name, client = clients[min(attempt, len(clients) - 1)]
        try:
            response = client.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            if response.status_code == 200:
                response.encoding = response.apparent_encoding or "utf-8"
                html = response.text
                if not _looks_blocked(html):
                    return FetchResult(
                        url, html, response.status_code, method=client_name
                    )
                last_error = f"Blocked/challenge page via {client_name}"
            else:
                last_error = f"HTTP {response.status_code} via {client_name}"
            if response.status_code in {403, 503} and attempt < retries:
                continue
        except requests.RequestException as exc:
            last_error = f"{client_name}: {exc}"
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))

    if browser_fallback or use_browser:
        logger.info("HTTP failed for %s (%s), trying Playwright...", url, last_error)
        browser_result = _fetch_browser(url)
        if browser_result.ok:
            return browser_result
        last_error = browser_result.error or last_error

    logger.warning("Failed to fetch %s: %s", url, last_error)
    return FetchResult(url, status_code=None, error=last_error)


def _fetch_browser(url: str) -> FetchResult:
    from scraper.browser import fetch_with_browser

    html, status, error = fetch_with_browser(url)
    if error:
        return FetchResult(url, html=html, status_code=status, error=error, method="playwright")
    return FetchResult(url, html, status or 200, method="playwright")


def _looks_blocked(html: str) -> bool:
    lower = html.lower()
    if len(html) < 5000 and any(
        m in lower
        for m in ("just a moment", "checking your browser", "cf-browser-verification")
    ):
        return True
    if "request rejected" in lower and len(html) < 2000:
        return True
    return False
