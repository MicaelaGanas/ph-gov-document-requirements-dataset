"""Post-scrape cleaning and deduplication."""

from __future__ import annotations

from scraper.models import RequirementRecord
from scraper.parsers.requirements import dedupe_key, infer_requirement_type_from_role, normalize_key


def normalize_record_types(records: list[RequirementRecord]) -> list[RequirementRecord]:
    """Ensure requirement_type always matches requirement_role."""
    for record in records:
        record.requirement_type = infer_requirement_type_from_role(record.requirement_role)
    return records


def dedupe_records(records: list[RequirementRecord]) -> list[RequirementRecord]:
    """Remove duplicate requirements while preserving the best record per key."""
    best: dict[str, RequirementRecord] = {}
    priority = {"success": 3, "partial": 2, "seed": 1, "blocked": 0}

    for record in records:
        key = dedupe_key(
            record.agency_code,
            record.service_name,
            record.requirement_role,
            record.requirement_name,
            conditional=record.conditional,
            condition=record.condition,
            source_section=record.source_section,
        )
        existing = best.get(key)
        if existing is None:
            best[key] = record
            continue
        if priority.get(record.scrape_status, 0) > priority.get(existing.scrape_status, 0):
            best[key] = record
            continue
        if len(record.requirement_description) > len(existing.requirement_description):
            best[key] = record

    return list(best.values())


def sort_records(records: list[RequirementRecord]) -> list[RequirementRecord]:
    role_order = {
        "required_document": 0,
        "acceptable_id": 1,
        "supporting_document": 2,
        "procedure": 3,
        "fee": 4,
        "processing_time": 5,
        "eligibility": 6,
        "metadata": 7,
    }
    return sorted(
        records,
        key=lambda r: (
            r.agency_code,
            normalize_key(r.service_name),
            role_order.get(r.requirement_role, 99),
            r.requirement_order or 9999,
            normalize_key(r.requirement_name),
        ),
    )
