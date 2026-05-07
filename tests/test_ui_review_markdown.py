from pathlib import Path

from ui import load_report_bundle, load_review_markdown, save_review_markdown


def test_save_review_markdown_writes_report_md_in_date_folder(tmp_path: Path) -> None:
    report_path = save_review_markdown(tmp_path, "20260507", "follow-up", "需要追蹤備份流量")

    assert report_path == tmp_path / "20260507" / "report.md"
    assert report_path.read_text(encoding="utf-8") == (
        "# 報告回報\n\n"
        "- 報告日期：2026-05-07\n"
        "- 回報狀態：有異常需追蹤\n\n"
        "## 備註\n\n"
        "需要追蹤備份流量\n"
    )


def test_load_review_markdown_returns_empty_when_report_md_is_missing(tmp_path: Path) -> None:
    assert load_review_markdown(tmp_path, "20260507") == {"reviewStatus": "", "reviewNote": ""}


def test_load_report_bundle_includes_review_from_report_md(tmp_path: Path) -> None:
    day_dir = tmp_path / "20260507"
    day_dir.mkdir()
    (day_dir / "report.csv").write_text("來源位址,目的地位址,應用程式,位元組\n10.0.0.1,10.0.0.2,web,1024\n", encoding="utf-8")
    (day_dir / "analysis.json").write_text('{"analysis":"摘要：測試報告"}', encoding="utf-8")
    save_review_markdown(tmp_path, "20260507", "normal", "已人工確認")

    bundle = load_report_bundle(tmp_path, "20260507")

    assert bundle["review"] == {"reviewStatus": "normal", "reviewNote": "已人工確認"}
