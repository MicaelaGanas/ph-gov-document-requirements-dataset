"""Run Apriori, FP-Growth, and Eclat from one SPMF jar on the primary matrix.

Lift is not passed to the miners. It is computed after the run as
confidence / support(consequent). Rules use every split of a frequent
itemset into a non-empty antecedent and a non-empty consequent.
"""

from __future__ import annotations

import csv
import os
import statistics
import subprocess
from collections import Counter
from fractions import Fraction
from itertools import combinations
from pathlib import Path

from mining.transaction_matrix import (
    encode_baskets,
    item_frequency,
    item_ids_for,
    load_dependencies,
    required_baskets,
    write_basket_sizes,
    write_baskets,
    write_frequency,
    write_item_map,
    write_spmf,
)

ROOT = Path(__file__).resolve().parents[1]
JAR_PATH = ROOT / "mining" / "lib" / "spmf.jar"
LAUNCHER_DIR = ROOT / "mining" / "lib"
ALGORITHMS = ("Apriori", "FPGrowth", "Eclat")
ALGORITHM_LABELS = {"Apriori": "Apriori", "FPGrowth": "FP-Growth", "Eclat": "Eclat"}
RUNS_PER_ALGORITHM = 3

# Locked from the item-frequency inspection of this matrix, before any lift was computed.
MIN_SUPPORT_COUNT = 2
MIN_CONFIDENCE = 0.5


