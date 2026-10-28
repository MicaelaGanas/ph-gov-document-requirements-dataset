"""DFA passport requirements (consular portal — all application types)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, find_main_content, infer_document_format, soup_from_html

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
    "pursuant to section",
)


@dataclass(frozen=True)
class PassportService:
    service_name: str
    url: str
    transaction_type: str
    applicant_type: str
    core_section: str
    include_valid_ids: bool = True


# Official consular.dfa.gov.ph requirement pages.
# Lost/mutilated passport requirements appear as conditional blocks on renewal pages.
PASSPORT_SERVICES: tuple[PassportService, ...] = (
    PassportService(
        service_name="Passport Application (Adult New)",
        url="https://consular.dfa.gov.ph/passport/10-passport/61-passport-requirements-new-adult",
        transaction_type="new_application",
        applicant_type="Adult (18+)",
        core_section="Core Requirements for Adult New Applications",
    ),
    PassportService(
        service_name="Passport Application (Adult Renewal - ePassport)",
        url="https://consular.dfa.gov.ph/adult-renewal-epassport/",
        transaction_type="renewal",
        applicant_type="Adult (18+)",
        core_section="Core Requirements for Adult Renewal (ePassport)",
    ),
    PassportService(
        service_name="Passport Application (Adult Renewal - non-ePassport)",
        url="https://consular.dfa.gov.ph/adult-renewal-non-epassport/",
        transaction_type="renewal",
        applicant_type="Adult (18+)",
        core_section="Core Requirements for Adult Renewal (non-ePassport)",
    ),
    PassportService(
        service_name="Passport Application (Minor New)",
        url="https://consular.dfa.gov.ph/minor-new/",
        transaction_type="new_application",
        applicant_type="Minor (under 18)",
        core_section="Core Requirements for Minor New Applications",
    ),
    PassportService(
        service_name="Passport Application (Minor Renewal - ePassport)",
        url="https://consular.dfa.gov.ph/minor-renewal-epassport/",
        transaction_type="renewal",
        applicant_type="Minor (under 18)",
        core_section="Core Requirements for Minor Renewal (ePassport)",
    ),
    PassportService(
        service_name="Passport Application (Minor Renewal - non-ePassport)",
        url="https://consular.dfa.gov.ph/minor-renewal-non-epassport/",
        transaction_type="renewal",
        applicant_type="Minor (under 18)",
        core_section="Core Requirements for Minor Renewal (non-ePassport)",
    ),
)

VALID_IDS_URL = "https://consular.dfa.gov.ph/valid-ids-for-passport-application/"


class DFAScraper(BaseScraper):
    agency = "Department of Foreign Affairs"
    agency_code = "DFA"

    def scrape(self) -> list:
        for service in PASSPORT_SERVICES:
            self._scrape_passport_page(service)
            if service.include_valid_ids:
                self._scrape_valid_ids(service)
        return self.records()

    def _scrape_passport_page(self, service: PassportService) -> None:
        result = self.fetch(service.url)
        if not result.ok:
            self.add_blocked_notice(
                service_name=service.service_name,
                source_url=service.url,
                reason=result.error or "fetch failed",
                notes="No seed checklist is stored when the consular page does not load.",
            )
            return

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        order = 0

        for li in root.select("ol > li.subtitle"):
            text = _clean_name(clean_text(li.get_text(" ", strip=True)))
            if not text or _is_header(text):
                continue
            order += 1
            role = _classify_dfa_core(text)
            conditional = "yes" if "married female" in text.lower() else "no"
            condition = "Married female using spouse's last name" if conditional == "yes" else ""
            self._add_requirement(
                service,
                requirement_name=text,
                source_url=service.url,
                requirement_role=role,
                conditional=conditional,
                condition=condition,
                source_section=service.core_section,
                requirement_order=order,
                issuing_agency="PSA / DFA",
                location="DFA consular offices",
                document_format=infer_document_format(text),
            )

        for details in root.find_all("details"):
            summary = details.find("summary")
            section_name = clean_text(summary.get_text()) if summary else "Supporting Documents"
            if _is_lost_section(section_name):
                section_name = f"Lost/Mutilated Passport — {section_name}"

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
                                self._add_requirement(
                                    service,
                                    requirement_name=item,
                                    source_url=service.url,
                                    requirement_role=_classify_supporting(item, section_name),
                                    conditional="yes",
                                    condition=section_name,
                                    source_section=section_name,
                                    requirement_order=order,
                                    issuing_agency="PSA / various",
                                    fee=_extract_fee(item, section_name),
                                )
                        continue

                    for item in _split_supporting_item(
                        _clean_name(clean_text(li.get_text(" ", strip=True)))
                    ):
                        if not item or _is_header(item):
                            continue
                        order += 1
                        self._add_requirement(
                            service,
                            requirement_name=item,
                            source_url=service.url,
                            requirement_role=_classify_supporting(item, section_name),
                            conditional="yes",
                            condition=section_name,
                            source_section=section_name,
                            requirement_order=order,
                            issuing_agency="PSA / various",
                            fee=_extract_fee(item, section_name),
                        )
        if order == 0:
            self.add_blocked_notice(
                service_name=service.service_name,
                source_url=service.url,
                reason="The consular page loaded without a requirement list",
                notes="No seed checklist is stored.",
            )

    def _add_requirement(
        self,
        service: PassportService,
        *,
        requirement_name: str,
        source_url: str,
        requirement_role: str,
        source_section: str,
        requirement_order: int,
        conditional: str = "no",
        condition: str = "",
        issuing_agency: str = "",
        location: str = "",
        document_format: str = "",
        fee: str = "",
        notes: str = "",
        scrape_status: str = "success",
    ) -> None:
        self.add(
            service_name=service.service_name,
            service_category="Travel Document",
            target_document="Philippine Passport",
            transaction_type=service.transaction_type,
            applicant_type=service.applicant_type,
            requirement_name=requirement_name,
            source_url=source_url,
            requirement_role=requirement_role,
            document_format=document_format or infer_document_format(requirement_name),
            conditional=conditional,
            condition=condition,
            issuing_agency=issuing_agency,
            application_method="online_appointment_and_walk_in",
            appointment_required="yes",
            location=location,
            fee=fee,
            source_section=source_section,
            requirement_order=requirement_order,
            notes=notes,
            scrape_status=scrape_status,
        )

    def _scrape_valid_ids(self, service: PassportService) -> None:
        if not hasattr(self, "_valid_ids_result"):
            self._valid_ids_result = self.fetch(VALID_IDS_URL)
        result = self._valid_ids_result
        if not result.ok:
            if service.service_name == PASSPORT_SERVICES[0].service_name:
                self.add_blocked_notice(
                    service_name=service.service_name,
                    source_url=VALID_IDS_URL,
                    reason=result.error or "Valid ID page did not load",
                    notes="No seed ID list is stored.",
                )
            return

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        order = 1000  # offset so IDs sort after core requirements
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
                for name, notes in _expand_id_entries(raw, service.applicant_type):
                    key = name.lower()[:80]
                    if key in seen:
                        continue
                    seen.add(key)
                    order += 1
                    self._add_requirement(
                        service,
                        requirement_name=name,
                        source_url=VALID_IDS_URL,
                        requirement_role="acceptable_id",
                        source_section="Acceptable IDs for Passport Application",
                        requirement_order=order,
                        notes=notes or "Pick any one acceptable ID (with photocopy)",
                        issuing_agency="Various government agencies",
                    )

def _is_lost_section(section_name: str) -> bool:
    lower = section_name.lower()
    return any(k in lower for k in ("lost", "mutilated", "frequently lost"))


def _classify_supporting(text: str, section_name: str) -> str:
    lower = text.lower()
    if "penalty fee" in lower or lower.startswith("php") or "p350" in lower.replace(" ", ""):
        return "fee"
    if "clearing period" in lower or "business day" in lower:
        return "processing_time"
    if _is_lost_section(section_name) and any(
        k in lower for k in ("police report", "affidavit of loss", "passport")
    ):
        return "required_document"
    return "supporting_document"


def _extract_fee(text: str, section_name: str) -> str:
    lower = text.lower()
    match = re.search(r"p(?:hp)?\s*[\d,]+(?:\.\d{2})?", lower)
    if match:
        return match.group(0).upper().replace("PHP", "PHP ")
    if "penalty fee" in section_name.lower():
        return "PHP 350.00"
    return ""


def _clean_name(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"[;\s]+and\s*$", "", text, flags=re.I)
    text = re.sub(r"[;\s]+or\s*$", "", text, flags=re.I)
    return text.strip(" ;,")


def _split_supporting_item(text: str) -> list[str]:
    if not text:
        return []
    if len(text) < 180:
        return [text]

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


def _expand_id_entries(raw: str, applicant_type: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []

    if "school id" in raw.lower() and "for minor applicants" in raw.lower():
        if "Minor" in applicant_type:
            entries.append(
                (
                    "School ID or Certificate of Enrolment with photo and dry seal of school",
                    "For minor applicants when school ID is not applicable",
                )
            )
        else:
            entries.append(
                (
                    "Certificate of Enrolment with photo of minor and dry seal of school",
                    "For minor applicants when school ID is not applicable",
                )
            )
            entries.append(
                ("School ID and Certificate of Registration", "For adult applicants"),
            )
        if entries:
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
    if "form" in lower or "birth" in lower or "marriage" in lower or "passport" in lower:
        return "required_document"
    if "id" in lower or "parent" in lower or "companion" in lower:
        return "acceptable_id"
    return "required_document"
