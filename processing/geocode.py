"""Geocode Philippine government office addresses via OpenStreetMap Nominatim."""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

# Alternate queries when the full official address fails Nominatim lookup.
ADDRESS_FALLBACKS: dict[str, str] = {
    "sangguniang panlungsod": "Sangguniang Panlungsod Building, San Pedro Street, Davao City, Philippines",
    "lto mvis compound": "Felcris Centrale, Quimpo Boulevard, Davao City, Philippines",
    "sss building, palma gil": "Palma Gil Street, Davao City, Philippines",
    "161 j.p. cabaguio": "Ango Building, J.P. Cabaguio Avenue, Davao City, Philippines",
    "ground floor, ango building": "Ango Building, J.P. Cabaguio Avenue, Davao City, Philippines",
    "ango building": "Ango Building, J.P. Cabaguio Avenue, Davao City, Philippines",
    "sm city davao": "SM City Davao, Ecoland Drive, Davao City, Philippines",
}


def _fallback_query(address: str) -> str | None:
    lower = address.lower()
    for key, fallback_query in ADDRESS_FALLBACKS.items():
        if key in lower:
            return fallback_query
    return None


def geocode_address(
    address: str,
    *,
    city: str = "Davao City",
    region: str = "Davao Region",
    country: str = "Philippines",
) -> dict[str, str]:
    """Return lat/lon dict or empty strings if geocoding fails."""
    fallback = _fallback_query(address)
    if fallback:
        result = _nominatim_search(fallback)
        if result:
            return _success_result(result, "OpenStreetMap Nominatim (building-specific)")

    query = ", ".join(p for p in (address, city, region, country) if p)
    result = _nominatim_search(query)
    if result:
        return _success_result(result, "OpenStreetMap Nominatim")

    # Retry with simplified query (street + city only).
    short = ", ".join(p for p in (address.split(",")[0], city, country) if p)
    if short != query:
        result = _nominatim_search(short)
        if result:
            return _success_result(result, "OpenStreetMap Nominatim (simplified query)")

    logger.warning("Geocoding failed for: %s", address)
    return {
        "latitude": "",
        "longitude": "",
        "geocode_source": "OpenStreetMap Nominatim",
        "geocode_status": "failed",
        "display_name": "",
    }


def _success_result(result: dict, source: str) -> dict[str, str]:
    return {
        "latitude": result.get("lat", ""),
        "longitude": result.get("lon", ""),
        "geocode_source": source,
        "geocode_status": "success",
        "display_name": result.get("display_name", ""),
    }


def _nominatim_search(query: str) -> dict | None:
    global _LAST_REQUEST_AT
    elapsed = time.time() - _LAST_REQUEST_AT
    if elapsed < _MIN_INTERVAL_SEC:
        time.sleep(_MIN_INTERVAL_SEC - elapsed)

    params = urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": "1", "countrycodes": "ph"}
    )
    url = f"{NOMINATIM_URL}?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        _LAST_REQUEST_AT = time.time()
        if data:
            return data[0]
    except Exception as exc:
        logger.warning("Nominatim error for %s: %s", query, exc)
        _LAST_REQUEST_AT = time.time()
    return None


USER_AGENT = "ph-gov-document-requirements-dataset/1.0 (academic research; contact: dataset maintainer)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_LAST_REQUEST_AT = 0.0
_MIN_INTERVAL_SEC = 1.1
