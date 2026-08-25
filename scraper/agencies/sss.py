"""SSS number / membership registration requirements."""

from __future__ import annotations

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, find_main_content, soup_from_html
from scraper.parsers.requirements import infer_requirement_role


class SSSScraper(BaseScraper):
    agency = "Social Security System"
    agency_code = "SSS"

    MEMBER_URL = "https://www.sss.gov.ph/become-an-sss-member/"
    VALID_IDS_URL = "https://www.sss.gov.ph/list-of-valid-ids/"

    def scrape(self) -> list:
        self._scrape_become_member()
        self._scrape_valid_ids()
        return self.records()

    def _scrape_become_member(self) -> None:
        result = self.fetch(self.MEMBER_URL)
        if not result.ok:
            self.add_blocked_notice(
                service_name="SSS Number / Membership Registration",
                source_url=self.MEMBER_URL,
                reason=result.error or "fetch failed",
            )
            return

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        order = 0
        current_section = "Become an SSS Member"

        # Only parse the main registration collapse panel, not FAQ/amendment panels
        for panel in root.select(".collapse, .card-body, .entry-content"):
            panel_id = (panel.get("id") or "").lower()
            if panel_id and not any(k in panel_id for k in ("collapse-1", "be-an", "member")):
                if "collapse" in panel_id and panel_id not in {"collapse-1"}:
                    continue

        for element in root.find_all(["h1", "h2", "h3"]):
            heading = clean_text(element.get_text())
            if heading:
                current_section = heading

        for li in root.select(".entry-content li, .collapse-1 li"):
            text = clean_text(li.get_text(" ", strip=True))
            if not text or len(text) < 10:
                continue
            lower = text.lower()
            if any(skip in lower for skip in ("login to my.sss", "click the link", "frequently asked")):
                continue
            if "change or update" in current_section.lower() and "postal id" in lower:
                continue  # ID list items belong on valid-ids page only

            order += 1
            role = infer_requirement_role(text, section=current_section)
            if "supporting document" in lower or "upload" in lower:
                role = "required_document"
            elif any(k in lower for k in ("go to", "choose from", "check the", "fill out", "register")):
                role = "procedure"

            self.add(
                service_name="SSS Number / Membership Registration",
                service_category="Social Insurance",
                target_document="SS Number / SSS Membership",
                transaction_type="new_registration",
                applicant_type="Employee|Self-Employed|OFW|Voluntary|Non-Working Spouse",
                requirement_name=text,
                source_url=self.MEMBER_URL,
                requirement_role=role,
                application_method="online",
                appointment_required="no",
                source_section=current_section,
                requirement_order=order,
                notes="Mandatory online registration per RA 11032 (July 15, 2020)",
            )

    def _scrape_valid_ids(self) -> None:
        result = self.fetch(self.VALID_IDS_URL)
        if not result.ok:
            return

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        order = 0
        current_section = "Primary ID and Document Requirements"

        for element in root.find_all(["strong", "b", "h2", "h3", "p"]):
            if element.name in {"strong", "b", "h2", "h3"}:
                heading = clean_text(element.get_text())
                if heading and len(heading) < 150:
                    current_section = heading
                continue

            if element.name == "p":
                text = clean_text(element.get_text())
                if text.startswith("In the absence of"):
                    # Section header for fallback ID group — not a requirement itself
                    current_section = text
                continue

        for ul in root.select(".entry-content ul"):
            heading = ul.find_previous(["strong", "b", "h2", "h3", "p"])
            section = clean_text(heading.get_text()) if heading else current_section
            is_fallback = "absence" in section.lower() or "in the absence" in section.lower()

            for li in ul.find_all("li", recursive=False):
                text = clean_text(li.get_text(" ", strip=True))
                if not text or len(text) < 4:
                    continue
                # Skip nested header rows that are not actual IDs
                if text.lower().startswith("in the absence of"):
                    continue

                order += 1
                role = "acceptable_id" if is_fallback else "required_document"
                if is_fallback:
                    conditional = "yes"
                    condition = "If primary ID/document is unavailable"
                else:
                    conditional = "no"
                    condition = ""

                self.add(
                    service_name="SSS Number / Membership Registration",
                    service_category="Social Insurance",
                    target_document="SS Number / SSS Membership",
                    transaction_type="new_registration|data_amendment",
                    applicant_type="SSS member or applicant",
                    requirement_name=text,
                    source_url=self.VALID_IDS_URL,
                    requirement_role=role,
                    conditional=conditional,
                    condition=condition,
                    application_method="online",
                    appointment_required="no",
                    source_section=section,
                    requirement_order=order,
                    notes=(
                        "Acceptable supporting ID/document for SS number issuance"
                        if role == "acceptable_id"
                        else "Primary ID or document for SS number issuance"
                    ),
                )
