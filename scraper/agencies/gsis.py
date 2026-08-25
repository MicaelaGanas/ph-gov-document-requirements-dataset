"""GSIS member services / forms."""

from __future__ import annotations

from scraper.base import BaseScraper
from scraper.http import fetch_page


class GSISScraper(BaseScraper):
    agency = "Government Service Insurance System"
    agency_code = "GSIS"

    HOME_URL = "https://www.gsis.gov.ph/"

    def scrape(self) -> list:
        result = fetch_page(self.HOME_URL, retries=2)
        blocked = not result.ok or "rejected" in result.html.lower() or len(result.html) < 1000
        if blocked:
            self.add_blocked_notice(
                service_name="GSIS Membership / eGSISMO Services",
                source_url=self.HOME_URL,
                reason=result.error or "WAF/request rejected",
                notes="Use GSIS eGSISMO portal for online transactions.",
            )

        for idx, req in enumerate(
            (
                "GSIS UMID eCard or valid GSIS ID",
                "Accomplished GSIS membership / update forms",
                "Certificate of Employment or agency certification (for new members)",
                "Birth certificate or valid government ID for identity verification",
            ),
            start=1,
        ):
            self.add(
                service_name="GSIS Membership / eGSISMO Services",
                service_category="Social Insurance (Government Employees)",
                target_document="GSIS Membership / UMID",
                transaction_type="new_registration|update",
                applicant_type="Government employee|Dependent|Retiree",
                requirement_name=req,
                requirement_description=req,
                requirement_type="document",
                issuing_agency="GSIS|PSA|Employing agency",
                application_method="online_and_walk_in",
                appointment_required="unknown",
                location="GSIS branches / eGSISMO",
                source_url=self.HOME_URL,
                source_section="Baseline (seed - site blocked)",
                requirement_order=idx,
                scrape_status="seed" if blocked else "partial",
            )
        return self.records()
