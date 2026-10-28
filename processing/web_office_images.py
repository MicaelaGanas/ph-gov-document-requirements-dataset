"""Find exterior building photos via web image search (Bing) for Davao offices."""

from __future__ import annotations

import html
import logging
import re
import time
import urllib.parse
from pathlib import Path

import requests

from processing.office_images import download_office_image

logger = logging.getLogger(__name__)

# Tailored queries improve exterior building hits vs generic office names.
_SEARCH_QUERIES: tuple[tuple[dict[str, str], str], ...] = (
    ({"agency_acronym": "PSA"}, "Ango Building Cabaguio Avenue Davao City Philippines building exterior"),
    ({"agency_acronym": "PHILSYS", "name_contains": "Ango"}, "Ango Building J.P. Cabaguio Avenue Davao City building"),
    ({"agency_acronym": "PHILSYS", "name_contains": "JM Agro"}, "JM Agro Building Governor Sales Davao City building"),
    ({"agency_acronym": "PHILSYS", "name_contains": "SM City"}, "SM City Davao Ecoland building exterior"),
    ({"agency_acronym": "LTO"}, "LTO Region 11 Quimpo Boulevard Davao City building exterior"),
    ({"agency_acronym": "SSS"}, "SSS Building J.P. Laurel Bajada Davao City Philippines exterior"),
    ({"agency_acronym": "NBI", "name_contains": "GAISANO"}, "Gaisano Mall Davao JP Laurel Bajada building exterior"),
    ({"agency_acronym": "NBI"}, "NBI office J.P. Laurel Avenue Davao City building exterior"),
    ({"agency_acronym": "LGU-DAVAO"}, "Sangguniang Panlungsod Building San Pedro Davao City building"),
    ({"agency_acronym": "COMELEC"}, "Sangguniang Panlungsod Building San Pedro Davao City building"),
)

# Curated exterior photos (verified manually) — tried before Bing search.
_CURATED_EXTERIOR: dict[str, dict[str, str]] = {
    "PSA-OFF-C96C1839": {
        "image_url": (
            "https://kirbysoutheastasia.com/wp-content/uploads/2021/03/"
            "dji_export_1637290384713-scaled.jpg"
        ),
        "source_url": "https://kirbysoutheastasia.com/",
    },
    "LTO-OFF-6BA7E79C": {
        "image_url": "https://davaotoday.com/wp-content/uploads/2017/09/LTO-DAVAO-REGION.jpg",
        "source_url": "https://davaotoday.com/",
    },
    "PHILSYS-OFF-C3D46FBA": {
        "image_url": "https://files01.pna.gov.ph/ograph/2022/01/02/philsys-davao.jpg",
        "source_url": "https://www.pna.gov.ph/",
    },
    "PHILSYS-OFF-CB3C9B90": {
        "image_url": "https://htrealty.ph/wp-content/uploads/2023/06/11-3-1170x785.jpg",
        "source_url": "https://htrealty.ph/",
    },
}

_SKIP_URL_TOKENS = (
    "logo", "icon", "avatar", "sprite", "seal", "map", "maps.google", "streetview",
    "pin", "emoji", "banner", "transparent", "favicon", "wikimedia.org/wiki",
    "shutterstock", "getty", "alamy", "dreamstime", "istockphoto",
    "ytimg.com/vi/", "maxresdefault", "i.ytimg.com",
    "national-bureau-of-investigation", "nbi-davao.png",
    "weebly.com", "ltoportal", "apply-job", "assumption-college", "aeon",
    "job", "hiring", "recruitment", "/nbi.png", "inquirer.net/files",
)

_MIN_IMAGE_BYTES = 12_000
_BING_SEARCH_URL = "https://www.bing.com/images/search?q={query}&qft=+filterui:photo-photo"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)


def build_web_search_query(office: dict) -> str:
    acronym = office.get("agency_acronym", "")
    name = office.get("office_name", "").lower()
    for match, query in _SEARCH_QUERIES:
        if match.get("agency_acronym") and match["agency_acronym"] != acronym:
            continue
        needle = match.get("name_contains", "").lower()
        if needle and needle not in name:
            continue
        return query

    address = (office.get("address") or "").split(",")[0].strip()
    office_name = office.get("office_name", "").strip()
    parts = [p for p in (office_name, address, "Davao City", "Philippines", "building exterior") if p]
    return " ".join(parts)


def fetch_exterior_from_web_search(
    office: dict,
    dest_dir: Path,
    office_id: str,
) -> tuple[str, str, str]:
    """Search the web for an exterior photo. Returns (path, image_url, source)."""
    curated = _CURATED_EXTERIOR.get(office_id)
    if curated:
        path = _download_candidate(curated["image_url"], dest_dir, office_id)
        if path:
            return path, curated["image_url"], "web_search_curated"

    query = build_web_search_query(office)
    urls = _bing_image_urls(query)
    if not urls:
        logger.warning("No web image results for %s (%s)", office_id, query)
        return "", "", ""

    for image_url in urls:
        if _should_skip_url(image_url):
            continue
        path = _download_candidate(image_url, dest_dir, office_id)
        if path:
            logger.info("Web image for %s from %s", office_id, image_url[:80])
            return path, image_url, "web_search_bing"

    return "", "", ""


def _download_candidate(image_url: str, dest_dir: Path, office_id: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", office_id)[:80]
    for existing in dest_dir.glob(f"{safe_id}.*"):
        existing.unlink(missing_ok=True)
    local_path = download_office_image(image_url, dest_dir, office_id)
    if not local_path:
        return ""
    full_path = Path(local_path)
    if not full_path.is_absolute():
        full_path = Path.cwd() / local_path
    if full_path.exists() and full_path.stat().st_size >= _MIN_IMAGE_BYTES:
        return local_path
    full_path.unlink(missing_ok=True)
    return ""


def _bing_image_urls(query: str, *, max_results: int = 12) -> list[str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright not installed; web image search skipped")
        return []

    encoded = urllib.parse.quote(query)
    url = _BING_SEARCH_URL.format(query=encoded)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(user_agent=_USER_AGENT)
            page.goto(url, timeout=90000)
            page.wait_for_timeout(4000)
            content = page.content()
            browser.close()
    except Exception as exc:
        logger.warning("Bing image search failed for %r: %s", query, exc)
        return []

    patterns = (
        r'murl&quot;:&quot;(https?://[^&]+?)&quot;',
        r'"murl":"(https?://[^"]+)"',
    )
    seen: set[str] = set()
    results: list[str] = []
    for pattern in patterns:
        for match in re.findall(pattern, content):
            decoded = html.unescape(match)
            if decoded in seen:
                continue
            seen.add(decoded)
            results.append(decoded)
            if len(results) >= max_results:
                return results
    return results


def _should_skip_url(url: str) -> bool:
    lower = url.lower()
    return any(token in lower for token in _SKIP_URL_TOKENS)


def search_pause() -> None:
    """Polite delay between Bing searches."""
    time.sleep(2.0)
