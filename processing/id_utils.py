"""Stable ID generation for normalized dataset tables."""

from __future__ import annotations

import hashlib
import re


def slugify(value: str, max_len: int = 48) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:max_len] or "item"


def digest(*parts: str, length: int = 8) -> str:
    base = "|".join(p.strip().lower() for p in parts if p is not None)
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:length].upper()


def make_service_id(agency_acronym: str, service_name: str) -> str:
    return f"{agency_acronym}-SVC-{digest(agency_acronym, service_name)}"


def make_requirement_id(service_id: str, requirement_name: str, requirement_role: str, order: int | None) -> str:
    return f"{service_id}-REQ-{digest(service_id, requirement_role, requirement_name, str(order or 0))}"


def make_office_id(agency_acronym: str, office_name: str, address: str) -> str:
    return f"{agency_acronym}-OFF-{digest(agency_acronym, office_name, address)}"


def make_service_location_id(service_id: str, office_id: str) -> str:
    return f"SL-{digest(service_id, office_id)}"


def make_dependency_id(service_id: str, target_document: str, required_document: str, relationship_type: str) -> str:
    return f"DEP-{digest(service_id, target_document, required_document, relationship_type)}"


def infer_office_type(text: str) -> str:
    lower = text.lower()
    mapping = (
        ("consular office", "consular_office"),
        ("foreign service post", "consular_office"),
        ("regional office", "regional_office"),
        ("district office", "district_office"),
        ("extension office", "extension_office"),
        ("satellite office", "satellite_office"),
        ("service center", "service_center"),
        ("branch", "branch"),
        ("bureau", "bureau"),
        ("central office", "central_office"),
        ("main office", "central_office"),
        ("citizen's charter", "central_office"),
        ("registration site", "registration_site"),
    )
    for needle, office_type in mapping:
        if needle in lower:
            return office_type
    return "service_center"
