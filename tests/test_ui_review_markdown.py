from pathlib import Path

from ui import load_report_bundle, load_review_markdown, save_review_markdown


def test_save_review_markdown_writes_minimal_report_md(tmp_path: Path) -> None:
    report_path = save_review_markdown(
        tmp_path,
        "20260507",
        "follow-up",
        "需要追蹤備份流量",
        0,
        {
            "來源位址": "192.168.2.154",
            "目的地位址": "17.253.87.201",
            "應用程式": "itunes-base",
            "傳輸量": "1.6 GB (1,696,665,784 bytes)",
            "其他欄位": "不應寫入 report.md",
        },
    )

    assert report_path == tmp_path / "report.md"
    assert report_path.read_text(encoding="utf-8") == (
        "# 報告回報\n"
        "- 來源位址：192.168.2.154\n"
        "- 目的地位址：17.253.87.201\n"
        "- 應用程式：itunes-base\n"
        "- 傳輸量：1.6 GB (1,696,665,784 bytes)\n"
        "## 備註\n\n"
        "需要追蹤備份流量\n"
    )



def test_load_review_markdown_returns_empty_when_report_md_is_missing(tmp_path: Path) -> None:
    assert load_review_markdown(tmp_path, "20260507") == {}



def test_load_report_bundle_includes_review_from_report_markdown(tmp_path: Path) -> None:
    day_dir = tmp_path / "20260507"
    day_dir.mkdir()
    (day_dir / "report.csv").write_text(
        "來源位址,目的地位址,應用程式,位元組\n192.168.2.154,17.253.87.201,itunes-base,1696665784\n",
        encoding="utf-8",
    )
    (day_dir / "analysis.json").write_text('{"analysis":"摘要：測試報告"}', encoding="utf-8")
    save_review_markdown(
        tmp_path,
        "20260507",
        "normal",
        "已人工確認",
        0,
        {
            "來源位址": "192.168.2.154",
            "目的地位址": "17.253.87.201",
            "應用程式": "itunes-base",
            "傳輸量": "1.6 GB (1,696,665,784 bytes)",
        },
    )

    bundle = load_report_bundle(day_dir, day_dir, tmp_path, "20260507")

    assert bundle["reviews"] == {
        "0": {
            "reviewStatus": "",
            "reviewNote": "已人工確認",
            "rowIndex": 0,
            "rowNumber": 1,
            "csvLineNumber": 2,
            "rowFields": {
                "來源位址": "192.168.2.154",
                "目的地位址": "17.253.87.201",
                "應用程式": "itunes-base",
                "傳輸量": "1.6 GB (1,696,665,784 bytes)",
            },
        }
    }
