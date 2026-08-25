"""Clean and deduplicate raw scraped records before normalization."""

from __future__ import annotations

from scraper.cleaning import dedupe_records, normalize_record_types, sort_records
from scraper.models import RequirementRecord


def clean_records(records: list[RequirementRecord]) -> list[RequirementRecord]:
    return sort_records(normalize_record_types(dedupe_records(records)))
