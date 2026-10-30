from pathlib import Path
import json
import tempfile
import unittest
from urllib.request import urlopen

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
            finally:
                server.stop()


if __name__ == "__main__":
    unittest.main()
