"""Requirement classification, splitting, and normalization."""

from __future__ import annotations

import re

from scraper.parsers.generic import clean_text

# Roles distinguish IDs accepted for identity vs documents that must be submitted.
REQUIREMENT_ROLES = frozenset(
    {
        "required_document",
        "acceptable_id",
        "supporting_document",
        "procedure",
        "fee",
        "processing_time",
        "eligibility",
        "metadata",
    }
)

ID_KEYWORDS = (
    " id",
    " id;",
    " id,",
    " id.",
    "identification",
    "identification card",
    " driver's license",
    " passport",
    " umid",
    " philid",
    " ephilid",
    " prc id",
    " sss card",
    " gsis card",
    " seaman",
    " voter's id",
    " voters id",
    " postal id",
    " tin id",
    " ltopf",
    " clearances",
    " clearance",
    " barangay id",
    " school id",
    " employee id",
)

DOCUMENT_KEYWORDS = (
    "certificate",
    "birth certificate",
    "marriage",
    "form",
    "affidavit",
    "transcript",
    "diploma",
    "diploma",
    "report of birth",
    "foundling",
    "medical certificate",
    "police report",
    "receipt",
    "application form",
    "tor ",
    " transcript",
)


def normalize_key(text: str) -> str:
    text = clean_text(text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def dedupe_key(
    agency_code: str,
    service_name: str,
    requirement_role: str,
    requirement_name: str,
    *,
    conditional: str = "no",
    condition: str = "",
    source_section: str = "",
) -> str:
    return "|".join(
        [
            agency_code,
            normalize_key(service_name),
            requirement_role,
            normalize_key(requirement_name),
            conditional,
            normalize_key(condition)[:80],
            normalize_key(source_section)[:80],
        ]
    )


def infer_quantity(text: str) -> str:
    patterns = [
        r"\b(\d+)\s*(?:copies|copy|pcs|pieces)\b",
        r"\b(?:two|2)\s*\(?2\)?\s*valid",
        r"\bone\s*\(?1\)?",
        r"\btwo\s*\(?2\)?",
        r"\bthree\s*\(?3\)?",
    ]
    lower = text.lower()
    if re.search(r"two\s*\(?2\)?\s*valid", lower) or "two (2)" in lower:
        return "2"
    if "one (1)" in lower or re.search(r"one\s*\(?1\)?", lower):
        return "1"
    for pattern in patterns[:1]:
        match = re.search(pattern, lower)
        if match:
            return match.group(1)
    return ""


def infer_requirement_role(
    text: str,
    *,
    section: str = "",
    explicit_role: str = "",
) -> str:
    if explicit_role:
        return explicit_role
    combined = f"{section} {text}".lower()

    if any(k in combined for k in ("fee", "php", "penalty")) and re.search(
        r"p\s*[\d,]+", combined
    ):
        return "fee"
    if any(
        k in combined
        for k in ("working day", "processing take", "duration of service", "minute")
    ):
        return "processing_time"
    if any(
        k in combined
        for k in (
            "appointment",
            "walk-in",
            "walk in",
            "personal appearance",
            "proceed to",
            "biometric",
            "log into",
            "click",
            "schedule",
            "online registration",
            "submit",
            "fill out",
            "await",
            "report your",
        )
    ):
        return "procedure"
    if "acceptable id" in combined or "valid id" in combined and "list" in combined:
        return "acceptable_id"
    if "secondary supporting" in combined or "secondary document" in combined:
        return "acceptable_id"
    if section and "acceptable id" in section.lower():
        return "acceptable_id"

    lower = text.lower()
    if _looks_like_id_item(lower):
        if any(k in lower for k in ("certificate of live birth", "birth certificate", "marriage certificate", "form 137", "transcript", "diploma", "nbi clearance")):
            # These are documents even when listed as ID alternatives
            if "clearance" in lower and "nbi" in lower:
                return "required_document"
            if "birth certificate" in lower or "certificate of live birth" in lower:
                return "required_document"
        return "acceptable_id"
    if any(k in lower for k in DOCUMENT_KEYWORDS):
        return "required_document"
    return "required_document"


def _looks_like_id_item(lower: str) -> bool:
    if any(k in lower for k in ID_KEYWORDS):
        return True
    if lower.endswith(" id") or " id " in lower:
        return True
    if "card" in lower and "credit" not in lower and "atm" not in lower:
        return True
    return False


def infer_requirement_type_from_role(role: str) -> str:
    mapping = {
        "required_document": "document",
        "acceptable_id": "document",
        "supporting_document": "document",
        "procedure": "procedure",
        "fee": "fee",
        "processing_time": "processing_time",
        "eligibility": "eligibility",
        "metadata": "metadata",
    }
    return mapping.get(role, "document")


def split_compound_requirement(text: str) -> list[str]:
    """Split bundled requirements into atomic items where possible."""
    text = clean_text(text)
    if not text:
        return []

    lower = text.lower()
    # Don't split short single requirements
    if len(text) < 120 and " and " not in lower and ";" not in text:
        return [text]

    # "What to Bring:" prefixed bundles
    if lower.startswith("what to bring"):
        parts = re.split(r"\.\s+(?=[A-Z(])", text)
        results = []
        for part in parts:
            part = re.sub(r"^What to Bring:\s*", "", part, flags=re.I).strip()
            if part:
                results.extend(_split_bullet_phrases(part))
        return [p for p in results if len(p) > 5]

    if ";" in text:
        return [clean_text(p) for p in text.split(";") if clean_text(p)]

    # "X and one (1) Y" pattern for PhilSys primary
    match = re.match(
        r"^(?P<a>.+?\bcertificate of live birth[^;]+?)\s+and\s+(?P<b>one\s*\(?1\)?\s+.+)$",
        text,
        re.I,
    )
    if match:
        return [clean_text(match.group("a")), clean_text(match.group("b"))]

    if " and " in text and any(k in lower for k in ("photocopy", "original", "certificate", "id")):
        parts = re.split(r"\s+and\s+", text, maxsplit=2)
        if len(parts) == 2 and all(len(p) > 15 for p in parts):
            return [clean_text(p) for p in parts]

    return [text]


def _split_bullet_phrases(text: str) -> list[str]:
    text = clean_text(text)
    if text.lower().startswith("(for "):
        return [text]
    # Split on ". " before capital or parenthetical sub-clauses
    chunks = re.split(r"\.\s+(?=\()", text)
    if len(chunks) > 1:
        return [clean_text(c).rstrip(".") for c in chunks if clean_text(c)]
    return [text]
