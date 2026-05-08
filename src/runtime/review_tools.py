from __future__ import annotations

from pathlib import Path


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _review_path(project_root: str | Path | None = None) -> Path:
    root = Path(project_root) if project_root is not None else DEFAULT_PROJECT_ROOT
    return root / ".agent" / "review.md"


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
    """Append concise AI-selected review rules to .agent/review.md.

    The model decides whether to call this tool. Runtime performs the file write.
    Duplicate normalized lines are ignored.
    """
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
