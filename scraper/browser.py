"""Playwright-based fetch for Cloudflare/WAF-protected government sites."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Lazy import so the scraper still runs without Playwright installed.
_playwright_available: Optional[bool] = None
_active_session: Optional["BrowserSession"] = None


def playwright_installed() -> bool:
    global _playwright_available
    if _playwright_available is not None:
        return _playwright_available
    try:
        import playwright  # noqa: F401

        _playwright_available = True
    except ImportError:
        _playwright_available = False
    return _playwright_available


class BrowserSession:
    """Reuse one Chromium instance across many URLs (much faster than per-URL launch)."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._context = None

    def start(self) -> None:
        if not playwright_installed():
            raise RuntimeError(
                "Playwright not installed (pip install playwright && playwright install chromium)"
            )
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1280, "height": 720},
        )

    def close(self) -> None:
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def fetch(
        self,
        url: str,
        *,
        timeout_ms: int = 45000,
        wait_selector: str = "body",
        wait_until: str = "domcontentloaded",
        spa: bool = False,
    ) -> tuple[str, int | None, str]:
        if not self._context:
            raise RuntimeError("BrowserSession not started")
        page = self._context.new_page()
        try:
            response = page.goto(url, wait_until=wait_until, timeout=timeout_ms)

            for _ in range(8 if spa else 6):
                title = page.title().lower()
                html_snippet = page.content()[:5000].lower()
                if "just a moment" not in title and "checking your browser" not in html_snippet:
                    break
                page.wait_for_timeout(3000)

            if spa:
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                page.wait_for_timeout(2000)

            for selector in (wait_selector, "article", "main", ".entry-content", "#main-content"):
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    break
                except Exception:
                    continue
            page.wait_for_timeout(1500)

            html = page.content()
            status = response.status if response else None
            return _validate_browser_html(html, status)
        except Exception as exc:
            logger.warning("Playwright fetch failed for %s: %s", url, exc)
            return "", None, f"playwright: {exc}"
        finally:
            page.close()


@contextmanager
def browser_session_scope() -> Iterator[BrowserSession]:
    """Open a shared browser for the duration of a scrape run."""
    global _active_session
    session = BrowserSession()
    session.start()
    _active_session = session
    try:
        yield session
    finally:
        session.close()
        _active_session = None


def _validate_browser_html(html: str, status: int | None) -> tuple[str, int | None, str]:
    if status and status >= 400 and _is_challenge_page(html):
        return html, status, f"HTTP {status} via playwright (Cloudflare blocked)"
    if status and status >= 400:
        return html, status, f"HTTP {status} via playwright"
    if _is_challenge_page(html):
        return html, status, "Cloudflare/bot challenge page still showing"
    if len(html) < 3000:
        return html, status, "Page content too short after browser load"
    return html, status or 200, ""


def fetch_with_browser(
    url: str,
    *,
    timeout_ms: int = 45000,
    wait_selector: str = "body",
    spa: bool = False,
) -> tuple[str, int | None, str]:
    """
    Load a page in headless Chromium and return (html, status_code, error).

    Returns empty html and an error string on failure.
    """
    if not playwright_installed():
        return "", None, "Playwright not installed (pip install playwright && playwright install chromium)"

    if _active_session is not None:
        return _active_session.fetch(
            url,
            timeout_ms=timeout_ms,
            wait_selector=wait_selector,
            spa=spa,
        )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return "", None, f"Playwright import failed: {exc}"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                viewport={"width": 1280, "height": 720},
            )
            page = context.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            for _ in range(6):
                title = page.title().lower()
                html_snippet = page.content()[:5000].lower()
                if "just a moment" not in title and "checking your browser" not in html_snippet:
                    break
                page.wait_for_timeout(3000)

            if spa:
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                page.wait_for_timeout(2000)

            for selector in (wait_selector, "article", "main", ".entry-content", "#main-content"):
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    break
                except Exception:
                    continue
            page.wait_for_timeout(1500)

            html = page.content()
            status = response.status if response else None
            browser.close()
            return _validate_browser_html(html, status)
    except Exception as exc:
        logger.warning("Playwright fetch failed for %s: %s", url, exc)
        return "", None, f"playwright: {exc}"


def host_needs_browser_first(url: str) -> bool:
    from scraper import config

    host = (urlparse(url).hostname or "").lower()
    return host in config.BROWSER_FIRST_HOSTS


def _is_challenge_page(html: str) -> bool:
    lower = html.lower()
    markers = (
        "just a moment",
        "checking your browser",
        "cf-browser-verification",
        "enable javascript and cookies",
        "attention required",
        "ray id",
    )
    return any(m in lower for m in markers) and len(html) < 25000


def fetch_with_playwright_bytes(url: str, *, timeout_ms: int = 45000) -> bytes:
    """Download binary content (e.g. official office photo) via Playwright."""
    if not playwright_installed():
        return b""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return b""

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            response = context.request.get(url, timeout=timeout_ms)
            browser.close()
            if response.ok:
                return response.body()
    except Exception as exc:
        logger.warning("Playwright byte fetch failed for %s: %s", url, exc)
    return b""
