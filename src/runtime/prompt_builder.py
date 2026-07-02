from __future__ import annotations

from pathlib import Path


def find_agents_md(start_dir: str | Path | None = None) -> Path | None:
    """Find the nearest AGENTS.md by walking upward from start_dir."""
    current = Path(start_dir or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    # Walk upward so scripts launched from src/, tests/, or a packaged working
    # directory can still locate the repository-level AGENTS.md contract.
    for directory in (current, *current.parents):
        candidate = directory / "AGENTS.md"
        if candidate.is_file():
            return candidate
    return None


def build_system_prompt(
    base_prompt: str,
    start_dir: str | Path | None = None,
    review_rules: str = "",
) -> str:
    """Inject runtime-owned project context into the system prompt.

    Runtime reads AGENTS.md and review.md before the LLM call. The model is not
    asked to discover or read workspace files by itself.
    """
    prompt_parts = [base_prompt]

    agents_path = find_agents_md(start_dir)
    if agents_path is not None:
        agents_content = agents_path.read_text(encoding="utf-8").strip()
        # Include the source path for debugging, but pass the content as already
        # loaded context rather than instructing the model to read files.
        prompt_parts.append(
            "以下是 runtime 預先載入的 AGENTS.md workspace 指示，請遵守。\n"
            f"來源: {agents_path}\n\n"
            "<agents_md>\n"
            f"{agents_content}\n"
            "</agents_md>"
        )

    if review_rules.strip():
        prompt_parts.append(
            "以下是 runtime 在本次任務開始前讀取的 review rules，是本次分析必須遵守的判斷規則。\n"
            "若 review rules 與一般高流量直覺衝突，必須優先遵守 review rules。\n"
            "最終結論仍必須只根據本次 CSV context 中真實存在的資料列。\n\n"
            "<review_rules>\n"
            f"{review_rules.strip()}\n"
            "</review_rules>"
        )

    return "\n\n".join(prompt_parts)
