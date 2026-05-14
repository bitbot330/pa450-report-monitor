from __future__ import annotations

import json
import re
from pathlib import Path


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEEDBACK_FILENAME_PATTERN = re.compile(r"^report_(\d{8})\.md$")


def _project_root(project_root: str | Path | None = None) -> Path:
    return Path(project_root) if project_root is not None else DEFAULT_PROJECT_ROOT


def _review_path(project_root: str | Path | None = None) -> Path:
    return _project_root(project_root) / ".agent" / "review.md"


def _review_state_path(project_root: str | Path | None = None) -> Path:
    return _project_root(project_root) / ".agent" / "review_state.json"


def _ui_review_dir_path(project_root: str | Path | None = None) -> Path:
    return _project_root(project_root) / ".agent" / "review_dir"


def read_ui_feedback_dir(project_root: str | Path | None = None) -> Path | None:
    path = _ui_review_dir_path(project_root)
    if not path.exists():
        return None
    review_dir = path.read_text(encoding="utf-8").strip()
    if not review_dir:
        return None
    return Path(review_dir).expanduser()


def write_ui_feedback_dir(review_dir: str | Path, project_root: str | Path | None = None) -> None:
    path = _ui_review_dir_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(Path(review_dir).expanduser()) + "\n", encoding="utf-8")


def _feedback_dir(project_root: str | Path | None = None) -> Path:
    configured = read_ui_feedback_dir(project_root)
    if configured is not None:
        return configured
    return _project_root(project_root) / "output"


def _normalize_rule_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped.startswith("- "):
        return stripped
    return f"- {stripped.lstrip('-•*0123456789.) ')}"


def read_review_memory(project_root: str | Path | None = None) -> str:
    """Read .agent/review.md for runtime-provided review rules."""
    path = _review_path(project_root)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_review_memory(rules: str, project_root: str | Path | None = None) -> str:
    """Append concise reusable review rules to .agent/review.md."""
    path = _review_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing_lines = [
        _normalize_rule_line(line)
        for line in read_review_memory(project_root).splitlines()
    ]
    new_lines = [_normalize_rule_line(line) for line in rules.splitlines()]

    merged: list[str] = []
    seen: set[str] = set()
    for line in existing_lines + new_lines:
        if not line:
            continue
        key = line.casefold()
        if key in seen:
            continue
        seen.add(key)
        merged.append(line)

    path.write_text("\n".join(merged) + ("\n" if merged else ""), encoding="utf-8")
    return f"written {len(merged)} review rule(s) to {path}"


def read_review_state(project_root: str | Path | None = None) -> dict[str, str]:
    """Read feedback processing checkpoint state."""
    path = _review_state_path(project_root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    value = data.get("last_processed_feedback_date")
    return {"last_processed_feedback_date": value} if isinstance(value, str) else {}


def write_review_state(state: dict[str, str], project_root: str | Path | None = None) -> None:
    """Write feedback processing checkpoint state."""
    path = _review_state_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_unprocessed_feedback_files(
    project_root: str | Path | None = None,
) -> list[tuple[str, Path]]:
    """Return report_YYYYMMDD.md feedback files newer than the saved checkpoint."""
    feedback_base = _feedback_dir(project_root)
    if not feedback_base.exists():
        return []

    last_processed = read_review_state(project_root).get("last_processed_feedback_date", "")
    feedback_files: list[tuple[str, Path]] = []
    for path in feedback_base.iterdir():
        match = FEEDBACK_FILENAME_PATTERN.match(path.name)
        if not match or not path.is_file():
            continue
        report_date = match.group(1)
        if report_date > last_processed:
            feedback_files.append((report_date, path))

    return sorted(feedback_files, key=lambda item: item[0])


def read_unprocessed_feedback(
    project_root: str | Path | None = None,
) -> tuple[str, str | None]:
    """Read all pending report_YYYYMMDD.md feedback as one text block."""
    pending_files = list_unprocessed_feedback_files(project_root)
    if not pending_files:
        return "", None

    chunks: list[str] = []
    latest_date: str | None = None
    for report_date, path in pending_files:
        content = path.read_text(encoding="utf-8").strip()
        latest_date = report_date
        if not content:
            continue
        chunks.append(
            f"## Feedback from {path.name}\n\n{content}"
        )

    return "\n\n".join(chunks), latest_date


def mark_feedback_processed(report_date: str, project_root: str | Path | None = None) -> None:
    """Mark feedback files through report_date as processed."""
    write_review_state({"last_processed_feedback_date": report_date}, project_root)
