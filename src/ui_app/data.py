from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from report import parse_int


DATE_KEY_RE = re.compile(r"^\d{8}$")
# AI output can arrive as one-line items or as a heading plus detail line. Keep
# these regexes centralized so row highlighting, summary cards, and tests parse
# the same analysis text shape.
ANALYSIS_ITEM_RE = re.compile(
    r"^第(?P<item_number>\d+)筆的來源：(?P<source>.*?)\s+"
    r"目的地：(?P<destination>.*?)\s+"
    r"(?:目的地國家：?.*?\s+)?"
    r"應用程式：(?P<application>.*?)\s+"
    r"位元組：(?P<bytes>.*)$"
)
ANALYSIS_ITEM_DETAIL_RE = re.compile(
    r"^(?:第(?P<prefix_item_number>\d+)筆(?:的)?\s*)?"
    r"來源：(?P<source>.*?)\s+"
    r"目的地：(?P<destination>.*?)\s+"
    r"(?:目的地國家：?.*?\s+)?"
    r"應用程式：(?P<application>.*?)\s+"
    r"位元組：(?P<bytes>.*)$"
)
ANALYSIS_ITEM_HEADING_RE = re.compile(r"^第(?P<item_number>\d+)筆[：:]?$")
ANALYSIS_ITEM_RAW_BYTES_RE = re.compile(r"^\d[\d,]*\s*bytes$", re.IGNORECASE)


def format_bytes_human(value: int | None) -> str:
    """Format raw byte counts for dense table/card display."""

    if value is None:
        return "—"
    units = ["bytes", "KB", "MB", "GB", "TB"]
    size = float(value)
    unit = units[0]
    for current_unit in units:
        unit = current_unit
        if size < 1024 or current_unit == units[-1]:
            break
        size /= 1024
    if unit == "bytes":
        return f"{value:,} bytes"
    return f"{size:.1f} {unit}"


def _analysis_item_from_match(item_match: re.Match[str], fallback_item_number: str = "") -> dict[str, str]:
    return {
        "item_number": (item_match.groupdict().get("item_number") or item_match.groupdict().get("prefix_item_number") or fallback_item_number).strip(),
        "source": item_match.group("source").strip(),
        "destination": item_match.group("destination").strip(),
        "application": item_match.group("application").strip(),
        "bytes": item_match.group("bytes").strip(),
    }


def parse_analysis_sections(analysis_text: str) -> dict[str, Any]:
    """Extract status, summary, reason, and abnormal row items from AI text."""

    parsed = {
        "status": "",
        "summary": "",
        "source": "",
        "destination": "",
        "application": "",
        "bytes": "",
        "reason": "",
        "items": [],
    }
    pending_item_number = ""
    for raw_line in analysis_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = line.lstrip("- ")
        item_match = ANALYSIS_ITEM_RE.match(normalized)
        item_detail_match = ANALYSIS_ITEM_DETAIL_RE.match(normalized)
        item_heading_match = ANALYSIS_ITEM_HEADING_RE.match(normalized)
        if normalized.startswith("異常狀態："):
            parsed["status"] = normalized.split("：", 1)[1].strip()
            pending_item_number = ""
        elif normalized.startswith("摘要："):
            parsed["summary"] = normalized.split("：", 1)[1].strip()
            pending_item_number = ""
        elif item_match:
            parsed["items"].append(_analysis_item_from_match(item_match))
            pending_item_number = ""
        elif item_detail_match and (pending_item_number or item_detail_match.groupdict().get("prefix_item_number")):
            parsed["items"].append(_analysis_item_from_match(item_detail_match, pending_item_number))
            pending_item_number = ""
        elif ANALYSIS_ITEM_RAW_BYTES_RE.match(normalized) and parsed["items"]:
            parsed["items"][-1]["bytes"] = normalized
        elif item_heading_match:
            pending_item_number = item_heading_match.group("item_number").strip()
        elif normalized.startswith("來源："):
            parsed["source"] = normalized.split("：", 1)[1].strip()
            pending_item_number = ""
        elif normalized.startswith("目的地："):
            parsed["destination"] = normalized.split("：", 1)[1].strip()
            pending_item_number = ""
        elif normalized.startswith("應用程式："):
            parsed["application"] = normalized.split("：", 1)[1].strip()
            pending_item_number = ""
        elif normalized.startswith("位元組："):
            parsed["bytes"] = normalized.split("：", 1)[1].strip()
            pending_item_number = ""
        elif normalized.startswith("原因："):
            parsed["reason"] = normalized.split("：", 1)[1].strip()
            pending_item_number = ""
    if parsed["items"]:
        first_item = parsed["items"][0]
        parsed["source"] = parsed["source"] or first_item["source"]
        parsed["destination"] = parsed["destination"] or first_item["destination"]
        parsed["application"] = parsed["application"] or first_item["application"]
        parsed["bytes"] = parsed["bytes"] or first_item["bytes"]
    return parsed


