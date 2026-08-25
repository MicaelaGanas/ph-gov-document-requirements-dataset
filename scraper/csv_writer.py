"""CSV export for requirement records."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from scraper.models import CSV_COLUMNS, RequirementRecord


def write_csv(records: Iterable[RequirementRecord], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [record.to_row() for record in records]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
