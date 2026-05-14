from __future__ import annotations

import argparse
import errno
import json
import threading
import webbrowser
from functools import partial
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from ui_app.data import (
    build_report_map,
    discover_reports,
    enrich_rows_for_display,
    format_bytes_human,
    load_analysis_payload,
    load_csv_rows,
    load_report_bundle,
    load_review_markdown,
    locate_report_paths,
    parse_analysis_sections,
    save_review_markdown,
    select_folder_dialog,
    summarize_rows,
    _normalized_base,
    _validated_date_key,
)
from ui_app.assets import render_index_html
from runtime.review_tools import write_ui_feedback_dir


DASHBOARD_TITLE = "PA450 Daily Review UI"
LOCALHOST = "127.0.0.1"


PROJECT_ROOT_MARKERS = ("AGENTS.md", "config.example.yaml", "pyproject.toml")


def _candidate_roots(path: Path) -> list[Path]:
    resolved = path.expanduser().resolve() if path.exists() else path.expanduser().absolute()
    start = resolved if resolved.is_dir() else resolved.parent
    return [start, *start.parents]


def _looks_like_project_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in PROJECT_ROOT_MARKERS)


def _find_project_root_from_paths(paths: list[Path]) -> Path | None:
    for path in paths:
        for candidate in _candidate_roots(path):
            if _looks_like_project_root(candidate):
                return candidate
    return None


def _settings_project_root(folders: dict[str, Path], default_data_dir: Path) -> Path:
    """Find the project root where analysis runtime will read .agent settings."""
    candidates = [
        folders.get("analysis_dir"),
        folders.get("csv_dir"),
        folders.get("review_dir"),
        default_data_dir,
        Path.cwd(),
    ]
    project_root = _find_project_root_from_paths([path for path in candidates if path is not None])
    return project_root or Path.cwd()


class ReportUIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args: Any, data_dir: str, **kwargs: Any) -> None:
        self.default_data_dir = _normalized_base(data_dir)
        super().__init__(*args, **kwargs)

    def _request_folders(self, parsed) -> dict[str, Path]:
        params = parse_qs(parsed.query)
        legacy_data_dir = (params.get("data_dir") or [""])[0].strip()
        default_dir = _normalized_base(legacy_data_dir) if legacy_data_dir else self.default_data_dir

        def pick(name: str) -> Path:
            requested = (params.get(name) or [""])[0].strip()
            return _normalized_base(requested) if requested else default_dir

        return {
            "csv_dir": pick("csv_dir"),
            "analysis_dir": pick("analysis_dir"),
            "review_dir": pick("review_dir"),
        }

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        folders = self._request_folders(parsed)
        if parsed.path == "/":
            self._send_html(render_index_html(
                title=escape(DASHBOARD_TITLE),
                csv_dir_json=json.dumps(str(self.default_data_dir), ensure_ascii=False),
                analysis_dir_json=json.dumps(str(self.default_data_dir), ensure_ascii=False),
                review_dir_json=json.dumps(str(self.default_data_dir), ensure_ascii=False),
            ))
            return
        if parsed.path == "/api/pick-folder":
            params = parse_qs(parsed.query)
            kind = (params.get("kind") or [""])[0].strip()
            current_dir = {
                "csv": folders["csv_dir"],
                "analysis": folders["analysis_dir"],
                "review": folders["review_dir"],
            }.get(kind, self.default_data_dir)
            try:
                selected = select_folder_dialog(current_dir)
            except RuntimeError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._send_json({"selected": bool(selected), "path": selected or ""})
            return
        if parsed.path == "/api/reports":
            write_ui_feedback_dir(folders["review_dir"], _settings_project_root(folders, self.default_data_dir))
            self._send_json({
                "csv_dir": str(folders["csv_dir"]),
                "analysis_dir": str(folders["analysis_dir"]),
                "review_dir": str(folders["review_dir"]),
                "reports": discover_reports(folders["csv_dir"], folders["analysis_dir"]),
            })
            return
        if parsed.path.startswith("/api/reports/"):
            write_ui_feedback_dir(folders["review_dir"], _settings_project_root(folders, self.default_data_dir))
            date_key = unquote(parsed.path.removeprefix("/api/reports/"))
            try:
                payload = load_report_bundle(folders["csv_dir"], folders["analysis_dir"], folders["review_dir"], date_key)
            except ValueError:
                self._send_json({"error": "Invalid report date"}, status=HTTPStatus.BAD_REQUEST)
                return
            except FileNotFoundError:
                self._send_json({"error": "Report not found"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json(payload)
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        folders = self._request_folders(parsed)
        if parsed.path.startswith("/api/reports/") and parsed.path.endswith("/review"):
            write_ui_feedback_dir(folders["review_dir"], _settings_project_root(folders, self.default_data_dir))
            date_key = unquote(parsed.path.removeprefix("/api/reports/").removesuffix("/review").strip("/"))
            try:
                date_key = _validated_date_key(date_key)
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length).decode("utf-8")
                payload = json.loads(body or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("Review payload must be an object")
                row_index = payload.get("rowIndex")
                if row_index is None:
                    raise ValueError("rowIndex is required")
                row_fields = payload.get("rowFields") or {}
                if not isinstance(row_fields, dict):
                    raise ValueError("rowFields must be an object")
                report_path = save_review_markdown(
                    folders["review_dir"],
                    date_key,
                    str(payload.get("reviewStatus") or ""),
                    str(payload.get("reviewNote") or ""),
                    int(row_index),
                    row_fields,
                    int(payload.get("rowNumber") or int(row_index) + 1),
                    int(payload.get("csvLineNumber") or int(row_index) + 2),
                )
                csv_path, _json_path = locate_report_paths(folders["csv_dir"], folders["analysis_dir"], date_key)
                headers, rows = load_csv_rows(csv_path)
                _display_headers, display_rows = enrich_rows_for_display(headers, rows)
            except (ValueError, json.JSONDecodeError):
                self._send_json({"error": "Invalid review payload"}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"ok": True, "path": str(report_path), "reviews": load_review_markdown(folders["review_dir"], date_key, display_rows)})
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)


def open_browser_when_ready(port: int) -> None:
    webbrowser.open(f"http://{LOCALHOST}:{port}")


def create_server(handler, requested_port: int) -> tuple[ThreadingHTTPServer, int, bool]:
    try:
        server = ThreadingHTTPServer((LOCALHOST, requested_port), handler)
        return server, requested_port, False
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
    fallback_server = ThreadingHTTPServer((LOCALHOST, 0), handler)
    fallback_port = int(fallback_server.server_address[1])
    return fallback_server, fallback_port, True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a localhost-only PA450 daily review UI")
    parser.add_argument("--data-dir", default=Path("output"), type=Path, help="Folder containing daily CSV/JSON results")
    parser.add_argument("--port", default=8765, type=int, help="Localhost port to bind the UI server")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    handler = partial(ReportUIHandler, data_dir=str(args.data_dir))
    server, active_port, used_fallback_port = create_server(handler, args.port)
    if used_fallback_port:
        print(
            f"Requested port {args.port} is already in use on {LOCALHOST}; "
            f"using http://{LOCALHOST}:{active_port} instead."
        )
    print(f"PA450 Daily Review UI running at http://{LOCALHOST}:{active_port}")
    if not args.no_browser:
        threading.Timer(0.6, open_browser_when_ready, args=(active_port,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
