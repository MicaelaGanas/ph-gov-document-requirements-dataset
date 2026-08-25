"""LTO driver's license requirements."""

from __future__ import annotations

from scraper.base import BaseScraper, records_from_list_items
from scraper.http import fetch_page
from scraper.parsers.generic import clean_text, find_main_content, soup_from_html


class LTOScraper(BaseScraper):
    agency = "Land Transportation Office"
    agency_code = "LTO"

    HOME_URL = "https://portal.lto.gov.ph/"
    FALLBACK_URLS = (
        "https://lto.gov.ph/",
        "https://lto.gov.ph/lto-forms-and-restrictions.html",
    )

    def scrape(self) -> list:
        result = fetch_page(
            self.HOME_URL,
            use_cloudscraper=True,
            retries=1,
            browser_fallback=True,
        )
        if result.ok:
            count_before = len(self._records)
            self._parse_page(result.html, result.url, method=result.method)
            if len(self._records) > count_before:
                return self.records()

        for alt in self.FALLBACK_URLS:
            alt_result = fetch_page(alt, browser_fallback=True)
            if alt_result.ok:
                count_before = len(self._records)
                self._parse_page(alt_result.html, alt_result.url, method=alt_result.method)
                if len(self._records) > count_before:
                    return self.records()

        self._seed_fallback(
            result.error
            or "LTO main site blocked by Cloudflare; portal.lto.gov.ph has no public requirements list"
        )
        return self.records()

    def _parse_page(self, html: str, source_url: str, method: str = "requests") -> None:
        soup = soup_from_html(html)
        root = find_main_content(soup)
        notes = f"Fetched via {method}"

        records_from_list_items(
            self,
            html=html,
            source_url=source_url,
            service_name="Driver's License Application / Renewal",
            target_document="Driver's License / Student Permit",
            transaction_type="new_application|renewal",
            applicant_type="Filipino citizen or resident",
            application_method="online_and_walk_in",
            appointment_required="unknown",
            location="LTO licensing offices",
        )

        order = len(self._records)
        for element in root.find_all(["p", "li"]):
            text = clean_text(element.get_text(" ", strip=True))
            if not text or len(text) < 10:
                continue
            lower = text.lower()
            if any(
                k in lower
                for k in (
                    "medical certificate",
                    "driver",
                    "license",
                    "valid id",
                    "birth certificate",
                    "requirement",
                    "document",
                    "student permit",
                )
            ):
                order += 1
                role = "acceptable_id" if "valid id" in lower else "required_document"
                self.add(
                    service_name="Driver's License Application / Renewal",
                    service_category="Transportation",
                    target_document="Driver's License / Student Permit",
                    transaction_type="new_application|renewal",
                    applicant_type="Filipino citizen or resident",
                    requirement_name=text[:500],
                    source_url=source_url,
                    requirement_role=role,
                    application_method="online_and_walk_in",
                    location="LTO licensing offices",
                    source_section="Page content",
                    requirement_order=order,
                    notes=notes,
                )

    def _seed_fallback(self, reason: str) -> None:
        self.add_blocked_notice(
            service_name="Driver's License Application / Renewal",
            source_url=self.HOME_URL,
            reason=reason,
            notes=(
                "Install Playwright: pip install playwright && playwright install chromium "
                "&& python scrape.py --browser"
            ),
        )
        baseline = [
            ("Medical Certificate (LTO-accredited clinic)", "required_document"),
            ("Valid government-issued ID", "acceptable_id"),
            ("Completed Application for Permits and Licenses (APL) form", "required_document"),
            ("Driver's Education Certificate (for student permit/new license)", "required_document"),
            ("Existing Driver's License (for renewal)", "required_document"),
        ]
        for idx, (req, role) in enumerate(baseline, start=1):
            self.add(
                service_name="Driver's License Application / Renewal",
                service_category="Transportation",
                target_document="Driver's License / Student Permit",
                transaction_type="new_application|renewal",
                applicant_type="Filipino citizen or resident",
                requirement_name=req,
                requirement_description=req,
                requirement_role=role,
                application_method="online_and_walk_in",
                appointment_required="unknown",
                location="LTO licensing offices",
                source_url=self.HOME_URL,
                source_section="Baseline (manual seed - site blocked)",
                requirement_order=idx,
                scrape_status="seed",
            )
