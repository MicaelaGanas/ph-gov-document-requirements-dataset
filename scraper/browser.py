"""Playwright-based fetch for Cloudflare/WAF-protected government sites."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import so the scraper still runs without Playwright installed.
_playwright_available: Optional[bool] = None


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


def fetch_with_browser(
    url: str,
    *,
    timeout_ms: int = 45000,
    wait_selector: str = "body",
) -> tuple[str, int | None, str]:
    """
    Load a page in headless Chromium and return (html, status_code, error).

    Returns empty html and an error string on failure.
    """
    if not playwright_installed():
        return "", None, "Playwright not installed (pip install playwright && playwright install chromium)"

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

            # Wait for Cloudflare challenge to finish (if present).
            for _ in range(6):
                title = page.title().lower()
                html_snippet = page.content()[:5000].lower()
                if "just a moment" not in title and "checking your browser" not in html_snippet:
                    break
                page.wait_for_timeout(3000)

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

            if status and status >= 400 and _is_challenge_page(html):
                return html, status, f"HTTP {status} via playwright (Cloudflare blocked)"
            if status and status >= 400:
                return html, status, f"HTTP {status} via playwright"
            if _is_challenge_page(html):
                return html, status, "Cloudflare/bot challenge page still showing"
            if len(html) < 3000:
                return html, status, "Page content too short after browser load"

            return html, status or 200, ""
    except Exception as exc:
        logger.warning("Playwright fetch failed for %s: %s", url, exc)
        return "", None, f"playwright: {exc}"


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
