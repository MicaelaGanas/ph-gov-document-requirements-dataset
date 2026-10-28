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
        result = self.fetch_requirements_page(self.PRIMARY_URL, spa=True)
        if result.ok and self._parse_supporting_documents(result.html):
            return
        self._add_verified_supporting_documents(
            result.error or "philsys.gov.ph is under maintenance"
        )

    def _parse_supporting_documents(self, html: str) -> bool:
        soup = soup_from_html(html)
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
                    self._add_supporting_option(
                        item.rstrip(";").strip(),
                        current_tier,
                        tier_title,
                        order,
                        scrape_status="success",
                    )
        return order > 0

    def _add_verified_supporting_documents(self, reason: str) -> None:
        """Last live reading of the supporting-documents page, kept while the site is down."""
        note = (
            "Verified reading of https://philsys.gov.ph/supporting-documents/ from 2026-08-27. "
            f"The live page could not be read ({reason}). "
            "Each primary line is one option. The birth certificate and one government ID stay one option."
        )
        order = 0
        for tier, items in (
            ("primary", _PRIMARY_OPTIONS),
            ("secondary", _SECONDARY_OPTIONS),
        ):
            for item in items:
                order += 1
                self._add_supporting_option(item, tier, tier.title() + " supporting documents", order, note)

    def _add_supporting_option(
        self,
        item: str,
        current_tier: str,
        tier_title: str,
        order: int,
        note: str = "",
        scrape_status: str = "partial",
    ) -> None:
        self.add(
            service_name="National ID Registration",
            service_category="Civil Registration / National ID",
            target_document="PhilSys National ID",
            transaction_type="new_registration",
            applicant_type="Filipino citizen or resident",
            requirement_name=item,
            source_url=self.PRIMARY_URL,
            requirement_role="acceptable_id",
            conditional="yes",
            condition=(
                "Any one primary supporting document"
                if current_tier == "primary"
                else "No primary supporting document is available. Any one secondary document"
            ),
            notes=note
            or (
                "One complete primary option. A birth certificate paired with one government ID stays one option."
                if current_tier == "primary"
                else "Secondary document accepted only when the registrant has no primary supporting document."
            ),
            issuing_agency="Various (see requirement)",
            application_method="walk-in",
            appointment_required="no",
            location="PSA/LGU/mall registration centers",
            source_section=tier_title,
            requirement_order=order,
            scrape_status=scrape_status,
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


# Last successful reading of the supporting-documents page (2026-08-27).
# Letter-shape errors from that extract (I rendered as l) are corrected here.
_PRIMARY_OPTIONS = (
    "PSA-issued Certificate of Live Birth and one (1) government-issued identification document which bears a full name, front-facing photograph, and signature or thumb mark",
    "Philippine Passport or ePassport issued by the Department of Foreign Affairs (DFA)",
    "Unified Multi-purpose Identification (UMID) Card issued by the Government Service Insurance System (GSIS) or Social Security System (SSS)",
    "Student's License Permit or Non-Professional/Professional Driver's License issued by the LTO",
)

_SECONDARY_OPTIONS = (
    "PSA-issued Certificate of Live Birth or National Statistics Office (NSO)-issued Certificate of Live Birth with Birth Reference Number (BreN)",
    "Local Civil Registry Office (LCRO)-issued Certificate of Live Birth",
    "PSA-issued Report of Birth",
    "PSA-issued Certificate of Foundling",
    "Integrated Bar of the Philippines (IBP) Identification Card",
    "Professional Regulatory Commission (PRC) ID",
    "Seaman's Book (Seafarer's Record Book)",
    "Overseas Workers Welfare Administration (OWWA) ID",
    "Senior Citizen's ID issued by the Office of Senior Citizens Affairs (OSCA) and/or Local Government Units (LGU)",
    "Social Security System (SSS) ID",
    "Pantawid Pamilyang Pilipino Program (4Ps) ID",
    "License to Own or Possess Firearms (LTOPF)",
    "National Bureau of Investigation (NBI) Clearance",
    "Police Clearance/ID",
    "Solo Parent's ID",
    "Person with Disability (PWD) ID issued by the National Council of Disability Affairs (NCDA) or its regional counterpart, Office of the Mayor, Department of Social Welfare and Development (DSWD) Office and other participating organizations with a Memorandum of Agreement with the Department of Health (DOH)",
    "Voter's ID issued by the Commission on Elections (COMELEC)",
    "Postal ID issued by the Philippine Postal Corporation (PhlPost)",
    "Taxpayer Identification Number (TIN) ID",
    "PhilHealth ID",
    "Special Resident Retiree's Visa (SRRV) issued by the Philippine Retirement Authority (PRA)",
    "National ID from other countries",
    "Residence ID from other countries",
    "Professional Identification Card issued by the Maritime Industry Authority (MARINA)",
    "Eligibility Card issued by the Civil Service Commission",
    "Dependent's ID issued by the Armed Forces of the Philippines (AFP) and Philippine National Police (PNP)",
    "Employee ID",
    "School ID (for pre-school, elementary and signature/thumbmark of the ID owner is not required)",
    "City/Municipal ID",
    "Barangay Clearance/Certificate",
    "Barangay ID",
    "Voter's Certification issued by the COMELEC, or Prison Record",
    "Certificate of Detention",
)
