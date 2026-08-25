"""PhilHealth member registration requirements."""

from __future__ import annotations

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, soup_from_html


class PhilHealthScraper(BaseScraper):
    agency = "Philippine Health Insurance Corporation"
    agency_code = "PHILHEALTH"

    REGISTRATION_URL = (
        "https://www.philhealth.gov.ph/members/formal/registration.php"
    )

    def scrape(self) -> list:
        result = self.fetch(self.REGISTRATION_URL)
        if not result.ok:
            self.add_blocked_notice(
                service_name="PhilHealth Member Registration (Formal Economy)",
                source_url=self.REGISTRATION_URL,
                reason=result.error or "fetch failed",
            )
            return self.records()

        soup = soup_from_html(result.html)
        order = 0
        current_applicant = "General"
        for h5 in soup.find_all("h5"):
            heading = clean_text(h5.get_text())
            if heading:
                current_applicant = heading
            ul = h5.find_next("ul")
            if not ul:
                continue
            for li in ul.find_all("li"):
                text = clean_text(li.get_text(" ", strip=True))
                if not text:
                    continue
                order += 1
                lower = text.lower()
                if "form" in lower or "pmrf" in lower:
                    role = "required_document"
                elif "report your pin" in lower or "indicate the same in their er2" in lower:
                    role = "procedure"
                elif "premium" in lower or "contribution" in lower:
                    role = "metadata"
                else:
                    role = "procedure"
                self.add(
                    service_name="PhilHealth Member Registration (Formal Economy)",
                    service_category="Health Insurance",
                    target_document="PhilHealth Member Data Record / PhilHealth ID",
                    transaction_type="new_registration",
                    applicant_type=current_applicant,
                    requirement_name=text[:250],
                    requirement_description=text,
                    requirement_role=role,
                    application_method="employer_mediated",
                    appointment_required="no",
                    location="Employer HR department",
                    source_url=self.REGISTRATION_URL,
                    source_section=current_applicant,
                    requirement_order=order,
                )

        return self.records()
