"""Validate normalized research dataset tables."""

from __future__ import annotations

import csv
from pathlib import Path


def validate_dataset_dir(dataset_dir: Path) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {}
    required_files = (
        "government_services.csv",
        "requirements.csv",
        "government_offices.csv",
        "service_locations.csv",
        "document_dependencies.csv",
    )

    for filename in required_files:
        path = dataset_dir / filename
        file_issues: list[str] = []
        if not path.exists():
            file_issues.append("missing file")
            issues[filename] = file_issues
            continue

        with path.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            file_issues.append("empty table")

        ids = [r.get(next(iter(r.keys()))) for r in rows] if rows else []
        if len(ids) != len(set(ids)):
            file_issues.append("duplicate primary IDs detected")

        if file_issues:
            issues[filename] = file_issues

    req_path = dataset_dir / "requirements.csv"
    svc_path = dataset_dir / "government_services.csv"
    if req_path.exists() and svc_path.exists():
        with req_path.open(encoding="utf-8") as handle:
            req_rows = list(csv.DictReader(handle))
        with svc_path.open(encoding="utf-8") as handle:
            svc_ids = {r["service_id"] for r in csv.DictReader(handle)}
        orphan = [r["requirement_id"] for r in req_rows if r.get("service_id") not in svc_ids]
        if orphan:
            issues.setdefault("requirements.csv", []).append(
                f"{len(orphan)} requirements reference unknown service_id"
            )

    sl_path = dataset_dir / "service_locations.csv"
    off_path = dataset_dir / "government_offices.csv"
    if sl_path.exists() and off_path.exists():
        with sl_path.open(encoding="utf-8") as handle:
            sl_rows = list(csv.DictReader(handle))
        with off_path.open(encoding="utf-8") as handle:
            office_ids = {r["office_id"] for r in csv.DictReader(handle)}
        bad = [r["service_location_id"] for r in sl_rows if r.get("office_id") not in office_ids]
        if bad:
            issues.setdefault("service_locations.csv", []).append(
                f"{len(bad)} rows reference unknown office_id"
            )

    return issues


def print_validation_report(dataset_dir: Path, counts: dict[str, int]) -> bool:
    issues = validate_dataset_dir(dataset_dir)
    total = sum(counts.values())
    print(f"\nDataset directory: {dataset_dir}")
    print("Record counts:")
    for name, count in counts.items():
        print(f"  {name}: {count}")
    print(f"  TOTAL (all tables): {total}")

    if issues:
        print("\nValidation issues:")
        for filename, file_issues in issues.items():
            for issue in file_issues:
                print(f"  - {filename}: {issue}")
        return False

    print("\nValidation: PASSED")
    return True
