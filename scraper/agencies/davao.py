"""Davao City LGU service requirements."""

from __future__ import annotations

from scraper.base import BaseScraper, records_from_list_items
from scraper.parsers.generic import clean_text, find_main_content, soup_from_html


class DavaoCityScraper(BaseScraper):
    agency = "Davao City LGU"
    agency_code = "LGU-DAVAO"

    HOME_URL = "https://davaocity.gov.ph/"
    BUSINESS_PERMIT_URL = (
        "https://davaocity.gov.ph/services/processing-of-business-permits/"
    )

    def scrape(self) -> list:
        self._scrape_business_permits()
        return self.records()

    def _scrape_business_permits(self) -> None:
        result = self.fetch(self.BUSINESS_PERMIT_URL)
        if not result.ok:
            self.add_blocked_notice(
                service_name="Business Permit Processing",
                source_url=self.BUSINESS_PERMIT_URL,
                reason=result.error or "fetch failed",
            )
            return

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        paragraphs = [clean_text(p.get_text()) for p in root.find_all("p")]
        combined = " ".join(p for p in paragraphs if p)
        if combined:
            self.add(
                service_name="Business Permit Processing",
                service_category="LGU Business Licensing",
                target_document="Davao City Business Permit",
                transaction_type="new_application|renewal",
                applicant_type="Business owner / enterprise",
                requirement_name="Business permit application overview",
                requirement_description=combined[:1500],
                requirement_role="procedure",
                application_method="walk_in",
                appointment_required="unknown",
                location="Business Bureau, Ground Floor SP Bldg., San Pedro St., Davao City",
                source_url=self.BUSINESS_PERMIT_URL,
                source_section="Processing of Business Permits",
                notes="Detailed checklist published as GIF on city website; contact Business Bureau for full list",
            )

        records_from_list_items(
            self,
            html=result.html,
            source_url=self.BUSINESS_PERMIT_URL,
            service_name="Business Permit Processing",
            target_document="Davao City Business Permit",
            transaction_type="new_application|renewal",
            applicant_type="Business owner",
            application_method="walk_in",
            location="Business Bureau, Davao City",
            scrape_status="partial",
        )
