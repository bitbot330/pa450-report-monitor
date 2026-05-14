from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analyze import parse_args, process_pending_feedback
from runtime.review_tools import list_unprocessed_feedback_files, read_unprocessed_feedback


def test_lists_feedback_from_configured_feedback_dir(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    default_output = project_root / "output"
    custom_feedback_dir = tmp_path / "custom-feedback"
    default_output.mkdir(parents=True)
    custom_feedback_dir.mkdir()
    (default_output / "report_20260515.md").write_text("wrong folder", encoding="utf-8")
    (custom_feedback_dir / "report_20260514.md").write_text("right folder", encoding="utf-8")

    files = list_unprocessed_feedback_files(project_root, custom_feedback_dir)
    feedback_text, latest_date = read_unprocessed_feedback(project_root, custom_feedback_dir)

    assert files == [("20260514", custom_feedback_dir / "report_20260514.md")]
    assert "right folder" in feedback_text
    assert "wrong folder" not in feedback_text
    assert latest_date == "20260514"


def test_process_pending_feedback_uses_configured_feedback_dir(tmp_path: Path, monkeypatch) -> None:
    project_root = tmp_path / "project"
    custom_feedback_dir = tmp_path / "review-folder"
    custom_feedback_dir.mkdir(parents=True)
    (custom_feedback_dir / "report_20260514.md").write_text("Youtube traffic is normal", encoding="utf-8")

    monkeypatch.setattr("analyze.PROJECT_ROOT", project_root)
    monkeypatch.setattr("analyze.extract_review_rules_from_feedback", lambda feedback, existing: "- Youtube traffic is normal")

    result = process_pending_feedback(custom_feedback_dir)

    assert result == "Processed feedback through 20260514."
    assert (project_root / ".agent" / "review.md").read_text(encoding="utf-8") == "- Youtube traffic is normal\n"
    assert '"last_processed_feedback_date": "20260514"' in (project_root / ".agent" / "review_state.json").read_text(encoding="utf-8")


def test_analyze_cli_accepts_feedback_dir() -> None:
    args = parse_args([
        "--input",
        "daily.csv",
        "--output",
        "analysis/report_20260514.json",
        "--feedback-dir",
        "custom-review",
    ])

    assert args.feedback_dir == Path("custom-review")
