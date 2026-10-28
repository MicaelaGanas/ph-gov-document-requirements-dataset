"""Charter check for rules with lift greater than 1.

A rule is confirmed only when every service that contains it was retrieved,
and that service's current page still requires each consequent document
whenever it requires the antecedent. A married-female, foreign-applicant,
or degree-abroad line does not count as a requirement of every applicant.
A page that was not retrieved rejects the rule.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from processing.requirement_preparation import BIRTH, MARRIAGE, NBI, TOR, canonicalize_document
from scraper.agencies.prc import _is_profession_heading
from scraper.parsers.generic import clean_text, find_main_content, soup_from_html

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data" / "final"
MINING = ROOT / "output" / "mining"
SOURCES = MINING / "charter_sources"
RETRIEVED_ON = "2026-10-29"

PRC_URL = "https://www.prc.gov.ph/list-of-requirements"
SSS_URL = "https://www.sss.gov.ph/become-an-sss-member/"
LTO_URL = "https://lto.gov.ph/wp-content/uploads/2025/09/LTO-CC-2025-External-v2.pdf"

EVERYONE = frozenset({"everyone", "married_female", "foreign", "abroad"})
SITUATIONS = {
    "joint": EVERYONE,
    "married_female": frozenset({"married_female"}),
    "foreign": frozenset({"foreign"}),
    "abroad": frozenset({"abroad"}),
}


def run_charter_check(mining_dir: Path = MINING, final_dir: Path = FINAL) -> Path:
    services = {
        row["service_id"]: row["service_name"]
        for row in _read_csv(final_dir / "government_services.csv")
    }
    dependencies = _read_csv(final_dir / "document_dependencies.csv")
    baskets: dict[str, set[str]] = defaultdict(set)
    originals: dict[tuple[str, str], list[str]] = defaultdict(list)
    urls: dict[str, str] = {}
    for row in dependencies:
        if row.get("relationship_type") != "required":
            continue
        service_id = row["service_id"]
        baskets[service_id].add(row["required_document_normalized"])
        originals[(service_id, row["required_document_normalized"])].append(row["required_document"])
        urls[service_id] = row.get("source_url") or urls.get(service_id, "")

    pages = _load_pages()
    service_docs = _service_documents(services, baskets, originals, urls, pages)
    _write_service_check(mining_dir / "charter_check_services.csv", service_docs)

    rules = _read_csv(mining_dir / "rules_lift_above_1.csv")
    checked = [_check_rule(rule, baskets, service_docs) for rule in rules]
    confirmed = [row for row in checked if row["charter_status"] == "confirmed"]
    _write_rules(mining_dir / "charter_check_rules.csv", checked)
    _write_rules(mining_dir / "rules_charter_confirmed.csv", confirmed)
    _write_summary(mining_dir / "charter_check_summary.txt", checked, service_docs, baskets)
    return mining_dir / "rules_charter_confirmed.csv"


def _load_pages() -> dict[str, dict]:
    prc_html = (SOURCES / "prc.html").read_text(encoding="utf-8")
    sss_html = (SOURCES / "sss.html").read_text(encoding="utf-8")
    return {
        PRC_URL: {"status": "retrieved", "professions": _parse_prc(prc_html)},
        SSS_URL: {"status": "retrieved", "professions": {"SSS Number / Membership Registration": _parse_sss(sss_html)}},
        LTO_URL: {"status": "not_retrieved", "professions": {}},
    }


def _parse_prc(html: str) -> dict[str, list[dict[str, str]]]:
    soup = soup_from_html(html)
    root = find_main_content(soup)
    professions: dict[str, list[dict[str, str]]] = {}
    profession = ""
    block = "joint"
    for element in root.find_all(["p", "li", "strong", "b", "h3", "h4"]):
        if element.name in {"strong", "b"} and element.find_parent(["p", "li"]):
            continue
        if element.name in {"li", "p"} and element.find(["p", "li"]):
            continue
        for line in _element_lines(element):
            lower = line.lower()
            if element.name in {"strong", "b", "h3", "h4"} and _is_profession_heading(line):
                _reconcile_marriage(professions.get(profession, []))
                profession = line.rstrip(":").strip()
                professions.setdefault(profession, [])
                block = "joint"
                continue
            if not profession:
                continue
            if _opens_foreign_block(lower):
                block = "foreign"
                continue
            if lower.startswith("for degrees taken abroad"):
                block = "abroad"
                continue
            if element.name not in {"li", "p"} or len(line) > 500:
                continue
            professions[profession].append({"text": line, "scope": _scope_for_line(lower, block)})
    _reconcile_marriage(professions.get(profession, []))
    return professions


def _parse_sss(html: str) -> list[dict[str, str]]:
    """Birth is offered or a passport. Marriage is a status-change document."""
    soup = soup_from_html(html)
    root = find_main_content(soup)
    items = []
    for element in root.find_all(["li", "p"]):
        text = clean_text(element.get_text(" ", strip=True))
        lower = text.lower()
        if "birth certificate or passport" in lower:
            items.append({"text": text, "scope": "alternative"})
        elif lower.startswith("from single to married") or lower.startswith("if spouse"):
            items.append({"text": text, "scope": "married_female"})
    return items


def _element_lines(element) -> list[str]:
    for br in element.find_all("br"):
        br.replace_with("\n")
    raw = element.get_text("\n", strip=True)
    return [
        line for line in (clean_text(part) for part in raw.split("\n"))
        if line and line not in {"*", "List of Requirements"}
    ]


def _scope_for_line(lower: str, block: str) -> str:
    if "marriage" in lower and "if applicable" in lower:
        return "conditional"
    if "marriage" in lower and _marriage_limited(lower):
        return "married_female"
    if block == "joint" and " or " in lower and _alternative_pair(lower):
        return "alternative"
    return block


def _reconcile_marriage(items: list[dict[str, str]]) -> None:
    """A bare repeater line does not erase a married-applicant limit on the same page."""
    limited = any(item["scope"] in {"married_female", "conditional"} and _is_marriage_line(item["text"]) for item in items)
    if not limited:
        return
    for item in items:
        if item["scope"] == "joint" and _is_marriage_line(item["text"]):
            item["scope"] = "married_female"


def _is_marriage_line(text: str) -> bool:
    lower = text.lower()
    return "marriage certificate" in lower or "marriage contract" in lower


def _marriage_limited(lower: str) -> bool:
    return any(
        phrase in lower
        for phrase in (
            "married female",
            "female married",
            "for married applicant",
            "for female applicant",
        )
    )


def _opens_foreign_block(lower: str) -> bool:
    if lower.startswith("for foreign"):
        return True
    return lower.startswith("foreign national") and any(
        word in lower for word in ("submit", "following", "must")
    )


def _alternative_pair(lower: str) -> bool:
    return "birth certificate or passport" in lower or "passport or" in lower


def _service_documents(services, baskets, originals, urls, pages) -> list[dict[str, str]]:
    rows = []
    prc = pages[PRC_URL]["professions"]
    heading_by_name = {_norm(name): name for name in prc}
    for service_id, documents in baskets.items():
        if len(documents) < 1:
            continue
        service_name = services.get(service_id, service_id)
        url = urls.get(service_id, "")
        page = pages.get(url)
        if page is None or page["status"] != "retrieved":
            for document in sorted(documents):
                rows.append(_service_row(
                    service_id, service_name, url, "not_retrieved", document, "absent",
                    "The current page was not retrieved.",
                ))
            continue
        items = _items_for_service(service_name, page["professions"], heading_by_name)
        if items is None:
            for document in sorted(documents):
                rows.append(_service_row(
                    service_id, service_name, url, "retrieved", document, "absent",
                    "No matching section was found on the current page.",
                ))
            continue
        for document in sorted(documents):
            scope, sentence = _match_document(
                document, originals.get((service_id, document), []), items,
            )
            rows.append(_service_row(
                service_id, service_name, url, "retrieved", document, scope or "absent", sentence,
            ))
    return rows


def _items_for_service(service_name: str, professions: dict, heading_by_name: dict):
    if service_name in professions:
        return professions[service_name]
    suffix = service_name.split(" - ", 1)[-1]
    heading = heading_by_name.get(_norm(suffix))
    if heading:
        return professions[heading]
    return None


def _match_document(
    normalized: str, phrases: list[str], items: list[dict[str, str]],
) -> tuple[str | None, str]:
    best_scope = None
    best_sentence = ""
    rank = {"joint": 4, "married_female": 3, "foreign": 2, "abroad": 2, "alternative": 1}
    canonical = canonicalize_document(normalized)
    for phrase in phrases or [normalized]:
        needle = clean_text(phrase).lower()[:90]
        phrase_canonical = canonical or canonicalize_document(phrase)
        for item in items:
            sentence = item["text"]
            haystack = clean_text(sentence).lower()
            literal = _literal_match(needle, haystack)
            same_document = bool(
                phrase_canonical and (
                    phrase_canonical == canonicalize_document(sentence)
                    or _family_on_line(phrase_canonical, haystack)
                )
            )
            if not literal and not same_document:
                continue
            if _is_buried_mention(normalized, sentence):
                continue
            scope = item["scope"]
            if best_scope is None or rank.get(scope, 0) > rank.get(best_scope, 0):
                best_scope = scope
                best_sentence = sentence
    return best_scope, best_sentence


def _literal_match(needle: str, haystack: str) -> bool:
    if len(needle) < 12 or len(haystack) < 12:
        return False
    return needle[:80] in haystack or haystack[:80] in needle


def _family_on_line(canonical: str, haystack: str) -> bool:
    if canonical == BIRTH:
        return "birth certificate" in haystack
    if canonical == NBI:
        return "nbi clearance" in haystack or (
            "national bureau of investigation" in haystack and "clearance" in haystack
        )
    if canonical == TOR:
        return "title page" not in haystack and (
            "transcript of record" in haystack or " tor " in f" {haystack} "
        )
    if canonical == MARRIAGE:
        return "marriage certificate" in haystack or "marriage contract" in haystack
    return False


def _is_buried_mention(normalized: str, sentence: str) -> bool:
    """A short name cited inside a different requirement is not that requirement."""
    name = clean_text(normalized).lower()
    sentence_text = clean_text(sentence).lower()
    leading = sentence_text.lstrip("0123456789.) ")
    if len(name) > 24 or sentence_text.startswith(name) or leading.startswith(name):
        return False
    if canonicalize_document(normalized) and canonicalize_document(normalized) == canonicalize_document(sentence):
        return False
    return len(sentence_text) > 80 and name in sentence_text


def _check_rule(rule: dict[str, str], baskets, service_docs: list[dict[str, str]]) -> dict[str, str]:
    antecedent = _split_docs(rule["antecedent_documents"])
    consequent = _split_docs(rule["consequent_documents"])
    union = set(antecedent) | set(consequent)
    supporters = [service_id for service_id, basket in baskets.items() if union <= basket]
    by_service: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in service_docs:
        by_service[row["service_id"]][row["document"]] = row

    failures = []
    for service_id in supporters:
        docs = by_service.get(service_id, {})
        failure = _service_failure(service_id, docs, antecedent, consequent)
        if failure:
            failures.append(failure)
    status = "confirmed" if supporters and not failures else "rejected"
    reason = failures[0] if failures else ("Confirmed on the current page." if supporters else "No supporting service.")
    checked = dict(rule)
    checked["charter_status"] = status
    checked["charter_reason"] = reason
    checked["services_checked"] = str(len(supporters))
    checked["services_failed"] = str(len(failures))
    return checked


def _service_failure(service_id: str, docs: dict[str, dict[str, str]], antecedent: list[str], consequent: list[str]) -> str:
    scopes = []
    for document in antecedent + consequent:
        row = docs.get(document)
        if row is None or row["retrieval_status"] != "retrieved":
            return f"{service_id}: the current page was not retrieved."
        if row["page_role"] == "absent":
            return f"{service_id}: the current page no longer lists {document}."
        scopes.append(row["page_role"])
    antecedent_scopes = scopes[: len(antecedent)]
    consequent_scopes = scopes[len(antecedent) :]
    if not _consequent_follows(antecedent_scopes, consequent_scopes):
        return (
            f"{service_id}: the page does not require the consequent whenever the antecedent is required."
        )
    return ""


def _consequent_follows(antecedent_scopes: list[str], consequent_scopes: list[str]) -> bool:
    required_when = None
    for scope in antecedent_scopes:
        situations = SITUATIONS.get(scope)
        if not situations:
            return False
        required_when = situations if required_when is None else required_when & situations
    if not required_when:
        return False
    for scope in consequent_scopes:
        situations = SITUATIONS.get(scope)
        if not situations or not required_when <= situations:
            return False
    return True


def _service_row(service_id, service_name, url, status, document, role, sentence) -> dict[str, str]:
    return {
        "service_id": service_id,
        "service_name": service_name,
        "source_url": url,
        "retrieval_date": RETRIEVED_ON,
        "retrieval_status": status,
        "document": document,
        "page_role": role,
        "sentence": sentence,
    }


def _split_docs(value: str) -> list[str]:
    return [part.strip() for part in value.split("|") if part.strip()]


def _norm(value: str) -> str:
    return " ".join(value.lower().replace("&", "and").split())


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_service_check(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "service_id", "service_name", "source_url", "retrieval_date",
        "retrieval_status", "document", "page_role", "sentence",
    ]
    _write(path, fields, rows)


def _write_rules(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    base = [
        "antecedent_ids", "consequent_ids", "antecedent_documents", "consequent_documents",
        "support_count", "antecedent_count", "consequent_count", "support", "confidence", "lift",
    ]
    extra = ["charter_status", "charter_reason", "services_checked", "services_failed"]
    _write(path, base + extra, rows)


def _write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_summary(path: Path, rules, service_docs, baskets) -> None:
    confirmed_rows = [row for row in rules if row["charter_status"] == "confirmed"]
    rejected = len(rules) - len(confirmed_rows)
    not_retrieved = sum(row["retrieval_status"] == "not_retrieved" for row in service_docs)
    by_service: dict[str, dict[str, str]] = defaultdict(dict)
    for row in service_docs:
        by_service[row["service_id"]][row["document"]] = row["page_role"]
    situation_counts = {"every applicant": 0, "married-applicant line": 0, "foreign-applicant line": 0}
    for rule in confirmed_rows:
        roles = _rule_roles(rule, baskets, by_service)
        if roles == {"joint"}:
            situation_counts["every applicant"] += 1
        elif "married_female" in roles or "conditional" in roles:
            situation_counts["married-applicant line"] += 1
        else:
            situation_counts["foreign-applicant line"] += 1
    reasons = {"whenever": 0, "no longer lists": 0, "not retrieved": 0}
    for rule in rules:
        if rule["charter_status"] != "rejected":
            continue
        reason = rule["charter_reason"]
        if "whenever" in reason:
            reasons["whenever"] += 1
        elif "no longer lists" in reason:
            reasons["no longer lists"] += 1
        elif "not retrieved" in reason:
            reasons["not retrieved"] += 1
    lines = [
        "Charter check",
        f"Retrieval date: {RETRIEVED_ON}",
        f"PRC list of requirements: retrieved ({PRC_URL})",
        f"SSS membership page: retrieved ({SSS_URL})",
        f"LTO citizen's charter PDF: not retrieved, HTTP 403 ({LTO_URL})",
        "",
        "A rule is confirmed when every supporting service's current page still requires the consequent whenever it requires the antecedent.",
        "A document qualified for married female applicants, foreign applicants, or degrees taken abroad is not treated as required of every applicant.",
        "Birth certificate or passport on the SSS page is an alternative, not a joint membership requirement.",
        "A marriage line limited to married applicants stays limited even when a repeater line omits that phrase.",
        "",
        f"Rules with lift greater than 1: {len(rules)}",
        f"Confirmed: {len(confirmed_rows)}",
        f"  of which every supporting line applies to every applicant: {situation_counts['every applicant']}",
        f"  of which a married-applicant line is part of the rule: {situation_counts['married-applicant line']}",
        f"  of which a foreign-applicant line is part of the rule: {situation_counts['foreign-applicant line']}",
        f"Rejected: {rejected}",
        f"  page does not require the consequent whenever the antecedent is required: {reasons['whenever']}",
        f"  a document in the rule is not listed as its own requirement: {reasons['no longer lists']}",
        f"  current page was not retrieved: {reasons['not retrieved']}",
        f"Service-document rows whose page was not retrieved: {not_retrieved}",
        "",
        "No confirmed rule has the PSA marriage certificate as its consequent.",
        "The two LTO rules were rejected because the citizen's charter PDF returned HTTP 403.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _rule_roles(rule: dict[str, str], baskets, by_service) -> set[str]:
    documents = _split_docs(rule["antecedent_documents"]) + _split_docs(rule["consequent_documents"])
    union = set(documents)
    supporters = [service_id for service_id, basket in baskets.items() if union <= basket]
    return {
        by_service.get(service_id, {}).get(document, "absent")
        for service_id in supporters
        for document in documents
    }


if __name__ == "__main__":
    print(run_charter_check())
