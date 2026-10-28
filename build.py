#!/usr/bin/env python3
"""End-to-end pipeline: scrape official sources → raw → cleaned → normalized final CSVs."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from processing.build_dataset import build_normalized_dataset, load_raw_records, write_dataset_csvs
from processing.clean_data import clean_records
from processing.validate_data import print_validation_report
from scrape import run_scrapers
from scraper.csv_writer import write_csv
from scraper.registry import ALL_AGENCY_KEYS

RAW_DIR = Path("data/raw")
CLEANED_DIR = Path("data/cleaned")
FINAL_DIR = Path("data/final")
OUTPUT_DIR = Path("output")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build PH government research dataset pipeline.")
    parser.add_argument(
        "-a",
        "--agencies",
        nargs="*",
        choices=ALL_AGENCY_KEYS,
        help="Agencies to scrape (default: all)",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Skip scraping; build final tables from existing raw CSV",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Use Playwright browser for Cloudflare-protected sites",
    )
    parser.add_argument(
        "--no-browser-fallback",
        action="store_true",
        help="Do not fall back to Playwright on HTTP 403",
    )
    parser.add_argument(
        "--skip-mining",
        action="store_true",
        help="Skip association rule mining output",
    )
    parser.add_argument(
        "--skip-offices",
        action="store_true",
        help="Skip Davao office geocoding and image enrichment",
    )
    parser.add_argument(
        "--offices-only",
        action="store_true",
        help="Only run Davao office scrape, geocode, and image download",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from scraper import config

    config.USE_BROWSER = args.browser
    config.BROWSER_FALLBACK = not args.no_browser_fallback

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.offices_only:
        from processing.enrich_offices import run_davao_office_pipeline

        run_davao_office_pipeline(FINAL_DIR / "government_offices.csv")
        return 0

    raw_path = RAW_DIR / "gov_requirements.csv"
    cleaned_path = CLEANED_DIR / "gov_requirements.csv"

    if args.export_only:
        if not raw_path.exists():
            logging.error("No raw file at %s — run without --export-only first", raw_path)
            return 1
        records = load_raw_records(raw_path)
    else:
        agency_keys = args.agencies or ALL_AGENCY_KEYS
        records = run_scrapers(agency_keys)
        write_csv(records, raw_path)
        logging.info("Wrote %d raw records to %s", len(records), raw_path)

    cleaned = clean_records(records if not args.export_only else load_raw_records(raw_path))
    write_csv(cleaned, cleaned_path)
    logging.info("Wrote %d cleaned records to %s", len(cleaned), cleaned_path)

    dataset = build_normalized_dataset(cleaned)
    counts = write_dataset_csvs(dataset, FINAL_DIR)
    ok = print_validation_report(FINAL_DIR, counts)

    if not args.skip_offices:
        from processing.enrich_offices import run_davao_office_pipeline

        merged_offices = run_davao_office_pipeline(FINAL_DIR / "government_offices.csv")
        counts["government_offices.csv"] = len(merged_offices)
        logging.info("Updated government_offices.csv with %d rows (Davao enriched)", len(merged_offices))

    if not args.skip_mining:
        from mining.association_analysis import run_analysis

        mining_path = run_analysis(FINAL_DIR, OUTPUT_DIR)
        logging.info("Wrote association mining output to %s", mining_path)

    if sum(counts.values()) < 500:
        logging.warning(
            "Total normalized records (%d) is below 500 target — "
            "some agencies are blocked; see scrape_status in requirements table.",
            sum(counts.values()),
        )

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
