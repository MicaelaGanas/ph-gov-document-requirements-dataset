"""Primary transaction matrix for association-rule mining.

One service is one basket. Only dependency rows with relationship_type
"required" are included. Alternatives and conditionals stay out.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def load_dependencies(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def required_baskets(dependencies: list[dict[str, str]]) -> list[tuple[str, frozenset[str]]]:
    """Return (service_id, required documents) for services that have at least one."""
    by_service: dict[str, set[str]] = {}
    for row in dependencies:
        if row.get("relationship_type") != "required":
            continue
        document = (row.get("required_document_normalized") or row.get("required_document") or "").strip()
        if not document:
            continue
        service_id = row["service_id"].strip()
        by_service.setdefault(service_id, set()).add(document)
    return [(service_id, frozenset(documents)) for service_id, documents in sorted(by_service.items()) if documents]


def item_ids_for(baskets: list[tuple[str, frozenset[str]]]) -> dict[str, int]:
    """Stable positive integer ids. SPMF item ids start at 1."""
    names = sorted({document for _, documents in baskets for document in documents})
    return {name: index for index, name in enumerate(names, start=1)}


def encode_baskets(
    baskets: list[tuple[str, frozenset[str]]],
    ids: dict[str, int],
) -> list[tuple[str, frozenset[str], frozenset[int]]]:
    encoded: list[tuple[str, frozenset[str], frozenset[int]]] = []
    for service_id, documents in baskets:
        encoded.append((service_id, documents, frozenset(ids[document] for document in documents)))
    return encoded


def write_spmf(path: Path, encoded: list[tuple[str, frozenset[str], frozenset[int]]]) -> None:
    """One transaction per line, items sorted, ASCII integers only."""
    lines = [" ".join(str(item_id) for item_id in sorted(item_set)) for _, _, item_set in encoded]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def write_item_map(path: Path, ids: dict[str, int]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item_id", "document"])
        for document, item_id in sorted(ids.items(), key=lambda pair: pair[1]):
            writer.writerow([item_id, document])


def write_baskets(
    path: Path,
    encoded: list[tuple[str, frozenset[str], frozenset[int]]],
    ids: dict[str, int],
) -> None:
    names = {item_id: document for document, item_id in ids.items()}
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["service_id", "basket_size", "item_ids", "documents"])
        for service_id, documents, item_set in encoded:
            ordered_ids = sorted(item_set)
            writer.writerow([
                service_id,
                len(documents),
                " ".join(str(item_id) for item_id in ordered_ids),
                " | ".join(names[item_id] for item_id in ordered_ids),
            ])


def item_frequency(baskets: list[tuple[str, frozenset[str]]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for _, documents in baskets:
        counts.update(documents)
    return counts


def write_frequency(path: Path, counts: Counter[str], ids: dict[str, int], transaction_count: int, min_support_count: int) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item_id", "document", "support_count", "support", "meets_min_support"])
        for document, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
            writer.writerow([
                ids[document],
                document,
                count,
                f"{count / transaction_count:.10f}",
                "yes" if count >= min_support_count else "no",
            ])


def write_basket_sizes(path: Path, baskets: list[tuple[str, frozenset[str]]]) -> None:
    sizes = Counter(len(documents) for _, documents in baskets)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["basket_size", "services"])
        for size in sorted(sizes):
            writer.writerow([size, sizes[size]])
