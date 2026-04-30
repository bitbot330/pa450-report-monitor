from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class OutputColumn:
    header: str
    candidates: list[str]


def xml_text_to_rows(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    rows: list[dict[str, str]] = []
    for entry in root.findall(".//entry"):
        row: dict[str, str] = {}
        for child in list(entry):
            if list(child):
                row[child.tag] = " ".join((grand.text or "").strip() for grand in list(child)).strip()
            else:
                row[child.tag] = (child.text or "").strip()
        if row:
            rows.append(row)
    return rows


def _first_matching_value(row: dict[str, str], candidates: list[str]) -> str:
    normalized = {key.lower().replace("_", "-").replace(" ", "-"): value for key, value in row.items()}
    for candidate in candidates:
        if candidate in row:
            return row[candidate]
        normalized_candidate = candidate.lower().replace("_", "-").replace(" ", "-")
        if normalized_candidate in normalized:
            return normalized[normalized_candidate]
    return ""


def _align_rows_to_columns(rows: list[dict[str, str]], columns: list[OutputColumn]) -> list[dict[str, str]]:
    aligned_rows: list[dict[str, str]] = []
    for row in rows:
        aligned_rows.append(
            {column.header: _first_matching_value(row, column.candidates) for column in columns}
        )
    return aligned_rows


def rows_to_csv(
    rows: list[dict[str, str]],
    csv_path: str | Path,
    columns: list[OutputColumn] | None = None,
) -> None:
    if not rows:
        raise ValueError("No rows found in XML report result")
    if columns:
        headers = [column.header for column in columns]
        rows = _align_rows_to_columns(rows, columns)
    else:
        headers = sorted({key for row in rows for key in row.keys()})
    with Path(csv_path).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def xml_file_to_csv(xml_path: str | Path, csv_path: str | Path) -> list[dict[str, str]]:
    xml_text = Path(xml_path).read_text(encoding="utf-8")
    rows = xml_text_to_rows(xml_text)
    rows_to_csv(rows, csv_path)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert PAN-OS report XML entries to CSV")
    parser.add_argument("xml_path")
    parser.add_argument("csv_path")
    args = parser.parse_args(argv)
    rows = xml_file_to_csv(args.xml_path, args.csv_path)
    print(f"wrote {args.csv_path} with {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
