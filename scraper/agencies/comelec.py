"""COMELEC voter registration requirements."""

from __future__ import annotations

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, soup_from_html


class COMELECScraper(BaseScraper):
    agency = "Commission on Elections"
    agency_code = "COMELEC"

    HOME_URL = "https://www.comelec.gov.ph/"
    REG_URL = "https://www.comelec.gov.ph/?r=VoterRegistration/RegistrationProcedures"

    def scrape(self) -> list:
        result = self.fetch(self.REG_URL)
        dynamic_shell = result.ok and "html-page-container" in result.html
        if not result.ok or dynamic_shell:
            self.add_blocked_notice(
                service_name="Voter Registration",
                source_url=self.REG_URL,
                reason="Content loaded via JavaScript" if dynamic_shell else (result.error or "fetch failed"),
                notes="COMELEC pages load content dynamically. Use COMELEC VRR portal or iRehistro.",
            )
            for idx, req in enumerate(
                (
                    "Valid ID or proof of identity",
                    "Accomplished COMELEC Registration Form (CEF-1)",
                    "Proof of residency in the precinct",
                    "Personal appearance at COMELEC office or registration site",
                ),
                start=1,
            ):
                self.add(
                    service_name="Voter Registration",
                    service_category="Elections",
                    target_document="Voter's Certificate / Registration",
                    transaction_type="new_registration|transfer|reactivation",
                    applicant_type="Filipino citizen aged 18+ (or 15-17 for SK)",
                    requirement_name=req,
                    requirement_description=req,
                    requirement_type="document" if "form" in req.lower() or "id" in req.lower() else "procedure",
                    application_method="walk_in",
                    appointment_required="no",
                    location="COMELEC offices / registration sites",
                    source_url=self.REG_URL,
                    source_section="Baseline (manual seed - JS-rendered page)",
                    requirement_order=idx,
                    scrape_status="seed",
                )
        return self.records()
