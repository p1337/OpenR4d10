"""Small, read-only HTTP server for the local OpenR4d10 dashboard."""

from __future__ import annotations

from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import threading
from typing import Any
from urllib.parse import urlsplit

LOG = logging.getLogger(__name__)

StatusProvider = Callable[[], dict[str, Any]]

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


class _DashboardHandler(BaseHTTPRequestHandler):
    static_directory: Path
    status_provider: StatusProvider
    server_version = "OpenR4d10/0.2"
    sys_version = ""

    def _headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; img-src 'self'; "
            "style-src 'self'; script-src 'self'; frame-ancestors 'none'",
        )
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _send(self, status: int, content_type: str, payload: bytes) -> None:
        self._headers(status, content_type, len(payload))
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _serve_status(self) -> None:
        payload = json.dumps(
            self.status_provider(), ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
        self._send(200, "application/json; charset=utf-8", payload)

    def _serve_static(self, path: str) -> None:
        entry = STATIC_FILES.get(path)
        if entry is None:
            self._send(404, "text/plain; charset=utf-8", b"Not found\n")
            return
        relative, content_type = entry
        try:
            payload = (self.static_directory / relative).read_bytes()
        except OSError:
            LOG.exception("Cannot read web asset %s", relative)
            self._send(500, "text/plain; charset=utf-8", b"Web asset unavailable\n")
            return
        self._send(200, content_type, payload)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        path = urlsplit(self.path).path
        if path == "/api/status":
            self._serve_status()
        elif path == "/healthz":
            self._send(200, "text/plain; charset=utf-8", b"ok\n")
        else:
            self._serve_static(path)

    def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        self.do_GET()

    def log_message(self, format_string: str, *args: object) -> None:
        LOG.debug("Web request: " + format_string, *args)


class WebServer:
    def __init__(
        self,
        host: str,
        port: int,
        static_directory: Path,
        status_provider: StatusProvider,
    ) -> None:
        handler = type(
            "DashboardHandler",
            (_DashboardHandler,),
            {
                "static_directory": static_directory,
                "status_provider": staticmethod(status_provider),
            },
        )
        self._server = ThreadingHTTPServer((host, port), handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="openr4d10-web",
            daemon=True,
        )

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._server.server_address[:2]
        return str(host), int(port)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=3)
