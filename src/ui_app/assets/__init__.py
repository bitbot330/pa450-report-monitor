from __future__ import annotations

import sys
from pathlib import Path


_PLACEHOLDERS = {
    "title": "__TITLE__",
    "csv_dir_json": "__CSV_DIR_JSON__",
    "analysis_dir_json": "__ANALYSIS_DIR_JSON__",
    "review_dir_json": "__REVIEW_DIR_JSON__",
}


def asset_root() -> Path:
    """Return the UI asset directory for source runs and PyInstaller onefile builds."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "ui_app" / "assets"
    return Path(__file__).resolve().parent


def load_index_html() -> str:
    return (asset_root() / "index.html").read_text(encoding="utf-8")


def render_index_html(*, title: str, csv_dir_json: str, analysis_dir_json: str, review_dir_json: str) -> str:
    html = load_index_html()
    values = {
        "title": title,
        "csv_dir_json": csv_dir_json,
        "analysis_dir_json": analysis_dir_json,
        "review_dir_json": review_dir_json,
    }
    for key, placeholder in _PLACEHOLDERS.items():
        html = html.replace(placeholder, values[key])
    return html
