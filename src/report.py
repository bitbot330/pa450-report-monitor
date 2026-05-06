from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import ssl
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from config import OutputColumn, load_config


class Pa450ApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReportDefinition:
    xml: str
    xpath: str


@dataclass
class Pa450ApiClient:
    host: str
    verify_tls: bool = True
    api_key: str | None = None

    @property
    def api_url(self) -> str:
        host = self.host
        if not host.startswith(("http://", "https://")):
            host = f"https://{host}"
        return f"{host.rstrip('/')}/api/"

    def _ssl_context(self):
        if self.verify_tls:
            return None
        return ssl._create_unverified_context()

    def _post(self, data: dict[str, str], include_key: bool = True) -> ET.Element:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if include_key and self.api_key:
            headers["X-PAN-KEY"] = self.api_key
        request = urllib.request.Request(self.api_url, data=encoded, headers=headers, method="POST")
        with urllib.request.urlopen(request, context=self._ssl_context(), timeout=60) as response:
            body = response.read()
        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            raise Pa450ApiError(f"PAN-OS API returned invalid XML: {exc}") from exc
        if root.attrib.get("status") == "error":
            raise Pa450ApiError(ET.tostring(root, encoding="unicode"))
        return root

    def keygen(self, username: str, password: str) -> str:
        root = self._post(
            {"type": "keygen", "user": username, "password": password},
            include_key=False,
        )
        key = root.findtext(".//key")
        if not key:
            raise Pa450ApiError("API key not found in keygen response")
        self.api_key = key
        return key

    def get_custom_report_definition(self, report_name: str) -> ReportDefinition:
        xpath = f"/config/shared/reports/entry[@name='{report_name}']"
        root = self._post({"type": "config", "action": "get", "xpath": xpath})
        entry = root.find(".//entry")
        if entry is not None:
            xml = "".join(ET.tostring(child, encoding="unicode") for child in list(entry))
            return ReportDefinition(xml=xml, xpath=xpath)
        raise Pa450ApiError(
            f"Custom report not found: report={report_name}. "
            f"Searched fixed XPath location: {xpath}"
        )

    def enqueue_dynamic_report(self, report_job_name: str, report_definition_xml: str | ReportDefinition) -> str:
        if isinstance(report_definition_xml, ReportDefinition):
            report_definition_xml = report_definition_xml.xml
        root = self._post(
            {
                "type": "report",
                "reporttype": "dynamic",
                "reportname": report_job_name,
                "cmd": report_definition_xml,
            }
        )
        job_id = root.findtext(".//job")
        if not job_id:
            raise Pa450ApiError("Job ID not found in report enqueue response")
        return job_id

    def get_report_result(self, job_id: str) -> ET.Element:
        return self._post({"type": "report", "action": "get", "job-id": job_id})

    def wait_for_report_result(self, job_id: str, attempts: int = 12, delay_seconds: int = 10) -> ET.Element:
        last_root: ET.Element | None = None
        for _ in range(attempts):
            root = self.get_report_result(job_id)
            last_root = root
            if root.find(".//entry") is not None or root.findtext(".//status") in {"FIN", "Completed"}:
                return root
            time.sleep(delay_seconds)
        if last_root is None:
            raise Pa450ApiError("No report result returned")
        return last_root


def xml_text_to_rows(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    rows: list[dict[str, str]] = []
    for entry in root.findall(".//entry"):
        row: dict[str, str] = {}
        for child in list(entry):
            if list(child):
                row[child.tag] = " ".join((grand.text or "").strip() for grand in list(child)).strip()
            else:
                row[child.tag] = (child.text or "").strip()
        if row:
            rows.append(row)
    return rows


def _first_matching_value(row: dict[str, str], candidates: list[str]) -> str:
    normalized = {key.lower().replace("_", "-").replace(" ", "-"): value for key, value in row.items()}
    for candidate in candidates:
        if candidate in row:
            return row[candidate]
        normalized_candidate = candidate.lower().replace("_", "-").replace(" ", "-")
        if normalized_candidate in normalized:
            return normalized[normalized_candidate]
    return ""


def _align_rows_to_columns(rows: list[dict[str, str]], columns: list[OutputColumn]) -> list[dict[str, str]]:
    return [{column.header: _first_matching_value(row, column.candidates) for column in columns} for row in rows]


def rows_to_csv(
    rows: list[dict[str, str]],
    csv_path: str | Path,
    columns: list[OutputColumn] | None = None,
) -> None:
    if not rows:
        raise ValueError("No rows found in XML report result")
    if columns:
        headers = [column.header for column in columns]
        rows = _align_rows_to_columns(rows, columns)
    else:
        headers = sorted({key for row in rows for key in row.keys()})
    with Path(csv_path).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def parse_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def rows_exceeding_bytes_threshold(
    rows: list[dict[str, str]],
    field_candidates: list[str],
    threshold: int,
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    for row in rows:
        value = None
        for field in field_candidates:
            value = parse_int(row.get(field))
            if value is not None:
                break
        if value is not None and value > threshold:
            alerts.append(row)
    return alerts


def format_alert_message(alert_rows: list[dict[str, str]], threshold: int) -> str:
    lines = [f"ALERT: {len(alert_rows)} rows exceeded bytes threshold {threshold}."]
    for row in alert_rows[:10]:
        preview = ", ".join(f"{key}={value}" for key, value in sorted(row.items())[:8])
        lines.append(f"- {preview}")
    if len(alert_rows) > 10:
        lines.append(f"... and {len(alert_rows) - 10} more rows")
    return "\n".join(lines)


def output_csv_path(output_dir: Path, today: date | None = None) -> Path:
    today = today or date.today()
    return output_dir / f"{today.strftime('%Y%m%d')}_report.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch PA450 custom report, convert to CSV, and monitor bytes")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--output-dir",
        default=Path("output"),
        type=Path,
        help="Folder for the CSV report file",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    cfg = load_config(args.config)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_csv_path(args.output_dir)

    client = Pa450ApiClient(cfg.pa450.host, verify_tls=cfg.pa450.verify_tls, api_key=cfg.pa450.api_key)
    if not client.api_key:
        if not cfg.pa450.username or not cfg.pa450.password:
            raise SystemExit("Missing PA450_API_KEY or PA450_USERNAME/PA450_PASSWORD")
        client.keygen(cfg.pa450.username, cfg.pa450.password)

    report_definition = client.get_custom_report_definition(cfg.pa450.report_name)
    job_id = client.enqueue_dynamic_report(cfg.pa450.report_job_name, report_definition)
    result_root = client.wait_for_report_result(job_id)

    xml_text = ET.tostring(result_root, encoding="unicode")

    rows = xml_text_to_rows(xml_text)
    rows_to_csv(rows, csv_path, columns=cfg.output.columns)

    alert_rows = rows_exceeding_bytes_threshold(
        rows,
        cfg.monitor.bytes_field_candidates,
        cfg.monitor.bytes_threshold,
    )

    if alert_rows:
        print(format_alert_message(alert_rows, cfg.monitor.bytes_threshold))
    else:
        print("OK: no rows exceeded threshold")

    print(f"CSV written: {csv_path}")
    print(f"Custom report XPath: {report_definition.xpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
