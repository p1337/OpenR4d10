"""Small, read-only HTTP server for the local OpenR4d10 dashboard."""

from __future__ import annotations

from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import re
import socket
import threading
from typing import Any
from urllib.parse import urlsplit

LOG = logging.getLogger(__name__)

StatusProvider = Callable[[], dict[str, Any]]
ControlProvider = Callable[[dict[str, object]], dict[str, object]]
ContentProvider = Callable[[str], tuple[str, bytes] | None]
ScreenProvider = Callable[[], bytes | None]
RedirectProvider = Callable[[str], str | None]

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/hoseline.js": ("hoseline.js", "text/javascript; charset=utf-8"),
    "/i18n.json": ("i18n.json", "application/json; charset=utf-8"),
}


class _DashboardHandler(BaseHTTPRequestHandler):
    static_directory: Path
    status_provider: StatusProvider
    control_provider: ControlProvider | None = None
    content_provider: ContentProvider | None = None
    screen_provider: ScreenProvider | None = None
    redirect_provider: RedirectProvider | None = None
    server_version = "OpenR4d10"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def _headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self' wss://hose.brandmeister.network; img-src 'self'; "
            "media-src 'self' https:; style-src 'self'; script-src 'self'; frame-ancestors 'none'",
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

    def _serve_control(self) -> None:
        if self.control_provider is None:
            self._send(503, "application/json; charset=utf-8", b'{"error":"control unavailable"}')
            return
        content_type = self.headers.get_content_type()
        if content_type != "application/json":
            self._send(415, "application/json; charset=utf-8", b'{"error":"application/json required"}')
            return
        origin = self.headers.get("Origin")
        host = self.headers.get("Host")
        if origin and (not host or origin not in {f"http://{host}", f"https://{host}"}):
            self._send(403, "application/json; charset=utf-8", b'{"error":"origin rejected"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if not 1 <= length <= 4096:
            self._send(400, "application/json; charset=utf-8", b'{"error":"invalid request size"}')
            return
        try:
            request = json.loads(self.rfile.read(length))
            if not isinstance(request, dict):
                raise ValueError("JSON object required")
            response = self.control_provider(request)
        except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
            payload = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self._send(400, "application/json; charset=utf-8", payload)
            return
        payload = json.dumps(response, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self._send(200, "application/json; charset=utf-8", payload)

    def _serve_content(self, name: str) -> None:
        item = self.content_provider(name) if self.content_provider is not None else None
        if item is None:
            self._send(404, "text/plain; charset=utf-8", b"Not found\n")
            return
        content_type, payload = item
        self._send(200, content_type, payload)

    def _serve_screen(self) -> None:
        payload = self.screen_provider() if self.screen_provider is not None else None
        if payload is None:
            self._send(404, "text/plain; charset=utf-8", b"Native screen unavailable\n")
            return
        self._send(200, "image/png", payload)

    def _serve_redirect(self, name: str) -> None:
        target = self.redirect_provider(name) if self.redirect_provider is not None else None
        if target is None:
            self._send(404, "text/plain; charset=utf-8", b"Not found\n")
            return
        self.send_response(302)
        self.send_header("Location", target)
        self.send_header("Content-Length", "0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        path = urlsplit(self.path).path
        if path == "/api/status":
            self._serve_status()
        elif path == "/api/brandmeister-talkgroups":
            self._serve_content("brandmeister-talkgroups.json")
        elif path == "/api/device-screen.png":
            self._serve_screen()
        elif re.fullmatch(r"/api/camera/\d{1,7}", path):
            self._serve_content(f"camera-{path.rsplit('/', 1)[-1]}.jpg")
        elif re.fullmatch(r"/api/radio-art/[a-z][a-z0-9_]{1,63}", path):
            self._serve_content(f"radio-art/{path.rsplit('/', 1)[-1]}")
        elif re.fullmatch(r"/api/ambient-art/[a-z][a-z0-9_]{1,63}", path):
            self._serve_content(f"ambient-art/{path.rsplit('/', 1)[-1]}")
        elif re.fullmatch(r"/api/media-cover/\d{1,10}", path):
            self._serve_content(f"media-cover/{path.rsplit('/', 1)[-1]}")
        elif re.fullmatch(r"/api/mediathek-video/[a-f0-9]{24}", path):
            self._serve_redirect(f"mediathek-video/{path.rsplit('/', 1)[-1]}")
        elif re.fullmatch(
            r"/api/weather-frame/weather-[a-z][a-z0-9_-]{1,63}-\d{8}T\d{6}Z\.jpg",
            path,
        ):
            self._serve_content(path.rsplit("/", 1)[-1])
        elif path == "/healthz":
            self._send(200, "text/plain; charset=utf-8", b"ok\n")
        else:
            self._serve_static(path)

    def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        if urlsplit(self.path).path == "/api/control":
            self._serve_control()
        else:
            self._send(404, "text/plain; charset=utf-8", b"Not found\n")

    def log_message(self, format_string: str, *args: object) -> None:
        LOG.debug("Web request: " + format_string, *args)


class _LowLatencyHTTPServer(ThreadingHTTPServer):
    """Keep small control responses off connection/setup and Nagle delays."""

    request_queue_size = 16

    def get_request(self) -> tuple[socket.socket, object]:
        request, address = super().get_request()
        request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return request, address


class WebServer:
    def __init__(
        self,
        host: str,
        port: int,
        static_directory: Path,
        status_provider: StatusProvider,
        control_provider: ControlProvider | None = None,
        content_provider: ContentProvider | None = None,
        screen_provider: ScreenProvider | None = None,
        redirect_provider: RedirectProvider | None = None,
    ) -> None:
        handler = type(
            "DashboardHandler",
            (_DashboardHandler,),
            {
                "static_directory": static_directory,
                "status_provider": staticmethod(status_provider),
                "control_provider": staticmethod(control_provider) if control_provider else None,
                "content_provider": staticmethod(content_provider) if content_provider else None,
                "screen_provider": staticmethod(screen_provider) if screen_provider else None,
                "redirect_provider": staticmethod(redirect_provider) if redirect_provider else None,
            },
        )
        self._server = _LowLatencyHTTPServer((host, port), handler)
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
