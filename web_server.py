from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse
import webbrowser

from agent import StudyPlanningAgent
from agent.html_view import HTMLViewModule


class StudyPlanningHTTPServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, StudyPlanningRequestHandler)
        self.project_root = Path(__file__).resolve().parent
        self.web_dir = self.project_root / "web"
        self.web_data_dir = self.web_dir / "data"
        self.agent = StudyPlanningAgent()
        self.html_view = HTMLViewModule()


class StudyPlanningRequestHandler(BaseHTTPRequestHandler):
    server: StudyPlanningHTTPServer

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self.send_html(self.server.html_view.render_app_page())
            return

        if path == "/record":
            query = parse_qs(parsed.query)
            self.serve_record_page(query.get("id", [""])[0])
            return

        if path == "/static/style.css":
            self.send_text_file(self.server.web_dir / "style.css", "text/css; charset=utf-8")
            return

        if path == "/static/app.js":
            self.send_text_file(self.server.web_dir / "app.js", "application/javascript; charset=utf-8")
            return

        if path == "/data/plans.js":
            self.send_text_file(
                self.server.web_data_dir / "plans.js",
                "application/javascript; charset=utf-8",
                extra_headers={"Cache-Control": "no-store"},
            )
            return

        if path == "/api/history":
            query = parse_qs(parsed.query)
            limit = self._parse_optional_int(query.get("limit", [""])[0])
            offset = self._parse_optional_int(query.get("offset", ["0"])[0], default=0) or 0
            self.send_json(
                {
                    "success": True,
                    "records": self.server.agent.get_history(limit=limit, offset=offset),
                }
            )
            return

        if path == "/api/latest":
            latest = self.server.agent.get_latest_plan()
            self.send_json(
                {
                    "success": True,
                    "record": latest,
                    "message": "No plan has been generated yet." if latest is None else None,
                }
            )
            return

        if path == "/api/record":
            query = parse_qs(parsed.query)
            self.serve_record_json(query.get("id", [""])[0])
            return

        self.send_json({"success": False, "error": "Not found."}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/create":
            payload = self.read_request_json()
            if payload is None:
                self.send_json({"success": False, "error": "Invalid JSON request body."}, status=400)
                return

            goal = str(payload.get("goal", "")).strip()
            if not goal:
                self.send_json({"success": False, "error": "Please enter a study goal."}, status=400)
                return

            record = self.server.agent.create_study_plan(goal)
            self.send_json({"success": True, "record": record})
            return

        if path == "/api/update":
            payload = self.read_request_json()
            if payload is None:
                self.send_json({"success": False, "error": "Invalid JSON request body."}, status=400)
                return

            feedback = str(payload.get("feedback", "")).strip()
            if not feedback:
                self.send_json({"success": False, "error": "Please enter feedback for the latest plan."}, status=400)
                return

            record = self.server.agent.update_latest_plan(feedback)
            if record is None:
                self.send_json(
                    {
                        "success": False,
                        "error": "No existing plan found. Please create a plan first.",
                    },
                    status=400,
                )
                return

            self.send_json({"success": True, "record": record})
            return

        if path == "/api/task-status":
            payload = self.read_request_json()
            if payload is None:
                self.send_json({"success": False, "error": "Invalid JSON request body."}, status=400)
                return

            record_id = str(payload.get("record_id", "")).strip()
            task_id = str(payload.get("task_id", "")).strip()
            status = str(payload.get("status", "")).strip()

            if not record_id or not task_id or not status:
                self.send_json(
                    {
                        "success": False,
                        "error": "Please provide record_id, task_id, and status.",
                    },
                    status=400,
                )
                return

            record = self.server.agent.update_task_status(record_id, task_id, status)
            if record is None:
                self.send_json({"success": False, "error": "Task not found."}, status=404)
                return

            self.send_json({"success": True, "record": record})
            return

        if path == "/api/update-plan":
            payload = self.read_request_json()
            if payload is None:
                self.send_json({"success": False, "error": "Invalid JSON request body."}, status=400)
                return

            record_id = str(payload.get("record_id", "")).strip()
            feedback = str(payload.get("feedback", "")).strip()
            if not record_id or not feedback:
                self.send_json(
                    {
                        "success": False,
                        "error": "Please provide record_id and feedback.",
                    },
                    status=400,
                )
                return

            record = self.server.agent.update_plan_by_id(record_id, feedback)
            if record is None:
                self.send_json({"success": False, "error": "Plan not found."}, status=404)
                return

            self.send_json({"success": True, "record": record})
            return

        if path == "/api/delete-plan":
            payload = self.read_request_json()
            if payload is None:
                self.send_json({"success": False, "error": "Invalid JSON request body."}, status=400)
                return

            record_id = str(payload.get("record_id", "")).strip()
            if not record_id:
                self.send_json(
                    {
                        "success": False,
                        "error": "Please provide record_id.",
                    },
                    status=400,
                )
                return

            deleted = self.server.agent.delete_plan(record_id)
            if not deleted:
                self.send_json({"success": False, "error": "Plan not found."}, status=404)
                return

            self.send_json({"success": True})
            return

        self.send_json({"success": False, "error": "Not found."}, status=404)

    def send_html(self, content: str, status: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text_file(
        self,
        file_path: Path,
        content_type: str,
        status: int = 200,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_json({"success": False, "error": "File not found."}, status=404)
            return

        body = file_path.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def read_request_json(self) -> dict[str, Any] | None:
        content_length = self.headers.get("Content-Length", "0")
        try:
            length = int(content_length)
        except ValueError:
            return None

        if length <= 0:
            return None

        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict):
            return None
        return payload

    def _parse_optional_int(self, raw_value: str, default: int | None = None) -> int | None:
        value = str(raw_value or "").strip()
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def serve_record_json(self, raw_record_id: str) -> None:
        record_id = raw_record_id.strip()
        if not record_id:
            self.send_json({"success": False, "error": "Please provide a record id."}, status=400)
            return

        record = self.server.agent.get_record_by_id(record_id)
        if record is None:
            self.send_json({"success": False, "error": "Record not found."}, status=404)
            return

        self.send_json({"success": True, "record": record})

    def serve_record_page(self, raw_record_id: str) -> None:
        record_id = raw_record_id.strip()
        if not record_id:
            self.send_html(
                self.server.html_view.render_record_not_found_page(
                    record_id="",
                    message="Please provide a record id in the query string.",
                    status_label="Missing Record",
                ),
                status=400,
            )
            return

        record = self.server.agent.get_record_by_id(record_id)
        if record is None:
            self.send_html(
                self.server.html_view.render_record_not_found_page(
                    record_id=record_id,
                    message="The requested record does not exist in web/data/plans.js.",
                    status_label="Record Not Found",
                ),
                status=404,
            )
            return

        self.send_html(self.server.html_view.render_record_page(record))


def run_server(host: str = "localhost", port: int = 8000) -> None:
    server = StudyPlanningHTTPServer((host, port))
    url = f"http://{host}:{port}"

    threading.Timer(0.3, _open_browser, args=(url,)).start()

    print("Study Planning Agent is running.")
    print(f"Open {url}")
    print("Press Ctrl+C to stop the server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _open_browser(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception:
        pass
