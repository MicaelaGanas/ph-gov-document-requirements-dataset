"""Shared scraper utilities (HTTP, parsing, record helpers)."""

from __future__ import annotations

from scraper.base import BaseScraper, records_from_list_items
from scraper.http import FetchResult, fetch_page
from scraper.models import RequirementRecord, make_record_id, slugify
from scraper.parsers.generic import clean_text, find_main_content, soup_from_html
from scraper.parsers.requirements import infer_requirement_role, split_compound_requirement

__all__ = [
    "BaseScraper",
    "FetchResult",
    "RequirementRecord",
    "clean_text",
    "fetch_page",
    "find_main_content",
    "infer_requirement_role",
    "make_record_id",
    "records_from_list_items",
    "slugify",
    "soup_from_html",
    "split_compound_requirement",
]
