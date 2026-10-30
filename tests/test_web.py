from pathlib import Path
import json
import tempfile
import unittest
from urllib.request import urlopen
from urllib.request import Request

from openr4d10.web import WebServer


class WebTests(unittest.TestCase):
    def test_dashboard_and_status_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            static = Path(raw)
            static.joinpath("index.html").write_text(
                "<!doctype html><title>Test dashboard</title>", encoding="utf-8"
            )
            static.joinpath("app.css").write_text("", encoding="utf-8")
            static.joinpath("app.js").write_text("", encoding="utf-8")
            server = WebServer(
                "127.0.0.1",
                0,
                static,
                lambda: {"service": "online", "version": "test"},
                lambda request: {"accepted": request["action"]},
                lambda name: ("image/jpeg", name.encode("ascii"))
                if name in {"camera-1.jpg", "radio-art/swr3"}
                else None,
            )
            server.start()
            try:
                host, port = server.address
                with urlopen(f"http://{host}:{port}/", timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn(b"Test dashboard", response.read())
                    self.assertEqual(response.headers["X-Frame-Options"], "DENY")
                with urlopen(
                    f"http://{host}:{port}/api/status", timeout=2
                ) as response:
                    payload = json.loads(response.read())
                    self.assertEqual(payload["service"], "online")
                request = Request(
                    f"http://{host}:{port}/api/control",
                    data=b'{"action":"pause"}',
                    headers={
                        "Content-Type": "application/json",
                        "Origin": f"http://{host}:{port}",
                    },
                    method="POST",
                )
                with urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read())
                    self.assertEqual(payload["accepted"], "pause")
                with urlopen(f"http://{host}:{port}/api/camera/1", timeout=2) as response:
                    self.assertEqual(response.headers["Content-Type"], "image/jpeg")
                    self.assertEqual(response.read(), b"camera-1.jpg")
                with urlopen(f"http://{host}:{port}/api/radio-art/swr3", timeout=2) as response:
                    self.assertEqual(response.headers["Content-Type"], "image/jpeg")
                    self.assertEqual(response.read(), b"radio-art/swr3")
            finally:
                server.stop()


if __name__ == "__main__":
    unittest.main()
