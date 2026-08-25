"""PRC licensure examination / registration requirements."""

from __future__ import annotations

import re

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, find_main_content, soup_from_html
from scraper.parsers.requirements import infer_requirement_role, split_compound_requirement


class PRCScraper(BaseScraper):
    agency = "Professional Regulation Commission"
    agency_code = "PRC"

    LIST_URL = "https://www.prc.gov.ph/list-of-requirements"

    def scrape(self) -> list:
        result = self.fetch(self.LIST_URL)
        if not result.ok:
            self.add_blocked_notice(
                service_name="Professional Licensure / Registration",
                source_url=self.LIST_URL,
                reason=result.error or "fetch failed",
            )
            return self.records()

        soup = soup_from_html(result.html)
        root = find_main_content(soup)
        current_profession = ""
        order = 0
        skip_general = False

        for element in root.find_all(["p", "li", "strong", "b", "h3", "h4", "h5"]):
            if element.name in {"h3", "h4", "h5", "strong", "b"}:
                text = clean_text(element.get_text())
                if text and len(text) < 120:
                    if _is_profession_heading(text):
                        current_profession = text
                        skip_general = True
                continue

            if element.name == "p":
                text = clean_text(element.get_text(" ", strip=True))
                if not text:
                    continue
                if "documentary requirements" in text.lower():
                    current_profession = text.split(":")[0].strip() or current_profession
                    continue
                if skip_general and current_profession.lower() == "general":
                    continue
                if _is_compound_blob(text):
                    for part in split_compound_requirement(text):
                        if _looks_like_requirement(part):
                            order += 1
                            self._add_requirement(current_profession, part, order)
                    continue
                if _looks_like_requirement(text):
                    order += 1
                    self._add_requirement(current_profession, text, order)
                continue

            if element.name == "li":
                text = clean_text(element.get_text(" ", strip=True))
                if not text or len(text) < 4:
                    continue
                if skip_general and not current_profession:
                    continue
                order += 1
                self._add_requirement(current_profession or "Unspecified Profession", text, order)

        return self.records()

    def _add_requirement(self, profession: str, text: str, order: int) -> None:
        conditional = "yes" if re.match(r"for foreign", text, re.I) else "no"
        condition = "Foreign national applicant" if conditional == "yes" else ""
        role = infer_requirement_role(text, section=profession)
        if "nbi clearance" in text.lower():
            role = "required_document"
        elif "birth certificate" in text.lower() or "transcript" in text.lower() or "diploma" in text.lower():
            role = "required_document"
        elif " passport" in text.lower() and "copy of passport" in text.lower():
            role = "required_document"

        self.add(
            service_name=f"PRC Licensure - {profession[:80]}",
            service_category="Professional Regulation",
            target_document="Professional License / Board Exam Application",
            transaction_type="examination_application|registration",
            applicant_type="Local graduate|Foreign graduate",
            requirement_name=text,
            source_url=self.LIST_URL,
            requirement_role=role,
            conditional=conditional,
            condition=condition,
            issuing_agency="School|PSA|NBI|Various",
            application_method="online_and_walk_in",
            appointment_required="unknown",
            source_section=profession,
            requirement_order=order,
        )


def _is_profession_heading(text: str) -> bool:
    lower = text.lower()
    keywords = (
        "engineering",
        "nurse",
        "medicine",
        "accountancy",
        "architecture",
        "education",
        "examination",
        "licensure",
        "board",
        "technology",
        "agricultural",
        "aeronautic",
    )
    return any(k in lower for k in keywords)


def _is_compound_blob(text: str) -> bool:
    return len(text) > 180 and (
        text.count("Certificate") > 1
        or text.count("Transcript") > 0 and text.count("Clearance") > 0
        or "Payment:" in text
    )


def _looks_like_requirement(text: str) -> bool:
    lower = text.lower()
    keywords = (
        "certificate",
        "transcript",
        "diploma",
        "nbi",
        "birth",
        "passport",
        "document",
        "clearance",
        "form",
        "notarized",
        "marriage",
        "payment",
        "id",
    )
    return any(k in lower for k in keywords) and len(text) < 600
