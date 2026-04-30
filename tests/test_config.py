from pathlib import Path

import pytest

from pa450_report_monitor.config import DEFAULT_COLUMNS, load_config


def test_load_config_rejects_placeholder_report_name(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
pa450:
  verify_tls: false
  vsys: vsys1
  report_name: YOUR_CUSTOM_REPORT_NAME
  report_job_name: pa450-custom-dynamic-report
monitor:
  bytes_threshold: 100
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("PA450_HOST", "10.0.0.1")

    with pytest.raises(ValueError, match="Replace pa450.report_name"):
        load_config(config_path)


def test_load_config_uses_fixed_env_names_and_default_output(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
pa450:
  verify_tls: false
  vsys: vsys1
  report_name: top-sources
  report_job_name: pa450-custom-dynamic-report
monitor:
  bytes_threshold: 100
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("PA450_HOST", "10.0.0.1")
    monkeypatch.setenv("PA450_USERNAME", "api-user")
    monkeypatch.setenv("PA450_PASSWORD", "api-password")

    config = load_config(config_path)

    assert config.pa450.host == "10.0.0.1"
    assert config.pa450.username == "api-user"
    assert config.pa450.password == "api-password"
    assert config.output.directory == Path("output")
    assert config.output.xml_file == "report_result.xml"
    assert config.output.csv_file == "report_result.csv"
    assert config.output.columns == DEFAULT_COLUMNS
