from __future__ import annotations

import json
from pathlib import Path

from ui_app.assets import render_index_html
from ui_app.data import load_report_range_bundle


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


def test_index_html_has_csv_pagination_controls_and_logic() -> None:
    html = render_index_html(
        title="PA450",
        csv_dir_json='"output"',
        analysis_dir_json='"output"',
        review_dir_json='"output"',
    )

    assert 'id="pageSizeSelect"' in html
    assert 'id="pagePrevButton"' in html
    assert 'id="pageNextButton"' in html
    assert 'id="pageStatus"' in html
    assert "const DEFAULT_PAGE_SIZE = 50" in html
    assert "function filteredRowsWithIndexes()" in html
    assert "function renderPaginationControls" in html
    assert "pageSizeSelect.addEventListener('change'" in html
