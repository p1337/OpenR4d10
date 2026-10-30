from pathlib import Path
import json
import tempfile
import unittest
from urllib.request import urlopen
from urllib.request import Request

from openr4d10.web import WebServer


class WebTests(unittest.TestCase):
    def test_checked_in_dashboard_exposes_virtual_encoder_controls(self) -> None:
        web_root = Path(__file__).resolve().parents[1] / "web"
        html = web_root.joinpath("index.html").read_text(encoding="utf-8")
        script = web_root.joinpath("app.js").read_text(encoding="utf-8")
        for control in (
            "left_outer",
            "left_inner",
            "right_outer",
            "right_inner",
            "left_press",
            "right_press",
        ):
            self.assertIn(f'data-device-control="{control}"', html)
        self.assertIn('action: "device_input"', script)
        for key_code in (
            "KeyW",
            "KeyS",
            "KeyA",
            "KeyD",
            "ArrowUp",
            "ArrowDown",
            "ArrowLeft",
            "ArrowRight",
            "Space",
            "Enter",
            "KeyQ",
        ):
            self.assertIn(key_code, script)
        self.assertIn('control: "ptt", active', script)
        self.assertIn("isEditableTarget", script)
        self.assertIn('KeyW: { control: "left_outer", steps: 1 }', script)
        self.assertIn('KeyA: { control: "left_inner", steps: -1 }', script)
        self.assertIn('ArrowUp: { control: "right_outer", steps: 1 }', script)
        self.assertIn('ArrowLeft: { control: "right_inner", steps: -1 }', script)
        self.assertIn('Space: { control: "left_press" }', script)
        self.assertIn('Enter: { control: "right_press" }', script)
        self.assertIn('"station_move"', script)
        self.assertIn('"station_delete"', script)
        self.assertIn("Wiedergabelautstärke", script)
        self.assertIn("payload.selected_preset", script)
        self.assertIn('window.addEventListener("blur"', script)
        self.assertIn('document.addEventListener("visibilitychange"', script)
        self.assertIn('id="ptt-button"', html)
        self.assertIn("System und Display online. Energieanzeige noch offen.", script)
        self.assertIn("Nur die verifizierte PiSugar-Telemetrie fehlt noch.", script)
        self.assertIn("PiSugar vorhanden", script)
        self.assertIn("Akkubetrieb bestätigt · Messwerte noch offen", script)
        self.assertNotIn("PiSugar-Adapter fehlt", script)
        self.assertIn('id="system-update"', html)
        self.assertIn('action: "system_update", confirmed: true', script)
        self.assertIn("window.confirm", script)
        self.assertIn("renderUpdate", script)
        self.assertIn('id="display-brightness"', html)
        self.assertIn('type="range" min="0" max="100"', html)
        self.assertIn('action: "display_brightness"', script)
        self.assertIn("display_brightness_percent", script)
        self.assertIn("dauerhaft gespeichert", script)

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
