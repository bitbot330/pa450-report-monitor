from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import yaml


@dataclass(frozen=True)
class OutputColumn:
    """Mapping from one UI/CSV header to possible PAN-OS XML field names."""

    header: str
    candidates: list[str]

# These are the CSV columns used by the analysis and Review UI. The candidate
# names cover common PAN-OS field-name variants so report.py can normalize XML
# output without hard-coding one firmware/export spelling.
DEFAULT_COLUMNS = [
    OutputColumn("產生時間", ["Generate Time", "generated-time", "receive_time", "receive-time", "time_generated"]),
    OutputColumn("來源位址", ["Source address", "source-address", "src", "source"]),
    OutputColumn("來源主機名稱", ["Source Hostname", "source-hostname", "src-host", "src_hostname"]),
    OutputColumn("來源使用者", ["Source User", "source-user", "srcuser", "src-user"]),
    OutputColumn("目的地位址", ["Destination address", "destination-address", "dst", "destination"]),
    OutputColumn("目的地國家", [
        "Destination Country",
        "destination-country",
        "destination_country",
        "dst-country",
        "dst_country",
        "dstloc",
        "dst-location",
        "dst_location",
    ]),
    OutputColumn("目的地主機名稱", ["Destination Hostname", "destination-hostname", "dst-host", "dst_hostname"]),
    OutputColumn("應用程式", ["Application", "app", "application"]),
    OutputColumn("位元組", ["Bytes", "bytes", "byte"]),
]


@dataclass(frozen=True)
class Pa450Config:
    """Firewall connection and custom-report settings used by report.py."""

    host: str
    username: str | None
    password: str | None
    api_key: str | None
    verify_tls: bool
    report_name: str
    report_job_name: str


@dataclass(frozen=True)
class OutputConfig:
    """CSV output shape shared by the downloader and analysis workflow."""

    columns: list[OutputColumn]


@dataclass(frozen=True)
class AppConfig:
    """Top-level runtime config object returned by load_config()."""

    pa450: Pa450Config
    output: OutputConfig


def load_dotenv(path: str | Path = ".env") -> None:
    """Load simple KEY=VALUE pairs into the process environment if absent."""

    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        # This lightweight parser intentionally supports only the .env shape the
        # project needs: comments, blank lines, and one KEY=VALUE per line.
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env(name: str) -> str | None:
    """Return a non-empty environment value, or None for missing/blank values."""

    value = os.environ.get(name)
    return value if value else None


def _bool_config(value: object, *, default: bool = True) -> bool:
    """Parse YAML booleans without treating the string "false" as truthy."""

    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    raise ValueError(f"Invalid boolean config value: {value!r}")


def load_config(path: str | Path) -> AppConfig:
    """Load config.yaml and local secrets into typed immutable config objects."""

    # Load .env before reading individual values so command-line runs and the UI
    # can share the same local secrets file without exporting variables first.
    load_dotenv()
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    pa = data["pa450"]

    host = _env("PA450_HOST")
    if not host:
        raise ValueError("Missing PA450_HOST in .env")

    report_name = pa.get("report_name")
    if not report_name:
        raise ValueError("Missing pa450.report_name in config")
    if report_name == "YOUR_CUSTOM_REPORT_NAME":
        # Fail fast on the template placeholder; otherwise PAN-OS would return a
        # less helpful "report not found" response later in the download step.
        raise ValueError(
            "Replace pa450.report_name in config.yaml with the exact custom report "
            "name from Monitor > Manage Custom Reports."
        )

    return AppConfig(
        pa450=Pa450Config(
            # Strip a trailing slash here so Pa450ApiClient can append /api/ in
            # exactly one place.
            host=host.rstrip("/"),
            username=_env("PA450_USERNAME"),
            password=_env("PA450_PASSWORD"),
            api_key=_env("PA450_API_KEY"),
            verify_tls=_bool_config(pa.get("verify_tls"), default=True),
            report_name=report_name,
            report_job_name=pa.get("report_job_name", "pa450-custom-dynamic-report"),
        ),
        output=OutputConfig(columns=DEFAULT_COLUMNS),
    )
