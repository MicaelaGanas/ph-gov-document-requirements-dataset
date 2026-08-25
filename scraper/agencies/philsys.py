"""PhilSys (PSA) National ID registration requirements."""

from __future__ import annotations

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, find_main_content, soup_from_html


class PhilSysScraper(BaseScraper):
    agency = "Philippine Statistics Authority (PhilSys)"
    agency_code = "PHILSYS"

    PRIMARY_URL = "https://philsys.gov.ph/supporting-documents/"
    PROCESS_URL = "https://philsys.gov.ph/registration-process/"

    def scrape(self) -> list:
        self._scrape_supporting_documents()
        self._scrape_registration_process()
        return self.records()

    def _scrape_supporting_documents(self) -> None:
        result = self.fetch(self.PRIMARY_URL)
        if not result.ok:
            self.add_blocked_notice(
                service_name="National ID Registration",
                source_url=self.PRIMARY_URL,
                reason=result.error or "fetch failed",
            )
            return

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        order = 0
        seen_items: set[str] = set()
        current_tier = ""

        for h2 in root.find_all("h2"):
            tier_title = clean_text(h2.get_text())
            tier_lower = tier_title.lower()
            if "primary" in tier_lower:
                current_tier = "primary"
            elif "secondary" in tier_lower:
                current_tier = "secondary"
            else:
                continue

            # Collect list items until the next h2
            for sibling in h2.find_all_next():
                if sibling.name == "h2":
                    break
                if sibling.name != "ul":
                    continue
                for li in sibling.find_all("li", recursive=False):
                    item = clean_text(li.get_text(" ", strip=True))
                    if not item or len(item) < 4:
                        continue
                    norm = item.lower()[:120]
                    if norm in seen_items:
                        continue
                    seen_items.add(norm)
                    order += 1

                    if current_tier == "primary":
                        self.add(
                            service_name="National ID Registration",
                            service_category="Civil Registration / National ID",
                            target_document="PhilSys National ID",
                            transaction_type="new_registration",
                            applicant_type="Filipino citizen or resident",
                            requirement_name=item,
                            source_url=self.PRIMARY_URL,
                            requirement_role="required_document",
                            conditional="no",
                            condition="",
                            notes="Primary supporting document option (registrant may bring any one complete primary set)",
                            issuing_agency="PSA / various",
                            application_method="walk-in",
                            appointment_required="no",
                            location="PSA/LGU/mall registration centers",
                            source_section=tier_title,
                            split_compounds=True,
                            requirement_order=order,
                        )
                    else:
                        role = (
                            "acceptable_id"
                            if self._is_id_like(item)
                            else "required_document"
                        )
                        self.add(
                            service_name="National ID Registration",
                            service_category="Civil Registration / National ID",
                            target_document="PhilSys National ID",
                            transaction_type="new_registration",
                            applicant_type="Filipino citizen or resident",
                            requirement_name=item,
                            source_url=self.PRIMARY_URL,
                            requirement_role=role,
                            conditional="yes",
                            condition="If registrant has no primary supporting document",
                            notes="Secondary/alternative supporting ID or document for PhilSys registration",
                            issuing_agency="Various (see requirement)",
                            application_method="walk-in",
                            appointment_required="no",
                            location="PSA/LGU/mall registration centers",
                            source_section=tier_title,
                            requirement_order=order,
                        )

    def _scrape_registration_process(self) -> None:
        result = self.fetch(self.PROCESS_URL)
        if not result.ok:
            return

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        order = 0
        nav_skip = {
            "home",
            "contact us",
            "testimonials",
            "news and events",
            "about national id",
            "registration registration process",
            "use cases",
            "the national id",
        }

        content_blocks = root.select(".elementor-widget-text-editor")
        if not content_blocks:
            content_blocks = [root]

        for block in content_blocks:
            heading = block.find_previous(["h2", "h3", "h4", "p"])
            section = clean_text(heading.get_text()) if heading else "Registration Steps"
            for li in block.select("ul > li"):
                item = clean_text(li.get_text(" ", strip=True))
                if not item or len(item) < 8:
                    continue
                if item.lower() in nav_skip or any(s in item.lower() for s in nav_skip):
                    continue
                order += 1
                self.add(
                    service_name="National ID Registration",
                    service_category="Civil Registration / National ID",
                    target_document="PhilSys National ID",
                    transaction_type="new_registration",
                    applicant_type="Filipino citizen or resident",
                    requirement_name=item,
                    source_url=self.PROCESS_URL,
                    requirement_role="procedure",
                    application_method="walk-in",
                    appointment_required="no",
                    location="Registration centers nationwide",
                    source_section=section,
                    requirement_order=order,
                )

    @staticmethod
    def _is_id_like(text: str) -> bool:
        lower = text.lower()
        doc_tokens = ("certificate of live birth", "report of birth", "foundling")
        if any(t in lower for t in doc_tokens):
            return False
        id_tokens = (" id", "identification", "license", "passport", "clearance", " card")
        return any(t in lower for t in id_tokens)
