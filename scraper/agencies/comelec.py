"""COMELEC voter registration requirements.

The public routes are a JavaScript shell. The text is the HTML fragment
those routes load. Identity documents are the alternatives on the
registration-requirements fragment. The CEF-1 file is the application form.
A community tax certificate and a PNP clearance are not stored: the page
says they are not honored.
"""

from __future__ import annotations

from urllib.parse import urljoin

from scraper.base import BaseScraper
from scraper.parsers.generic import clean_text, soup_from_html

SITE = "https://www.comelec.gov.ph/"
REQUIREMENTS_PAGE = (
    "https://www.comelec.gov.ph/?r=VoterRegistration/WhatisVoterRegistration/RegistrationRequirements"
)
PROCEDURES_PAGE = (
    "https://www.comelec.gov.ph/?r=VoterRegistration/WhatisVoterRegistration/RegistrationProcedures"
)
FORMS_PAGE = "https://www.comelec.gov.ph/?r=VoterRegistration/ApplicationsForms"
REQUIREMENTS_HTML = (
    "https://www.comelec.gov.ph/html-tpls/VoterRegistration/"
    "WhatisVoterRegistration/RegistrationRequirements.html"
)
PROCEDURES_HTML = (
    "https://www.comelec.gov.ph/html-tpls/VoterRegistration/"
    "WhatisVoterRegistration/RegistrationProcedures.html"
)
FORMS_HTML = "https://www.comelec.gov.ph/html-tpls/VoterRegistration/ApplicationsForms.html"

SERVICE = "Voter Registration"
TARGET = "Voter Registration Record"
APPLICANT = "Filipino citizen who is not yet a registered voter"
NOT_HONORED = (
    "A community tax certificate (cedula) and a PNP clearance are not honored "
    "as identification for registration."
)


