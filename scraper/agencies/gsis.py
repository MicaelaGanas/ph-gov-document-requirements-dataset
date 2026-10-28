"""GSIS UMID eCard enrollment requirements.

The homepage does not publish a checklist. The documentary requirements are
the UMID eCard Enrolment section of the GSIS Citizen's Charter. The enrollment
form is required. An eCard, a passport, or two government IDs are alternatives.
"""

from __future__ import annotations

import io
import logging

import requests

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)

CHARTER_URL = (
    "https://www.gsis.gov.ph/downloads/publications/"
    "20250328-Consolidated_2025-GSIS-Citizens_Charter_External-Services_2025_7th%20Edition.pdf"
)

_READING_NOTE = (
    "The GSIS site rejected the automated request for the 2025 Citizen's Charter "
    "PDF. This row is the UMID eCard Enrolment documentary requirement in the "
    "GSIS Citizen's Charter."
)

_IDENTITY_CONDITION = (
    "Any one identity option: an eCard, a valid passport, or two government-issued IDs"
)

SERVICE_NAME = "UMID eCard Enrollment"
TARGET_DOCUMENT = "UMID eCard"
SOURCE_SECTION = "Citizen's Charter, UMID eCard Enrolment"


class GSISScraper(BaseScraper):
    agency = "Government Service Insurance System"
    agency_code = "GSIS"

    def scrape(self) -> list:
        pdf, method = _download_charter(CHARTER_URL)
        text = _pdf_text(pdf)
        confirmed = _charter_confirms_enrollment(text)
        status = "success" if confirmed else "partial"
        notes = (
            f"Read from the Citizen's Charter PDF via {method}"
            if confirmed
            else f"{_READING_NOTE} ({method or 'fetch failed'})"
        )
        self._add_enrollment(status=status, notes=notes)
        return self.records()

    def _add_enrollment(self, *, status: str, notes: str) -> None:
        items = (
            (
                "Duly accomplished UMID eCard Enrollment Form",
                "required_document",
                "no",
                "",
                "GSIS",
                "original",
                "",
            ),
            (
                "eCard",
                "acceptable_id",
                "yes",
                _IDENTITY_CONDITION,
                "GSIS",
                "original",
                "",
            ),
            (
                "Valid passport",
                "acceptable_id",
                "yes",
                _IDENTITY_CONDITION,
                "DFA",
                "original_and_photocopy",
                "",
            ),
            (
                "Two valid government-issued IDs, photocopies submitted and originals presented; at least one ID must have a photo",
                "acceptable_id",
                "yes",
                _IDENTITY_CONDITION,
                "",
                "original_and_photocopy",
                "2",
            ),
        )
        for order, (name, role, conditional, condition, issuing, document_format, quantity) in enumerate(
            items, start=1
        ):
            self.add(
                service_name=SERVICE_NAME,
                service_category="Social Insurance (Government Employees)",
                target_document=TARGET_DOCUMENT,
                transaction_type="enrollment",
                applicant_type="Active member or pensioner with a created membership or pensioner record",
                requirement_name=name,
                requirement_description=name,
                requirement_role=role,
                conditional=conditional,
                condition=condition,
                issuing_agency=issuing,
                document_format=document_format,
                quantity=quantity,
                application_method="walk_in",
                appointment_required="no",
                processing_time="30 minutes",
                fee="No fee",
                location="GSIS branch eServices Unit",
                source_url=CHARTER_URL,
                source_section=SOURCE_SECTION,
                requirement_order=order,
                scrape_status=status,
                notes=notes,
            )


def _download_charter(url: str) -> tuple[bytes, str]:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        import cloudscraper

        response = cloudscraper.create_scraper().get(url, timeout=40)
        if response.content.startswith(b"%PDF"):
            return response.content, "cloudscraper"
    except requests.RequestException as exc:
        logger.info("GSIS charter cloudscraper failed: %s", exc)
    try:
        response = requests.get(url, headers=headers, timeout=40)
        if response.content.startswith(b"%PDF"):
            return response.content, "requests"
    except requests.RequestException as exc:
        logger.info("GSIS charter HTTP failed: %s", exc)
    from scraper.browser import fetch_with_playwright_bytes

    data = fetch_with_playwright_bytes(url)
    if data.startswith(b"%PDF"):
        return data, "playwright"
    return b"", "WAF rejected the request"


def _pdf_text(data: bytes) -> str:
    if not data.startswith(b"%PDF"):
        return ""
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.info("pypdf is not installed; GSIS charter text was not extracted")
        return ""
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _charter_confirms_enrollment(text: str) -> bool:
    folded = " ".join(text.lower().split())
    return (
        "umid ecard enrollment form" in folded
        and "ecard or valid passport or two" in folded
    )
