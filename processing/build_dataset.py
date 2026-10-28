"""Build normalized research CSVs from raw scraped requirement records."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from processing.id_utils import (
    infer_office_type,
    make_dependency_id,
    make_office_id,
    make_requirement_id,
    make_service_id,
    make_service_location_id,
)
from processing.normalize_documents import normalize_agency_acronym, normalize_document_name, source_title_from_url
from processing.requirement_preparation import (
    canonicalize_document,
    is_conditional_instruction,
    is_procedure,
    prepare_required_row,
)
from processing.schemas import (
    DOCUMENT_DEPENDENCIES_COLUMNS,
    GOVERNMENT_OFFICES_COLUMNS,
    GOVERNMENT_SERVICES_COLUMNS,
    REQUIREMENTS_COLUMNS,
    SERVICE_LOCATIONS_COLUMNS,
)
from scraper.models import RequirementRecord


@dataclass
class NormalizedDataset:
    services: list[dict[str, Any]] = field(default_factory=list)
    requirements: list[dict[str, Any]] = field(default_factory=list)
    offices: list[dict[str, Any]] = field(default_factory=list)
    service_locations: list[dict[str, Any]] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)


def build_normalized_dataset(records: Iterable[RequirementRecord]) -> NormalizedDataset:
    records = list(records)
    dataset = NormalizedDataset()

    service_map: dict[tuple[str, str], dict[str, Any]] = {}
    service_req_counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    office_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    service_location_seen: set[str] = set()
    dependency_seen: set[str] = set()

    for record in records:
        acronym = normalize_agency_acronym(record.agency, record.agency_code)
        service_key = (acronym, record.service_name)
        service_id = make_service_id(acronym, record.service_name)

        if service_key not in service_map:
            service_map[service_key] = {
                "service_id": service_id,
                "agency": record.agency,
                "agency_acronym": acronym,
                "service_name": record.service_name,
                "target_document": record.target_document,
                "transaction_type": record.transaction_type,
                "applicant_type": record.applicant_type,
                "application_method": record.application_method,
                "appointment_required": record.appointment_required,
                "processing_time": _best_value(record.processing_time),
                "fee": _best_value(record.fee),
                "source_url": record.source_url,
                "source_title": source_title_from_url(record.source_url),
                "last_verified": record.last_verified,
                "scrape_status": record.scrape_status,
                "record_count": 0,
            }
        else:
            svc = service_map[service_key]
            svc["processing_time"] = svc["processing_time"] or _best_value(record.processing_time)
            svc["fee"] = svc["fee"] or _best_value(record.fee)
            svc["application_method"] = svc["application_method"] or record.application_method
            if _STATUS_RANK.get(record.scrape_status, 0) > _STATUS_RANK.get(svc["scrape_status"], 0):
                svc["scrape_status"] = record.scrape_status
            svc["source_url"] = record.source_url or svc["source_url"]
            svc["source_title"] = source_title_from_url(svc["source_url"])
            svc["last_verified"] = max(svc["last_verified"], record.last_verified)

        service_req_counts[service_key] += 1

        if record.requirement_role == "required_document" and is_procedure(record.requirement_name):
            record.requirement_role = "procedure"
            record.requirement_type = "procedure"
        elif record.requirement_role == "required_document" and is_conditional_instruction(record.requirement_name):
            record.conditional = "yes"
            if not record.condition:
                record.condition = "Required only in the situation named in the row, not for every application."

        req_id = record.record_id or make_requirement_id(
            service_id,
            record.requirement_name,
            record.requirement_role,
            record.requirement_order,
        )
        dataset.requirements.append(
            {
                "requirement_id": req_id,
                "service_id": service_id,
                "requirement_name": record.requirement_name,
                "requirement_name_normalized": normalize_document_name(record.requirement_name),
                "requirement_type": record.requirement_type,
                "requirement_role": record.requirement_role,
                "conditional": record.conditional,
                "condition": record.condition,
                "issuing_agency": record.issuing_agency,
                "document_format": record.document_format,
                "quantity": record.quantity,
                "source_url": record.source_url,
                "source_title": source_title_from_url(record.source_url),
                "source_section": record.source_section,
                "requirement_order": record.requirement_order or "",
                "requirement_description": record.requirement_description or record.requirement_name,
                "last_verified": record.last_verified,
                "scrape_status": record.scrape_status,
            }
        )

        _maybe_add_office_and_location(
            record,
            acronym=acronym,
            service_id=service_id,
            office_map=office_map,
            dataset=dataset,
            service_location_seen=service_location_seen,
            service_row=service_map[service_key],
        )

        for dep in _dependencies_from_record(record, service_id, acronym):
            if dep["dependency_id"] not in dependency_seen:
                dependency_seen.add(dep["dependency_id"])
                dataset.dependencies.append(dep)

    for key, svc in service_map.items():
        svc["record_count"] = service_req_counts[key]
        dataset.services.append(svc)

    dataset.services.sort(key=lambda r: (r["agency_acronym"], r["service_name"]))
    dataset.requirements.sort(key=lambda r: (r["service_id"], r.get("requirement_order") or 9999, r["requirement_name"]))
    dataset.offices.sort(key=lambda r: (r["agency_acronym"], r["office_name"]))
    dataset.service_locations.sort(key=lambda r: (r["service_id"], r["office_id"]))
    dataset.dependencies.sort(key=lambda r: (r["service_id"], r["relationship_type"], r["required_document"]))
    return dataset


def _maybe_add_office_and_location(
    record: RequirementRecord,
    *,
    acronym: str,
    service_id: str,
    office_map: dict[tuple[str, str, str], dict[str, Any]],
    dataset: NormalizedDataset,
    service_location_seen: set[str],
    service_row: dict[str, Any],
) -> None:
    location = clean_location(record.location)
    if not location:
        return

    office_name, address, contact = _parse_office_fields(location, record.agency)
    office_key = (acronym, office_name, address)
    office_id = make_office_id(acronym, office_name, address)

    if office_key not in office_map:
        office_map[office_key] = {
            "office_id": office_id,
            "agency": record.agency,
            "agency_acronym": acronym,
            "office_name": office_name,
            "office_type": infer_office_type(f"{office_name} {address} {record.source_section}"),
            "region": "",
            "province": "",
            "city": _extract_city(address),
            "municipality": "",
            "barangay": "",
            "address": address,
            "latitude": "",
            "longitude": "",
            "contact_number": contact,
            "email": "",
            "official_url": "",
            "operating_hours": "",
            "source_url": record.source_url,
            "last_verified": record.last_verified,
        }
        dataset.offices.append(office_map[office_key])

    sl_id = make_service_location_id(service_id, office_id)
    if sl_id in service_location_seen:
        return
    service_location_seen.add(sl_id)
    dataset.service_locations.append(
        {
            "service_location_id": sl_id,
            "service_id": service_id,
            "office_id": office_id,
            "service_available": "yes",
            "application_method": record.application_method or service_row.get("application_method", ""),
            "appointment_required": record.appointment_required or service_row.get("appointment_required", ""),
            "processing_time": record.processing_time or service_row.get("processing_time", ""),
            "fee": record.fee or service_row.get("fee", ""),
            "source_url": record.source_url,
            "last_verified": record.last_verified,
        }
    )


_STATUS_RANK = {"blocked": 0, "seed": 1, "partial": 2, "success": 3}


def _dependencies_from_record(
    record: RequirementRecord, service_id: str, acronym: str
) -> list[dict[str, Any]]:
    base = _dependency_from_record(record, service_id, acronym)
    if base is None:
        return []
    if base["relationship_type"] != "required":
        canonical = canonicalize_document(base["required_document"])
        if canonical:
            base["required_document_normalized"] = canonical
        base["dependency_id"] = make_dependency_id(
            service_id,
            base["target_document"],
            base["required_document_normalized"],
            base["relationship_type"],
        )
        return [base]

    prepared: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in prepare_required_row(base):
        item["dependency_id"] = make_dependency_id(
            service_id,
            item["target_document"],
            item["required_document_normalized"],
            item["relationship_type"],
        )
        if item["dependency_id"] in seen:
            continue
        seen.add(item["dependency_id"])
        prepared.append(item)
    return prepared


def _dependency_from_record(
    record: RequirementRecord, service_id: str, acronym: str
) -> dict[str, Any] | None:
    role = record.requirement_role
    if record.scrape_status not in {"success", "partial"}:
        return None
    if role not in {"required_document", "supporting_document", "acceptable_id", "procedure"}:
        return None
    if record.requirement_name.startswith("[SCRAPE BLOCKED"):
        return None

    relationship = {
        "required_document": "required",
        "supporting_document": "conditional",
        "acceptable_id": "alternative",
        "procedure": "procedure",
    }[role]

    target = record.target_document or record.service_name
    required = record.requirement_name
    dep_id = make_dependency_id(service_id, target, required, relationship)

    return {
        "dependency_id": dep_id,
        "service_id": service_id,
        "target_document": target,
        "required_document": required,
        "required_document_normalized": normalize_document_name(required),
        "relationship_type": relationship,
        "condition": record.condition if record.conditional == "yes" else (
            "Pick any one acceptable ID" if role == "acceptable_id" else ""
        ),
        "target_agency": acronym,
        "required_document_agency": record.issuing_agency or acronym,
        "source_url": record.source_url,
        "last_verified": record.last_verified,
    }


def clean_location(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    lower = value.lower()
    if lower in {"online", "bnrs.dti.gov.ph", "unknown", "n/a"}:
        return ""
    office_keywords = (
        "office", "bureau", "branch", "consular", "center", "site", "charter",
        "street", "st.", "ave", "building", "intramuros", "manila", "davao",
    )
    if any(k in lower for k in office_keywords):
        return value
    if len(value) >= 12:
        return value
    return ""


def _parse_office_fields(location: str, agency: str) -> tuple[str, str, str]:
    contact = ""
    address = location
    office_name = agency

    phone_match = re.search(r"(?:tel\.?|phone|contact)\s*[:\-]?\s*([+\d\s\-()]+)", location, re.I)
    if phone_match:
        contact = clean_text(phone_match.group(1))
        address = clean_text(location[: phone_match.start()])

    if " - " in address:
        left, right = address.split(" - ", 1)
        if len(left) < 80:
            office_name = left.strip()
            address = right.strip()

    if address.lower().startswith("http"):
        office_name = agency
        address = location

    return office_name, address, contact


def _extract_city(address: str) -> str:
    match = re.search(
        r"\b(Manila|Quezon City|Makati|Davao City|Cebu City|Taguig|Pasig|Caloocan|"
        r"Parañaque|Las Piñas|Muntinlupa|Intramuros)\b",
        address,
        re.I,
    )
    return match.group(1) if match else ""


def _best_value(value: str) -> str:
    return (value or "").strip()


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def write_dataset_csvs(dataset: NormalizedDataset, output_dir: Path) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = (
        ("government_services.csv", GOVERNMENT_SERVICES_COLUMNS, dataset.services),
        ("requirements.csv", REQUIREMENTS_COLUMNS, dataset.requirements),
        ("government_offices.csv", GOVERNMENT_OFFICES_COLUMNS, dataset.offices),
        ("service_locations.csv", SERVICE_LOCATIONS_COLUMNS, dataset.service_locations),
        ("document_dependencies.csv", DOCUMENT_DEPENDENCIES_COLUMNS, dataset.dependencies),
    )
    counts: dict[str, int] = {}
    for filename, columns, rows in tables:
        path = output_dir / filename
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        counts[filename] = len(rows)
    return counts


def load_raw_records(path: Path) -> list[RequirementRecord]:
    records: list[RequirementRecord] = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            order = row.get("requirement_order", "")
            records.append(
                RequirementRecord(
                    agency=row.get("agency", ""),
                    agency_code=row.get("agency_code", ""),
                    service_name=row.get("service_name", ""),
                    service_category=row.get("service_category", ""),
                    target_document=row.get("target_document", ""),
                    transaction_type=row.get("transaction_type", ""),
                    applicant_type=row.get("applicant_type", ""),
                    requirement_name=row.get("requirement_name", ""),
                    requirement_type=row.get("requirement_type", "document"),
                    requirement_role=row.get("requirement_role", "required_document"),
                    requirement_description=row.get("requirement_description", ""),
                    document_format=row.get("document_format", ""),
                    quantity=row.get("quantity", ""),
                    conditional=row.get("conditional", "no"),
                    condition=row.get("condition", ""),
                    issuing_agency=row.get("issuing_agency", ""),
                    application_method=row.get("application_method", ""),
                    appointment_required=row.get("appointment_required", "unknown"),
                    processing_time=row.get("processing_time", ""),
                    fee=row.get("fee", ""),
                    fee_currency=row.get("fee_currency", "PHP"),
                    location=row.get("location", ""),
                    source_url=row.get("source_url", ""),
                    source_section=row.get("source_section", ""),
                    requirement_order=int(order) if str(order).isdigit() else None,
                    last_verified=row.get("last_verified", ""),
                    scrape_status=row.get("scrape_status", "success"),
                    notes=row.get("notes", ""),
                )
            )
    return records
