"""Enrich government offices with geocoding and official images (Davao City first)."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from processing.davao_office_photos import resolve_photo_source
from processing.geocode import geocode_address
from processing.maps_office_photos import verified_office
from processing.office_images import download_office_image
from processing.web_office_images import fetch_exterior_from_web_search, search_pause
from processing.schemas import GOVERNMENT_OFFICES_COLUMNS
from scraper.agencies.davao_offices import DavaoOfficesScraper

logger = logging.getLogger(__name__)

IMAGE_DIR = Path("data/raw/office_images/davao")
RAW_OFFICES_CSV = Path("data/raw/davao_government_offices.csv")


def scrape_davao_offices() -> list[dict]:
    scraper = DavaoOfficesScraper()
    scraper.scrape()
    rows = [office.to_row() for office in scraper.offices()]
    _write_offices_csv(rows, RAW_OFFICES_CSV)
    logger.info("Scraped %d Davao office records to %s", len(rows), RAW_OFFICES_CSV)
    return rows


def _clear_stale_map_images(dest_dir: Path) -> None:
    if not dest_dir.exists():
        return
    for path in dest_dir.glob("*_map.png"):
        path.unlink(missing_ok=True)


def _purge_stale_office_images(keep_ids: set[str]) -> None:
    if not IMAGE_DIR.exists():
        return
    for path in IMAGE_DIR.iterdir():
        if not path.is_file():
            continue
        if path.stem not in keep_ids:
            path.unlink(missing_ok=True)


def enrich_office_rows(rows: list[dict], *, download_images: bool = True) -> list[dict]:
    if download_images:
        _clear_stale_map_images(IMAGE_DIR)

    enriched: list[dict] = []
    for row in rows:
        row = dict(row)
        row["office_image_url"] = ""
        row["office_image_path"] = ""
        row["office_image_source"] = ""

        verified = verified_office(row.get("office_id", ""))
        if verified:
            row["latitude"] = verified["latitude"]
            row["longitude"] = verified["longitude"]
            row["geocode_source"] = "Google Maps"
            row["geocode_status"] = "success"
            if download_images:
                row["office_image_url"] = verified["maps_url"]
                row["office_image_path"] = verified["image_path"]
                row["office_image_source"] = verified["image_kind"]
            if not row.get("region") and row.get("city") == "Davao City":
                row["region"] = "Region XI (Davao Region)"
                row["province"] = row.get("province") or "Davao del Sur"
            enriched.append(row)
            continue

        if not row.get("latitude") or row.get("geocode_status") in ("", "failed"):
            geo = geocode_address(
                row.get("address", ""),
                city=row.get("city", "Davao City"),
                region=row.get("region", "Davao Region"),
            )
            row["latitude"] = geo.get("latitude", "")
            row["longitude"] = geo.get("longitude", "")
            row["geocode_source"] = geo.get("geocode_source", "")
            row["geocode_status"] = geo.get("geocode_status", "")

        if download_images:
            photo = resolve_photo_source(row)
            if photo and photo.get("image_url"):
                row["office_image_url"] = photo["image_url"]
                row["office_image_path"] = download_office_image(
                    photo["image_url"],
                    IMAGE_DIR,
                    row.get("office_id", "office"),
                )
                if row["office_image_path"]:
                    row["office_image_source"] = "official_gov_ph"
                else:
                    row["office_image_url"] = ""

            if not row.get("office_image_path"):
                search_pause()
                path, image_url, web_source = fetch_exterior_from_web_search(
                    row,
                    IMAGE_DIR,
                    row.get("office_id", "office"),
                )
                if path:
                    row["office_image_path"] = path
                    row["office_image_url"] = image_url
                    row["office_image_source"] = web_source

        if not row.get("region") and row.get("city") == "Davao City":
            row["region"] = "Region XI (Davao Region)"
            row["province"] = row.get("province") or "Davao del Sur"

        enriched.append(row)

    if download_images:
        keep_ids = {r["office_id"] for r in enriched if r.get("office_image_path")}
        _purge_stale_office_images(keep_ids)

    return enriched


def merge_office_tables(
    existing: list[dict],
    davao_enriched: list[dict],
) -> list[dict]:
    """Replace generic/non-Davao rows with enriched Davao offices; keep others."""
    davao_keys = {
        (r.get("agency_acronym", ""), r.get("office_name", "").lower())
        for r in davao_enriched
    }
    kept = [
        row for row in existing
        if row.get("city") != "Davao City"
        and (row.get("agency_acronym", ""), row.get("office_name", "").lower()) not in davao_keys
        and "davao" not in (row.get("address") or "").lower()
    ]
    merged = kept + davao_enriched
    merged.sort(key=lambda r: (r.get("city", ""), r.get("agency_acronym", ""), r.get("office_name", "")))
    return merged


def load_offices_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_offices_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=GOVERNMENT_OFFICES_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_davao_office_pipeline(final_offices_path: Path) -> list[dict]:
    davao_rows = scrape_davao_offices()
    davao_enriched = enrich_office_rows(davao_rows)
    existing = load_offices_csv(final_offices_path)
    merged = merge_office_tables(existing, davao_enriched)
    write_offices_csv(merged, final_offices_path)
    write_offices_csv(davao_enriched, Path("data/final/davao_government_offices.csv"))
    _update_davao_service_locations(Path("data/final/service_locations.csv"), davao_enriched)
    geocoded = sum(1 for r in davao_enriched if r.get("geocode_status") == "success")
    imaged = sum(1 for r in davao_enriched if r.get("office_image_path"))
    logger.info(
        "Davao offices: %d total, %d geocoded, %d with exterior photos "
        "(%d official, %d web curated, %d web search)",
        len(davao_enriched),
        geocoded,
        imaged,
        sum(1 for r in davao_enriched if r.get("office_image_source") == "official_gov_ph"),
        sum(1 for r in davao_enriched if r.get("office_image_source") == "web_search_curated"),
        sum(1 for r in davao_enriched if r.get("office_image_source") == "web_search_bing"),
    )
    return merged


def _update_davao_service_locations(path: Path, davao_offices: list[dict]) -> None:
    """Link Davao-relevant services to Davao office rows."""
    from processing.id_utils import make_service_location_id

    services_path = Path("data/final/government_services.csv")
    if not services_path.exists():
        return

    with services_path.open(encoding="utf-8") as handle:
        services = list(csv.DictReader(handle))

    existing: list[dict] = []
    if path.exists():
        with path.open(encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))

    existing_keys = {(r.get("service_id"), r.get("office_id")) for r in existing}
    new_rows = [r for r in existing if "Davao City" not in (r.get("source_url") or "")]

    for office in davao_offices:
        acronym = office.get("agency_acronym", "")
        for service in services:
            if service.get("agency_acronym") != acronym and not (
                acronym == "PHILSYS" and service.get("agency_acronym") == "PHILSYS"
            ):
                continue
            if service.get("city") == "Davao City":
                continue
            key = (service.get("service_id"), office.get("office_id"))
            if key in existing_keys:
                continue
            new_rows.append({
                "service_location_id": make_service_location_id(
                    service.get("service_id", ""), office.get("office_id", "")
                ),
                "service_id": service.get("service_id", ""),
                "office_id": office.get("office_id", ""),
                "service_available": "yes",
                "application_method": service.get("application_method", ""),
                "appointment_required": service.get("appointment_required", ""),
                "processing_time": service.get("processing_time", ""),
                "fee": service.get("fee", ""),
                "source_url": office.get("source_url", ""),
                "last_verified": office.get("last_verified", ""),
            })

    from processing.schemas import SERVICE_LOCATIONS_COLUMNS

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SERVICE_LOCATIONS_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(new_rows)


def _write_offices_csv(rows: list[dict], path: Path) -> None:
    write_offices_csv(rows, path)
