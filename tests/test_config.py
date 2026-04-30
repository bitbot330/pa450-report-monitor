from pathlib import Path

import pytest

from pa450_report_monitor.config import load_config


def test_load_config_rejects_placeholder_report_name(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
pa450:
  host_env: PA450_HOST
  username_env: PA450_USERNAME
  password_env: PA450_PASSWORD
  api_key_env: PA450_API_KEY
  verify_tls: false
  vsys: vsys1
  report_name: YOUR_CUSTOM_REPORT_NAME
  report_job_name: pa450-custom-dynamic-report
output:
  directory: output
  xml_file: report_result.xml
  csv_file: report_result.csv
monitor:
  bytes_field_candidates:
    - bytes
  bytes_threshold: 100
alert:
  discord_webhook_env: DISCORD_WEBHOOK_URL
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("PA450_HOST", "10.0.0.1")

    with pytest.raises(ValueError, match="Replace pa450.report_name"):
        load_config(config_path)
