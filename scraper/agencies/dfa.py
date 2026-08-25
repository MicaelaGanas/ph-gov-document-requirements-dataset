"""DFA passport requirements (consular portal only — no FAQ noise)."""

from __future__ import annotations

import re

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, find_main_content, infer_document_format, soup_from_html

# List-item text that is a section header, not an actual requirement.
_HEADER_PATTERNS = (
    "at least one of the following",
    "if unable to provide",
    "any of the following acceptable",
    "the following identification documents",
    "click here",
    "school records such as:",
    "all ids presented should",
    "for applicants based overseas, they may use",
    "the following are the additional requirements",
    "shall submit the following documents",
    "shall submit any of the following",
)


class DFAScraper(BaseScraper):
    agency = "Department of Foreign Affairs"
    agency_code = "DFA"

    ADULT_NEW_URL = (
        "https://consular.dfa.gov.ph/passport/10-passport/61-passport-requirements-new-adult"
    )
    VALID_IDS_URL = "https://consular.dfa.gov.ph/valid-ids-for-passport-application/"

    def scrape(self) -> list:
        self._scrape_adult_new_requirements()
        self._scrape_valid_ids()
        return self.records()

    def _scrape_adult_new_requirements(self) -> None:
        result = self.fetch(self.ADULT_NEW_URL)
        if not result.ok:
            self.add_blocked_notice(
                service_name="Passport Application (Adult New)",
                source_url=self.ADULT_NEW_URL,
                reason=result.error or "fetch failed",
            )
            self._seed_adult_new_requirements()
            return

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        section = "Core Requirements for Adult New Applications"
        order = 0

        for li in root.select("ol > li.subtitle"):
            text = _clean_name(clean_text(li.get_text(" ", strip=True)))
            if not text or _is_header(text):
                continue
            order += 1
            role = _classify_dfa_core(text)
            conditional = "yes" if "married female" in text.lower() else "no"
            condition = "Married female using spouse's last name" if conditional == "yes" else ""
            self.add(
                service_name="Passport Application (Adult New)",
                service_category="Travel Document",
                target_document="Philippine Passport",
                transaction_type="new_application",
                applicant_type="Adult (18+)",
                requirement_name=text,
                source_url=self.ADULT_NEW_URL,
                requirement_role=role,
                document_format=infer_document_format(text),
                conditional=conditional,
                condition=condition,
                issuing_agency="PSA / DFA",
                application_method="online_appointment_and_walk_in",
                appointment_required="yes",
                location="DFA consular offices",
                source_section=section,
                requirement_order=order,
            )

        for details in root.find_all("details"):
            summary = details.find("summary")
            section_name = clean_text(summary.get_text()) if summary else "Supporting Documents"
            for ul in details.find_all("ul", recursive=False):
                for li in ul.find_all("li", recursive=False):
                    nested = li.find("ul")
                    if nested:
                        for sub_li in nested.find_all("li", recursive=False):
                            for item in _split_supporting_item(
                                _clean_name(clean_text(sub_li.get_text(" ", strip=True)))
                            ):
                                if not item or _is_header(item):
                                    continue
                                order += 1
                                self._add_supporting(item, section_name, order, self.ADULT_NEW_URL)
                        continue

                    for item in _split_supporting_item(
                        _clean_name(clean_text(li.get_text(" ", strip=True)))
                    ):
                        if not item or _is_header(item):
                            continue
                        order += 1
                        self._add_supporting(item, section_name, order, self.ADULT_NEW_URL)

    def _add_supporting(
        self, text: str, section_name: str, order: int, source_url: str
    ) -> None:
        self.add(
            service_name="Passport Application (Adult New)",
            service_category="Travel Document",
            target_document="Philippine Passport",
            transaction_type="new_application",
            applicant_type="Adult (18+)",
            requirement_name=text,
            source_url=source_url,
            requirement_role="supporting_document",
            document_format=infer_document_format(text),
            conditional="yes",
            condition=section_name,
            issuing_agency="PSA / various",
            application_method="online_appointment_and_walk_in",
            appointment_required="yes",
            source_section=section_name,
            requirement_order=order,
        )

    def _scrape_valid_ids(self) -> None:
        result = self.fetch(self.VALID_IDS_URL)
        if not result.ok:
            self._seed_valid_ids()
            return

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        order = 0
        seen: set[str] = set()

        container = root.select_one(".sub-container") or root
        for ul in container.find_all("ul"):
            parent_heading = ul.find_previous(["h3", "h1", "p"])
            in_id_section = parent_heading and "acceptable" in clean_text(
                parent_heading.get_text()
            ).lower()
            if not in_id_section and ul.find_previous("h3", class_="headerTitle") is None:
                continue
            for li in ul.find_all("li", recursive=False):
                raw = clean_text(li.get_text(" ", strip=True))
                if not raw or len(raw) < 4 or _is_header(raw):
                    continue
                for name, notes in _expand_id_entries(raw):
                    key = name.lower()[:80]
                    if key in seen:
                        continue
                    seen.add(key)
                    order += 1
                    self.add(
                        service_name="Passport Application (Adult New)",
                        service_category="Travel Document",
                        target_document="Philippine Passport",
                        transaction_type="new_application",
                        applicant_type="Adult (18+)",
                        requirement_name=name,
                        source_url=self.VALID_IDS_URL,
                        requirement_role="acceptable_id",
                        conditional="no",
                        notes=notes or "Pick any one acceptable ID (with photocopy)",
                        issuing_agency="Various government agencies",
                        application_method="online_appointment_and_walk_in",
                        appointment_required="yes",
                        source_section="Acceptable IDs for Passport Application",
                        requirement_order=order,
                    )

    def _seed_adult_new_requirements(self) -> None:
        core = [
            ("Confirmed Online Appointment", "procedure"),
            ("Personal Appearance", "procedure"),
            ("Accomplished Application Form", "required_document"),
            (
                "Original and photocopy of PSA-issued Certificate of Live Birth on Security Paper",
                "required_document",
            ),
            ("Any acceptable government-issued ID with one (1) photocopy", "acceptable_id"),
        ]
        for idx, (req, role) in enumerate(core, start=1):
            self.add(
                service_name="Passport Application (Adult New)",
                service_category="Travel Document",
                target_document="Philippine Passport",
                transaction_type="new_application",
                applicant_type="Adult (18+)",
                requirement_name=req,
                source_url=self.ADULT_NEW_URL,
                requirement_role=role,
                document_format=infer_document_format(req),
                application_method="online_appointment_and_walk_in",
                appointment_required="yes",
                location="DFA consular offices",
                source_section="Core Requirements (seed)",
                requirement_order=idx,
                scrape_status="seed",
                notes="Seeded from consular.dfa.gov.ph; verify when site is accessible",
            )

    def _seed_valid_ids(self) -> None:
        ids = [
            "Philippine Identification (PhilID)",
            "Electronic Philippine ID / Digital National ID (printed copy)",
            "Social Security System (SSS) Card",
            "Government Service Insurance System (GSIS) Card",
            "Unified Multi-Purpose Identification (UMID) Card",
            "Land Transportation Office (LTO) Driver's License",
            "Professional Regulatory Commission (PRC) ID",
        ]
        for idx, req in enumerate(ids, start=1):
            self.add(
                service_name="Passport Application (Adult New)",
                service_category="Travel Document",
                target_document="Philippine Passport",
                transaction_type="new_application",
                applicant_type="Adult (18+)",
                requirement_name=req,
                source_url=self.VALID_IDS_URL,
                requirement_role="acceptable_id",
                application_method="online_appointment_and_walk_in",
                appointment_required="yes",
                source_section="Acceptable IDs (seed)",
                requirement_order=idx,
                scrape_status="seed",
            )