def load_csv_rows(csv_path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a UTF-8-sig CSV report and preserve header order for the UI table."""

    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = [{key: value or "" for key, value in row.items()} for row in reader]
    if not headers:
        raise ValueError(f"CSV file has no headers: {csv_path}")
    return headers, rows


def load_analysis_payload(analysis_json_path: str | Path) -> dict[str, Any]:
    """Read the analysis JSON written by analyze.py."""

    payload = json.loads(Path(analysis_json_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Analysis JSON must be an object: {analysis_json_path}")
    return payload


def summarize_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Build lightweight CSV-only summary metrics shown above the table."""

    source_counter = Counter(row.get("來源位址", "").strip() for row in rows if row.get("來源位址", "").strip())
    destination_counter = Counter(row.get("目的地位址", "").strip() for row in rows if row.get("目的地位址", "").strip())
    byte_values = [parse_int(row.get("位元組")) for row in rows]
    valid_bytes = [value for value in byte_values if value is not None]
    max_bytes = max(valid_bytes, default=0)
    total_bytes = sum(valid_bytes)
    top_source_value, top_source_count = source_counter.most_common(1)[0] if source_counter else ("-", 0)
    return {
        "total_rows": len(rows),
        "unique_sources": len(source_counter),
        "unique_destinations": len(destination_counter),
        "max_bytes_human": format_bytes_human(max_bytes),
        "max_bytes_raw": f"{max_bytes:,} bytes",
        "total_bytes_human": format_bytes_human(total_bytes),
        "total_bytes_raw": f"{total_bytes:,} bytes",
        "top_source": {"value": top_source_value, "row_count": top_source_count},
    }


def enrich_rows_for_display(headers: list[str], rows: list[dict[str, str]]) -> tuple[list[str], list[dict[str, str]]]:
    """Add UI-friendly byte labels while preserving raw bytes for matching."""

    display_headers = ["傳輸量" if header == "位元組" else header for header in headers]
    display_rows: list[dict[str, str]] = []
    for row in rows:
        display_row = dict(row)
        if "位元組" in row:
            raw_bytes = row.get("位元組", "")
            byte_value = parse_int(raw_bytes)
            display_row["傳輸量"] = raw_bytes if byte_value is None else f"{format_bytes_human(byte_value)} ({byte_value:,} bytes)"
            display_row["__raw_bytes"] = raw_bytes
            display_row.pop("位元組", None)
        display_rows.append(display_row)
    return display_headers, display_rows


REVIEW_STATUS_LABELS = {
    "": "未設定",
    "normal": "整體正常",
    "follow-up": "有異常需追蹤",
    "ai-adjustment": "AI 判讀需調整",
}


def _report_date_label(date_key: str) -> str:
    return f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:8]}"


def _report_month_group(date_key: str) -> str:
    return f"{date_key[:4]}-{date_key[4:6]}"


def _report_month_label(date_key: str) -> str:
    return f"{date_key[:4]} 年 {date_key[4:6]} 月"


def _review_markdown_path(review_dir: str | Path, date_key: str | None = None) -> Path:
    if date_key is None:
        raise ValueError("date_key is required for review markdown path")
    _validated_date_key(date_key)
    return _normalized_base(review_dir) / f"report_{date_key}.md"


def _split_review_markdown_entries(text: str) -> list[str]:
    entries = [chunk.strip() for chunk in re.split(r"\n\s*---\s*\n", text.strip())]
    return [entry for entry in entries if entry]


def _parse_review_markdown(text: str) -> dict[str, str]:
    note = ""
    marker = "## 備註\n"
    if marker in text:
        note = text.split(marker, 1)[1].lstrip("\n").rstrip("\n")

    status_match = re.search(r"(?m)^- 分類：\s*(.*)$", text)

    row_fields: dict[str, str] = {}
    for header in ["來源位址", "目的地位址", "應用程式", "傳輸量"]:
        match = re.search(rf"(?m)^- {re.escape(header)}：\s*(.*)$", text)
        row_fields[header] = match.group(1).strip() if match else ""

    return {
        "reviewStatus": status_match.group(1).strip() if status_match else "",
        "reviewNote": note,
        "rowFields": row_fields,
    }


