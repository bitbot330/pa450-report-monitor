from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from report import parse_int

DASHBOARD_TITLE = "PA450 CSV / AI Review Dashboard"


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
        raise ValueError("CSV file has no headers")
    return headers, rows


def load_analysis_payload(analysis_json_path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(analysis_json_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Analysis JSON must be an object")
    return payload


def summarize_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    source_counter = Counter(row.get("來源位址", "").strip() for row in rows if row.get("來源位址", "").strip())
    destination_counter = Counter(row.get("目的地位址", "").strip() for row in rows if row.get("目的地位址", "").strip())
    user_counter = Counter(row.get("來源使用者", "").strip() for row in rows if row.get("來源使用者", "").strip())
    app_counter = Counter(row.get("應用程式", "").strip() for row in rows if row.get("應用程式", "").strip())

    byte_values = [parse_int(row.get("位元組")) for row in rows]
    valid_bytes = [value for value in byte_values if value is not None]
    max_bytes = max(valid_bytes, default=0)
    total_bytes = sum(valid_bytes)

    top_source_value, top_source_count = source_counter.most_common(1)[0] if source_counter else ("-", 0)
    top_app_value, top_app_count = app_counter.most_common(1)[0] if app_counter else ("-", 0)
    top_user_value, top_user_count = user_counter.most_common(1)[0] if user_counter else ("-", 0)

    return {
        "total_rows": len(rows),
        "unique_sources": len(source_counter),
        "unique_destinations": len(destination_counter),
        "unique_users": len(user_counter),
        "max_bytes": max_bytes,
        "total_bytes": total_bytes,
        "top_source": {"value": top_source_value, "row_count": top_source_count},
        "top_application": {"value": top_app_value, "row_count": top_app_count},
        "top_user": {"value": top_user_value, "row_count": top_user_count},
    }


def enrich_rows_for_display(headers: list[str], rows: list[dict[str, str]]) -> tuple[list[str], list[dict[str, str]]]:
    display_headers = ["傳輸量" if header == "位元組" else header for header in headers]
    display_rows: list[dict[str, str]] = []
    for row in rows:
        display_row = dict(row)
        if "位元組" in row:
            byte_value = parse_int(row.get("位元組"))
            if byte_value is None:
                display_row["傳輸量"] = row.get("位元組", "")
            else:
                display_row["傳輸量"] = f"{format_bytes_human(byte_value)} ({byte_value:,} bytes)"
            display_row.pop("位元組", None)
        display_rows.append(display_row)
    return display_headers, display_rows


def build_dashboard_context(csv_path: str | Path, analysis_json_path: str | Path) -> dict[str, Any]:
    headers, rows = load_csv_rows(csv_path)
    analysis_payload = load_analysis_payload(analysis_json_path)
    analysis_text = str(analysis_payload.get("analysis") or "")
    display_headers, display_rows = enrich_rows_for_display(headers, rows)
    analysis_sections = parse_analysis_sections(analysis_text)
    analysis_bytes_value = parse_int(analysis_sections.get("bytes"))
    analysis_sections["bytes_human"] = format_bytes_human(analysis_bytes_value) if analysis_bytes_value is not None else ""
    analysis_sections["bytes_raw"] = f"{analysis_bytes_value:,} bytes" if analysis_bytes_value is not None else analysis_sections.get("bytes", "")

    return {
        "title": DASHBOARD_TITLE,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "csv_path": str(csv_path),
        "analysis_json_path": str(analysis_json_path),
        "display_headers": display_headers,
        "display_rows": display_rows,
        "summary": summarize_rows(rows),
        "analysis_text": analysis_text,
        "analysis_sections": analysis_sections,
    }


def _json_for_script(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def build_dashboard_html(context: dict[str, Any]) -> str:
    summary = context["summary"]
    analysis_sections = context["analysis_sections"]
    status_text = escape(analysis_sections.get("status") or "資料不足，需人工確認")
    summary_text = escape(analysis_sections.get("summary") or context["analysis_text"] or "資料不足，需人工確認")
    source_text = escape(analysis_sections.get("source") or "—")
    destination_text = escape(analysis_sections.get("destination") or "—")
    application_text = escape(analysis_sections.get("application") or "—")
    bytes_human_text = escape(analysis_sections.get("bytes_human") or analysis_sections.get("bytes") or "—")
    bytes_raw_text = escape(analysis_sections.get("bytes_raw") or "")
    reason_text = escape(analysis_sections.get("reason") or "—")
    dashboard_data = _json_for_script(
        {
            "headers": context["display_headers"],
            "rows": context["display_rows"],
            "summary": context["summary"],
            "analysisText": context["analysis_text"],
            "csvPath": context["csv_path"],
            "analysisJsonPath": context["analysis_json_path"],
            "generatedAt": context["generated_at"],
        }
    )

    return f'''<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(context['title'])}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #0b1220;
      --panel: #111b2e;
      --panel-2: #16223a;
      --line: #29405f;
      --text: #e8eefc;
      --muted: #9eb2d0;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, "Noto Sans TC", sans-serif; background: var(--bg); color: var(--text); }}
    .page {{ max-width: 1600px; margin: 0 auto; padding: 24px; }}
    h1, h2 {{ margin: 0; }}
    .subtle {{ color: var(--muted); font-size: 14px; }}
    .hero {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 20px; }}
    .grid {{ display: grid; gap: 16px; }}
    .summary-grid {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-bottom: 20px; }}
    .card {{ background: linear-gradient(180deg, var(--panel), var(--panel-2)); border: 1px solid var(--line); border-radius: 16px; padding: 16px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18); }}
    .metric {{ font-size: 30px; font-weight: 700; margin-top: 10px; }}
    .layout {{ display: grid; grid-template-columns: minmax(320px, 420px) minmax(0, 1fr); gap: 16px; align-items: start; }}
    .stack {{ display: grid; gap: 16px; }}
    .label {{ color: var(--muted); font-size: 13px; margin-bottom: 6px; }}
    .panel-title {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
    .report-text {{ white-space: pre-wrap; line-height: 1.7; font-size: 14px; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }}
    input, select, textarea {{ width: 100%; background: #0d1525; color: var(--text); border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; font: inherit; }}
    textarea {{ min-height: 120px; resize: vertical; }}
    .toolbar .control {{ min-width: 180px; flex: 1; }}
    .table-wrap {{ overflow: auto; border: 1px solid var(--line); border-radius: 14px; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 900px; }}
    thead th {{ position: sticky; top: 0; background: #13213a; z-index: 1; text-align: left; }}
    th, td {{ padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.08); font-size: 14px; vertical-align: top; }}
    tbody tr {{ cursor: pointer; }}
    tbody tr:hover {{ background: rgba(101, 183, 255, 0.08); }}
    tbody tr.is-selected {{ background: rgba(101, 183, 255, 0.18); }}
    .detail-list {{ display: grid; gap: 10px; }}
    .detail-row {{ border-bottom: 1px dashed rgba(255,255,255,0.12); padding-bottom: 10px; }}
    .detail-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .detail-key {{ color: var(--muted); font-size: 12px; margin-bottom: 4px; }}
    .pill {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 10px; font-size: 12px; border: 1px solid var(--line); color: var(--muted); }}
    .footer-note {{ margin-top: 12px; color: var(--muted); font-size: 12px; }}
    @media (max-width: 1080px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .hero {{ flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div>
        <h1>{escape(context['title'])}</h1>
        <div class="subtle">CSV：{escape(context['csv_path'])}</div>
        <div class="subtle">AI JSON：{escape(context['analysis_json_path'])}</div>
      </div>
      <div class="pill">產生時間 {escape(context['generated_at'])}</div>
    </section>

    <section class="grid summary-grid">
      <div class="card"><div class="label">總資料筆數</div><div class="metric">{summary['total_rows']}</div></div>
      <div class="card"><div class="label">來源 IP 數</div><div class="metric">{summary['unique_sources']}</div></div>
      <div class="card"><div class="label">目的地數</div><div class="metric">{summary['unique_destinations']}</div></div>
      <div class="card"><div class="label">最大傳輸量</div><div class="metric">{format_bytes_human(summary['max_bytes'])}</div><div class="subtle">{summary['max_bytes']:,} bytes</div></div>
      <div class="card"><div class="label">總傳輸量</div><div class="metric">{format_bytes_human(summary['total_bytes'])}</div><div class="subtle">{summary['total_bytes']:,} bytes</div></div>
      <div class="card"><div class="label">最多列的來源</div><div class="metric">{escape(summary['top_source']['value'])}</div><div class="subtle">{summary['top_source']['row_count']} 列</div></div>
    </section>

    <section class="layout">
      <div class="stack">
        <article class="card">
          <div class="panel-title"><h2>AI 報告</h2><span class="pill">給人讀的摘要</span></div>
          <div class="detail-list">
            <div class="detail-row"><div class="detail-key">異常狀態</div><div>{status_text}</div></div>
            <div class="detail-row"><div class="detail-key">摘要</div><div class="report-text">{summary_text}</div></div>
            <div class="detail-row"><div class="detail-key">來源</div><div>{source_text}</div></div>
            <div class="detail-row"><div class="detail-key">目的地</div><div>{destination_text}</div></div>
            <div class="detail-row"><div class="detail-key">應用程式</div><div>{application_text}</div></div>
            <div class="detail-row"><div class="detail-key">傳輸量</div><div>{bytes_human_text}</div><div class="subtle">{bytes_raw_text}</div></div>
            <div class="detail-row"><div class="detail-key">原因</div><div class="report-text">{reason_text}</div></div>
          </div>
        </article>

        <article class="card">
          <div class="panel-title"><h2>報告回報</h2><span class="pill">localStorage</span></div>
          <div class="label">回報狀態</div>
          <select id="reviewStatus">
            <option value="">未設定</option>
            <option value="normal">整體正常</option>
            <option value="follow-up">有異常需追蹤</option>
            <option value="ai-adjustment">AI 判讀需調整</option>
          </select>
          <div class="label" style="margin-top: 12px;">備註</div>
          <textarea id="reviewNote" placeholder="例如：這次高流量其實是備份流量，AI 需要學會辨識。"></textarea>
          <div class="footer-note">這版先把回報存在瀏覽器本機，方便你先用 UI 審閱流程。</div>
        </article>

        <article class="card">
          <div class="panel-title"><h2>列明細</h2><span class="pill">點右側表格列查看</span></div>
          <div id="rowDetail" class="subtle">尚未選取資料列。</div>
        </article>
      </div>

      <article class="card">
        <div class="panel-title"><h2>CSV 完整檢視</h2><span class="pill">Evidence</span></div>
        <div class="toolbar">
          <div class="control">
            <div class="label">搜尋 CSV</div>
            <input id="searchInput" type="search" placeholder="輸入 IP、使用者、應用程式、主機名稱...">
          </div>
          <div class="control">
            <div class="label">來源 IP</div>
            <select id="sourceFilter"></select>
          </div>
          <div class="control">
            <div class="label">應用程式</div>
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

  <script>
    const dashboardData = {dashboard_data};
    const tableHead = document.getElementById('tableHead');
    const tableBody = document.getElementById('tableBody');
    const searchInput = document.getElementById('searchInput');
    const sourceFilter = document.getElementById('sourceFilter');
    const appFilter = document.getElementById('appFilter');
    const rowDetail = document.getElementById('rowDetail');
    const reviewStatus = document.getElementById('reviewStatus');
    const reviewNote = document.getElementById('reviewNote');
    const storageKey = `pa450-review::${{dashboardData.csvPath}}::${{dashboardData.analysisJsonPath}}`;
    let selectedRowIndex = null;

    function uniqueValues(field) {{
      return [...new Set(dashboardData.rows.map((row) => (row[field] || '').trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-Hant'));
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

    function renderHead() {{
      tableHead.innerHTML = '';
      dashboardData.headers.forEach((header) => {{
        const th = document.createElement('th');
        th.textContent = header;
        tableHead.appendChild(th);
      }});
    }}

    function matchesFilters(row) {{
      const search = searchInput.value.trim().toLowerCase();
      const source = sourceFilter.value;
      const app = appFilter.value;
      const textBlob = dashboardData.headers.map((header) => row[header] || '').join(' ').toLowerCase();
      if (search && !textBlob.includes(search)) return false;
      if (source && (row['來源位址'] || '') !== source) return false;
      if (app && (row['應用程式'] || '') !== app) return false;
      return true;
    }}

    function renderDetails(row) {{
      rowDetail.innerHTML = '';
      const wrapper = document.createElement('div');
      wrapper.className = 'detail-list';
      dashboardData.headers.forEach((header) => {{
        const rowWrap = document.createElement('div');
        rowWrap.className = 'detail-row';
        const key = document.createElement('div');
        key.className = 'detail-key';
        key.textContent = header;
        const value = document.createElement('div');
        value.textContent = row[header] || '—';
        rowWrap.appendChild(key);
        rowWrap.appendChild(value);
        wrapper.appendChild(rowWrap);
      }});
      rowDetail.appendChild(wrapper);
    }}

    function renderRows() {{
      tableBody.innerHTML = '';
      const filtered = dashboardData.rows.filter(matchesFilters);
      filtered.forEach((row, filteredIndex) => {{
        const tr = document.createElement('tr');
        if (selectedRowIndex === filteredIndex) {{
          tr.classList.add('is-selected');
        }}
        tr.addEventListener('click', () => {{
          selectedRowIndex = filteredIndex;
          renderRows();
          renderDetails(row);
        }});
        dashboardData.headers.forEach((header) => {{
          const td = document.createElement('td');
          td.textContent = row[header] || '';
          tr.appendChild(td);
        }});
        tableBody.appendChild(tr);
      }});
      if (!filtered.length) {{
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = dashboardData.headers.length;
        td.textContent = '沒有符合條件的 CSV 列。';
        tr.appendChild(td);
        tableBody.appendChild(tr);
      }}
    }}

    function loadReviewState() {{
      try {{
        const raw = localStorage.getItem(storageKey);
        if (!raw) return;
        const saved = JSON.parse(raw);
        reviewStatus.value = saved.reviewStatus || '';
        reviewNote.value = saved.reviewNote || '';
      }} catch (_error) {{}}
    }}

    function saveReviewState() {{
      localStorage.setItem(storageKey, JSON.stringify({{
        reviewStatus: reviewStatus.value,
        reviewNote: reviewNote.value,
      }}));
    }}

    searchInput.addEventListener('input', renderRows);
    sourceFilter.addEventListener('change', renderRows);
    appFilter.addEventListener('change', renderRows);
    reviewStatus.addEventListener('change', saveReviewState);
    reviewNote.addEventListener('input', saveReviewState);

    renderHead();
    fillSelect(sourceFilter, '來源位址', '來源 IP');
    fillSelect(appFilter, '應用程式', '應用程式');
    loadReviewState();
    renderRows();
  </script>
</body>
</html>'''


def write_dashboard(output_path: str | Path, html: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a reviewable PA450 CSV/AI dashboard")
    parser.add_argument("--csv", required=True, type=Path, help="Path to PA450 report CSV")
    parser.add_argument("--analysis-json", required=True, type=Path, help="Path to AI analysis JSON")
    parser.add_argument("--output", required=True, type=Path, help="Where to write the dashboard HTML")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    context = build_dashboard_context(args.csv, args.analysis_json)
    html = build_dashboard_html(context)
    write_dashboard(args.output, html)
    print(f"Dashboard written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
