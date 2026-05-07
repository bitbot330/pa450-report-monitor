from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
import tkinter as tk
from tkinter import ttk

from report import parse_int

APP_TITLE = "PA450 Daily Review UI"
DARK_BG = "#0b1220"
PANEL_BG = "#111b2e"
PANEL_BG_2 = "#16223a"
TEXT_COLOR = "#e8eefc"
MUTED_COLOR = "#9eb2d0"
ACCENT_COLOR = "#65b7ff"
TREE_BG = "#13213a"


def format_bytes_human(value: int | None) -> str:
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


def parse_analysis_sections(analysis_text: str) -> dict[str, str]:
    parsed = {
        "status": "",
        "summary": "",
        "source": "",
        "destination": "",
        "application": "",
        "bytes": "",
        "reason": "",
    }
    for raw_line in analysis_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = line.lstrip("- ")
        if normalized.startswith("異常狀態："):
            parsed["status"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("摘要："):
            parsed["summary"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("來源："):
            parsed["source"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("目的地："):
            parsed["destination"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("應用程式："):
            parsed["application"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("位元組："):
            parsed["bytes"] = normalized.split("：", 1)[1].strip()
        elif normalized.startswith("原因："):
            parsed["reason"] = normalized.split("：", 1)[1].strip()
    return parsed


def load_csv_rows(csv_path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = list(reader.fieldnames or [])
        rows = [{key: value or "" for key, value in row.items()} for row in reader]
    if not headers:
        raise ValueError(f"CSV file has no headers: {csv_path}")
    return headers, rows


def load_analysis_payload(analysis_json_path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(analysis_json_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Analysis JSON must be an object: {analysis_json_path}")
    return payload


def summarize_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
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
        "max_bytes": max_bytes,
        "max_bytes_human": format_bytes_human(max_bytes),
        "max_bytes_raw": f"{max_bytes:,} bytes",
        "total_bytes": total_bytes,
        "total_bytes_human": format_bytes_human(total_bytes),
        "total_bytes_raw": f"{total_bytes:,} bytes",
        "top_source": {"value": top_source_value, "row_count": top_source_count},
    }


def enrich_rows_for_display(headers: list[str], rows: list[dict[str, str]]) -> tuple[list[str], list[dict[str, str]]]:
    display_headers = ["傳輸量" if header == "位元組" else header for header in headers]
    display_rows: list[dict[str, str]] = []
    for row in rows:
        display_row = dict(row)
        if "位元組" in row:
            byte_value = parse_int(row.get("位元組"))
            display_row["傳輸量"] = row.get("位元組", "") if byte_value is None else f"{format_bytes_human(byte_value)} ({byte_value:,} bytes)"
            display_row.pop("位元組", None)
        display_rows.append(display_row)
    return display_headers, display_rows


def _report_date_label(date_key: str) -> str:
    if len(date_key) == 8 and date_key.isdigit():
        return f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:8]}"
    return date_key


def discover_reports(data_dir: str | Path) -> list[dict[str, str]]:
    base = Path(data_dir)
    report_map: dict[str, dict[str, Path]] = {}

    if not base.exists():
        return []

    for csv_path in sorted(base.glob("*_report.csv")):
        date_key = csv_path.stem.removesuffix("_report")
        report_map.setdefault(date_key, {})["csv"] = csv_path
    for json_path in sorted(base.glob("*.json")):
        report_map.setdefault(json_path.stem, {})["analysis"] = json_path
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        csv_candidate = child / "report.csv"
        analysis_candidate = child / "analysis.json"
        if csv_candidate.exists() and analysis_candidate.exists():
            report_map.setdefault(child.name, {})["csv"] = csv_candidate
            report_map.setdefault(child.name, {})["analysis"] = analysis_candidate

    reports: list[dict[str, str]] = []
    for date_key, paths in sorted(report_map.items(), reverse=True):
        if "csv" not in paths or "analysis" not in paths:
            continue
        reports.append(
            {
                "date": date_key,
                "label": _report_date_label(date_key),
                "summary": f"CSV: {paths['csv'].name} · AI: {paths['analysis'].name}",
            }
        )
    return reports


def load_report_bundle(data_dir: str | Path, date_key: str) -> dict[str, Any]:
    base = Path(data_dir)
    csv_path = base / f"{date_key}_report.csv"
    json_path = base / f"{date_key}.json"
    if not (csv_path.exists() and json_path.exists()):
        folder_csv = base / date_key / "report.csv"
        folder_json = base / date_key / "analysis.json"
        if folder_csv.exists() and folder_json.exists():
            csv_path, json_path = folder_csv, folder_json
    if not csv_path.exists() or not json_path.exists():
        raise FileNotFoundError(f"Report bundle not found for date: {date_key}")

    raw_headers, raw_rows = load_csv_rows(csv_path)
    analysis_payload = load_analysis_payload(json_path)
    analysis_text = str(analysis_payload.get("analysis") or "")
    display_headers, display_rows = enrich_rows_for_display(raw_headers, raw_rows)
    analysis_sections = parse_analysis_sections(analysis_text)
    analysis_bytes_value = parse_int(analysis_sections.get("bytes"))
    analysis_sections["bytes_human"] = format_bytes_human(analysis_bytes_value) if analysis_bytes_value is not None else ""
    analysis_sections["bytes_raw"] = f"{analysis_bytes_value:,} bytes" if analysis_bytes_value is not None else analysis_sections.get("bytes", "")

    return {
        "date": date_key,
        "label": _report_date_label(date_key),
        "csv_path": str(csv_path),
        "analysis_json_path": str(json_path),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "headers": display_headers,
        "rows": display_rows,
        "summary": summarize_rows(raw_rows),
        "analysis_text": analysis_text,
        "analysis_sections": analysis_sections,
    }


class DesktopReportApp(tk.Tk):
    def __init__(self, data_dir: str | Path) -> None:
        super().__init__()
        self.data_dir = Path(data_dir)
        self.reports = discover_reports(self.data_dir)
        self.current_report: dict[str, Any] | None = None
        self.filtered_rows: list[dict[str, str]] = []
        self.search_var = tk.StringVar()
        self.source_var = tk.StringVar()
        self.app_var = tk.StringVar()
        self.review_status_var = tk.StringVar()

        self.title(APP_TITLE)
        self.geometry("1500x900")
        self.configure(bg=DARK_BG)
        self._configure_ttk()
        self._build_layout()
        self._load_initial_report()

    def _configure_ttk(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Dark.Treeview", background=PANEL_BG, fieldbackground=PANEL_BG, foreground=TEXT_COLOR, rowheight=28)
        style.configure("Dark.Treeview.Heading", background=TREE_BG, foreground=TEXT_COLOR)
        style.map("Dark.Treeview", background=[("selected", ACCENT_COLOR)], foreground=[("selected", DARK_BG)])

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = tk.Frame(self, bg="#0f1728", width=280)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)

        tk.Label(sidebar, text=APP_TITLE, bg="#0f1728", fg=TEXT_COLOR, font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 6))
        tk.Label(sidebar, text=f"資料夾：{self.data_dir}", bg="#0f1728", fg=MUTED_COLOR, justify="left", wraplength=240).grid(row=1, column=0, sticky="w", padx=18)

        self.report_listbox = tk.Listbox(sidebar, bg=PANEL_BG, fg=TEXT_COLOR, selectbackground=ACCENT_COLOR, selectforeground=DARK_BG, relief="flat", highlightthickness=0)
        self.report_listbox.grid(row=2, column=0, sticky="nsew", padx=18, pady=18)
        self.report_listbox.bind("<<ListboxSelect>>", self._on_report_selected)
        for report in self.reports:
            self.report_listbox.insert(tk.END, f"{report['label']}  {report['summary']}")

        main = tk.Frame(self, bg=DARK_BG)
        main.grid(row=0, column=1, sticky="nsew", padx=18, pady=18)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        self.summary_frame = tk.Frame(main, bg=DARK_BG)
        self.summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        content = tk.Frame(main, bg=DARK_BG)
        content.grid(row=2, column=0, sticky="nsew")
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        left = tk.Frame(content, bg=DARK_BG, width=400)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_propagate(False)

        self.analysis_card = self._make_card(left, "AI 報告")
        self.analysis_card.pack(fill="x", pady=(0, 12))
        self.analysis_content = tk.Frame(self.analysis_card, bg=PANEL_BG)
        self.analysis_content.pack(fill="both", expand=True)

        review_card = self._make_card(left, "報告回報")
        review_card.pack(fill="x", pady=(0, 12))
        tk.Label(review_card, text="回報狀態", bg=PANEL_BG, fg=MUTED_COLOR).pack(anchor="w")
        self.review_status = ttk.Combobox(review_card, textvariable=self.review_status_var, state="readonly", values=["", "整體正常", "有異常需追蹤", "AI 判讀需調整"])
        self.review_status.pack(fill="x", pady=(6, 10))
        self.review_status.bind("<<ComboboxSelected>>", lambda _e: self._save_review_state())
        tk.Label(review_card, text="備註", bg=PANEL_BG, fg=MUTED_COLOR).pack(anchor="w")
        self.review_note = tk.Text(review_card, height=6, bg="#0d1525", fg=TEXT_COLOR, insertbackground=TEXT_COLOR, relief="flat")
        self.review_note.pack(fill="x", pady=(6, 0))
        self.review_note.bind("<KeyRelease>", lambda _e: self._save_review_state())

        detail_card = self._make_card(left, "列明細")
        detail_card.pack(fill="both", expand=True)
        self.detail_text = tk.Text(detail_card, bg="#0d1525", fg=TEXT_COLOR, wrap="word", relief="flat")
        self.detail_text.pack(fill="both", expand=True)
        self.detail_text.configure(state="disabled")

        right = tk.Frame(content, bg=DARK_BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        toolbar_card = self._make_card(right, "CSV 完整檢視")
        toolbar_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        toolbar = tk.Frame(toolbar_card, bg=PANEL_BG)
        toolbar.pack(fill="x")
        toolbar.grid_columnconfigure(0, weight=2)
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.grid_columnconfigure(2, weight=1)
        tk.Label(toolbar, text="搜尋 CSV", bg=PANEL_BG, fg=MUTED_COLOR).grid(row=0, column=0, sticky="w")
        tk.Label(toolbar, text="來源 IP", bg=PANEL_BG, fg=MUTED_COLOR).grid(row=0, column=1, sticky="w", padx=(12, 0))
        tk.Label(toolbar, text="應用程式", bg=PANEL_BG, fg=MUTED_COLOR).grid(row=0, column=2, sticky="w", padx=(12, 0))
        search_entry = tk.Entry(toolbar, textvariable=self.search_var, bg="#0d1525", fg=TEXT_COLOR, insertbackground=TEXT_COLOR, relief="flat")
        search_entry.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        search_entry.bind("<KeyRelease>", lambda _e: self._apply_filters())
        self.source_combo = ttk.Combobox(toolbar, textvariable=self.source_var, state="readonly")
        self.source_combo.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(6, 0))
        self.source_combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_filters())
        self.app_combo = ttk.Combobox(toolbar, textvariable=self.app_var, state="readonly")
        self.app_combo.grid(row=1, column=2, sticky="ew", padx=(12, 0), pady=(6, 0))
        self.app_combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_filters())

        table_card = self._make_card(right, "")
        table_card.grid(row=1, column=0, sticky="nsew")
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(table_card, show="headings", style="Dark.Treeview")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_row_selected)
        yscroll = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(table_card, orient="horizontal", command=self.tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

    def _make_card(self, parent: tk.Widget, title: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=PANEL_BG, highlightbackground="#29405f", highlightthickness=1, padx=14, pady=14)
        if title:
            tk.Label(frame, text=title, bg=PANEL_BG, fg=TEXT_COLOR, font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 10))
        return frame

    def _load_initial_report(self) -> None:
        if not self.reports:
            self._set_text(self.detail_text, "目前找不到任何每日報告。")
            return
        self.report_listbox.selection_set(0)
        self._load_report(self.reports[0]["date"])

    def _review_file(self, date_key: str) -> Path:
        review_dir = self.data_dir / ".reviews"
        review_dir.mkdir(parents=True, exist_ok=True)
        return review_dir / f"{date_key}.json"

    def _load_review_state(self) -> None:
        self.review_status_var.set("")
        self.review_note.delete("1.0", tk.END)
        if not self.current_report:
            return
        review_file = self._review_file(self.current_report["date"])
        if not review_file.exists():
            return
        try:
            payload = json.loads(review_file.read_text(encoding="utf-8"))
        except Exception:
            return
        self.review_status_var.set(payload.get("status", ""))
        self.review_note.insert("1.0", payload.get("note", ""))

    def _save_review_state(self) -> None:
        if not self.current_report:
            return
        payload = {
            "status": self.review_status_var.get(),
            "note": self.review_note.get("1.0", tk.END).strip(),
        }
        self._review_file(self.current_report["date"]).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_report(self, date_key: str) -> None:
        self.current_report = load_report_bundle(self.data_dir, date_key)
        self._render_summary()
        self._render_analysis()
        self._populate_filters()
        self._build_table()
        self._load_review_state()
        self._set_text(self.detail_text, "尚未選取資料列。")

    def _render_summary(self) -> None:
        for child in self.summary_frame.winfo_children():
            child.destroy()
        if not self.current_report:
            return
        summary = self.current_report["summary"]
        cards = [
            ("報告日期", self.current_report["label"], self.current_report["date"]),
            ("總資料筆數", str(summary["total_rows"]), ""),
            ("來源 IP 數", str(summary["unique_sources"]), ""),
            ("目的地數", str(summary["unique_destinations"]), ""),
            ("最大傳輸量", summary["max_bytes_human"], summary["max_bytes_raw"]),
            ("總傳輸量", summary["total_bytes_human"], summary["total_bytes_raw"]),
        ]
        for index, (label, value, secondary) in enumerate(cards):
            card = tk.Frame(self.summary_frame, bg=PANEL_BG_2, highlightbackground="#29405f", highlightthickness=1, padx=14, pady=12)
            card.grid(row=0, column=index, padx=(0, 10), sticky="nsew")
            tk.Label(card, text=label, bg=PANEL_BG_2, fg=MUTED_COLOR).pack(anchor="w")
            tk.Label(card, text=value, bg=PANEL_BG_2, fg=TEXT_COLOR, font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(6, 0))
            if secondary:
                tk.Label(card, text=secondary, bg=PANEL_BG_2, fg=MUTED_COLOR).pack(anchor="w", pady=(4, 0))
            self.summary_frame.grid_columnconfigure(index, weight=1)

    def _render_analysis(self) -> None:
        for child in self.analysis_content.winfo_children():
            child.destroy()
        if not self.current_report:
            return
        sections = self.current_report["analysis_sections"]
        rows = [
            ("異常狀態", sections.get("status") or "資料不足，需人工確認", ""),
            ("摘要", sections.get("summary") or self.current_report["analysis_text"] or "資料不足，需人工確認", ""),
            ("來源", sections.get("source", ""), ""),
            ("目的地", sections.get("destination", ""), ""),
            ("應用程式", sections.get("application", ""), ""),
            ("傳輸量", sections.get("bytes_human") or sections.get("bytes", ""), sections.get("bytes_raw", "")),
            ("原因", sections.get("reason", ""), ""),
        ]
        for label, value, secondary in rows:
            block = tk.Frame(self.analysis_content, bg=PANEL_BG)
            block.pack(fill="x", pady=(0, 10), anchor="w")
            tk.Label(block, text=label, bg=PANEL_BG, fg=MUTED_COLOR).pack(anchor="w")
            tk.Label(block, text=value or "—", bg=PANEL_BG, fg=TEXT_COLOR, justify="left", wraplength=340).pack(anchor="w", pady=(3, 0))
            if secondary:
                tk.Label(block, text=secondary, bg=PANEL_BG, fg=MUTED_COLOR).pack(anchor="w")

    def _populate_filters(self) -> None:
        if not self.current_report:
            return
        rows = self.current_report["rows"]
        source_values = sorted({row.get("來源位址", "").strip() for row in rows if row.get("來源位址", "").strip()})
        app_values = sorted({row.get("應用程式", "").strip() for row in rows if row.get("應用程式", "").strip()})
        self.source_combo["values"] = [""] + source_values
        self.app_combo["values"] = [""] + app_values
        self.source_var.set("")
        self.app_var.set("")
        self.search_var.set("")
        self._apply_filters()

    def _build_table(self) -> None:
        if not self.current_report:
            return
        headers = self.current_report["headers"]
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = headers
        for header in headers:
            self.tree.heading(header, text=header)
            self.tree.column(header, width=150, anchor="w")
        self._apply_filters()

    def _apply_filters(self) -> None:
        if not self.current_report:
            return
        search = self.search_var.get().strip().lower()
        source = self.source_var.get().strip()
        app = self.app_var.get().strip()
        rows = []
        for row in self.current_report["rows"]:
            blob = " ".join(row.get(header, "") for header in self.current_report["headers"]).lower()
            if search and search not in blob:
                continue
            if source and row.get("來源位址", "") != source:
                continue
            if app and row.get("應用程式", "") != app:
                continue
            rows.append(row)
        self.filtered_rows = rows
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(rows):
            values = [row.get(header, "") for header in self.current_report["headers"]]
            self.tree.insert("", tk.END, iid=str(index), values=values)

    def _on_report_selected(self, _event: Any) -> None:
        selection = self.report_listbox.curselection()
        if not selection:
            return
        self._load_report(self.reports[selection[0]]["date"])

    def _on_row_selected(self, _event: Any) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        row = self.filtered_rows[int(selection[0])]
        text = "\n\n".join(f"{header}\n{row.get(header, '—')}" for header in self.current_report["headers"])
        self._set_text(self.detail_text, text)

    @staticmethod
    def _set_text(widget: tk.Text, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.configure(state="disabled")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the PA450 desktop review UI")
    parser.add_argument("--data-dir", default=Path("output"), type=Path, help="Folder containing daily CSV/JSON results")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    app = DesktopReportApp(args.data_dir)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