def _minimal_review_markdown_content(review_note: str, row_fields: dict[str, Any] | None = None, review_status: str = "") -> str:
    row_fields = row_fields or {}
    lines = ["# 報告回報"]
    status = str(review_status or "").strip()
    if status:
        lines.append(f"- 分類：{status}")
    for header in ["來源位址", "目的地位址", "應用程式", "傳輸量"]:
        lines.append(f"- {header}：{str(row_fields.get(header) or '').strip()}")
    lines.append("## 備註")
    note = str(review_note or "").rstrip()
    if note:
        lines.extend(["", note])
    return "\n".join(lines).rstrip() + "\n"


def _review_identity_fields(row_fields: dict[str, Any] | None = None) -> dict[str, str]:
    row_fields = row_fields or {}
    return {
        header: str(row_fields.get(header) or "").strip()
        for header in ["來源位址", "目的地位址", "應用程式", "傳輸量"]
    }


def _same_review_identity(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
    return _review_identity_fields(left) == _review_identity_fields(right)


def save_review_markdown(
    review_dir: str | Path,
    date_key: str,
    review_status: str,
    review_note: str,
    row_index: int,
    row_fields: dict[str, Any] | None = None,
    row_number: int | None = None,
    csv_line_number: int | None = None,
) -> Path:
    """Create or update one row-review entry in report_YYYYMMDD.md."""

    _validated_date_key(date_key)
    int(row_index)
    report_path = _review_markdown_path(review_dir, date_key)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_row_fields = _review_identity_fields(row_fields)
    entry = _minimal_review_markdown_content(review_note, normalized_row_fields, review_status).rstrip()
    separator = "\n---\n\n"
    if not report_path.exists() or not report_path.read_text(encoding="utf-8").strip():
        report_path.write_text(entry + "\n", encoding="utf-8")
        return report_path

    existing_entries = [
        _parse_review_markdown(existing_entry)
        for existing_entry in _split_review_markdown_entries(report_path.read_text(encoding="utf-8"))
    ]
    # Row indexes can shift when reports are regenerated, so replacement uses
    # stable row identity fields instead of trusting the previous index alone.
    replacement_index = next(
        (index for index, existing_entry in enumerate(existing_entries) if _same_review_identity(existing_entry.get("rowFields"), normalized_row_fields)),
        None,
    )
    rendered_entries = [
        _minimal_review_markdown_content(
            str(entry_payload.get("reviewNote") or ""),
            _review_identity_fields(entry_payload.get("rowFields") or {}),
            str(entry_payload.get("reviewStatus") or ""),
        ).rstrip()
        for entry_payload in existing_entries
    ]
    if replacement_index is None:
        rendered_entries.append(entry)
    else:
        rendered_entries[replacement_index] = entry
    report_path.write_text(separator.join(rendered_entries) + "\n", encoding="utf-8")
    return report_path


def load_review_markdown(
    review_dir: str | Path,
    date_key: str,
    rows: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Load saved row-review markdown and map entries back to current rows."""

    _validated_date_key(date_key)
    report_path = _review_markdown_path(review_dir, date_key)
    if not report_path.exists():
        return {}
    parsed_entries = [_parse_review_markdown(entry) for entry in _split_review_markdown_entries(report_path.read_text(encoding="utf-8"))]
    if not rows:
        return {
            str(index): {
                **entry,
                "rowIndex": index,
                "rowNumber": index + 1,
                "csvLineNumber": index + 2,
            }
            for index, entry in enumerate(parsed_entries)
        }

    reviews: dict[str, dict[str, Any]] = {}
    used_row_indexes: set[int] = set()
    for entry in parsed_entries:
        matched_index: int | None = None
        entry_fields = entry.get("rowFields")
        if not isinstance(entry_fields, dict):
            continue
        for index, row in enumerate(rows):
            if index in used_row_indexes:
                continue
            if _same_review_identity(row, entry_fields):
                matched_index = index
                break
        if matched_index is None:
            continue
        used_row_indexes.add(matched_index)
        reviews[str(matched_index)] = {
            **entry,
            "rowIndex": matched_index,
            "rowNumber": matched_index + 1,
            "csvLineNumber": matched_index + 2,
        }
    return reviews


def _validated_date_key(date_key: str) -> str:
    """Validate the compact YYYYMMDD date keys used in file names and routes."""

    if not DATE_KEY_RE.fullmatch(date_key):
        raise ValueError(f"Invalid report date: {date_key}")
    return date_key


def validate_date_key(date_key: str) -> str:
    """Public route/API wrapper for validating compact YYYYMMDD report dates."""

    return _validated_date_key(date_key)


def _normalized_base(data_dir: str | Path) -> Path:
    return Path(data_dir).expanduser()


def normalize_base_dir(data_dir: str | Path) -> Path:
    """Public route/API wrapper for normalizing user-selected folders."""

    return _normalized_base(data_dir)


def _date_key_from_ancestors(path: Path) -> str | None:
    for part in reversed(path.parent.parts):
        if DATE_KEY_RE.fullmatch(part):
            return part
    return None


def _csv_date_key(path: Path) -> str | None:
    name = path.name
    if name.endswith("_report.csv"):
        date_key = path.stem.removesuffix("_report")
        if DATE_KEY_RE.fullmatch(date_key):
            return date_key
    if name == "report.csv":
        return _date_key_from_ancestors(path)
    return None


def _analysis_date_key(path: Path) -> str | None:
    if path.suffix.lower() != ".json":
        return None
    if DATE_KEY_RE.fullmatch(path.stem):
        return path.stem
    if path.name == "analysis.json":
        return _date_key_from_ancestors(path)
    return None


def _iter_files(base: Path):
    if not base.exists() or not base.is_dir():
        return
    for root, _dirs, files in os.walk(base):
        for filename in files:
            yield Path(root) / filename


def _candidate_score(base: Path, path: Path) -> tuple[int, int, str]:
    try:
        relative = path.relative_to(base)
    except ValueError:
        relative = path
    # 越靠近 base 越優先；同層級時以較新的檔案優先。
    try:
        mtime = int(path.stat().st_mtime)
    except OSError:
        mtime = 0
    return (len(relative.parts), -mtime, str(relative))


def _set_best_candidate(report_map: dict[str, dict[str, Path]], date_key: str, kind: str, path: Path, base: Path) -> None:
    current = report_map.setdefault(date_key, {}).get(kind)
    if current is None or _candidate_score(base, path) < _candidate_score(base, current):
        report_map[date_key][kind] = path


def _relative_label(base: Path, path: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def build_report_map(csv_dir: str | Path, analysis_dir: str | Path) -> dict[str, dict[str, Path]]:
    """Find matching CSV and analysis JSON files grouped by report date."""

    csv_base = _normalized_base(csv_dir)
    analysis_base = _normalized_base(analysis_dir)
    report_map: dict[str, dict[str, Path]] = {}

    for path in _iter_files(csv_base):
        if path.suffix.lower() != ".csv":
            continue
        date_key = _csv_date_key(path)
        if date_key:
            _set_best_candidate(report_map, date_key, "csv", path, csv_base)

    for path in _iter_files(analysis_base):
        if path.suffix.lower() != ".json":
            continue
        date_key = _analysis_date_key(path)
        if date_key:
            _set_best_candidate(report_map, date_key, "analysis", path, analysis_base)

    return report_map


def discover_reports(csv_dir: str | Path, analysis_dir: str | Path) -> list[dict[str, str]]:
    """Return sidebar-ready report metadata for dates with both CSV and JSON."""

    csv_base = _normalized_base(csv_dir)
    analysis_base = _normalized_base(analysis_dir)
    report_map = build_report_map(csv_base, analysis_base)

    reports: list[dict[str, str]] = []
    for date_key, paths in sorted(report_map.items(), reverse=True):
        if "csv" not in paths or "analysis" not in paths:
            continue
        reports.append({
            "date": date_key,
            "label": _report_date_label(date_key),
            "month_group": _report_month_group(date_key),
            "month_label": _report_month_label(date_key),
            "summary": f"CSV: {_relative_label(csv_base, paths['csv'])} · AI: {_relative_label(analysis_base, paths['analysis'])}",
            "csv_path": str(paths["csv"]),
            "analysis_path": str(paths["analysis"]),
        })
    return reports


def locate_report_paths(csv_dir: str | Path, analysis_dir: str | Path, date_key: str) -> tuple[Path, Path]:
    """Resolve the best CSV/JSON pair for one report date."""

    report_map = build_report_map(csv_dir, analysis_dir)
    paths = report_map.get(date_key, {})
    csv_path = paths.get("csv")
    json_path = paths.get("analysis")
    if not csv_path or not json_path:
        raise FileNotFoundError(f"Report bundle not found for date: {date_key}")
    return csv_path, json_path


def select_folder_dialog(initial_dir: str | Path) -> str | None:
    """Open a native folder picker for the localhost UI."""

    initial_path = _normalized_base(initial_dir)
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise RuntimeError(f"Cannot open folder picker because tkinter is unavailable: {exc}") from exc

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    try:
        selected = filedialog.askdirectory(
            parent=root,
            initialdir=str(initial_path if initial_path.exists() else Path.cwd()),
            title="選擇資料夾",
            mustexist=False,
        )
    finally:
        root.destroy()
    return selected or None


def load_report_bundle(csv_dir: str | Path, analysis_dir: str | Path, review_dir: str | Path, date_key: str) -> dict[str, Any]:
    """Load one day's CSV, AI analysis, summary metrics, and row reviews."""

    date_key = _validated_date_key(date_key)
    csv_path, json_path = locate_report_paths(csv_dir, analysis_dir, date_key)

    headers, rows = load_csv_rows(csv_path)
    analysis_payload = load_analysis_payload(json_path)
    analysis_text = str(analysis_payload.get("analysis") or "")
    display_headers, display_rows = enrich_rows_for_display(headers, rows)
    analysis_sections = parse_analysis_sections(analysis_text)
    analysis_bytes_value = parse_int(analysis_sections.get("bytes"))
    analysis_sections["bytes_human"] = format_bytes_human(analysis_bytes_value) if analysis_bytes_value is not None else ""
    analysis_sections["bytes_raw"] = f"{analysis_bytes_value:,} bytes" if analysis_bytes_value is not None else analysis_sections.get("bytes", "")

    return {
        "mode": "single",
        "date": date_key,
        "label": _report_date_label(date_key),
        "csv_dir": str(_normalized_base(csv_dir)),
        "analysis_dir": str(_normalized_base(analysis_dir)),
        "review_dir": str(_normalized_base(review_dir)),
        "csv_path": str(csv_path),
        "analysis_path": str(json_path),
        "headers": display_headers,
        "rows": display_rows,
        "summary": summarize_rows(rows),
        "analysis_text": analysis_text,
        "analysis_sections": analysis_sections,
        "daily_analyses": [],
        "reviews": load_review_markdown(review_dir, date_key, display_rows),
    }


def load_report_range_bundle(
    csv_dir: str | Path,
    analysis_dir: str | Path,
    review_dir: str | Path,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Load a date-range view while preserving each row's source report date."""

    start_date = _validated_date_key(start_date)
    end_date = _validated_date_key(end_date)
    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")

    selected_reports = [
        report
        for report in discover_reports(csv_dir, analysis_dir)
        if start_date <= report["date"] <= end_date
    ]
    if not selected_reports:
        raise FileNotFoundError(f"No report bundles found for date range: {start_date}-{end_date}")

    range_headers: list[str] = []
    range_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, str]] = []
    daily_analyses: list[dict[str, Any]] = []
    range_reviews: dict[str, dict[str, Any]] = {}

    for report in selected_reports:
        bundle = load_report_bundle(csv_dir, analysis_dir, review_dir, report["date"])
        if not range_headers:
            range_headers = ["報告日期", *bundle["headers"]]
        daily_analyses.append({
            "date": bundle["date"],
            "label": bundle["label"],
            "analysis_text": bundle["analysis_text"],
            "analysis_sections": bundle["analysis_sections"],
            "summary": bundle["summary"],
        })
        _raw_headers, raw_rows = load_csv_rows(bundle["csv_path"])
        summary_rows.extend(raw_rows)
        for row_index, row in enumerate(bundle["rows"]):
            global_index = len(range_rows)
            range_row = dict(row)
            range_row["報告日期"] = bundle["label"]
            range_row["__report_date"] = bundle["date"]
            range_row["__report_row_index"] = row_index
            range_rows.append(range_row)
            saved_review = (bundle.get("reviews") or {}).get(str(row_index))
            if saved_review:
                range_reviews[str(global_index)] = saved_review

    daily_analyses.sort(key=lambda item: item["date"])

    summary = summarize_rows(summary_rows)
    summary["covered_days"] = len(selected_reports)
    return {
        "mode": "range",
        "date": f"{start_date}-{end_date}",
        "start_date": start_date,
        "end_date": end_date,
        "label": f"{_report_date_label(start_date)} ～ {_report_date_label(end_date)}",
        "csv_dir": str(_normalized_base(csv_dir)),
        "analysis_dir": str(_normalized_base(analysis_dir)),
        "review_dir": str(_normalized_base(review_dir)),
        "headers": range_headers,
        "rows": range_rows,
        "summary": summary,
        "analysis_text": "",
        "analysis_sections": {},
        "daily_analyses": daily_analyses,
        "reviews": range_reviews,
    }
