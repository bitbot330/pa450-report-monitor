from datetime import date
from pathlib import Path

from pa450_report_monitor.__main__ import output_csv_path, parse_args


def test_output_csv_path_uses_cli_directory_without_daily_folder():
    assert output_csv_path(Path("output"), today=date(2026, 4, 30)) == Path("output") / "20260430_report.csv"


def test_cli_output_dir_argument_sets_download_directory():
    args = parse_args(["--config", "config.yaml", "--output-dir", "D:\\pa450-reports"])

    assert args.config == "config.yaml"
    assert args.output_dir == Path("D:\\pa450-reports")
