from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analyze import ANALYSIS_USER_PROMPT_TEMPLATE, build_context, build_monitoring_guidance


def test_build_monitoring_guidance_marks_current_csv_outlier_rows_only() -> None:
    context = build_context(Path(__file__).resolve().parents[1] / "output" / "20260512_report.csv")

    guidance = build_monitoring_guidance(context)

    assert "資料列總數：50" in guidance
    assert "row-level IQR upper fence：385747459.375" in guidance
    assert "第1筆：來源 192.168.3.69 目的地 142.250.198.65 應用程式 google-base 位元組 1334722569" in guidance
    assert "第2筆：來源 192.168.2.75 目的地 65.9.180.72 應用程式 ssl 位元組 590730634" in guidance
    assert "第3筆：來源 192.168.11.169 目的地 17.253.17.207 應用程式 ssl 位元組 391167996" in guidance
    assert "第4筆：來源 192.168.11.169 目的地 17.253.17.210" not in guidance
    assert "來源 192.168.11.169 總位元組 1097637448" in guidance


def test_build_monitoring_guidance_reports_insufficient_data_when_bytes_missing() -> None:
    context = "來源位址,目的地位址,應用程式\n192.168.1.1,8.8.8.8,ssl\n"

    guidance = build_monitoring_guidance(context)

    assert "資料不足，需人工確認" in guidance
    assert "位元組" in guidance


def test_prompt_tells_llm_to_monitor_without_item_cap_or_listing_all_rows() -> None:
    assert "不要把所有 context rows 當成異常清單輸出" in ANALYSIS_USER_PROMPT_TEMPLATE
    assert "不限制異常筆數" in ANALYSIS_USER_PROMPT_TEMPLATE
    assert "沒有異常就說沒有" in ANALYSIS_USER_PROMPT_TEMPLATE
    assert "{monitoring_guidance}" in ANALYSIS_USER_PROMPT_TEMPLATE
