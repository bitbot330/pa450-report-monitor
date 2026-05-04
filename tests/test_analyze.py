from pathlib import Path

from pa450_report_monitor import analyze


def test_build_context_reads_csv_text(tmp_path):
    csv_path = tmp_path / "20260504_report.csv"
    csv_path.write_text("來源位址,目的地位址,位元組\n10.0.0.1,8.8.8.8,123\n", encoding="utf-8-sig")

    assert analyze.build_context(csv_path) == "來源位址,目的地位址,位元組\n10.0.0.1,8.8.8.8,123\n"


def test_write_analysis_result_writes_model_content_json(tmp_path):
    output_path = tmp_path / "20260504_analysis.json"

    analyze.write_analysis_result(output_path, "分析結果")

    assert output_path.read_text(encoding="utf-8") == '{\n  "analysis": "分析結果"\n}\n'


def test_parse_args_accepts_input_output_and_query():
    args = analyze.parse_args([
        "--input",
        "output/20260504_report.csv",
        "--output",
        "output/20260504_analysis.json",
        "--query",
        "判斷是否異常",
    ])

    assert args.input == Path("output/20260504_report.csv")
    assert args.output == Path("output/20260504_analysis.json")
    assert args.query == "判斷是否異常"
