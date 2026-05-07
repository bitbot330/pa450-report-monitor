from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from functools import partial
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from report import parse_int

DASHBOARD_TITLE = "PA450 Daily Review UI"


INDEX_HTML_TEMPLATE = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0b1220;
      --panel: #111b2e;
      --panel-2: #16223a;
      --line: #29405f;
      --text: #e8eefc;
      --muted: #9eb2d0;
      --accent: #65b7ff;
      --accent-bg: rgba(101, 183, 255, 0.18);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, "Noto Sans TC", sans-serif; background: var(--bg); color: var(--text); }}
    h1, h2, h3, p {{ margin: 0; }}
    button, input, select, textarea {{ font: inherit; }}
    .app {{ display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }}
    .sidebar {{ border-right: 1px solid var(--line); background: #0f1728; padding: 20px; }}
    .main {{ padding: 24px; }}
    .brand {{ margin-bottom: 18px; }}
    .brand h1 {{ font-size: 22px; margin-bottom: 8px; }}
    .subtle {{ color: var(--muted); font-size: 13px; }}
    .report-list {{ display: grid; gap: 10px; margin-top: 18px; }}
    .report-item {{ width: 100%; text-align: left; padding: 14px; border-radius: 12px; border: 1px solid var(--line); background: var(--panel); color: var(--text); cursor: pointer; }}
    .report-item:hover, .report-item.active {{ border-color: var(--accent); background: var(--accent-bg); }}
    .layout {{ display: grid; gap: 16px; }}
    .summary-grid {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
    .content-grid {{ display: grid; grid-template-columns: minmax(320px, 420px) minmax(0, 1fr); gap: 16px; align-items: start; }}
    .stack {{ display: grid; gap: 16px; }}
    .card {{ background: linear-gradient(180deg, var(--panel), var(--panel-2)); border: 1px solid var(--line); border-radius: 16px; padding: 16px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18); }}
    .metric {{ font-size: 30px; font-weight: 700; margin-top: 10px; }}
    .pill {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 10px; font-size: 12px; border: 1px solid var(--line); color: var(--muted); }}
    .panel-title {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 8px; }}
    .detail-list {{ display: grid; gap: 10px; }}
    .detail-row {{ border-bottom: 1px dashed rgba(255,255,255,0.12); padding-bottom: 10px; }}
    .detail-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .detail-key {{ color: var(--muted); font-size: 12px; margin-bottom: 4px; }}
    .report-text {{ white-space: pre-wrap; line-height: 1.7; font-size: 14px; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }}
    input, select, textarea {{ width: 100%; background: #0d1525; color: var(--text); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; }}
    textarea {{ min-height: 120px; resize: vertical; }}
    .toolbar .control {{ min-width: 180px; flex: 1; }}
    .table-wrap {{ overflow: auto; border: 1px solid var(--line); border-radius: 14px; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 900px; }}
    thead th {{ position: sticky; top: 0; background: #13213a; z-index: 1; text-align: left; }}
    th, td {{ padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.08); font-size: 14px; vertical-align: top; }}
    tbody tr {{ cursor: pointer; }}
    tbody tr:hover {{ background: rgba(101, 183, 255, 0.08); }}
    tbody tr.is-selected {{ background: rgba(101, 183, 255, 0.18); }}
    .empty {{ padding: 18px; border: 1px dashed var(--line); border-radius: 12px; color: var(--muted); }}
    .error {{ color: #ff9a9a; }}
    @media (max-width: 1080px) {{
      .app {{ grid-template-columns: 1fr; }}
      .sidebar {{ border-right: none; border-bottom: 1px solid var(--line); }}
      .content-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <h1>{title}</h1>
        <p class="subtle">同一個 UI 直接切換每日報告，不用每次重生 dashboard。</p>
      </div>
      <div class="subtle">資料來源資料夾：<span id="dataDirLabel"></span></div>
      <div class="report-list" id="reportList"></div>
    </aside>
    <main class="main">
      <div id="loading" class="empty">載入中...</div>
      <div id="errorBox" class="empty error" hidden></div>
      <div id="reportApp" class="layout" hidden>
        <section class="summary-grid" id="summaryGrid"></section>
        <section class="content-grid">
          <div class="stack">
            <article class="card">
              <div class="panel-title"><h2>AI 報告</h2><span class="pill">給人讀的摘要</span></div>
              <div class="detail-list" id="analysisCard"></div>
            </article>
            <article class="card">
              <div class="panel-title"><h2>報告回報</h2><span class="pill">localStorage</span></div>
              <div class="detail-key">回報狀態</div>
              <select id="reviewStatus">
                <option value="">未設定</option>
                <option value="normal">整體正常</option>
                <option value="follow-up">有異常需追蹤</option>
                <option value="ai-adjustment">AI 判讀需調整</option>
              </select>
              <div class="detail-key" style="margin-top:12px;">備註</div>
              <textarea id="reviewNote" placeholder="例如：這次高流量其實是備份流量，AI 需要學會辨識。"></textarea>
            </article>
            <article class="card">
              <div class="panel-title"><h2>列明細</h2><span class="pill">點右側表格列查看</span></div>
              <div id="rowDetail" class="empty">尚未選取資料列。</div>
            </article>
          </div>
          <article class="card">
            <div class="panel-title"><h2>CSV 完整檢視</h2><span class="pill">Evidence</span></div>
            <div class="toolbar">
              <div class="control">
                <div class="detail-key">搜尋 CSV</div>
                <input id="searchInput" type="search" placeholder="輸入 IP、使用者、應用程式、主機名稱...">
              </div>
              <div class="control">
                <div class="detail-key">來源 IP</div>
                <select id="sourceFilter"></select>
              </div>
              <div class="control">
                <div class="detail-key">應用程式</div>
                <select id="appFilter"></select>
              </div>
            </div>
            <div class="table-wrap">
              <table>
                <thead><tr id="tableHead"></tr></thead>
                <tbody id="tableBody"></tbody>
              </table>
            </div>
          </article>
        </section>
      </div>
    </main>
  </div>

  <script>
    const appState = {{ reports: [], current: null, selectedRowIndex: null }};
    const dataDirLabel = document.getElementById('dataDirLabel');
    const reportList = document.getElementById('reportList');
    const loading = document.getElementById('loading');
    const errorBox = document.getElementById('errorBox');
    const reportApp = document.getElementById('reportApp');
    const summaryGrid = document.getElementById('summaryGrid');
    const analysisCard = document.getElementById('analysisCard');
    const searchInput = document.getElementById('searchInput');
    const sourceFilter = document.getElementById('sourceFilter');
    const appFilter = document.getElementById('appFilter');
    const tableHead = document.getElementById('tableHead');
    const tableBody = document.getElementById('tableBody');
    const rowDetail = document.getElementById('rowDetail');
    const reviewStatus = document.getElementById('reviewStatus');
    const reviewNote = document.getElementById('reviewNote');

    function showError(message) {{
      errorBox.hidden = false;
      errorBox.textContent = message;
      loading.hidden = true;
      reportApp.hidden = true;
    }}

    function clearError() {{
      errorBox.hidden = true;
      errorBox.textContent = '';
    }}

    function formatDetailRow(key, value, secondary = '') {{
      return `<div class="detail-row"><div class="detail-key">${{key}}</div><div>${{value || '—'}}</div>${{secondary ? `<div class="subtle">${{secondary}}</div>` : ''}}</div>`;
    }}

    function reviewStorageKey() {{
      return appState.current ? `pa450-review::${{appState.current.date}}` : 'pa450-review';
    }}

    function saveReviewState() {{
      if (!appState.current) return;
      localStorage.setItem(reviewStorageKey(), JSON.stringify({{
        reviewStatus: reviewStatus.value,
        reviewNote: reviewNote.value,
      }}));
    }}

    function loadReviewState() {{
      reviewStatus.value = '';
      reviewNote.value = '';
      if (!appState.current) return;
      try {{
        const raw = localStorage.getItem(reviewStorageKey());
        if (!raw) return;
        const saved = JSON.parse(raw);
        reviewStatus.value = saved.reviewStatus || '';
        reviewNote.value = saved.reviewNote || '';
      }} catch (_error) {{}}
    }}

    function uniqueValues(field) {{
      if (!appState.current) return [];
      return [...new Set(appState.current.rows.map((row) => (row[field] || '').trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-Hant'));
    }}

    function fillSelect(selectEl, field, label) {{
      selectEl.innerHTML = '';
      const defaultOption = document.createElement('option');
      defaultOption.value = '';
      defaultOption.textContent = `全部${{label}}`;
      selectEl.appendChild(defaultOption);
      uniqueValues(field).forEach((value) => {{
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        selectEl.appendChild(option);
      }});
    }}

    function renderSidebar() {{
      reportList.innerHTML = '';
      appState.reports.forEach((report) => {{
        const btn = document.createElement('button');
        btn.className = 'report-item';
        if (appState.current && report.date === appState.current.date) btn.classList.add('active');
        btn.innerHTML = `<div><strong>${{report.label}}</strong></div><div class="subtle">${{report.summary}}</div>`;
        btn.addEventListener('click', () => loadReport(report.date));
        reportList.appendChild(btn);
      }});
    }}

    function renderSummary() {{
      const summary = appState.current.summary;
      const cards = [
        ['報告日期', appState.current.label, appState.current.date],
        ['總資料筆數', summary.total_rows, ''],
        ['來源 IP 數', summary.unique_sources, ''],
        ['目的地數', summary.unique_destinations, ''],
        ['最大傳輸量', summary.max_bytes_human, summary.max_bytes_raw],
        ['總傳輸量', summary.total_bytes_human, summary.total_bytes_raw],
      ];
      summaryGrid.innerHTML = cards.map(([label, value, secondary]) => `
        <div class="card">
          <div class="detail-key">${{label}}</div>
          <div class="metric">${{value}}</div>
          ${{secondary ? `<div class="subtle">${{secondary}}</div>` : ''}}
        </div>
      `).join('');
    }}

    function renderAnalysis() {{
      const a = appState.current.analysis_sections;
      analysisCard.innerHTML = [
        formatDetailRow('異常狀態', a.status || '資料不足，需人工確認'),
        formatDetailRow('摘要', a.summary || appState.current.analysis_text || '資料不足，需人工確認'),
        formatDetailRow('來源', a.source),
        formatDetailRow('目的地', a.destination),
        formatDetailRow('應用程式', a.application),
        formatDetailRow('傳輸量', a.bytes_human || a.bytes || '—', a.bytes_raw || ''),
        formatDetailRow('原因', a.reason),
      ].join('');
    }}

    function renderHead() {{
      tableHead.innerHTML = '';
      appState.current.headers.forEach((header) => {{
        const th = document.createElement('th');
        th.textContent = header;
        tableHead.appendChild(th);
      }});
    }}

    function matchesFilters(row) {{
      const search = searchInput.value.trim().toLowerCase();
      const source = sourceFilter.value;
      const app = appFilter.value;
      const textBlob = appState.current.headers.map((header) => row[header] || '').join(' ').toLowerCase();
      if (search && !textBlob.includes(search)) return false;
      if (source && (row['來源位址'] || '') !== source) return false;
      if (app && (row['應用程式'] || '') !== app) return false;
      return true;
    }}

    function renderDetails(row) {{
      const wrapper = document.createElement('div');
      wrapper.className = 'detail-list';
      appState.current.headers.forEach((header) => {{
        const rowWrap = document.createElement('div');
        rowWrap.className = 'detail-row';
        rowWrap.innerHTML = `<div class="detail-key">${{header}}</div><div>${{row[header] || '—'}}</div>`;
        wrapper.appendChild(rowWrap);
      }});
      rowDetail.innerHTML = '';
      rowDetail.className = '';
      rowDetail.appendChild(wrapper);
    }}

    function renderRows() {{
      tableBody.innerHTML = '';
      const filtered = appState.current.rows.filter(matchesFilters);
      filtered.forEach((row, filteredIndex) => {{
        const tr = document.createElement('tr');
        if (appState.selectedRowIndex === filteredIndex) tr.classList.add('is-selected');
        tr.addEventListener('click', () => {{
          appState.selectedRowIndex = filteredIndex;
          renderRows();
          renderDetails(row);
        }});
        appState.current.headers.forEach((header) => {{
          const td = document.createElement('td');
          td.textContent = row[header] || '';
          tr.appendChild(td);
        }});
        tableBody.appendChild(tr);
      }});
      if (!filtered.length) {{
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = appState.current.headers.length;
        td.textContent = '沒有符合條件的 CSV 列。';
        tr.appendChild(td);
        tableBody.appendChild(tr);
      }}
    }}

    function renderCurrentReport() {{
      if (!appState.current) return;
      clearError();
      loading.hidden = true;
      reportApp.hidden = false;
      appState.selectedRowIndex = null;
      rowDetail.className = 'empty';
      rowDetail.textContent = '尚未選取資料列。';
      renderSidebar();
      renderSummary();
      renderAnalysis();
      renderHead();
      fillSelect(sourceFilter, '來源位址', '來源 IP');
      fillSelect(appFilter, '應用程式', '應用程式');
      loadReviewState();
      renderRows();
    }}

    async function loadReport(date) {{
      const response = await fetch(`/api/reports/${{encodeURIComponent(date)}}`);
      if (!response.ok) throw new Error(`載入報告失敗：${{response.status}}`);
      appState.current = await response.json();
      renderCurrentReport();
    }}

    async function bootstrap() {{
      try {{
        const response = await fetch('/api/reports');
        if (!response.ok) throw new Error(`載入報告列表失敗：${{response.status}}`);
        const payload = await response.json();
        dataDirLabel.textContent = payload.data_dir;
        appState.reports = payload.reports;
        if (!payload.reports.length) {{
          loading.hidden = true;
          reportList.innerHTML = '<div class="empty">目前找不到任何每日報告。</div>';
          return;
        }}
        renderSidebar();
        await loadReport(payload.reports[0].date);
      }} catch (error) {{
        showError(error.message || '載入失敗');
      }}
    }}

    searchInput.addEventListener('input', renderRows);
    sourceFilter.addEventListener('change', renderRows);
    appFilter.addEventListener('change', renderRows);
    reviewStatus.addEventListener('change', saveReviewState);
    reviewNote.addEventListener('input', saveReviewState);
    bootstrap();
  </script>
</body>
</html>
"""


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

    for csv_path in sorted(base.glob("*_report.csv")):
        date_key = csv_path.stem.removesuffix("_report")
        report_map.setdefault(date_key, {})["csv"] = csv_path
    for json_path in sorted(base.glob("*.json")):
        date_key = json_path.stem
        report_map.setdefault(date_key, {})["analysis"] = json_path

    for child in sorted(base.iterdir()) if base.exists() else []:
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
            csv_path = folder_csv
            json_path = folder_json
    if not csv_path.exists() or not json_path.exists():
        raise FileNotFoundError(f"Report bundle not found for date: {date_key}")

    headers, rows = load_csv_rows(csv_path)
    analysis_payload = load_analysis_payload(json_path)
    analysis_text = str(analysis_payload.get("analysis") or "")
    display_headers, display_rows = enrich_rows_for_display(headers, rows)
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
        "summary": summarize_rows(rows),
        "analysis_text": analysis_text,
        "analysis_sections": analysis_sections,
    }


class ReportUIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args: Any, data_dir: str, **kwargs: Any) -> None:
        self.data_dir = Path(data_dir)
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(INDEX_HTML_TEMPLATE.format(title=escape(DASHBOARD_TITLE)))
            return
        if parsed.path == "/api/reports":
            payload = {"data_dir": str(self.data_dir), "reports": discover_reports(self.data_dir)}
            self._send_json(payload)
            return
        if parsed.path.startswith("/api/reports/"):
            date_key = unquote(parsed.path.removeprefix("/api/reports/"))
            try:
                payload = load_report_bundle(self.data_dir, date_key)
            except FileNotFoundError:
                self._send_json({"error": f"Report not found: {date_key}"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json(payload)
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a persistent PA450 daily review UI")
    parser.add_argument("--data-dir", default=Path("output"), type=Path, help="Folder containing daily CSV/JSON results")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the UI server")
    parser.add_argument("--port", default=8765, type=int, help="Port to bind the UI server")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    handler = partial(ReportUIHandler, data_dir=str(args.data_dir))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"PA450 Daily Review UI running at http://{args.host}:{args.port} (data dir: {args.data_dir})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
