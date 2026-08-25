"""Pag-IBIG membership registration requirements."""

from __future__ import annotations

from scraper.base import BaseScraper
from scraper.http import fetch_page


class PagIBIGScraper(BaseScraper):
    agency = "Pag-IBIG Fund"
    agency_code = "PAGIBIG"

    HOME_URL = "https://www.pagibigfund.gov.ph/"
    MEMBERSHIP_URL = "https://www.pagibigfund.gov.ph/membership/"

    def scrape(self) -> list:
        result = fetch_page(self.MEMBERSHIP_URL, retries=3)
        blocked = (
            not result.ok
            or "recaptcha" in result.html.lower()
            or "checking your browser" in result.html.lower()
        )
        if blocked:
            self.add_blocked_notice(
                service_name="Pag-IBIG Membership Registration",
                source_url=self.MEMBERSHIP_URL,
                reason=result.error or "Bot protection (reCAPTCHA)",
                notes="Use Pag-IBIG Virtual Branch or employer enrollment.",
            )

        for idx, req in enumerate(
            (
                "Pag-IBIG Membership Form (HDMF Form)",
                "Valid government-issued ID",
                "Proof of income or employment (for voluntary/self-employed)",
                "Employer enrollment for formal sector employees",
            ),
            start=1,
        ):
            self.add(
                service_name="Pag-IBIG Membership Registration",
                service_category="Housing / Savings Fund",
                target_document="Pag-IBIG MID / Membership",
                transaction_type="new_registration",
                applicant_type="Employee|Self-employed|OFW|Voluntary",
                requirement_name=req,
                requirement_description=req,
                requirement_type="document",
                application_method="online_and_employer",
                appointment_required="no",
                source_url=self.MEMBERSHIP_URL,
                source_section="Baseline (seed - site protected)",
                requirement_order=idx,
                scrape_status="seed" if blocked else "partial",
            )
        return self.records()
