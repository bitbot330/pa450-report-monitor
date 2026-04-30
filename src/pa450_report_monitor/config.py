from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import yaml


@dataclass(frozen=True)
class Pa450Config:
    host: str
    username: str | None
    password: str | None
    api_key: str | None
    verify_tls: bool
    vsys: str
    report_name: str
    report_job_name: str


@dataclass(frozen=True)
class OutputConfig:
    directory: Path
    xml_file: str
    csv_file: str


@dataclass(frozen=True)
class MonitorConfig:
    bytes_field_candidates: list[str]
    bytes_threshold: int


@dataclass(frozen=True)
class AlertConfig:
    discord_webhook_url: str | None


@dataclass(frozen=True)
class AppConfig:
    pa450: Pa450Config
    output: OutputConfig
    monitor: MonitorConfig
    alert: AlertConfig


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env(name: str | None) -> str | None:
    if not name:
        return None
    value = os.environ.get(name)
    return value if value else None


def load_config(path: str | Path) -> AppConfig:
    load_dotenv()
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    pa = data["pa450"]
    monitor = data["monitor"]
    output = data["output"]
    alert = data.get("alert", {})

    host = _env(pa.get("host_env"))
    if not host:
        raise ValueError(f"Missing PA450 host env var: {pa.get('host_env')}")

    report_name = pa.get("report_name")
    if not report_name:
        raise ValueError("Missing pa450.report_name in config")

    return AppConfig(
        pa450=Pa450Config(
            host=host.rstrip("/"),
            username=_env(pa.get("username_env")),
            password=_env(pa.get("password_env")),
            api_key=_env(pa.get("api_key_env")),
            verify_tls=bool(pa.get("verify_tls", True)),
            vsys=pa.get("vsys", "vsys1"),
            report_name=report_name,
            report_job_name=pa.get("report_job_name", "pa450-custom-dynamic-report"),
        ),
        output=OutputConfig(
            directory=Path(output.get("directory", "output")),
            xml_file=output.get("xml_file", "report_result.xml"),
            csv_file=output.get("csv_file", "report_result.csv"),
        ),
        monitor=MonitorConfig(
            bytes_field_candidates=list(monitor.get("bytes_field_candidates", ["bytes", "Bytes"])),
            bytes_threshold=int(monitor.get("bytes_threshold", 0)),
        ),
        alert=AlertConfig(discord_webhook_url=_env(alert.get("discord_webhook_env"))),
    )
