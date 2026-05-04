from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from .alert import format_alert_message, send_discord_webhook
from .config import load_config
from .convert import rows_to_csv, xml_text_to_rows
from .monitor import rows_exceeding_bytes_threshold
from .pa450_api import Pa450ApiClient


def dated_output_dir(base_dir: Path, today: date | None = None) -> Path:
    today = today or date.today()
    return base_dir / today.strftime("%Y%m%d")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch PA450 custom report, convert to CSV, and monitor bytes")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--output-dir",
        default=Path("output"),
        type=Path,
        help="Base folder for downloaded report files; daily YYYYMMDD folders are created under this path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    cfg = load_config(args.config)
    output_dir = dated_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    xml_path = output_dir / cfg.output.xml_file
    csv_path = output_dir / cfg.output.csv_file

    client = Pa450ApiClient(cfg.pa450.host, verify_tls=cfg.pa450.verify_tls, api_key=cfg.pa450.api_key)
    if not client.api_key:
        if not cfg.pa450.username or not cfg.pa450.password:
            raise SystemExit("Missing PA450_API_KEY or PA450_USERNAME/PA450_PASSWORD")
        client.keygen(cfg.pa450.username, cfg.pa450.password)

    report_definition = client.get_custom_report_definition(cfg.pa450.report_name)
    job_id = client.enqueue_dynamic_report(cfg.pa450.report_job_name, report_definition)
    result_root = client.wait_for_report_result(job_id)

    xml_text = ET.tostring(result_root, encoding="unicode")
    xml_path.write_text(xml_text, encoding="utf-8")

    rows = xml_text_to_rows(xml_text)
    rows_to_csv(rows, csv_path, columns=cfg.output.columns)

    alert_rows = rows_exceeding_bytes_threshold(
        rows,
        cfg.monitor.bytes_field_candidates,
        cfg.monitor.bytes_threshold,
    )

    if alert_rows:
        print(f"ALERT: {len(alert_rows)} rows exceeded threshold")
        if cfg.alert.discord_webhook_url:
            send_discord_webhook(
                cfg.alert.discord_webhook_url,
                format_alert_message(alert_rows, cfg.monitor.bytes_threshold),
            )
    else:
        print("OK: no rows exceeded threshold")

    print(f"CSV written: {csv_path}")
    print(f"XML written: {xml_path}")
    print(f"Custom report XPath: {report_definition.xpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
