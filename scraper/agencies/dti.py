"""DTI Business Name Registration requirements.

The BNRS landing page is not the checklist. Identity documents are the
alternatives in Annex A. A representative's authorization letter and ID are
conditional. A foreign national's Certificate of Authority under RA 7042, and
DOJ recognition for a refugee or stateless person, are a separate conditional
set. Fees stay in the fee field. Proposed name, address, and business activity
are form fields and are not stored as documents.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import requests

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, soup_from_html

logger = logging.getLogger(__name__)

FAQ_URL = "https://bnrs.dti.gov.ph/faq"
ANNEX_A_URL = "https://dtibnrs.s3-ap-southeast-1.amazonaws.com/files/20230629/n1xa3vwmok1513.pdf"

SERVICE_NAME = "Business Name Registration"
TARGET_DOCUMENT = "DTI Certificate of Business Name Registration"
APPLICANT = "Sole proprietor at least 18 years of age"
FEE = (
    "PHP 200 (barangay), PHP 500 (city/municipality), PHP 1,000 (regional), "
    "or PHP 2,000 (national), plus PHP 30 documentary stamp tax. Late filing "
    "adds 50% of the registration fee."
)
REPRESENTATIVE_CONDITION = (
    "A representative files the registration and provides a valid ID and an "
    "authorization letter signed by the business owner, together with the other requirements"
)
FOREIGN_CONDITION = (
    "Non-Philippine national at least 18 years of age. The application is "
    "processed only after the supporting documents are submitted at a DTI office "
    "and the fees are paid"
)
REFUGEE_CONDITION = (
    "Refugee or stateless person at least 18 years of age whose recognition is "
    "not subject to cancellation, revocation, or cessation"
)

_READING_NOTE = (
    "The BNRS FAQ or Annex A (List of Government-issued IDs) could not be "
    "confirmed on this run. This row is a reading of those official pages."
)


@dataclass(frozen=True)
class ChecklistItem:
    name: str
    role: str
    source_url: str
    source_section: str
    conditional: str = "no"
    condition: str = ""
    issuing_agency: str = ""
    document_format: str = "original"


_IDS: tuple[tuple[str, str], ...] = (
    ("Passport", "DFA"),
    ("Driver's License", "LTO"),
    ("Professional Regulation Commission (PRC) ID", "PRC"),
    ("National Bureau of Investigation (NBI) Clearance", "NBI"),
    ("Police Clearance", ""),
    ("Postal ID", "PHLPost"),
    ("Voter's ID", "COMELEC"),
    ("Unified Multi-Purpose ID", ""),
    ("Overseas Workers Welfare Administration (OWWA) ID", "OWWA"),
    ("Seaman's Book", "MARINA"),
    ("Integrated Bar of the Philippines (IBP) ID", "Integrated Bar of the Philippines"),
    ("Senior Citizen's ID", ""),
    ("Persons with Disability (PWD) ID", ""),
    ("Government Office ID", ""),
    ("Validated State College/University ID", ""),
    ("Philippine Identification (PhilID or printed ePhilID)", "PSA"),
    (
        "Other government-issued identification document with the applicant's printed full name, signature, and photograph, valid and active at the time of application",
        "",
    ),
)


def _items() -> tuple[ChecklistItem, ...]:
    ids = tuple(
        ChecklistItem(
            name=name,
            role="acceptable_id",
            source_url=ANNEX_A_URL,
            source_section="Annex A - List of Government-issued IDs",
            issuing_agency=issuer,
        )
        for name, issuer in _IDS
    )
    return ids + (
        ChecklistItem(
            name="Authorization letter signed by the business owner",
            role="supporting_document",
            source_url=FAQ_URL,
            source_section="BNRS FAQ, representative filing",
            conditional="yes",
            condition=REPRESENTATIVE_CONDITION,
            document_format="original",
        ),
        ChecklistItem(
            name="Valid government-issued ID of the representative",
            role="supporting_document",
            source_url=FAQ_URL,
            source_section="BNRS FAQ, representative filing",
            conditional="yes",
            condition=REPRESENTATIVE_CONDITION,
        ),
        ChecklistItem(
            name="Certificate of Registration of Sole Proprietorship or Certificate of Authority to Engage in Business under RA 7042 (Foreign Investments Act)",
            role="supporting_document",
            source_url=FAQ_URL,
            source_section="BNRS FAQ, foreign national",
            conditional="yes",
            condition=FOREIGN_CONDITION,
            issuing_agency="DTI",
        ),
        ChecklistItem(
            name="Written recognition from the Refugee and Stateless Persons Protection Unit of the Department of Justice (DOJ-RSPPU)",
            role="supporting_document",
            source_url=FAQ_URL,
            source_section="BNRS FAQ, refugee or stateless person",
            conditional="yes",
            condition=REFUGEE_CONDITION,
            issuing_agency="DOJ",
        ),
    )


class DTIScraper(BaseScraper):
    agency = "Department of Trade and Industry"
    agency_code = "DTI"

    def scrape(self) -> list:
        faq = self.fetch(FAQ_URL)
        faq_text = _page_text(faq.html) if faq.ok else ""
        pdf, method = _download_pdf(ANNEX_A_URL)
        annex_text = _pdf_text(pdf)
        confirmed = _sources_confirm(annex_text, faq_text)
        status = "success" if confirmed else "partial"
        if confirmed:
            notes = (
                f"Read from the BNRS FAQ and Annex A via {method}. "
                "Proposed business name, address, and line of business are form fields "
                "on the registration guide and are not documents. Foreign-proprietor "
                "form templates and Memorandum Circular No. 22-06 are linked from the "
                "downloads page; the circular has no extractable text, so those templates "
                "are not stored as a checklist."
            )
        else:
            notes = f"{_READING_NOTE} ({method or 'Annex A fetch failed'}; FAQ {'ok' if faq.ok else 'failed'})"
        for order, item in enumerate(_items(), start=1):
            self.add(
                service_name=SERVICE_NAME,
                service_category="Business Registration",
                target_document=TARGET_DOCUMENT,
                transaction_type="new_registration",
                applicant_type=APPLICANT,
                requirement_name=item.name,
                requirement_description=item.name,
                requirement_role=item.role,
                conditional=item.conditional,
                condition=item.condition,
                issuing_agency=item.issuing_agency,
                document_format=item.document_format,
                application_method="online",
                appointment_required="no",
                fee=FEE,
                location="bnrs.dti.gov.ph",
                source_url=item.source_url,
                source_section=item.source_section,
                requirement_order=order,
                scrape_status=status,
                notes=notes,
            )
        return self.records()


def _page_text(html: str) -> str:
    if not html:
        return ""
    root = soup_from_html(html)
    return clean_text(root.get_text(" ", strip=True))


def _download_pdf(url: str) -> tuple[bytes, str]:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=40)
        if response.content.startswith(b"%PDF"):
            return response.content, "requests"
    except requests.RequestException as exc:
        logger.info("DTI Annex A HTTP failed: %s", exc)
    try:
        import cloudscraper

        response = cloudscraper.create_scraper().get(url, timeout=40)
        if response.content.startswith(b"%PDF"):
            return response.content, "cloudscraper"
    except requests.RequestException as exc:
        logger.info("DTI Annex A cloudscraper failed: %s", exc)
    from scraper.browser import fetch_with_playwright_bytes

    data = fetch_with_playwright_bytes(url)
    if data.startswith(b"%PDF"):
        return data, "playwright"
    return b"", ""


def _pdf_text(data: bytes) -> str:
    if not data.startswith(b"%PDF"):
        return ""
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.info("pypdf is not installed; DTI Annex A text was not extracted")
        return ""
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _sources_confirm(annex_text: str, faq_text: str) -> bool:
    annex = " ".join(annex_text.lower().split())
    faq = " ".join(faq_text.lower().split())
    annex_markers = (
        "list of government-issued",
        "passport",
        "philippine identification",
        "seaman",
        "printed full name",
    )
    faq_markers = (
        "php 200",
        "php 500",
        "php 1,000",
        "php 2,000",
        "php 30",
        "authorization letter",
        "ra 7042",
        "doj-rsppu",
    )
    return all(marker in annex for marker in annex_markers) and all(
        marker in faq for marker in faq_markers
    )
