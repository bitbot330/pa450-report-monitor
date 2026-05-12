from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from runtime.prompt_builder import build_system_prompt


def test_review_rules_are_mandatory_not_auxiliary(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("workspace rules", encoding="utf-8")

    prompt = build_system_prompt("base", start_dir=tmp_path, review_rules="- ms-update is normal")

    assert "必須遵守的判斷規則" in prompt
    assert "優先遵守 review rules" in prompt
    assert "僅可作為輔助判斷依據" not in prompt
