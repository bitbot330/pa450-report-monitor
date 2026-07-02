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
    discover_reports,
    enrich_rows_for_display,
    load_csv_rows,
    load_report_bundle,
    load_report_range_bundle,
    load_review_markdown,
    locate_report_paths,
    normalize_base_dir,
    save_review_markdown,
    select_folder_dialog,
    validate_date_key,
)
from ui_app.assets import render_index_html
from runtime.review_tools import write_ui_feedback_dir


DASHBOARD_TITLE = "PA450 Daily Review UI"
LOCALHOST = "127.0.0.1"


class ReportUIHandler(BaseHTTPRequestHandler):
    """HTTP handler for report discovery, report loading, and row review writes."""

    def __init__(self, *args: Any, data_dir: str, **kwargs: Any) -> None:
        self.default_data_dir = normalize_base_dir(data_dir)
        super().__init__(*args, **kwargs)

    def _request_folders(self, parsed) -> dict[str, Path]:
        # Each request carries the currently selected CSV/analysis/review folders
        # so the browser can keep independent folder state without server-side
        # sessions. data_dir remains as the legacy/default fallback.
        params = parse_qs(parsed.query)
        legacy_data_dir = (params.get("data_dir") or [""])[0].strip()
        default_dir = normalize_base_dir(legacy_data_dir) if legacy_data_dir else self.default_data_dir

        def pick(name: str) -> Path:
            requested = (params.get(name) or [""])[0].strip()
            return normalize_base_dir(requested) if requested else default_dir

        return {
            "csv_dir": pick("csv_dir"),
            "analysis_dir": pick("analysis_dir"),
            "review_dir": pick("review_dir"),
        }

    def do_GET(self) -> None:
        # Route only the few endpoints the local UI needs; anything else returns
        # JSON 404 so browser fetch callers can show a useful error message.
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
            # Persist the selected review folder so standalone analyze.py can
            # scan the same feedback location before the next AI run.
            write_ui_feedback_dir(folders["review_dir"])
            self._send_json({
                "csv_dir": str(folders["csv_dir"]),
                "analysis_dir": str(folders["analysis_dir"]),
                "review_dir": str(folders["review_dir"]),
                "reports": discover_reports(folders["csv_dir"], folders["analysis_dir"]),
            })
            return
        if parsed.path == "/api/reports/range":
            # Range mode merges CSV evidence across dates while keeping the AI
            # daily analyses separate for the carousel in app.js.
            write_ui_feedback_dir(folders["review_dir"])
            params = parse_qs(parsed.query)
            start_date = (params.get("start_date") or [""])[0].strip()
            end_date = (params.get("end_date") or [""])[0].strip()
            try:
                payload = load_report_range_bundle(
                    folders["csv_dir"],
                    folders["analysis_dir"],
                    folders["review_dir"],
                    start_date,
                    end_date,
                )
            except ValueError:
                self._send_json({"error": "Invalid report date range"}, status=HTTPStatus.BAD_REQUEST)
                return
            except FileNotFoundError:
                self._send_json({"error": "Reports not found"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json(payload)
            return
        if parsed.path.startswith("/api/reports/"):
            write_ui_feedback_dir(folders["review_dir"])
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
            # Save human feedback as report_YYYYMMDD.md. analyze.py later turns
            # this feedback into reusable review rules via runtime.review_tools.
            write_ui_feedback_dir(folders["review_dir"])
            date_key = unquote(parsed.path.removeprefix("/api/reports/").removesuffix("/review").strip("/"))
            try:
                date_key = validate_date_key(date_key)
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
        # Suppress stdlib per-request logging; UI errors are returned as JSON and
        # the CLI prints only startup information.
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
    """Open the Review UI in the user's default browser."""

    webbrowser.open(f"http://{LOCALHOST}:{port}")


def create_server(handler, requested_port: int) -> tuple[ThreadingHTTPServer, int, bool]:
    """Bind localhost, falling back to an available port if the default is busy."""

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
    # Launch the browser shortly after bind so the server is already accepting
    # requests when the browser tab opens.
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
