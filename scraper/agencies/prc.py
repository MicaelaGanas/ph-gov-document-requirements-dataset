"""PRC licensure requirements, one service per profession."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, find_main_content, soup_from_html

_SECTION_LABELS = {
    "first timer",
    "first-timer",
    "first timers",
    "first time applicants",
    "repeater",
    "repeaters",
    "payment",
    "documentary requirements",
    "documentary",
    "requirements",
    "special requirements",
    "educational qualification",
    "general",
}


@dataclass
class PendingItem:
    name: str
    role: str
    sections: set[str] = field(default_factory=set)
    extra_condition: str = ""


class PRCScraper(BaseScraper):
    agency = "Professional Regulation Commission"
    agency_code = "PRC"

    LIST_URL = "https://www.prc.gov.ph/list-of-requirements"

    def scrape(self) -> list:
        result = self.fetch(self.LIST_URL)
        if not result.ok:
            self.add_blocked_notice(
                service_name="Professional Licensure",
                source_url=self.LIST_URL,
                reason=result.error or "fetch failed",
            )
            return self.records()

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        profession = ""
        section = ""
        pending: dict[str, PendingItem] = {}
        fee = ""

        def flush() -> None:
            nonlocal fee
            if profession:
                self._flush_profession(profession, pending, fee)
            pending.clear()
            fee = ""

        for element in root.find_all(["p", "li", "strong", "b", "h3", "h4"]):
            if element.name in {"strong", "b"} and element.find_parent(["strong", "b", "p", "li"]):
                if element.find_parent(["p", "li"]):
                    continue
            text = clean_text(element.get_text(" ", strip=True))
            if not text or text in {"*", "List of Requirements"}:
                continue
            if element.name in {"strong", "b", "h3", "h4"} and _is_profession_heading(text):
                flush()
                profession = text.rstrip(":").strip()
                section = ""
                continue
            kind = _section_kind(text)
            if kind:
                section = kind
                continue
            if not profession:
                continue
            if _is_fee(text):
                fee = text
                continue
            if not _looks_like_requirement(text):
                continue
            key = " ".join(text.lower().split())[:180]
            item = pending.get(key)
            if item is None:
                item = PendingItem(
                    name=text,
                    role=_requirement_role(text),
                    extra_condition=_extra_condition(text),
                )
                pending[key] = item
            if section:
                item.sections.add(section)
        flush()
        if not self._records:
            self.add_blocked_notice(
                service_name="Professional Licensure",
                source_url=self.LIST_URL,
                reason="The requirements page did not yield profession checklists",
            )
        return self.records()

    def _flush_profession(self, profession: str, pending: dict[str, PendingItem], fee: str) -> None:
        order = 0
        for item in pending.values():
            order += 1
            conditions = []
            if item.extra_condition:
                conditions.append(item.extra_condition)
            if item.sections == {"first_timer"}:
                conditions.append("First-time applicant")
            elif item.sections == {"repeater"}:
                conditions.append("Repeater")
            condition = ". ".join(conditions)
            self.add(
                service_name=f"PRC Licensure - {profession}",
                service_category="Professional Regulation",
                target_document=f"{profession} professional license",
                transaction_type="examination_application",
                applicant_type="Board examination applicant",
                requirement_name=item.name,
                source_url=self.LIST_URL,
                requirement_role=item.role,
                conditional="yes" if condition else "no",
                condition=condition,
                issuing_agency=_issuer(item.name),
                application_method="online_and_walk_in",
                appointment_required="unknown",
                source_section=profession,
                requirement_order=order,
            )
        if fee:
            self.add(
                service_name=f"PRC Licensure - {profession}",
                service_category="Professional Regulation",
                target_document=f"{profession} professional license",
                transaction_type="examination_application",
                applicant_type="Board examination applicant",
                requirement_name=fee,
                source_url=self.LIST_URL,
                requirement_role="fee",
                fee=fee,
                application_method="online_and_walk_in",
                appointment_required="unknown",
                source_section=profession,
                requirement_order=len(pending) + 1,
            )


def _is_profession_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped.endswith(":") or len(stripped) > 70:
        return False
    lower = stripped.lower()
    if lower in _SECTION_LABELS:
        return False
    if any(
        phrase in lower
        for phrase in (
            "applicant",
            "submit",
            "failure",
            "payment",
            "fee",
            "document",
            "certificate",
            "clearance",
            "transcript",
        )
    ):
        return False
    words = stripped.split()
    return 1 <= len(words) <= 6 and stripped[:1].isupper()


def _section_kind(text: str) -> str:
    lower = text.strip().rstrip(":").strip().lower()
    if lower in {"first timer", "first-timer", "first timers", "first time applicants"}:
        return "first_timer"
    if lower in {"repeater", "repeaters"}:
        return "repeater"
    return ""


def _is_fee(text: str) -> bool:
    lower = text.lower()
    return lower.startswith("payment") or bool(re.search(r"\bp\s*\d", lower))


def _looks_like_requirement(text: str) -> bool:
    lower = text.lower()
    if lower.rstrip(":") in _SECTION_LABELS or _section_kind(text):
        return False
    if "other documents that the board" in lower:
        return False
    keywords = (
        "certificate",
        "transcript",
        "diploma",
        "nbi",
        "birth",
        "passport",
        "clearance",
        "tor",
        "marriage",
        "thesis",
        "good moral",
        "refresher",
    )
    return any(keyword in lower for keyword in keywords) and len(text) < 400


def _requirement_role(text: str) -> str:
    lower = text.lower()
    if "refresher" in lower or "failure" in lower:
        return "eligibility"
    return "required_document"


def _extra_condition(text: str) -> str:
    lower = text.lower()
    if "married female" in lower:
        return "Married female applicant"
    if "foreign" in lower:
        return "Foreign applicant"
    return ""


def _issuer(text: str) -> str:
    lower = text.lower()
    if "nbi" in lower:
        return "NBI"
    if "psa" in lower or "birth" in lower or "marriage" in lower:
        return "PSA"
    if "transcript" in lower or "diploma" in lower or "tor" in lower:
        return "School"
    return ""