def run_primary_matrix(
    final_dir: Path,
    output_dir: Path,
    *,
    min_support_count: int = MIN_SUPPORT_COUNT,
    min_confidence: float = MIN_CONFIDENCE,
) -> Path:
    """Mine the primary matrix and write the comparison tables. Returns the mining directory."""
    if min_support_count < 1:
        raise ValueError("minimum support count must be at least 1")
    if not 0 < min_confidence <= 1:
        raise ValueError("minimum confidence must be in (0, 1]")

    mining_dir = output_dir / "mining"
    mining_dir.mkdir(parents=True, exist_ok=True)
    _require_runtime()

    dependencies = load_dependencies(final_dir / "document_dependencies.csv")
    baskets = required_baskets(dependencies)
    if not baskets:
        raise RuntimeError("The primary matrix has no services with a required document.")
    ids = item_ids_for(baskets)
    encoded = encode_baskets(baskets, ids)
    names = {item_id: document for document, item_id in ids.items()}
    transaction_count = len(encoded)
    transactions = [item_set for _, _, item_set in encoded]

    input_name = "primary_transactions.spmf"
    write_spmf(mining_dir / input_name, encoded)
    write_item_map(mining_dir / "item_map.csv", ids)
    write_baskets(mining_dir / "transaction_baskets.csv", encoded, ids)
    frequencies = item_frequency(baskets)
    write_frequency(mining_dir / "item_frequency.csv", frequencies, ids, transaction_count, min_support_count)
    write_basket_sizes(mining_dir / "basket_sizes.csv", baskets)

    parsed: dict[str, dict[frozenset[int], int]] = {}
    timings_ms: dict[str, list[float]] = {}
    reported_ratio: str | None = None
    log_lines: list[str] = []

    for algorithm in ALGORITHMS:
        run_itemsets: list[dict[frozenset[int], int]] = []
        run_times: list[float] = []
        first_text = ""
        for run_index in range(1, RUNS_PER_ALGORITHM + 1):
            text, fields, stderr = _run_spmf(
                algorithm,
                mining_dir,
                input_name,
                mining_dir / f"_run_{algorithm}.txt",
                min_support_count,
            )
            if fields["TRANSACTIONS"] != str(transaction_count):
                raise RuntimeError(
                    f"{algorithm} read {fields['TRANSACTIONS']} transactions; the matrix has {transaction_count}."
                )
            if fields["MINSUP_ABSOLUTE"] != str(min_support_count):
                raise RuntimeError(
                    f"{algorithm} applied absolute support {fields['MINSUP_ABSOLUTE']} instead of {min_support_count}."
                )
            if reported_ratio is None:
                reported_ratio = fields["MINSUP_RATIO"]
            elif fields["MINSUP_RATIO"] != reported_ratio:
                raise RuntimeError("The three algorithms did not receive the same minimum-support ratio.")
            itemsets = _parse_itemsets(text)
            if any(count < min_support_count for count in itemsets.values()):
                raise RuntimeError(f"{algorithm} returned an itemset below the minimum support.")
            run_itemsets.append(itemsets)
            elapsed_ms = int(fields["ELAPSED_NS"]) / 1_000_000
            run_times.append(elapsed_ms)
            if run_index == 1:
                first_text = text
            elif itemsets != run_itemsets[0]:
                raise RuntimeError(f"{algorithm} run {run_index} did not match run 1.")
            log_lines.append(
                f"{algorithm} run {run_index}: {len(itemsets)} itemsets, {elapsed_ms:.3f} ms"
            )
            if stderr.strip():
                log_lines.append(stderr.strip())
        parsed[algorithm] = run_itemsets[0]
        timings_ms[algorithm] = run_times
        (mining_dir / f"itemsets_{algorithm.lower()}.txt").write_text(first_text, encoding="ascii")

    (mining_dir / "_run_Apriori.txt").unlink(missing_ok=True)
    (mining_dir / "_run_FPGrowth.txt").unlink(missing_ok=True)
    (mining_dir / "_run_Eclat.txt").unlink(missing_ok=True)
    (mining_dir / "spmf_run_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    reference = parsed["Apriori"]
    collections_match = all(parsed[algorithm] == reference for algorithm in ALGORITHMS)
    _write_comparison(
        mining_dir / "algorithm_comparison.csv",
        parsed,
        timings_ms,
        collections_match,
    )
    if not collections_match:
        raise RuntimeError(
            "Apriori, FP-Growth, and Eclat returned different frequent itemsets. "
            "Rules were not written. See output/mining/algorithm_comparison.csv and the itemset files."
        )

    recounted = _recount(reference, transactions)
    mismatched = [itemset for itemset, count in reference.items() if recounted[itemset] != count]
    if mismatched:
        example = sorted(mismatched[0])
        raise RuntimeError(
            f"SPMF support does not match a recount of the matrix. Example item ids: {example}."
        )

    python_itemsets = _python_frequent_itemsets(transactions, min_support_count)
    if python_itemsets != reference:
        missing = next(iter(python_itemsets.keys() - reference.keys()), None)
        extra = next(iter(reference.keys() - python_itemsets.keys()), None)
        raise RuntimeError(
            "SPMF itemsets differ from a separate frequent-itemset recount. "
            f"Missing example: {sorted(missing) if missing else None}. "
            f"Extra example: {sorted(extra) if extra else None}."
        )

    _check_pairs(dependencies, reference, ids, min_support_count)
    _write_frequent_itemsets(mining_dir / "frequent_itemsets.csv", reference, names, transaction_count)
    _write_itemset_sizes(mining_dir / "frequent_itemset_sizes.csv", reference)
    rules = _generate_rules(reference, transaction_count, min_confidence)
    _write_rules(mining_dir / "association_rules.csv", rules, names, transaction_count)
    kept = [rule for rule in rules if rule["lift"] > 1]
    _write_rules(mining_dir / "rules_lift_above_1.csv", kept, names, transaction_count)
    _write_parameters(
        mining_dir / "run_parameters.txt",
        dependencies=dependencies,
        baskets=baskets,
        frequencies=frequencies,
        transaction_count=transaction_count,
        min_support_count=min_support_count,
        minsup_ratio=reported_ratio or "",
        min_confidence=min_confidence,
        itemset_count=len(reference),
        rule_count=len(rules),
        lift_count=len(kept),
    )
    return mining_dir


def _require_runtime() -> None:
    if not JAR_PATH.is_file():
        raise FileNotFoundError(f"SPMF jar is missing: {JAR_PATH}")
    if not (LAUNCHER_DIR / "SpmfItemsetRun.class").is_file():
        raise FileNotFoundError("SpmfItemsetRun.class is missing from mining/lib.")


def _run_spmf(
    algorithm: str,
    mining_dir: Path,
    input_name: str,
    output_path: Path,
    min_support_count: int,
) -> tuple[str, dict[str, str], str]:
    classpath = os.pathsep.join([str(JAR_PATH), str(LAUNCHER_DIR), str(mining_dir)])
    completed = subprocess.run(
        [
            "java",
            "-cp",
            classpath,
            "SpmfItemsetRun",
            algorithm,
            input_name,
            str(output_path),
            str(min_support_count),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{algorithm} failed with exit code {completed.returncode}.\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    fields: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[0] in {"ELAPSED_NS", "TRANSACTIONS", "MINSUP_RATIO", "MINSUP_ABSOLUTE"}:
            fields[parts[0]] = parts[1].strip()
    if set(fields) != {"ELAPSED_NS", "TRANSACTIONS", "MINSUP_RATIO", "MINSUP_ABSOLUTE"}:
        raise RuntimeError(f"{algorithm} did not report its run. Output:\n{completed.stdout}\n{completed.stderr}")
    return output_path.read_text(encoding="ascii"), fields, completed.stderr


def _parse_itemsets(text: str) -> dict[frozenset[int], int]:
    itemsets: dict[frozenset[int], int] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if "#SUP:" not in line:
            raise RuntimeError(f"SPMF line {line_number} has no support: {line}")
        left, right = line.split("#SUP:", 1)
        itemset = frozenset(int(token) for token in left.split())
        support = int(right.strip().split()[0])
        if not itemset:
            raise RuntimeError(f"SPMF line {line_number} has an empty itemset.")
        if itemset in itemsets and itemsets[itemset] != support:
            raise RuntimeError(f"SPMF reported two supports for item ids {sorted(itemset)}.")
        itemsets[itemset] = support
    return itemsets


def _recount(itemsets: dict[frozenset[int], int], transactions: list[frozenset[int]]) -> dict[frozenset[int], int]:
    return {
        itemset: sum(1 for basket in transactions if itemset <= basket)
        for itemset in itemsets
    }


def _python_frequent_itemsets(
    transactions: list[frozenset[int]],
    min_support_count: int,
) -> dict[frozenset[int], int]:
    """Independent recount used only to detect a missing or extra SPMF itemset."""
    item_counts: Counter[int] = Counter(item for basket in transactions for item in basket)
    frequent: dict[frozenset[int], int] = {
        frozenset([item]): count for item, count in item_counts.items() if count >= min_support_count
    }
    previous = list(frequent)
    size = 2
    while previous:
        candidates: set[frozenset[int]] = set()
        for index, left in enumerate(previous):
            for right in previous[index + 1 :]:
                union = left | right
                if len(union) != size:
                    continue
                if all(frozenset(subset) in frequent for subset in combinations(union, size - 1)):
                    candidates.add(union)
        current: list[frozenset[int]] = []
        for candidate in candidates:
            count = sum(1 for basket in transactions if candidate <= basket)
            if count >= min_support_count:
                frequent[candidate] = count
                current.append(candidate)
        previous = current
        size += 1
    return frequent


def _check_pairs(
    dependencies: list[dict[str, str]],
    itemsets: dict[frozenset[int], int],
    ids: dict[str, int],
    min_support_count: int,
) -> None:
    from mining.association_analysis import mine_cooccurring_documents

    pair_counts = {
        frozenset((ids[left], ids[right])): count
        for left, right, count in mine_cooccurring_documents(dependencies, min_support=min_support_count)
    }
    mined_pairs = {itemset: count for itemset, count in itemsets.items() if len(itemset) == 2}
    if pair_counts != mined_pairs:
        raise RuntimeError(
            "Size-2 frequent itemsets do not match the required-document pair counts. "
            f"Pair table has {len(pair_counts)}; SPMF has {len(mined_pairs)}."
        )


def _write_comparison(
    path: Path,
    parsed: dict[str, dict[frozenset[int], int]],
    timings_ms: dict[str, list[float]],
    collections_match: bool,
) -> None:
    key_sets = {algorithm: set(itemsets) for algorithm, itemsets in parsed.items()}
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "algorithm",
            "frequent_itemset_count",
            "run_1_ms",
            "run_2_ms",
            "run_3_ms",
            "median_ms",
            "jaccard_with_apriori",
            "jaccard_with_fpgrowth",
            "jaccard_with_eclat",
            "itemsets_identical",
        ])
        for algorithm in ALGORITHMS:
            times = timings_ms[algorithm]
            writer.writerow([
                ALGORITHM_LABELS[algorithm],
                len(parsed[algorithm]),
                f"{times[0]:.3f}",
                f"{times[1]:.3f}",
                f"{times[2]:.3f}",
                f"{statistics.median(times):.3f}",
                f"{_jaccard(key_sets[algorithm], key_sets['Apriori']):.10f}",
                f"{_jaccard(key_sets[algorithm], key_sets['FPGrowth']):.10f}",
                f"{_jaccard(key_sets[algorithm], key_sets['Eclat']):.10f}",
                "yes" if collections_match else "no",
            ])


def _jaccard(left: set[frozenset[int]], right: set[frozenset[int]]) -> float:
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def _write_frequent_itemsets(
    path: Path,
    itemsets: dict[frozenset[int], int],
    names: dict[int, str],
    transaction_count: int,
) -> None:
    rows = sorted(itemsets.items(), key=lambda pair: (len(pair[0]), sorted(pair[0])))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item_ids", "documents", "size", "support_count", "support"])
        for itemset, count in rows:
            ordered = sorted(itemset)
            writer.writerow([
                " ".join(str(item_id) for item_id in ordered),
                " | ".join(names[item_id] for item_id in ordered),
                len(itemset),
                count,
                f"{count / transaction_count:.10f}",
            ])


def _write_itemset_sizes(path: Path, itemsets: dict[frozenset[int], int]) -> None:
    sizes = Counter(len(itemset) for itemset in itemsets)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["size", "frequent_itemsets"])
        for size in sorted(sizes):
            writer.writerow([size, sizes[size]])


