"""Pag-IBIG membership registration requirements."""

from __future__ import annotations

from scraper.base import BaseScraper


class PagIBIGScraper(BaseScraper):
    agency = "Pag-IBIG Fund"
    agency_code = "PAGIBIG"

    HOME_URL = "https://www.pagibigfund.gov.ph/"
    MEMBERSHIP_URL = "https://www.pagibigfund.gov.ph/membership/"

    def scrape(self) -> list:
        result = self.fetch(self.MEMBERSHIP_URL)
        if not result.ok or "recaptcha" in result.html.lower():
            result = self.fetch(self.MEMBERSHIP_URL, use_browser=True)
        blocked = (
            not result.ok
            or "recaptcha" in result.html.lower()
            or "checking your browser" in result.html.lower()
        )
        if blocked or not _add_parsed_requirements(self, result.html):
            self.add_blocked_notice(
                service_name="Pag-IBIG Membership Registration",
                source_url=self.MEMBERSHIP_URL,
                reason=result.error or "The membership page did not return a checklist",
                notes="No seed list is stored.",
            )
        return self.records()


def _add_parsed_requirements(scraper: PagIBIGScraper, html: str) -> bool:
    from scraper.parsers.generic import clean_text, find_main_content, soup_from_html

    if not html:
        return False
    root = find_main_content(soup_from_html(html))
    heading = next(
        (
            tag
            for tag in root.find_all(["h1", "h2", "h3", "h4"])
            if "requirement" in tag.get_text(" ", strip=True).lower()
        ),
        None,
    )
    if heading is None:
        return False
    added = 0
    for item in heading.find_all_next("li"):
        if item.find_previous(["h1", "h2", "h3", "h4"]) != heading:
            break
        text = clean_text(item.get_text(" ", strip=True))
        if len(text) < 12 or len(text) > 240:
            continue
        lower = text.lower()
        if not any(token in lower for token in ("id", "form", "certificate", "document", "income")):
            continue
        added += 1
        scraper.add(
            service_name="Pag-IBIG Membership Registration",
            service_category="Housing / Savings Fund",
            target_document="Pag-IBIG MID / Membership",
            transaction_type="new_registration",
            applicant_type="Employee, self-employed, OFW, or voluntary member",
            requirement_name=text,
            source_url=scraper.MEMBERSHIP_URL,
            requirement_role="required_document",
            application_method="online_and_employer",
            appointment_required="no",
            source_section="Membership page",
            requirement_order=added,
        )
    return added >= 2
