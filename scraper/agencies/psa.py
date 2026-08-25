"""PSA civil registration requirements."""

from __future__ import annotations

from scraper.base import BaseScraper, records_from_list_items
from scraper.http import fetch_page
from scraper.parsers.generic import clean_text, find_main_content, soup_from_html


class PSAScraper(BaseScraper):
    agency = "Philippine Statistics Authority"
    agency_code = "PSA"

    CIVIL_REG_URL = "https://psa.gov.ph/civilregistration"
    SERBILIS_URL = "https://psa.gov.ph/"

    def scrape(self) -> list:
        result = fetch_page(
            self.CIVIL_REG_URL,
            use_cloudscraper=True,
            retries=2,
            browser_fallback=True,
        )
        if result.ok and len(result.html) >= 5000:
            self._parse_page(result.html, result.url, method=result.method)
        else:
            self._seed_fallback(result.error or "fetch failed")
        return self.records()

    def _parse_page(self, html: str, source_url: str, method: str = "requests") -> None:
        soup = soup_from_html(html)
        root = find_main_content(soup)
        notes = f"Fetched via {method}"
        records_from_list_items(
            self,
            html=html,
            source_url=source_url,
            service_name="Civil Registration (Birth, Marriage, Death Certificates)",
            target_document="PSA Certificate (Birth|Marriage|Death|CENOMAR|etc.)",
            transaction_type="certificate_request",
            applicant_type="Document owner or authorized representative",
            application_method="online_and_walk_in",
            appointment_required="no",
            root_selector=None,
            only_direct_li=False,
        )
        # Also capture paragraph-based requirements
        order = len(self._records)
        for p in root.find_all("p"):
            text = clean_text(p.get_text(" ", strip=True))
            if not text or len(text) < 15:
                continue
            lower = text.lower()
            if any(
                k in lower
                for k in ("requirement", "document", "valid id", "certificate", "submit", "bring")
            ):
                order += 1
                self.add(
                    service_name="Civil Registration (Birth, Marriage, Death Certificates)",
                    service_category="Civil Registration",
                    target_document="PSA Certificate (Birth|Marriage|Death|CENOMAR|etc.)",
                    transaction_type="certificate_request",
                    applicant_type="Document owner or authorized representative",
                    requirement_name=text[:500],
                    source_url=source_url,
                    requirement_role="required_document",
                    application_method="online_and_walk_in",
                    source_section="Page content",
                    requirement_order=order,
                    notes=notes,
                )

    def _seed_fallback(self, reason: str) -> None:
        self.add_blocked_notice(
            service_name="Civil Registration (Birth, Marriage, Death Certificates)",
            source_url=self.CIVIL_REG_URL,
            reason=reason,
            notes=(
                "Install Playwright to bypass Cloudflare: "
                "pip install playwright && playwright install chromium && python scrape.py --browser"
            ),
        )
        for req in (
            "Valid government-issued ID of requester",
            "Accomplished PSA certificate application form",
            "Payment of applicable certificate fees",
            "Authorization letter and ID of representative (if applying through representative)",
        ):
            self.add(
                service_name="Civil Registration (Birth, Marriage, Death Certificates)",
                service_category="Civil Registration",
                target_document="PSA Certificate (Birth|Marriage|Death|CENOMAR|etc.)",
                transaction_type="certificate_request",
                applicant_type="Document owner or authorized representative",
                requirement_name=req,
                requirement_description=req,
                requirement_role="required_document",
                application_method="online_and_walk_in",
                appointment_required="no",
                source_url=self.CIVIL_REG_URL,
                source_section="Baseline (manual seed - site blocked)",
                scrape_status="seed",
                notes="Seeded baseline; re-run with --browser after installing Playwright",
            )
