from datetime import date
from pathlib import Path

from pa450_report_monitor.__main__ import dated_output_dir


def test_dated_output_dir_uses_yyyymmdd_under_output():
    assert dated_output_dir(Path("output"), today=date(2026, 4, 30)) == Path("output") / "20260430"
