"""PSA copy-issuance requirements for birth, marriage, death, and CENOMAR.

Each certificate is one service. The checklist is the information the official
page tells the requester to provide. A live fetch is used when psa.gov.ph
returns the page. When Cloudflare returns a challenge, the rows are a reading
of that same official page, not a made-up baseline.
"""

from __future__ import annotations

from dataclasses import dataclass

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, find_main_content, soup_from_html

_NAV_ITEMS = {
    "birth certificate",
    "marriage certificate",
    "death certificate",
    "cenomar",
    "application form",
}

_READING_NOTE = (
    "Automated fetch of this official page returned a Cloudflare challenge. "
    "This row is a reading of that page, checked on 2026-10-28."
)


@dataclass(frozen=True)
class CertificateService:
    service_name: str
    target_document: str
    url: str
    applicant_type: str
    application_method: str
    appointment_required: str
    location: str
    information_section: str
    information_items: tuple[str, ...]
    procedures: tuple[str, ...] = ()
    eligibility: tuple[str, ...] = ()
    eligibility_section: str = ""


# Readings of the official pages. Birth was checked against the 8 June 2026
# text of https://psa.gov.ph/birth-certificate. Marriage, death, and CENOMAR
# were checked against the 31 May 2025 text of their psa.gov.ph pages. Those
# pages were still the ones indexed for those URLs when the live fetch was blocked.
CERTIFICATE_SERVICES: tuple[CertificateService, ...] = (
    CertificateService(
        service_name="Certificate of Live Birth",
        target_document="Certificate of Live Birth (PSA)",
        url="https://psa.gov.ph/birth-certificate",
        applicant_type="Document owner or representative",
        application_method="online_and_walk_in",
        appointment_required="yes",
        location="Census Serbilis Centers",
        information_section="Information to be provided for the issuance of Birth Certificate",
        information_items=(
            "Complete name of the child (first, middle, last)",
            "Complete name of the father",
            "Complete maiden name of the mother",
            "Date of birth (month, day, year)",
            "Place of birth (city/municipality, province)",
            "Whether or not registered late. (If registered late, please state the year when it was registered.",
            "Complete name and address of the requesting party",
            "Relationship to the child",
            "Number of copies needed",
            "Purpose of the certification",
        ),
        procedures=(
            "Application made in person by the owner or by his/her representatives will be received at different Census Serbilis Centers.",
            "Appointment is required for walk-in. Visit https://appointment.psa.gov.ph/",
        ),
        eligibility_section="Article 7, Child and Youth Welfare Code (nondisclosure of birth records)",
        eligibility=(
            "The person himself, or any person authorized by him",
            "His spouse, his parent or parents, his direct descendants, or the guardian or institution legally in charge of him, if he is a minor",
            "The court or proper public official whenever absolutely necessary in administrative, judicial or other official proceedings to determine the identity of the child's parents or other circumstances surrounding his birth",
            "In case of the person's death, the nearest of kin",
        ),
    ),
    CertificateService(
        service_name="Certificate of Marriage",
        target_document="Certificate of Marriage (PSA)",
        url="https://psa.gov.ph/marriage-certificate",
        applicant_type="Interested party",
        application_method="",
        appointment_required="unknown",
        location="",
        information_section="Information to be provided for the issuance of Marriage Certificate",
        information_items=(
            "Complete name of the husband",
            "Complete name of the wife",
            "Date of marriage",
            "Place of marriage",
            "Complete name and address of the requesting party",
            "Number of copies needed",
            "Purpose of the certification",
        ),
    ),
    CertificateService(
        service_name="Certificate of Death",
        target_document="Certificate of Death (PSA)",
        url="https://psa.gov.ph/death-certificate",
        applicant_type="Interested party",
        application_method="",
        appointment_required="unknown",
        location="",
        information_section="Information to be provided for the issuance of Death Certificate",
        information_items=(
            "Complete name of the deceased person",
            "Date of death",
            "Place of death",
            "Place of marriage",
            "Complete name and address of the requesting party",
            "Number of copies needed",
            "Purpose of the certification",
        ),
    ),
    CertificateService(
        service_name="Certificate of No Marriage (CENOMAR)",
        target_document="Certificate of No Marriage (CENOMAR)",
        url="https://psa.gov.ph/cenomar",
        applicant_type="Interested party",
        application_method="",
        appointment_required="unknown",
        location="",
        information_section="Information to be provided for the issuance of CENOMAR",
        information_items=(
            "Complete name of the person",
            "Complete name of the father",
            "Complete maiden name of the mother",
            "Date of birth",
            "Place of birth",
            "Complete name and address of the requesting party",
            "Number of copies needed",
            "Purpose of the certification",
        ),
    ),
)


