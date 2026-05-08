from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class PromptBuilderTest(unittest.TestCase):
    def test_build_system_prompt_preloads_agents_md(self):
        from runtime.prompt_builder import build_system_prompt

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            nested = workspace / "src"
            nested.mkdir()
            (workspace / "AGENTS.md").write_text(
                "# AGENTS.md\n\n- 啟動時由 runtime 預先載入。\n",
                encoding="utf-8",
            )

            prompt = build_system_prompt("基礎 system prompt", start_dir=nested)

        self.assertIn("基礎 system prompt", prompt)
        self.assertIn("以下是 runtime 預先載入的 AGENTS.md", prompt)
        self.assertIn("啟動時由 runtime 預先載入", prompt)

    def test_build_system_prompt_does_not_change_base_prompt_when_agents_md_missing(self):
        from runtime.prompt_builder import build_system_prompt

        with tempfile.TemporaryDirectory() as tmp_dir:
            prompt = build_system_prompt("基礎 system prompt", start_dir=tmp_dir)

        self.assertEqual("基礎 system prompt", prompt)


if __name__ == "__main__":
    unittest.main()
