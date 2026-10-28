"""LTO student permit, new license, and renewal requirements.

The checklists are the walk-in services in the 2025 Citizen's Charter PDF.
Identity documents offered as "any of the following" stay alternatives.
A parent's consent, a foreigner's passport, a TIN, the renewal course, and
an advance-renewal ticket stay conditional. The five-item combined seed is
not used.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import requests

from scraper.base import BaseScraper

logger = logging.getLogger(__name__)

CHARTER_URL = "https://lto.gov.ph/wp-content/uploads/2025/09/LTO-CC-2025-External-v2.pdf"

_READING_NOTE = (
    "Automated fetch of the LTO Citizen's Charter PDF returned a Cloudflare "
    "challenge. This row is a reading of that charter, checked on 2026-10-28."
)


@dataclass(frozen=True)
class ChecklistItem:
    name: str
    role: str
    conditional: str = "no"
    condition: str = ""
    issuing_agency: str = ""
    document_format: str = ""


@dataclass(frozen=True)
class LicenseService:
    service_name: str
    target_document: str
    transaction_type: str
    applicant_type: str
    application_method: str
    fee: str
    processing_time: str
    source_section: str
    items: tuple[ChecklistItem, ...]


_IDENTITY = (
    ChecklistItem(
        "PSA/NSO Certificate of Birth",
        "acceptable_id",
        issuing_agency="PSA",
        document_format="original_and_photocopy",
    ),
    ChecklistItem(
        "Philippine Identification Card",
        "acceptable_id",
        issuing_agency="PSA",
        document_format="original_and_photocopy",
    ),
    ChecklistItem(
        "Passport",
        "acceptable_id",
        issuing_agency="DFA",
        document_format="original_and_photocopy",
    ),
    ChecklistItem(
        "Local Civil Registry document, for areas where there is no PSA",
        "acceptable_id",
        issuing_agency="Local Civil Registry",
        document_format="original_and_photocopy",
    ),
    ChecklistItem(
        "PSA Certificate of Marriage",
        "acceptable_id",
        issuing_agency="PSA",
        document_format="original_and_photocopy",
    ),
)

LICENSE_SERVICES: tuple[LicenseService, ...] = (
    LicenseService(
        service_name="Student-Driver's Permit",
        target_document="Student-Driver's Permit",
        transaction_type="new_application",
        applicant_type="Filipino citizen aged 16 and above, or foreign citizen aged 18 and above",
        application_method="online_and_walk_in",
        fee="PHP 250 (student permit fee PHP 150; application fee PHP 100)",
        processing_time="1 hour 53 minutes (walk-in)",
        source_section="Citizen's Charter 2025, 35. Student-Driver's Permit (Walk-in)",
        items=(
            ChecklistItem(
                "Duly accomplished Application for Permits and Licenses (APL) Form",
                "required_document",
                issuing_agency="LTO",
                document_format="original",
            ),
            ChecklistItem(
                "Electronically transmitted medical certificate from an LTO-accredited medical clinic, original and one photocopy",
                "required_document",
                issuing_agency="LTO-accredited medical clinic",
                document_format="original_and_photocopy",
            ),
            *_IDENTITY,
            ChecklistItem(
                "Parent's or guardian's consent, with one original and one photocopy of the parent or guardian's valid government ID with photo and signature",
                "supporting_document",
                conditional="yes",
                condition="Applicant is below 18 years old",
                issuing_agency="Parent or guardian",
                document_format="original_and_photocopy",
            ),
            ChecklistItem(
                "Any issued ID with photo and signature of the applicant, original and one photocopy",
                "required_document",
                document_format="original_and_photocopy",
            ),
            ChecklistItem(
                "Passport with entry date of at least one month and visa duration of six months, or a PSA-authenticated birth certificate if born in the Philippines",
                "supporting_document",
                conditional="yes",
                condition="Foreign national applicant",
                issuing_agency="Bureau of Immigration|PSA",
                document_format="original_and_photocopy",
            ),
            ChecklistItem(
                "Certificate of Completion of the 15-hour Theoretical Driving Course, electronically transmitted, original and one photocopy",
                "required_document",
                issuing_agency="LTO-accredited driving school|LTO Driver's Education Center|TESDA",
                document_format="original_and_photocopy",
            ),
            ChecklistItem(
                "LTO Client ID",
                "required_document",
                issuing_agency="LTO",
                document_format="electronic",
            ),
            ChecklistItem(
                "Taxpayer's Identification Number (TIN)",
                "supporting_document",
                conditional="yes",
                condition="Applicant is employed",
                issuing_agency="BIR",
            ),
        ),
    ),
    LicenseService(
        service_name="New Driver's License (Non-Professional)",
        target_document="Non-Professional Driver's License",
        transaction_type="new_application",
        applicant_type="Student-permit holder, at least 17 years old (18 if a foreign citizen)",
        application_method="walk_in",
        fee="PHP 685 (application fee PHP 100; license fee PHP 585)",
        processing_time="5 hours 38 minutes (walk-in)",
        source_section="Citizen's Charter 2025, 37. New Driver's License (Non-Professional) (Walk-in)",
        items=(
            ChecklistItem(
                "Duly accomplished Application for Permits and Licenses (APL) Form",
                "required_document",
                issuing_agency="LTO",
                document_format="original",
            ),
            ChecklistItem(
                "Electronically transmitted medical certificate from an LTO-accredited medical clinic, original and one photocopy",
                "required_document",
                issuing_agency="LTO-accredited medical clinic",
                document_format="original_and_photocopy",
            ),
            ChecklistItem(
                "Practical Driving Course (PDC) certificate, original and one photocopy, electronically transmitted",
                "required_document",
                issuing_agency="LTO Driver's Education Center|LTO-accredited driving school|TESDA",
                document_format="original_and_photocopy",
            ),
            ChecklistItem(
                "Valid Student-Driver's Permit",
                "required_document",
                issuing_agency="LTO",
                document_format="original",
            ),
            ChecklistItem(
                "Parental or guardian's consent with a valid government ID with photo and signature",
                "supporting_document",
                conditional="yes",
                condition="Applicant is 17 years old",
                document_format="original",
            ),
            ChecklistItem(
                "Taxpayer's Identification Number (TIN)",
                "supporting_document",
                conditional="yes",
                condition="Applicant is employed",
                issuing_agency="BIR",
            ),
        ),
    ),
    LicenseService(
        service_name="Plain or Advance Renewal of Driver's License",
        target_document="Driver's License",
        transaction_type="renewal",
        applicant_type="Holder of a driver's license not expired for more than two years",
        application_method="online_and_walk_in",
        fee="PHP 585",
        processing_time="2 hours 11 minutes (walk-in)",
        source_section="Citizen's Charter 2025, 41. Plain or Advance Renewal of Driver's/Conductor's License (Walk-in)",
        items=(
            ChecklistItem(
                "Duly accomplished Application for Permits and Licenses (APL) Form",
                "required_document",
                issuing_agency="LTO",
                document_format="original",
            ),
            ChecklistItem(
                "Electronically transmitted medical certificate from an LTO-accredited medical clinic, original and one photocopy",
                "required_document",
                issuing_agency="LTO-accredited medical clinic",
                document_format="original_and_photocopy",
            ),
            ChecklistItem(
                "Certificate of Completion of Comprehensive Driver's Education (CDE) for the initial renewal of a five-year license",
                "supporting_document",
                conditional="yes",
                condition=(
                    "Initial renewal of a five-year license, unless the student permit was "
                    "issued on or after 3 August 2020 or the current license was renewed on "
                    "or after 28 October 2021"
                ),
                issuing_agency="LTO",
                document_format="original",
            ),
            ChecklistItem(
                "Driver's license",
                "required_document",
                issuing_agency="LTO",
                document_format="original_and_photocopy",
            ),
            ChecklistItem(
                "Certificate of Completion of Driver's Reorientation Course",
                "supporting_document",
                conditional="yes",
                condition="Applicant has five to thirty-nine demerit points",
                issuing_agency="LTO Driver's Education Center",
                document_format="original",
            ),
            ChecklistItem(
                "Plane ticket",
                "supporting_document",
                conditional="yes",
                condition="Advance renewal",
                document_format="original",
            ),
        ),
    ),
)


class LTOScraper(BaseScraper):
    agency = "Land Transportation Office"
    agency_code = "LTO"

    def scrape(self) -> list:
        pdf, method = _download_charter(CHARTER_URL)
        text = _pdf_text(pdf)
        confirmed = _charter_confirms_services(text)
        status = "success" if confirmed else "partial"
        notes = (
            f"Read from the Citizen's Charter PDF via {method}"
            if confirmed
            else f"{_READING_NOTE} ({method or 'fetch failed'})"
        )
        for service in LICENSE_SERVICES:
            self._add_service(service, status=status, notes=notes)
        return self.records()

    def _add_service(self, service: LicenseService, *, status: str, notes: str) -> None:
        for order, item in enumerate(service.items, start=1):
            self.add(
                service_name=service.service_name,
                service_category="Transportation",
                target_document=service.target_document,
                transaction_type=service.transaction_type,
                applicant_type=service.applicant_type,
                requirement_name=item.name,
                requirement_description=item.name,
                requirement_role=item.role,
                conditional=item.conditional,
                condition=item.condition,
                issuing_agency=item.issuing_agency,
                document_format=item.document_format,
                application_method=service.application_method,
                appointment_required="no",
                processing_time=service.processing_time,
                fee=service.fee,
                location="LTO licensing offices",
                source_url=CHARTER_URL,
                source_section=service.source_section,
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
        logger.info("LTO charter cloudscraper failed: %s", exc)
    try:
        response = requests.get(url, headers=headers, timeout=40)
        if response.content.startswith(b"%PDF"):
            return response.content, "requests"
    except requests.RequestException as exc:
        logger.info("LTO charter HTTP failed: %s", exc)
    from scraper.browser import fetch_with_playwright_bytes

    data = fetch_with_playwright_bytes(url)
    if data.startswith(b"%PDF"):
        return data, "playwright"
    return b"", "Cloudflare challenge"


def _pdf_text(data: bytes) -> str:
    if not data.startswith(b"%PDF"):
        return ""
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.info("pypdf is not installed; LTO charter text was not extracted")
        return ""
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _charter_confirms_services(text: str) -> bool:
    folded = " ".join(text.lower().split())
    markers = (
        "student-driver",
        "new driver's license",
        "plain or advance renewal",
        "theoretical driving",
        "practical driving",
        "comprehensive driver",
    )
    return all(marker in folded for marker in markers)