class PSAScraper(BaseScraper):
    agency = "Philippine Statistics Authority"
    agency_code = "PSA"

    def scrape(self) -> list:
        for service in CERTIFICATE_SERVICES:
            self._scrape_service(service)
        return self.records()

    def _scrape_service(self, service: CertificateService) -> None:
        result = self.fetch(service.url)
        if result.ok and not _is_challenge(result.html):
            if self._parse_page(result.html, service, method=result.method):
                return

        reason = "Cloudflare challenge" if result.html and _is_challenge(result.html) else (
            result.error or "fetch failed"
        )
        self._add_page_reading(service, reason)

    def _parse_page(self, html: str, service: CertificateService, *, method: str) -> bool:
        soup = soup_from_html(html)
        root = find_main_content(soup)
        pending: list[tuple[str, str, str, str, str]] = []
        information_count = 0
        section = ""

        for element in root.find_all(["h2", "h3", "h4", "p", "li"]):
            if element.name in {"h2", "h3", "h4"}:
                section = clean_text(element.get_text(" ", strip=True))
                continue
            if element.name == "p":
                text = clean_text(element.get_text(" ", strip=True))
                if text and "appointment is required" in text.lower():
                    pending.append((text, "procedure", section or "Walk-in Application", "no", ""))
                continue
            if element.find_parent("li") is not None:
                continue
            text = clean_text(element.get_text(" ", strip=True))
            if not text or text.lower() in _NAV_ITEMS or len(text) < 8:
                continue
            role, conditional, condition = _classify(text, section)
            if role == "procedure":
                information_count += 1
            pending.append((text, role, section or service.information_section, conditional, condition))

        if information_count < 4:
            return False

        notes = f"Fetched via {method}"
        for order, (text, role, item_section, conditional, condition) in enumerate(pending, start=1):
            self._add_item(
                service,
                text,
                role=role,
                section=item_section,
                order=order,
                status="success",
                notes=notes,
                conditional=conditional,
                condition=condition,
            )
        return True

    def _add_page_reading(self, service: CertificateService, reason: str) -> None:
        notes = f"{_READING_NOTE} ({reason})"
        order = 0
        for text in service.procedures:
            order += 1
            self._add_item(
                service,
                text,
                role="procedure",
                section="Walk-in Application",
                order=order,
                status="partial",
                notes=notes,
            )
        for text in service.information_items:
            order += 1
            self._add_item(
                service,
                text,
                role="procedure",
                section=service.information_section,
                order=order,
                status="partial",
                notes=notes,
            )
        for text in service.eligibility:
            order += 1
            self._add_item(
                service,
                text,
                role="eligibility",
                section=service.eligibility_section,
                order=order,
                status="partial",
                notes=notes,
            )

    def _add_item(
        self,
        service: CertificateService,
        text: str,
        *,
        role: str,
        section: str,
        order: int,
        status: str,
        notes: str,
        conditional: str = "no",
        condition: str = "",
    ) -> None:
        self.add(
            service_name=service.service_name,
            service_category="Civil Registration",
            target_document=service.target_document,
            transaction_type="certificate_request",
            applicant_type=service.applicant_type,
            requirement_name=text[:500],
            requirement_description=text[:500],
            requirement_role=role,
            conditional=conditional,
            condition=condition,
            issuing_agency="PSA",
            application_method=service.application_method,
            appointment_required=service.appointment_required,
            location=service.location,
            source_url=service.url,
            source_section=section,
            requirement_order=order,
            scrape_status=status,
            notes=notes,
        )


def _is_challenge(html: str) -> bool:
    lower = (html or "").lower()
    return "just a moment" in lower or "performing security verification" in lower


def _classify(text: str, section: str) -> tuple[str, str, str]:
    lower = text.lower()
    section_lower = section.lower()
    if (
        "nondisclosure" in section_lower
        or "article 7" in section_lower
        or lower.startswith("the person himself")
        or lower.startswith("his spouse")
        or lower.startswith("the court or proper")
        or lower.startswith("in case of the person's death")
    ):
        return "eligibility", "no", ""
    if "authorization letter" in lower or "special power of attorney" in lower:
        return (
            "supporting_document",
            "yes",
            "Request is filed by a representative of the document owner",
        )
    if "valid id" in lower or "identification card" in lower:
        representative = "representative" in lower or "authorized" in lower
        return (
            "acceptable_id",
            "yes" if representative else "no",
            "Request is filed by a representative of the document owner" if representative else "",
        )
    return "procedure", "no", ""
