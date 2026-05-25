from __future__ import annotations

import json
from pathlib import Path

from ui_app.assets import load_asset_text, render_index_html
from ui_app.data import load_report_range_bundle, parse_analysis_sections


def write_daily_bundle(base: Path, date_key: str, source: str, bytes_value: int, analysis: str) -> None:
    (base / f"{date_key}_report.csv").write_text(
        "來源位址,目的地位址,應用程式,位元組\n"
        f"{source},8.8.8.8,dns,{bytes_value}\n",
        encoding="utf-8",
    )
    (base / f"{date_key}.json").write_text(
        json.dumps({"analysis": analysis}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_parse_analysis_sections_accepts_single_line_item_with_destination_country() -> None:
    parsed = parse_analysis_sections(
        "第1筆的來源：192.168.3.159 目的地：199.232.114.172 目的地國家：SG 應用程式：web-browsing 位元組：1,238,420,545 bytes"
    )

    assert parsed["items"] == [
        {
            "item_number": "1",
            "source": "192.168.3.159",
            "destination": "199.232.114.172",
            "application": "web-browsing",
            "bytes": "1,238,420,545 bytes",
        }
    ]


def test_parse_analysis_sections_accepts_split_item_blocks_with_destination_country() -> None:
    analysis = "\n".join([
        "異常狀態：有異常",
        "摘要：來源 192.168.3.48 的累積傳輸量高達 1,567,432,442 位元組。",
        "第1筆",
        "來源：192.168.3.159 目的地：199.232.114.172 目的地國家：SG 應用程式：web-browsing 位元組：1.2 GB",
        "1,238,420,545 bytes",
        "第2筆",
        "來源：192.168.3.48 目的地：154.94.110.20 目的地國家：SC 應用程式：ssl 位元組：525.7 MB",
        "551,198,906 bytes",
        "原因：row-level IQR 候選異常。",
    ])

    parsed = parse_analysis_sections(analysis)

    assert parsed["status"] == "有異常"
    assert parsed["items"] == [
        {
            "item_number": "1",
            "source": "192.168.3.159",
            "destination": "199.232.114.172",
            "application": "web-browsing",
            "bytes": "1,238,420,545 bytes",
        },
        {
            "item_number": "2",
            "source": "192.168.3.48",
            "destination": "154.94.110.20",
            "application": "ssl",
            "bytes": "551,198,906 bytes",
        },
    ]


def test_load_report_range_bundle_returns_daily_ai_summaries_and_rows(tmp_path: Path) -> None:
    write_daily_bundle(tmp_path, "20260520", "10.0.0.1", 1000, "異常狀態：無明顯異常\n摘要：第一天")
    write_daily_bundle(tmp_path, "20260521", "10.0.0.2", 2048, "異常狀態：有異常需追蹤\n摘要：第二天")
    write_daily_bundle(tmp_path, "20260522", "10.0.0.3", 4096, "異常狀態：無明顯異常\n摘要：第三天")

    payload = load_report_range_bundle(tmp_path, tmp_path, tmp_path, "20260520", "20260521")

    assert payload["mode"] == "range"
    assert payload["date"] == "20260520-20260521"
    assert payload["label"] == "2026-05-20 ～ 2026-05-21"
    assert [item["date"] for item in payload["daily_analyses"]] == ["20260521", "20260520"]
    assert [item["analysis_sections"]["summary"] for item in payload["daily_analyses"]] == ["第二天", "第一天"]
    assert payload["headers"][0] == "報告日期"
    assert [row["報告日期"] for row in payload["rows"]] == ["2026-05-21", "2026-05-20"]
    assert payload["summary"]["covered_days"] == 2
    assert payload["summary"]["total_rows"] == 2
    assert payload["summary"]["unique_sources"] == 2
    assert payload["summary"]["total_bytes_raw"] == "3,048 bytes"


def rendered_index_html() -> str:
    return render_index_html(
        title="PA450",
        csv_dir_json='"output"',
        analysis_dir_json='"output"',
        review_dir_json='"output"',
    )


def test_render_index_html_inlines_split_css_and_js_assets() -> None:
    html = rendered_index_html()

    assert "__STYLE_CSS__" not in html
    assert "__APP_JS__" not in html
    assert "__CSV_DIR_JSON__" not in html
    assert "__ANALYSIS_DIR_JSON__" not in html
    assert "__REVIEW_DIR_JSON__" not in html
    assert load_asset_text("styles.css").strip() in html
    assert "const DEFAULT_PAGE_SIZE = 50" in load_asset_text("app.js")
    assert "<style>" in html
    assert "<script>" in html


def test_index_html_has_csv_pagination_controls_and_logic() -> None:
    html = rendered_index_html()

    assert 'id="pageSizeSelect"' in html
    assert 'id="pagePrevButton"' in html
    assert 'id="pageNextButton"' in html
    assert 'id="pageStatus"' in html
    assert 'class="pagination-control"' in html
    assert "const DEFAULT_PAGE_SIZE = 50" in html
    assert "function filteredRowsWithIndexes()" in html
    assert "function renderPaginationControls" in html
    assert "pageSizeSelect.addEventListener('change'" in html


def test_index_html_has_compact_summary_and_collapsible_right_rail() -> None:
    html = rendered_index_html()

    assert "summary-item" in html
    assert "summary-value" in html
    assert 'id="contentGrid"' in html
    assert 'id="rightRailToggleButton"' in html
    assert "function setRightRailOpen(open)" in html
    assert "right-rail-collapsed" in html
    assert "setRightRailOpen(true);" in html


def test_index_html_matches_range_rows_against_same_day_ai_analysis() -> None:
    html = rendered_index_html()

    assert "function dailyAnalysisForRow(row)" in html
    assert "analysis.date === rowDate" in html
    assert "dailyAnalysisForRow(row)" in html
    assert "完整命中 AI 報告異常項目：日期 + 來源 IP + 目的地 IP + 應用程式" in html
