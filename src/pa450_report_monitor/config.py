from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import yaml

from .convert import OutputColumn

DEFAULT_COLUMNS = [
    OutputColumn("產生時間", ["Generate Time", "generated-time", "receive_time", "receive-time", "time_generated"]),
    OutputColumn("來源位址", ["Source address", "source-address", "src", "source"]),
    OutputColumn("來源主機名稱", ["Source Hostname", "source-hostname", "src-host", "src_hostname"]),
    OutputColumn("來源使用者", ["Source User", "source-user", "srcuser", "src-user"]),
    OutputColumn("目的地位址", ["Destination address", "destination-address", "dst", "destination"]),
    OutputColumn("目的地主機名稱", ["Destination Hostname", "destination-hostname", "dst-host", "dst_hostname"]),
    OutputColumn("應用程式", ["Application", "app", "application"]),
    OutputColumn("位元組", ["Bytes", "bytes", "byte"]),
]


@dataclass(frozen=True)
class Pa450Config:
    host: str
    username: str | None
    password: str | None
    api_key: str | None
    verify_tls: bool
    report_name: str
    report_job_name: str


@dataclass(frozen=True)
class OutputConfig:
    columns: list[OutputColumn]


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


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    return value if value else None


def load_config(path: str | Path) -> AppConfig:
    load_dotenv()
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    pa = data["pa450"]
    monitor = data.get("monitor", {})
    alert = data.get("alert", {})

    host = _env("PA450_HOST")
    if not host:
        raise ValueError("Missing PA450_HOST in .env")

    report_name = pa.get("report_name")
    if not report_name:
        raise ValueError("Missing pa450.report_name in config")
    if report_name == "YOUR_CUSTOM_REPORT_NAME":
        raise ValueError(
            "Replace pa450.report_name in config.yaml with the exact custom report "
            "name from Monitor > Manage Custom Reports."
        )

    return AppConfig(
        pa450=Pa450Config(
            host=host.rstrip("/"),
            username=_env("PA450_USERNAME"),
            password=_env("PA450_PASSWORD"),
            api_key=_env("PA450_API_KEY"),
            verify_tls=bool(pa.get("verify_tls", True)),
            report_name=report_name,
            report_job_name=pa.get("report_job_name", "pa450-custom-dynamic-report"),
        ),
        output=OutputConfig(columns=DEFAULT_COLUMNS),
        monitor=MonitorConfig(
            bytes_field_candidates=list(monitor.get("bytes_field_candidates", ["bytes", "Bytes", "位元組", "repeatcnt"])),
            bytes_threshold=int(monitor.get("bytes_threshold", 0)),
        ),
        alert=AlertConfig(discord_webhook_url=_env("DISCORD_WEBHOOK_URL")),
    )
