from datetime import date
from pathlib import Path

from pa450_report_monitor.__main__ import dated_output_dir, parse_args


def test_dated_output_dir_uses_yyyymmdd_under_output():
    assert dated_output_dir(Path("output"), today=date(2026, 4, 30)) == Path("output") / "20260430"


def test_cli_output_dir_argument_sets_download_base_directory():
    args = parse_args(["--config", "config.yaml", "--output-dir", "D:\\pa450-reports"])

    assert args.config == "config.yaml"
    assert args.output_dir == Path("D:\\pa450-reports")
