"""Association rule mining on document dependencies (research starter)."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path


def load_dependencies(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mine_cooccurring_documents(
    dependencies: list[dict[str, str]],
    *,
    min_support: int = 2,
) -> list[tuple[str, str, int]]:
    """Return jointly required document pairs. Alternatives and conditionals stay out of this basket."""
    by_service: defaultdict[str, set[str]] = defaultdict(set)
    for row in dependencies:
        if row.get("relationship_type") != "required":
            continue
        doc = (row.get("required_document_normalized") or row.get("required_document") or "").strip()
        if not doc:
            continue
        by_service[row["service_id"]].add(doc)

    pair_counts: Counter[tuple[str, str]] = Counter()
    for docs in by_service.values():
        for a, b in combinations(sorted(docs), 2):
            pair_counts[(a, b)] += 1

    return [(a, b, count) for (a, b), count in pair_counts.most_common() if count >= min_support]


def run_analysis(final_dir: Path, output_dir: Path, min_support: int = 2) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    deps = load_dependencies(final_dir / "document_dependencies.csv")
    pairs = mine_cooccurring_documents(deps, min_support=min_support)

    out_path = output_dir / "association_document_pairs.csv"
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["document_a", "document_b", "co_occurrence_count"])
        writer.writerows(pairs)

    from mining.spmf_runner import run_primary_matrix

    run_primary_matrix(final_dir, output_dir, min_support_count=min_support)
    return out_path


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    print(run_analysis(root / "data" / "final", root / "output"))
