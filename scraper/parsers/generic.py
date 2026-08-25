"""Generic HTML parsing helpers."""

from __future__ import annotations

import re
from typing import Iterable, Iterator, Optional

from bs4 import BeautifulSoup, NavigableString, Tag


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def soup_from_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def iter_list_items(
    root: Tag,
    *,
    skip_navigation: bool = True,
) -> Iterator[tuple[str, str]]:
    """Yield (section_heading, list_item_text) pairs from ul/ol under headings."""
    current_section = ""
    for element in root.descendants:
        if not isinstance(element, Tag):
            continue
        if skip_navigation and _is_navigation(element):
            continue
        if element.name in {"h1", "h2", "h3", "h4", "h5", "h6", "strong", "b"}:
            heading = clean_text(element.get_text(" ", strip=True))
            if heading and len(heading) < 200:
                current_section = heading
        elif element.name == "li":
            text = clean_text(element.get_text(" ", strip=True))
            if text and len(text) > 2:
                yield current_section, text


def extract_label_value_pairs(root: Tag) -> dict[str, str]:
    """Parse citizen-charter style `<strong>Label</strong><br /> value` blocks."""
    pairs: dict[str, str] = {}
    for strong in root.find_all("strong"):
        label = clean_text(strong.get_text())
        if not label:
            continue
        value_parts: list[str] = []
        for sibling in strong.next_siblings:
            if isinstance(sibling, Tag):
                if sibling.name in {"strong", "h2", "h3", "p"} and value_parts:
                    break
                if sibling.name == "br":
                    continue
                text = clean_text(sibling.get_text(" ", strip=True))
                if text:
                    value_parts.append(text)
            elif isinstance(sibling, NavigableString):
                text = clean_text(str(sibling))
                if text:
                    value_parts.append(text)
        value = clean_text(" ".join(value_parts))
        if value and not value.endswith(":"):
            pairs[label.rstrip(":")] = value
    return pairs


def split_requirements_blob(text: str) -> list[str]:
    """Split semicolon or newline separated requirement strings."""
    parts = re.split(r";|\n|<br\s*/?>", text, flags=re.I)
    return [clean_text(part) for part in parts if clean_text(part)]


def infer_document_format(text: str) -> str:
    lower = text.lower()
    formats: list[str] = []
    if "original and photocopy" in lower or "original and copy" in lower:
        formats.append("original_and_photocopy")
    elif "photocopy" in lower or "copy" in lower:
        formats.append("photocopy")
    if "original" in lower:
        formats.append("original")
    if "notarized" in lower:
        formats.append("notarized")
    if "security paper" in lower:
        formats.append("security_paper")
    return "|".join(dict.fromkeys(formats))


def infer_requirement_type(text: str, *, section: str = "", role: str = "") -> str:
    if role:
        from scraper.parsers.requirements import infer_requirement_type_from_role

        return infer_requirement_type_from_role(role)
    combined = f"{section} {text}".lower()
    if "in the absence of" in combined:
        return "document"
    if any(k in combined for k in ("fee", "php", "penalty")) and re.search(
        r"p\s*[\d,]+", combined
    ):
        return "fee"
    if any(k in combined for k in ("working day", "processing take", "minute", "hour")):
        return "processing_time"
    if any(
        k in combined
        for k in ("appointment", "walk-in", "walk in", "personal appearance", "proceed to")
    ):
        return "procedure"
    if any(k in combined for k in ("eligible", "qualified", "must be", "aged")):
        return "eligibility"
    return "document"


def iter_section_lists(root: Tag) -> Iterator[tuple[str, list[str]]]:
    """Yield (section_title, list_item_texts) once per heading+list pair."""
    seen_lists: set[int] = set()
    for heading in root.find_all(["h1", "h2", "h3", "h4", "h5"]):
        title = clean_text(heading.get_text())
        if not title or len(title) > 200:
            continue
        ul = heading.find_next_sibling(["ul", "ol"])
        if ul is None:
            parent = heading.find_parent(["div", "section"])
            if parent:
                for candidate in parent.find_all(["ul", "ol"], recursive=False):
                    if candidate.find_previous(["h1", "h2", "h3", "h4", "h5"]) == heading:
                        ul = candidate
                        break
        if ul is None:
            ul = heading.find_next(["ul", "ol"])
        if ul is None or id(ul) in seen_lists:
            continue
        seen_lists.add(id(ul))
        items = []
        for li in ul.find_all("li", recursive=False):
            text = clean_text(li.get_text(" ", strip=True))
            if text and len(text) > 2:
                items.append(text)
        if items:
            yield title, items


def _is_navigation(element: Tag) -> bool:
    classes = " ".join(element.get("class", [])).lower()
    element_id = (element.get("id") or "").lower()
    nav_tokens = ("menu", "nav", "footer", "breadcrumb", "sidebar", "widget")
    return any(token in classes or token in element_id for token in nav_tokens)


def find_main_content(soup: BeautifulSoup) -> Tag:
    selectors = [
        "article .entry-content",
        "article",
        "#main-content",
        ".entry-content",
        ".site-content",
        "main",
        "#content",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node and clean_text(node.get_text()):
            return node
    return soup.body or soup
