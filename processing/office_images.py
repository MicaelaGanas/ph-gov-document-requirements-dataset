"""Download official office images for research dataset."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def download_office_image(
    image_url: str,
    dest_dir: Path,
    office_id: str,
) -> str:
    """Download image; return relative path from repo root or empty string."""
    if not image_url:
        return ""

    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = _extension_from_url(image_url)
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", office_id)[:80]
    dest_path = dest_dir / f"{safe_id}{ext}"

    if dest_path.exists() and dest_path.stat().st_size > 0:
        return _relative_path(dest_path)

    dest_path.unlink(missing_ok=True)

    try:
        response = requests.get(
            image_url,
            timeout=45,
            headers={"User-Agent": "ph-gov-document-requirements-dataset/1.0"},
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type and not image_url.lower().endswith(IMAGE_EXTENSIONS):
            logger.warning("Skipping non-image URL: %s (%s)", image_url, content_type)
            return ""
        dest_path.write_bytes(response.content)
        return _relative_path(dest_path)
    except Exception as exc:
        logger.warning("Image download failed for %s: %s", image_url, exc)

    return _download_image_playwright(image_url, dest_dir, safe_id, ext)


def _download_image_playwright(
    image_url: str, dest_dir: Path, safe_id: str, ext: str
) -> str:
    try:
        from scraper.browser import fetch_with_playwright_bytes

        content = fetch_with_playwright_bytes(image_url)
        if not content:
            return ""
        dest_path = dest_dir / f"{safe_id}{ext}"
        dest_path.write_bytes(content)
        return _relative_path(dest_path)
    except Exception as exc:
        logger.warning("Playwright image download failed for %s: %s", image_url, exc)
        return ""


def capture_official_page_photo(
    page_url: str,
    dest_dir: Path,
    office_id: str,
    *,
    image_src_contains: str = "",
    min_width: int = 150,
) -> tuple[str, str]:
    """Screenshot a building/facility photo from an official .gov.ph page."""
    if not page_url:
        return "", ""

    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", office_id)[:80]
    dest_path = dest_dir / f"{safe_id}.jpg"

    if dest_path.exists() and dest_path.stat().st_size > 5000:
        return _relative_path(dest_path), ""

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright not installed; cannot capture photo from %s", page_url)
        return "", ""

    skip_tokens = (
        "logo", "icon", "banner", "footer", "header", "avatar", "sprite",
        "seal", "transparency", "pilipinas", "bagong", "govph", "hashtag",
        "fb.png", "tw.png", "cookie", "error.jpg",
    )

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                ),
                locale="en-PH",
            )

            chosen_src = ""
            for attempt in range(3):
                page.goto(page_url, wait_until="load", timeout=120000)
                page.wait_for_timeout(6000 + attempt * 2000)
                if "403" in page.title() or "forbidden" in page.title().lower():
                    continue

                for img in page.locator("img").all():
                    src = img.get_attribute("src") or ""
                    if not src or src.startswith("data:"):
                        continue
                    lower = src.lower()
                    if any(token in lower for token in skip_tokens):
                        continue
                    if image_src_contains and image_src_contains.lower() not in lower:
                        continue
                    box = img.bounding_box()
                    if not box or box["width"] < min_width or box["height"] < min_width * 0.4:
                        continue
                    img.screenshot(path=str(dest_path))
                    chosen_src = src
                    break

                if dest_path.exists() and dest_path.stat().st_size > 5000:
                    break

            browser.close()

        if dest_path.exists() and dest_path.stat().st_size > 5000:
            return _relative_path(dest_path), chosen_src
    except Exception as exc:
        logger.warning("Page photo capture failed for %s: %s", page_url, exc)

    return "", ""


def pick_largest_content_image(html: str, page_url: str) -> str:
    """Pick the most likely office/building photo from an official page."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    candidates: list[tuple[int, str]] = []

    skip_tokens = (
        "logo", "icon", "banner", "footer", "header", "avatar", "sprite", "npc",
        "seal", "transparency", "pilipinas", "bagong", "govph", "hashtag",
        "fb.png", "tw.png", "application-pdf", "file_field_icons",
    )

    for img in soup.find_all("img"):
        src = (img.get("src") or img.get("data-src") or "").strip()
        if not src or src.startswith("data:"):
            continue
        absolute = urljoin(page_url, src)
        lower = absolute.lower()
        if any(t in lower for t in skip_tokens):
            continue
        if not lower.endswith(IMAGE_EXTENSIONS) and "upload" not in lower:
            continue
        width = _parse_int(img.get("width"))
        height = _parse_int(img.get("height"))
        if width and height and (width < 120 or height < 120):
            continue
        score = (width or 0) * (height or 0)
        if score == 0:
            score = len(absolute)
        candidates.append((score, absolute))

    if not candidates:
        return ""
    candidates.sort(reverse=True)
    return candidates[0][1]


def _extension_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    for ext in IMAGE_EXTENSIONS:
        if path.endswith(ext):
            return ext
    return ".jpg"


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(re.sub(r"[^\d]", "", str(value)))
    except ValueError:
        return None


def _relative_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()
