"""Base scraper class shared by agency modules."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Iterable, Optional

from scraper.http import FetchResult, fetch_page
from scraper.models import RequirementRecord
from scraper.parsers.generic import (
    clean_text,
    find_main_content,
    infer_document_format,
    infer_requirement_type,
    soup_from_html,
)
from scraper.parsers.requirements import (
    dedupe_key,
    infer_quantity,
    infer_requirement_role,
    infer_requirement_type_from_role,
    split_compound_requirement,
)

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    agency: str
    agency_code: str

    def __init__(self) -> None:
        self._records: list[RequirementRecord] = []
        self._seen_keys: set[str] = set()

    @abstractmethod
    def scrape(self) -> list[RequirementRecord]:
        raise NotImplementedError

    def fetch(self, url: str, *, use_browser: bool = False) -> FetchResult:
        from scraper import config

        return fetch_page(
            url,
            use_browser=use_browser or config.USE_BROWSER,
            browser_fallback=config.BROWSER_FALLBACK,
        )

    def add(
        self,
        *,
        service_name: str,
        requirement_name: str,
        source_url: str,
        requirement_role: str = "",
        split_compounds: bool = False,
        skip_duplicate: bool = True,
        **kwargs,
    ) -> list[RequirementRecord]:
        section = kwargs.get("source_section", "")
        names = (
            split_compound_requirement(requirement_name)
            if split_compounds
            else [requirement_name]
        )
        created: list[RequirementRecord] = []
        for name in names:
            name = clean_text(name)
            if not name or len(name) < 3:
                continue
            role = requirement_role or infer_requirement_role(name, section=section)
            # Always derive type from role so the two columns stay consistent.
            req_type = infer_requirement_type_from_role(role)
            key = dedupe_key(
                self.agency_code,
                service_name,
                role,
                name,
                conditional=kwargs.get("conditional", "no"),
                condition=kwargs.get("condition", ""),
                source_section=section,
            )
            if skip_duplicate and key in self._seen_keys:
                continue
            self._seen_keys.add(key)

            quantity = kwargs.get("quantity") or infer_quantity(name)
            record = RequirementRecord(
                agency=self.agency,
                agency_code=self.agency_code,
                service_name=service_name,
                requirement_name=name[:500],
                source_url=source_url,
                requirement_role=role,
                requirement_type=req_type,
                requirement_description=kwargs.get("requirement_description", name),
                document_format=kwargs.get(
                    "document_format", infer_document_format(name)
                ),
                quantity=quantity,
                **{k: v for k, v in kwargs.items() if k not in {"requirement_type", "requirement_description", "document_format", "quantity"}},
            )
            self._records.append(record)
            created.append(record)
        return created

    def add_blocked_notice(
        self,
        *,
        service_name: str,
        source_url: str,
        reason: str,
        notes: str = "",
    ) -> RequirementRecord:
        records = self.add(
            service_name=service_name,
            requirement_name="[SCRAPE BLOCKED - manual verification required]",
            source_url=source_url,
            requirement_role="metadata",
            requirement_type="metadata",
            scrape_status="blocked",
            notes=f"{reason}. {notes}".strip(),
            skip_duplicate=False,
        )
        return records[0]

    def extend(self, records: Iterable[RequirementRecord]) -> None:
        self._records.extend(records)

    def records(self) -> list[RequirementRecord]:
        return list(self._records)


def records_from_list_items(
    scraper: BaseScraper,
    *,
    html: str,
    source_url: str,
    service_name: str,
    target_document: str = "",
    transaction_type: str = "",
    applicant_type: str = "",
    application_method: str = "",
    appointment_required: str = "unknown",
    processing_time: str = "",
    fee: str = "",
    location: str = "",
    conditional: str = "no",
    condition: str = "",
    scrape_status: str = "success",
    requirement_role: str = "",
    root_selector: Optional[str] = None,
    only_direct_li: bool = True,
) -> list[RequirementRecord]:
    soup = soup_from_html(html)
    root = soup.select_one(root_selector) if root_selector else find_main_content(soup)
    records: list[RequirementRecord] = []
    order = 0

    lists = root.find_all(["ul", "ol"])
    for ul in lists:
        if only_direct_li:
            items = ul.find_all("li", recursive=False)
        else:
            items = ul.find_all("li")
        if not items:
            continue
        heading = ul.find_previous(["h1", "h2", "h3", "h4", "h5", "strong"])
        section = clean_text(heading.get_text()) if heading else ""
        for li in items:
            text = clean_text(li.get_text(" ", strip=True))
            if not text or len(text) < 3:
                continue
            order += 1
            role = requirement_role or infer_requirement_role(text, section=section)
            created = scraper.add(
                service_name=service_name,
                requirement_name=text,
                source_url=source_url,
                target_document=target_document,
                transaction_type=transaction_type,
                applicant_type=applicant_type,
                application_method=application_method,
                appointment_required=appointment_required,
                processing_time=processing_time,
                fee=fee,
                location=location,
                conditional=conditional,
                condition=condition if conditional == "yes" else "",
                requirement_role=role,
                source_section=section,
                requirement_order=order,
                scrape_status=scrape_status,
            )
            records.extend(created)
    return records