def _generate_rules(
    itemsets: dict[frozenset[int], int],
    transaction_count: int,
    min_confidence: float,
) -> list[dict[str, object]]:
    minimum = Fraction(str(min_confidence))
    rules: list[dict[str, object]] = []
    for itemset, union_count in itemsets.items():
        if len(itemset) < 2:
            continue
        ordered = tuple(sorted(itemset))
        for width in range(1, len(ordered)):
            for antecedent_items in combinations(ordered, width):
                antecedent = frozenset(antecedent_items)
                consequent = itemset - antecedent
                if antecedent not in itemsets or consequent not in itemsets:
                    raise RuntimeError(
                        "A frequent itemset has a subset the miners did not return: "
                        f"{sorted(itemset)}"
                    )
                antecedent_count = itemsets[antecedent]
                consequent_count = itemsets[consequent]
                confidence = Fraction(union_count, antecedent_count)
                if confidence < minimum:
                    continue
                lift = Fraction(union_count * transaction_count, antecedent_count * consequent_count)
                rules.append({
                    "antecedent": antecedent,
                    "consequent": consequent,
                    "union_count": union_count,
                    "antecedent_count": antecedent_count,
                    "consequent_count": consequent_count,
                    "confidence": confidence,
                    "lift": lift,
                })
    rules.sort(
        key=lambda rule: (
            -rule["lift"],
            -rule["confidence"],
            sorted(rule["antecedent"]),
            sorted(rule["consequent"]),
        )
    )
    return rules


