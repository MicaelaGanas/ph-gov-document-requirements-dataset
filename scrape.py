#!/usr/bin/env python3
"""Scrape Philippine government service requirements into CSV."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from scraper.cleaning import dedupe_records, normalize_record_types, sort_records
from scraper.csv_writer import write_csv
from scraper.models import RequirementRecord
from scraper.registry import ALL_AGENCY_KEYS, SCRAPER_REGISTRY

DEFAULT_OUTPUT = Path("data/gov_requirements.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract PH government service requirements from official websites."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "-a",
        "--agencies",
        nargs="*",
        choices=ALL_AGENCY_KEYS,
        help="Agencies to scrape (default: all)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Use Playwright browser for Cloudflare-protected sites (PSA, LTO, DFA consular)",
    )
    parser.add_argument(
        "--no-browser-fallback",
        action="store_true",
        help="Do not fall back to Playwright when HTTP requests return 403",
    )
    return parser.parse_args()


def run_scrapers(agency_keys: list[str]) -> list[RequirementRecord]:
    all_records: list[RequirementRecord] = []
    for key in agency_keys:
        scraper_cls = SCRAPER_REGISTRY[key]
        scraper = scraper_cls()
        logging.info("Scraping %s (%s)...", scraper.agency, key)
        try:
            records = scraper.scrape()
            logging.info("  -> %d records", len(records))
            all_records.extend(records)
        except Exception:
            logging.exception("Scraper failed for %s", key)
    return all_records


def main() -> int:
    args = parse_args()
    from scraper import config

    config.USE_BROWSER = args.browser
    config.BROWSER_FALLBACK = not args.no_browser_fallback

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    agency_keys = args.agencies or ALL_AGENCY_KEYS
    records = sort_records(normalize_record_types(dedupe_records(run_scrapers(agency_keys))))
    count = write_csv(records, args.output)

    success = sum(1 for r in records if r.scrape_status == "success")
    seed = sum(1 for r in records if r.scrape_status == "seed")
    blocked = sum(1 for r in records if r.scrape_status == "blocked")
    partial = sum(1 for r in records if r.scrape_status == "partial")
    roles = {}
    for r in records:
        roles[r.requirement_role] = roles.get(r.requirement_role, 0) + 1

    print(f"Wrote {count} records to {args.output}")
    print(
        f"Status breakdown: success={success}, partial={partial}, "
        f"seed={seed}, blocked={blocked}"
    )
    print(f"Role breakdown: {roles}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
