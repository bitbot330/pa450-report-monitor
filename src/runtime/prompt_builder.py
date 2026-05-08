from __future__ import annotations

from pathlib import Path


def find_agents_md(start_dir: str | Path | None = None) -> Path | None:
    """Find the nearest AGENTS.md by walking upward from start_dir."""
    current = Path(start_dir or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        candidate = directory / "AGENTS.md"
        if candidate.is_file():
            return candidate
    return None


def read_agents_md(start_dir: str | Path | None = None) -> str:
    """Return preloaded AGENTS.md content, or an empty string when absent."""
    agents_path = find_agents_md(start_dir)
    if agents_path is None:
        return ""
    return agents_path.read_text(encoding="utf-8")


def build_system_prompt(base_prompt: str, start_dir: str | Path | None = None) -> str:
    """Inject AGENTS.md into the system prompt before calling the LLM.

    The runtime reads AGENTS.md and passes the resulting instructions as part of
    the SystemMessage. The model is not asked to discover or read workspace
    files by itself.
    """
    agents_path = find_agents_md(start_dir)
    if agents_path is None:
        return base_prompt

    agents_content = agents_path.read_text(encoding="utf-8")
    return (
        f"{base_prompt}\n\n"
        "以下是 runtime 預先載入的 AGENTS.md workspace 指示，請遵守。\n"
        f"來源: {agents_path}\n\n"
        "<agents_md>\n"
        f"{agents_content.strip()}\n"
        "</agents_md>"
    )
