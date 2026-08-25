"""DTI Business Name Registration requirements."""

from __future__ import annotations

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, find_main_content, soup_from_html

_SEED_ITEMS: tuple[tuple[str, str], ...] = (
    ("Valid government-issued ID of owner", "acceptable_id"),
    ("Proposed business name (3 name choices recommended)", "procedure"),
    ("Business address and contact details", "procedure"),
    ("Line of business / business activity description", "procedure"),
    ("Payment of registration fee", "fee"),
)


class DTIScraper(BaseScraper):
    agency = "Department of Trade and Industry"
    agency_code = "DTI"

    BNRS_URL = "https://bnrs.dti.gov.ph/"

    def scrape(self) -> list:
        result = self.fetch(self.BNRS_URL)
        if result.ok:
            soup = soup_from_html(result.html)
            root = find_main_content(soup)
            text = clean_text(root.get_text(" ", strip=True))
            if "business name" in text.lower():
                self.add(
                    service_name="Business Name Registration",
                    service_category="Business Registration",
                    target_document="DTI Certificate of Business Name Registration",
                    transaction_type="new_registration|renewal",
                    applicant_type="Sole proprietor",
                    requirement_name="DTI BNRS online registration via bnrs.dti.gov.ph",
                    requirement_description=text[:1000],
                    requirement_role="procedure",
                    application_method="online",
                    appointment_required="no",
                    source_url=self.BNRS_URL,
                    source_section="BNRS Landing Page",
                    notes="Detailed documentary requirements are collected during BNRS online application flow",
                )

        for idx, (req, role) in enumerate(_SEED_ITEMS, start=1):
            self.add(
                service_name="Business Name Registration",
                service_category="Business Registration",
                target_document="DTI Certificate of Business Name Registration",
                transaction_type="new_registration|renewal",
                applicant_type="Sole proprietor",
                requirement_name=req,
                requirement_description=req,
                requirement_role=role,
                application_method="online",
                appointment_required="no",
                location="bnrs.dti.gov.ph",
                source_url=self.BNRS_URL,
                source_section="Standard BNRS requirements (seed)",
                requirement_order=idx,
                scrape_status="seed" if not result.ok else "partial",
                notes="Verify fee schedule and ID list in BNRS portal at application time",
            )
        return self.records()
