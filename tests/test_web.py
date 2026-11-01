from pathlib import Path
from html import unescape
from http.client import HTTPConnection
import json
import re
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
        hoseline = web_root.joinpath("hoseline.js").read_text(encoding="utf-8")
        stylesheet = web_root.joinpath("app.css").read_text(encoding="utf-8")
        translations = json.loads(
            web_root.joinpath("i18n.json").read_text(encoding="utf-8")
        )
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
        self.assertIn("const RECORDER_SCREEN_REFRESH_MS = 100", script)
        self.assertIn('latestDeviceState?.service === "REC"', script)
        self.assertIn("if (deviceScreenPending) return", script)
        self.assertIn("const rotaryInputQueue = []", script)
        self.assertIn("last.request.steps + request.steps", script)
        self.assertIn("Math.max(-10, Math.min(10, combined))", script)
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
            "Backspace",
        ):
            self.assertIn(key_code, script)
        self.assertNotIn("KeyQ", script)
        self.assertIn('control: "ptt", active', script)
        self.assertIn("isEditableTarget", script)
        self.assertIn("deviceMenuOwnsArrowKey", script)
        self.assertIn('latestDeviceState?.menu_open === true', script)
        self.assertIn('KeyW: { control: "left_outer", steps: 1 }', script)
        self.assertIn('KeyA: { control: "left_inner", steps: -1 }', script)
        self.assertIn('ArrowUp: { control: "right_outer", steps: -1 }', script)
        self.assertIn('ArrowDown: { control: "right_outer", steps: 1 }', script)
        self.assertIn("keyboardDeviceRequest", script)
        self.assertNotIn("steps: -request.steps", script)
        self.assertIn('ArrowLeft: { control: "right_inner", steps: -1 }', script)
        self.assertIn('Space: { control: "home" }', script)
        self.assertIn('Enter: { control: "right_press" }', script)
        self.assertIn('image.src = scene.artwork;\n      image.alt = "";\n      image.loading = "eager"', script)
        self.assertIn('id="ambient-layer-list"', html)
        self.assertIn('id="ambient-favorite-form"', html)
        self.assertIn('"ambient_layer_set"', script)
        self.assertIn('"ambient_favorite_save"', script)
        self.assertIn('data-tab="brandmeister"', html)
        self.assertIn('id="brandmeister-talkgroup"', html)
        self.assertIn("https://hose.brandmeister.network/", html)
        self.assertIn("wss://hose.brandmeister.network/spotter/", hoseline)
        self.assertIn("new WebSocket(ENDPOINT, PROTOCOL)", hoseline)
        self.assertIn("muLawSample", hoseline)
        self.assertIn("groupMessage(1, talkgroups)", hoseline)
        self.assertIn('id="brandmeister-talkgroup-list"', html)
        self.assertIn("BRANDMEISTER_FLAGS", script)
        self.assertIn("talkgroup <= 90", script)
        self.assertIn("chooseBrandmeisterReplacement", script)
        self.assertIn("replace_talkgroup: replacement", script)
        self.assertIn("Six talkgroups are active. Which one should be replaced?", translations["messages"])
        self.assertIn('"station_move"', script)
        self.assertIn('"station_delete"', script)
        self.assertIn("Playback volume {{volume}}%", script)
        self.assertIn("payload.selected_preset", script)
        self.assertIn('window.addEventListener("blur"', script)
        self.assertIn('document.addEventListener("visibilitychange"', script)
        self.assertIn('id="ptt-button"', html)
        self.assertIn(
            "System and display online. Power telemetry is not configured yet.",
            script,
        )
        self.assertIn("Only verified PiSugar telemetry is still missing.", script)
        self.assertIn("PiSugar present", script)
        self.assertIn("Battery operation confirmed · telemetry not configured", script)
        self.assertNotIn("PiSugar-Adapter fehlt", script)
        self.assertIn('id="system-update"', html)
        self.assertIn('action: "system_update", confirmed: true', script)
        self.assertIn("window.confirm", script)
        self.assertIn("renderUpdate", script)
        self.assertIn('id="wifi-repair-form"', html)
        self.assertIn('action: "wifi_repair"', script)
        self.assertIn("replace_existing: replaceExisting", script)
        self.assertIn('request.passphrase = ""', script)
        self.assertIn("renderWifiRepair", script)
        self.assertIn('id="display-brightness"', html)
        self.assertIn('type="range" min="0" max="100"', html)
        self.assertIn('action: "display_brightness"', script)
        self.assertIn("display_brightness_percent", script)
        self.assertIn("Display brightness {{brightness}}% saved permanently.", script)
        self.assertIn('id="display-accent-color" type="color"', html)
        self.assertIn('action: "display_appearance"', script)
        self.assertNotIn("display-screen-border", html)
        self.assertNotIn("screen_border_enabled", script)
        self.assertIn("border-radius: 43px", stylesheet)
        for tab in ("radio", "podcasts", "mediathek", "weather", "media", "device", "system", "services"):
            self.assertIn(f'data-tab="{tab}"', html)
            self.assertIn(f'data-tab-panel="{tab}"', html)
        self.assertIn('id="device-screen-preview"', html)
        self.assertIn("/api/device-screen.png", html)
        self.assertIn("station-row-artwork", script)
        self.assertIn('play.classList.add("library-play")', script)
        self.assertIn(".library-actions button.library-play", stylesheet)
        self.assertNotIn("radio-preset-grid", html)
        self.assertNotIn("radio-preset-grid", script)
        self.assertNotIn("radio-preset-card", stylesheet)
        self.assertIn('id="station-search" type="search"', html)
        self.assertIn('id="station-language"', html)
        self.assertIn('id="station-category"', html)
        self.assertNotIn('id="media-source"', html)
        self.assertNotIn('data-i18n="Direct audio source"', html)
        self.assertIn('data-action="pause"', html)
        self.assertIn('data-action="stop"', html)
        self.assertIn('data-action="radio_keep_current"', html)
        self.assertIn('id="radio-continuous"', html)
        self.assertIn('id="station-active-tab"', html)
        self.assertIn('id="station-catalog-tab"', html)
        self.assertIn('id="station-active-panel"', html)
        self.assertIn('id="station-catalog-panel"', html)
        self.assertIn('id="station-catalog-list"', html)
        self.assertIn('"preset_save"', script)
        self.assertIn('function selectStationLibraryView(view)', script)
        self.assertIn('selectStationLibraryView("active")', script)
        self.assertIn('.station-library-tabs button[aria-selected="true"]', stylesheet)
        self.assertIn('border-color: var(--cyan);', stylesheet)
        self.assertIn('color: var(--text);', stylesheet)
        self.assertIn('box-shadow: inset 0 -3px 0 var(--cyan);', stylesheet)
        station_tab_rule = re.search(
            r'\.station-library-tabs button\[aria-selected="true"\]\s*\{([^}]+)\}',
            stylesheet,
        )
        self.assertIsNotNone(station_tab_rule)
        self.assertNotIn('var(--accent)', station_tab_rule.group(1))
        self.assertNotRegex(
            html,
            r'id="station-(?:active|catalog)-tab"[^>]*\shidden(?:\s|>)',
        )
        self.assertIn('id="podcast-subscribe-form"', html)
        self.assertIn('id="podcast-subscription-list"', html)
        self.assertIn('id="podcast-episode-list"', html)
        self.assertIn('"podcast_subscribe"', script)
        self.assertIn('"podcast_play"', script)
        self.assertIn('id="mediathek-search-form"', html)
        self.assertIn('id="mediathek-result-list"', html)
        self.assertIn('id="mediathek-provider"', html)
        self.assertIn('id="mediathek-collections"', html)
        self.assertIn('id="mediathek-video"', html)
        self.assertIn("/api/mediathek-video/", script)
        self.assertIn('t("Watch in browser")', script)
        self.assertIn('t("Audio on device")', script)
        self.assertIn('t("Video on device")', script)
        self.assertIn('mode: "audio"', script)
        self.assertIn('mode: "video"', script)
        self.assertIn('"mediathek_search"', script)
        self.assertIn('"mediathek_play"', script)
        self.assertIn('id="service-search" type="search"', html)
        self.assertIn('id="service-list"', html)
        self.assertIn("serviceMatchesSearch", script)
        self.assertIn("JSON.stringify(service)", script)
        self.assertNotIn('id="service-grid"', html)
        self.assertNotIn("service-card", stylesheet)
        self.assertIn('id="weather-image"', html)
        self.assertIn('id="weather-channel-list"', html)
        self.assertIn(
            ".tab-title, #hero-title { font-size: clamp(1.175rem, 3vw, 2.5rem);",
            stylesheet,
        )
        self.assertGreaterEqual(html.count('class="tab-title"'), 5)
        self.assertIn('"weather_channel_move"', script)
        self.assertIn('"service_move"', script)
        self.assertIn('id="weather-provider"', html)
        self.assertIn('setText("weather-provider", selected?.provider, "DWD")', script)
        self.assertIn('data-i18n="DWD WEATHER"', html)
        self.assertIn('id="language-select"', html)
        self.assertIn('action: "display_language"', script)
        self.assertIn("settings.language", script)
        self.assertIn("Device language saved.", script)
        for locale in ("en", "de", "pl", "fr", "es"):
            self.assertIn(f'<option value="{locale}">', html)
        self.assertNotIn("Geräteansicht", html)
        self.assertNotIn("device-screen-title", html)
        self.assertIn('data-i18n="LIVE DISPLAY"', html)
        self.assertIn('href="/service-controls.svg"', html)
        self.assertIn('data-i18n="CONTROL GUIDE"', html)
        self.assertTrue(web_root.joinpath("controls-overview.svg").is_file())
        self.assertTrue(web_root.joinpath("service-controls.svg").is_file())
        hardware_guide = web_root.joinpath("controls-overview.svg").read_text(
            encoding="utf-8"
        )
        self.assertIn("kein erfundenes Gehäuse", hardware_guide)
        self.assertIn("GEPLANTE BEDIENELEMENTE · NOCH NICHT MONTIERT", hardware_guide)
        self.assertIn("VORNE · HEUTE VORHANDEN", hardware_guide)
        self.assertIn("RÜCKSEITE DES WHISPLAY · HEUTE VORHANDEN", hardware_guide)
        self.assertIn("Whisplay HAT", hardware_guide)
        self.assertIn("Raspberry Pi Zero 2 W", hardware_guide)
        self.assertIn("PiSugar 3 + Akku", hardware_guide)
        service_guide = web_root.joinpath("service-controls.svg").read_text(
            encoding="utf-8"
        )
        self.assertIn('fill="#fff"', service_guide)
        self.assertIn("Alle 16 aktuell aktivierten Dienste", service_guide)
        self.assertIn("13 bereit · 3 mit Konfigurationsbedarf", service_guide)
        self.assertIn("Funktionen am Gerät", service_guide)
        self.assertIn("Keine native", service_guide)
        self.assertEqual(service_guide.count("OpenR4d10 · Whisplay-Front"), 16)
        self.assertEqual(translations["locales"], ["en", "de", "pl", "fr", "es"])
        messages = translations["messages"]
        html_keys = {
            unescape(match.group(1))
            for match in re.finditer(
                r'data-i18n(?:-placeholder|-aria-label|-alt)?="([^"]+)"', html
            )
        }
        script_keys = {
            match.group(1)
            for match in re.finditer(
                r'(?<![A-Za-z])t\("((?:[^"\\]|\\.)*)"', script
            )
        }
        self.assertFalse((html_keys | script_keys) - set(messages))
        placeholder_pattern = re.compile(r"\{\{[a-z_]+\}\}")
        for key, values in messages.items():
            self.assertEqual(len(values), 5, key)
            self.assertTrue(all(isinstance(value, str) and value for value in values), key)
            placeholders = sorted(placeholder_pattern.findall(key))
            for value in values:
                self.assertEqual(
                    sorted(placeholder_pattern.findall(value)), placeholders, key
                )
        self.assertNotIn("`${station.name} · ${station.source}`", script)

    def test_dashboard_and_status_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            static = Path(raw)
            static.joinpath("index.html").write_text(
                "<!doctype html><title>Test dashboard</title>", encoding="utf-8"
            )
            static.joinpath("app.css").write_text("", encoding="utf-8")
            static.joinpath("app.js").write_text("", encoding="utf-8")
            static.joinpath("i18n.json").write_text(
                '{"locales":["en"],"messages":{}}', encoding="utf-8"
            )
            static.joinpath("controls-overview.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8"
            )
            server = WebServer(
                "127.0.0.1",
                0,
                static,
                lambda: {"service": "online", "version": "test"},
                lambda request: {"accepted": request["action"]},
                lambda name: ("image/jpeg", name.encode("ascii"))
                if name in {
                    "camera-1.jpg",
                    "radio-art/swr3",
                    "ambient-art/cafe",
                    "weather-dwd-deutschland-20261031T060000Z.jpg",
                }
                else None,
                lambda: b"native-png",
                lambda name: "https://media.example/program.mp4"
                if name == "mediathek-video/0123456789abcdef01234567"
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
                with urlopen(f"http://{host}:{port}/i18n.json", timeout=2) as response:
                    self.assertEqual(
                        response.headers["Content-Type"],
                        "application/json; charset=utf-8",
                    )
                    self.assertEqual(json.loads(response.read())["locales"], ["en"])
                with urlopen(f"http://{host}:{port}/controls-overview.svg", timeout=2) as response:
                    self.assertEqual(response.headers["Content-Type"], "image/svg+xml")
                    self.assertIn(b"<svg", response.read())
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
                with urlopen(f"http://{host}:{port}/api/ambient-art/cafe", timeout=2) as response:
                    self.assertEqual(response.headers["Content-Type"], "image/jpeg")
                    self.assertEqual(response.read(), b"ambient-art/cafe")
                weather_name = "weather-dwd-deutschland-20261031T060000Z.jpg"
                with urlopen(f"http://{host}:{port}/api/weather-frame/{weather_name}", timeout=2) as response:
                    self.assertEqual(response.headers["Content-Type"], "image/jpeg")
                    self.assertEqual(response.read(), weather_name.encode("ascii"))
                with urlopen(f"http://{host}:{port}/api/device-screen.png", timeout=2) as response:
                    self.assertEqual(response.headers["Content-Type"], "image/png")
                    self.assertEqual(response.read(), b"native-png")
                connection = HTTPConnection(host, port, timeout=2)
                try:
                    connection.request("GET", "/api/mediathek-video/0123456789abcdef01234567")
                    redirect = connection.getresponse()
                    self.assertEqual(redirect.status, 302)
                    self.assertEqual(
                        redirect.headers["Location"],
                        "https://media.example/program.mp4",
                    )
                    self.assertEqual(redirect.headers["Cache-Control"], "no-store")
                    redirect.read()
                finally:
                    connection.close()
            finally:
                server.stop()

    def test_control_connection_stays_open_for_low_latency_repeats(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            static = Path(raw)
            static.joinpath("index.html").write_text("ok", encoding="utf-8")
            server = WebServer(
                "127.0.0.1",
                0,
                static,
                lambda: {"service": "online"},
                lambda request: {"accepted": request["steps"]},
            )
            server.start()
            connection = None
            try:
                host, port = server.address
                connection = HTTPConnection(host, port, timeout=2)
                headers = {"Content-Type": "application/json"}
                connection.request(
                    "POST",
                    "/api/control",
                    body=b'{"action":"device_input","steps":1}',
                    headers=headers,
                )
                first = connection.getresponse()
                self.assertEqual(first.version, 11)
                self.assertEqual(json.loads(first.read())["accepted"], 1)
                first_socket = connection.sock
                self.assertIsNotNone(first_socket)

                connection.request(
                    "POST",
                    "/api/control",
                    body=b'{"action":"device_input","steps":2}',
                    headers=headers,
                )
                second = connection.getresponse()
                self.assertEqual(second.version, 11)
                self.assertEqual(json.loads(second.read())["accepted"], 2)
                self.assertIs(connection.sock, first_socket)
            finally:
                if connection is not None:
                    connection.close()
                server.stop()


if __name__ == "__main__":
    unittest.main()