def _clean_name(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"[;\s]+and\s*$", "", text, flags=re.I)
    text = re.sub(r"[;\s]+or\s*$", "", text, flags=re.I)
    return text.strip(" ;,")


def _split_supporting_item(text: str) -> list[str]:
    """Split bundled supporting-document lines into atomic items."""
    if not text:
        return []
    if len(text) < 180:
        return [text]

    # Drop leading scenario explanation before the actual document list.
    for marker in (
        "the following are the additional requirements ",
        "shall submit the following documents: ",
        "shall submit any of the following documents: ",
        "for other reasons of reversion: ",
    ):
        lower = text.lower()
        if marker in lower:
            idx = lower.index(marker) + len(marker)
            text = text[idx:].strip()
            break

    parts = re.split(r";\s*(?:and|or)\s+", text)
    if len(parts) == 1:
        parts = re.split(r";\s+", text)

    cleaned = [_clean_name(p) for p in parts if _clean_name(p)]
    if len(cleaned) > 1 and all(len(p) > 15 for p in cleaned):
        return cleaned
    return [text]


def _expand_id_entries(raw: str) -> list[tuple[str, str]]:
    """Normalize acceptable-ID lines; split bundled school-ID cases."""
    entries: list[tuple[str, str]] = []

    if "school id" in raw.lower() and "for minor applicants" in raw.lower():
        minor_match = re.search(
            r"for minor applicants[^f]*(.+?)(?=for adult applicants|$)",
            raw,
            re.I,
        )
        adult_match = re.search(r"for adult applicants[^:]*-?\s*(.+)$", raw, re.I)
        if minor_match:
            entries.append(
                (
                    "Certificate of Enrolment with photo of minor and dry seal of school",
                    "For minor applicants when school ID is not applicable",
                )
            )
        if adult_match:
            entries.append(
                (
                    "School ID and Certificate of Registration",
                    "For adult applicants",
                )
            )
        if not entries:
            entries.append(("School ID", "Pick any one acceptable ID (with photocopy)"))
        return entries

    name = raw
    notes = ""
    if " *" in raw:
        name, footnote = re.split(r"\s+\*", raw, maxsplit=1)
        name = _clean_name(name)
        notes = clean_text(footnote)
    else:
        name = _clean_name(name)

    if name.lower().startswith("electronic philippine id"):
        return [
            ("Electronic Philippine ID", notes or "Pick any one acceptable ID (with photocopy)"),
            (
                "Digital National ID (printed copy)",
                notes or "Generate via national-id.gov.ph or eGovPH app; submit printed copy",
            ),
        ]

    if "digital national id" in name.lower():
        name = "Digital National ID (printed copy)"

    return [(name, notes)]


def _is_header(text: str) -> bool:
    lower = text.lower().strip()
    if any(p in lower for p in _HEADER_PATTERNS):
        return True
    if lower.endswith(":") and len(lower) < 120:
        return True
    if lower.startswith(("for persons", "by virtue of", "if the passport", "if the psa")):
        return True
    if lower.startswith("applicants those born") or lower.startswith("applicants covered by"):
        return True
    if lower.startswith("applicant is a derivative"):
        return True
    return False


def _classify_dfa_core(text: str) -> str:
    lower = text.lower()
    if "appointment" in lower or "appearance" in lower:
        return "procedure"
    if "form" in lower or "birth" in lower or "marriage" in lower:
        return "required_document"
    if "id" in lower:
        return "acceptable_id"
    return "required_document"