def _write_rules(
    path: Path,
    rules: list[dict[str, object]],
    names: dict[int, str],
    transaction_count: int,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "antecedent_ids",
            "consequent_ids",
            "antecedent_documents",
            "consequent_documents",
            "support_count",
            "antecedent_count",
            "consequent_count",
            "support",
            "confidence",
            "lift",
        ])
        for rule in rules:
            antecedent = sorted(rule["antecedent"])
            consequent = sorted(rule["consequent"])
            union_count = int(rule["union_count"])
            writer.writerow([
                " ".join(str(item_id) for item_id in antecedent),
                " ".join(str(item_id) for item_id in consequent),
                " | ".join(names[item_id] for item_id in antecedent),
                " | ".join(names[item_id] for item_id in consequent),
                union_count,
                rule["antecedent_count"],
                rule["consequent_count"],
                f"{union_count / transaction_count:.10f}",
                f"{float(rule['confidence']):.10f}",
                f"{float(rule['lift']):.10f}",
            ])


def _write_parameters(
    path: Path,
    *,
    dependencies: list[dict[str, str]],
    baskets: list[tuple[str, frozenset[str]]],
    frequencies: Counter[str],
    transaction_count: int,
    min_support_count: int,
    minsup_ratio: str,
    min_confidence: float,
    itemset_count: int,
    rule_count: int,
    lift_count: int,
) -> None:
    relationship_counts = Counter(row.get("relationship_type", "") for row in dependencies)
    sizes = [len(documents) for _, documents in baskets]
    frequent_items = sum(1 for count in frequencies.values() if count >= min_support_count)
    lines = [
        "Primary transaction matrix",
        "One service is one basket. Only document_dependencies.csv rows with relationship_type = required are included.",
        "A document listed more than once on the same service is stored once in that basket.",
        "Alternative and conditional rows are stored in the dependency table and are not items in this matrix.",
        "The sensitivity matrix (one transaction per alternative group) is not part of this run.",
        "",
        f"Dependency rows: {len(dependencies)}",
        f"Required rows: {relationship_counts.get('required', 0)}",
        f"Alternative rows: {relationship_counts.get('alternative', 0)}",
        f"Conditional rows: {relationship_counts.get('conditional', 0)}",
        f"Services in the matrix (N): {transaction_count}",
        f"Distinct documents: {len(frequencies)}",
        f"Documents with support count >= {min_support_count}: {frequent_items}",
        f"Basket size min / median / max: {min(sizes)} / {statistics.median(sizes)} / {max(sizes)}",
        "",
        "Thresholds locked before rule generation",
        f"Minimum support count: {min_support_count}",
        f"Minimum support ratio passed through SPMF: {minsup_ratio}",
        "SPMF converts that ratio with ceil(ratio * N). The launcher adjusts the double so the absolute count is exact.",
        f"Minimum confidence: {min_confidence}",
        "Lift is not an input. lift = confidence / support(consequent) = (support count of X union Y) * N / (support count of X * support count of Y).",
        "A rule is every split of a frequent itemset into a non-empty antecedent and a non-empty consequent whose confidence meets the minimum.",
        "",
        "Algorithms",
        "Apriori, FP-Growth, and Eclat were called from mining/lib/spmf.jar (SPMF 2.12.1, ca.pfv.spmf).",
        "Each algorithm read the same file, primary_transactions.spmf, and the same minimum support.",
        "The recorded time is the median of three runs, measured around the SPMF call in nanoseconds and reported in milliseconds.",
        "Frequent-itemset collections were compared before any rule was written. A difference stops the run.",
        "Support in the tables was recounted from the Python transactions and matched the SPMF #SUP values.",
        "",
        f"Frequent itemsets: {itemset_count}",
        f"Rules at or above minimum confidence: {rule_count}",
        f"Rules with lift greater than 1: {lift_count}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
