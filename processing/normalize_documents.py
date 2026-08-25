"""Document and agency name normalization helpers."""

from __future__ import annotations

import re

from scraper.parsers.generic import clean_text

# Common abbreviations expanded for join/analysis — original wording preserved elsewhere.
DOCUMENT_ALIASES: dict[str, str] = {
    "psa certificate of live birth": "Certificate of Live Birth (PSA)",
    "certificate of live birth": "Certificate of Live Birth (PSA)",
    "colb": "Certificate of Live Birth (PSA)",
    "birth certificate": "Certificate of Live Birth (PSA)",
    "nbi clearance": "NBI Clearance",
    "philid": "Philippine Identification (PhilID)",
    "philippine identification": "Philippine Identification (PhilID)",
    "national id": "Philippine Identification (PhilID)",
    "umid": "Unified Multi-Purpose ID (UMID)",
    "sss card": "SSS ID",
    "gsis card": "GSIS ID",
    "prc id": "PRC ID",
    "driver's license": "Driver's License (LTO)",
    "drivers license": "Driver's License (LTO)",
    "student permit": "Student Permit (LTO)",
    "voter's id": "Voter's ID (COMELEC)",
    "voters id": "Voter's ID (COMELEC)",
    "application form": "Application Form",
    "accomplished application form": "Application Form",
    "cenomar": "Certificate of No Marriage (CENOMAR)",
    "certificate of no marriage": "Certificate of No Marriage (CENOMAR)",
}

AGENCY_ACRONYMS: dict[str, str] = {
    "department of foreign affairs": "DFA",
    "philippine statistics authority (philsys)": "PHILSYS",
    "philippine statistics authority": "PSA",
    "national bureau of investigation": "NBI",
    "land transportation office": "LTO",
    "professional regulation commission": "PRC",
    "commission on elections": "COMELEC",
    "department of trade and industry": "DTI",
    "social security system": "SSS",
    "philippine health insurance corporation": "PHILHEALTH",
    "pag-ibig fund": "PAGIBIG",
    "government service insurance system": "GSIS",
    "davao city lgu": "LGU-DAVAO",
}


def normalize_document_name(text: str) -> str:
    """Return a canonical short label when recognized; otherwise cleaned original."""
    cleaned = clean_text(text)
    if not cleaned:
        return ""
    lower = cleaned.lower()
    # Strip leading procedural phrasing for dependency joins.
    lower = re.sub(
        r"^(original and photocopy of|photocopy of|original of|accomplished|valid|any acceptable)\s+",
        "",
        lower,
    )
    lower = re.sub(r"\s+on security paper.*$", "", lower)
    lower = re.sub(r"[.;,]+$", "", lower).strip()

    for key, canonical in DOCUMENT_ALIASES.items():
        if key in lower or lower.startswith(key):
            return canonical

    # Title-case short names; keep long official strings trimmed.
    if len(cleaned) <= 80:
        return cleaned.strip(" ;,")
    return cleaned[:120].strip(" ;,") + "..."


def normalize_agency_acronym(agency: str, agency_code: str = "") -> str:
    if agency_code:
        return agency_code.upper()
    lower = agency.lower().strip()
    if lower in AGENCY_ACRONYMS:
        return AGENCY_ACRONYMS[lower]
    for key, acronym in AGENCY_ACRONYMS.items():
        if key in lower:
            return acronym
    return agency_code or agency.split()[0].upper()[:12]


def source_title_from_url(url: str) -> str:
    if not url:
        return ""
    path = url.rstrip("/").split("/")[-1]
    path = path.split("?")[0]
    return path.replace("-", " ").replace("_", " ").title()
