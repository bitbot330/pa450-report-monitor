from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


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


def rows_to_csv(rows: list[dict[str, str]], csv_path: str | Path) -> None:
    if not rows:
        raise ValueError("No rows found in XML report result")
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
