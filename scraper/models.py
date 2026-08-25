"""Data models for government service requirement records."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


# Core columns requested by the user, plus analyst-oriented extensions.
CSV_COLUMNS = [
    # --- core ---
    "record_id",
    "agency",
    "service_name",
    "target_document",
    "transaction_type",
    "applicant_type",
    "requirement_name",
    "requirement_type",
    "requirement_role",
    "conditional",
    "condition",
    "issuing_agency",
    "application_method",
    "appointment_required",
    "processing_time",
    "fee",
    "location",
    "source_url",
    "last_verified",
    # --- analyst extensions ---
    "agency_code",
    "service_category",
    "requirement_description",
    "document_format",
    "quantity",
    "fee_currency",
    "source_section",
    "requirement_order",
    "scrape_status",
    "notes",
]


def slugify(value: str, max_len: int = 40) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:max_len] or "item"


def make_record_id(
    agency_code: str,
    service_name: str,
    requirement_name: str,
    *,
    requirement_role: str = "",
    order: int | None = None,
) -> str:
    base = f"{agency_code}|{service_name}|{requirement_role}|{requirement_name}|{order or 0}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:8].upper()
    service_slug = slugify(service_name, 24)
    req_slug = slugify(requirement_name, 24)
    return f"{agency_code}-{service_slug}-{req_slug}-{digest}"


@dataclass
class RequirementRecord:
    agency: str
    service_name: str
    requirement_name: str
    source_url: str
    agency_code: str = ""
    service_category: str = ""
    target_document: str = ""
    transaction_type: str = ""
    applicant_type: str = ""
    requirement_type: str = "document"
    requirement_role: str = "required_document"
    requirement_description: str = ""
    document_format: str = ""
    quantity: str = ""
    conditional: str = "no"
    condition: str = ""
    issuing_agency: str = ""
    application_method: str = ""
    appointment_required: str = "unknown"
    processing_time: str = ""
    fee: str = ""
    fee_currency: str = "PHP"
    location: str = ""
    source_section: str = ""
    requirement_order: int | None = None
    last_verified: str = field(default_factory=lambda: date.today().isoformat())
    scrape_status: str = "success"
    notes: str = ""
    record_id: str = field(default="", init=False)

    def __post_init__(self) -> None:
        if not self.agency_code:
            self.agency_code = slugify(self.agency, 12).upper()
        if not self.record_id:
            self.record_id = make_record_id(
                self.agency_code,
                self.service_name,
                self.requirement_name,
                requirement_role=self.requirement_role,
                order=self.requirement_order,
            )

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        return {col: row.get(col, "") for col in CSV_COLUMNS}
