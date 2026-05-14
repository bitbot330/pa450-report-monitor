from __future__ import annotations

from pathlib import Path
import sys


def resolve_file_root() -> Path:
    """Return the root folder for CSV/AI JSON/feedback files.

    Source run:
        <project>/src/ui_config.py -> <project>

    PyInstaller onefile run from <project>/dist/PA450-Daily-Review-UI.exe:
        sys.executable -> <project>/dist/PA450-Daily-Review-UI.exe -> <project>
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if exe_dir.name.lower() == "dist":
            return exe_dir.parent
        return exe_dir
    return Path(__file__).resolve().parent.parent


FILE_ROOT = resolve_file_root()
DEFAULT_LOAD_DIR = FILE_ROOT / "output"