class COMELECScraper(BaseScraper):
    agency = "Commission on Elections"
    agency_code = "COMELEC"

    def scrape(self) -> list:
        requirements = self.fetch(REQUIREMENTS_HTML)
        requirements_text = _page_text(requirements.html) if requirements.ok else ""
        if not requirements.ok or "valid identification documents" not in requirements_text.lower():
            self.add_blocked_notice(
                service_name=SERVICE,
                source_url=REQUIREMENTS_PAGE,
                reason=requirements.error or "Registration requirements fragment did not include the ID list",
                notes="The public COMELEC route is a JavaScript shell. No summary checklist is stored.",
            )
            return self.records()

        soup = soup_from_html(requirements.html)
        order = self._add_qualifications(soup)
        order = self._add_identification(soup, order)
        self._add_procedures(order)
        return self.records()

    def _add_qualifications(self, soup) -> int:
        order = 0
        container = soup.select_one(".page-content-container") or soup
        heading = None
        for paragraph in container.find_all("p"):
            if clean_text(paragraph.get_text()).lower() == "qualifications to register":
                heading = paragraph
                break
        if heading is None:
            return order
        inner = heading.find_next("ol", attrs={"type": "a"})
        if inner is None:
            return order
        for item in inner.find_all("li", recursive=False):
            text = clean_text(item.get_text(" ", strip=True))
            if not text:
                continue
            order += 1
            self._add(
                text,
                "eligibility",
                REQUIREMENTS_PAGE,
                "Qualifications to Register",
                order,
            )
        return order

    def _add_identification(self, soup, order: int) -> int:
        container = soup.select_one(".page-content-container") or soup
        id_list = None
        for paragraph in container.find_all("p"):
            if "valid identification documents" in clean_text(paragraph.get_text()).lower():
                id_list = paragraph.find_next("ol")
                break
        if id_list is None:
            return order
        for item in id_list.find_all("li", recursive=False):
            text = clean_text(item.get_text(" ", strip=True))
            text = text.rstrip(";").strip()
            if text.lower().endswith(" and"):
                text = text[:-4].rstrip(";").strip()
            if not text:
                continue
            order += 1
            conditional = "yes" if "in case of" in text.lower() else "no"
            condition = (
                "Member of an indigenous cultural community or indigenous people"
                if conditional == "yes"
                else ""
            )
            self._add(
                text,
                "acceptable_id",
                REQUIREMENTS_PAGE,
                "Documentary Requirements",
                order,
                conditional=conditional,
                condition=condition,
                issuing_agency=_issuer(text),
                document_format="original",
                notes=NOT_HONORED,
            )
        oath = soup.select_one("#noValidID")
        if oath is not None:
            order += 1
            self._add(
                clean_text(oath.get_text(" ", strip=True)),
                "supporting_document",
                REQUIREMENTS_PAGE,
                "Documentary Requirements",
                order,
                conditional="yes",
                condition=(
                    "The applicant has none of the listed identification documents. "
                    "One registered voter of the precinct, or one relative within the "
                    "fourth civil degree, may identify at most three applicants under oath."
                ),
                notes=NOT_HONORED,
            )
        return order

    def _add_procedures(self, order: int) -> None:
        procedures = self.fetch(PROCEDURES_HTML)
        if not procedures.ok or "election officer" not in _page_text(procedures.html).lower():
            return
        soup = soup_from_html(procedures.html)
        container = soup.select_one(".page-content-container") or soup
        ordered = container.find("ol")
        if ordered is None:
            return
        form_url, form_name = self._application_form()
        for item in ordered.find_all("li", recursive=False):
            text = clean_text(item.get_text(" ", strip=True))
            if not text:
                continue
            order += 1
            lower = text.lower()
            if "application form" in lower:
                self._add(
                    form_name or "Application form, three copies",
                    "required_document",
                    form_url or PROCEDURES_PAGE,
                    "Registration Procedures",
                    order,
                    document_format="original",
                    quantity="3",
                    fee="No fee. Application forms are free of charge at the Office of the Election Officer.",
                    notes=(
                        "Three copies are issued after identity is verified. A blank form "
                        "may be downloaded and filled in advance. It is signed and "
                        "thumbmarked only before the Election Officer. Application forms "
                        "are free of charge at the Office of the Election Officer."
                    ),
                )
                continue
            self._add(
                text,
                "procedure",
                PROCEDURES_PAGE,
                "Registration Procedures",
                order,
            )

    def _application_form(self) -> tuple[str, str]:
        result = self.fetch(FORMS_HTML)
        if not result.ok:
            return "", ""
        soup = soup_from_html(result.html)
        for link in soup.find_all("a", href=True):
            label = clean_text(link.get_text(" ", strip=True))
            if label.upper().startswith("CEF-1"):
                return urljoin(SITE, link["href"].strip()), label
        return "", ""

    def _add(
        self,
        name: str,
        role: str,
        source_url: str,
        section: str,
        order: int,
        *,
        conditional: str = "no",
        condition: str = "",
        issuing_agency: str = "",
        document_format: str = "",
        quantity: str = "",
        fee: str = "",
        notes: str = "",
    ) -> None:
        self.add(
            service_name=SERVICE,
            service_category="Elections",
            target_document=TARGET,
            transaction_type="new_registration",
            applicant_type=APPLICANT,
            requirement_name=name,
            requirement_description=name,
            requirement_role=role,
            conditional=conditional,
            condition=condition,
            issuing_agency=issuing_agency,
            document_format=document_format,
            quantity=quantity,
            application_method="walk_in",
            appointment_required="no",
            fee=fee,
            location="Office of the Election Officer",
            source_url=source_url,
            source_section=section,
            requirement_order=order,
            notes=notes,
        )


def _page_text(html: str) -> str:
    if not html:
        return ""
    return clean_text(soup_from_html(html).get_text(" ", strip=True))


def _issuer(name: str) -> str:
    lower = name.lower()
    if "philsys" in lower or "philippine identification system" in lower:
        return "PSA"
    if "postal" in lower:
        return "PHLPost"
    if "land transportation" in lower or "driver" in lower:
        return "LTO"
    if "national bureau of investigation" in lower:
        return "NBI"
    if "passport" in lower:
        return "DFA"
    if "professional regulatory" in lower:
        return "PRC"
    if "indigenous" in lower or "ncip" in lower:
        return "NCIP"
    if "integrated bar" in lower:
        return "Integrated Bar of the Philippines"
    return ""
