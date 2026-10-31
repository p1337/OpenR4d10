from pathlib import Path
import json
import tempfile
import unittest

from openr4d10.adapters import FileDisplay, SystemTelemetry, UnconfiguredTelemetry
from openr4d10.app import OpenR4d10App
from openr4d10.config import AppConfig
from openr4d10.input_events import Control


class AppTests(unittest.TestCase):
    def test_display_brightness_restores_and_persists_through_app_control(self) -> None:
        class BrightnessDisplay:
            def __init__(self) -> None:
                self.values = []

            def render(self, _frame) -> None:
                pass

            def set_brightness(self, value):
                self.values.append(value)

            def snapshot(self):
                return {"brightness_percent": self.values[-1]}

        class Services:
            active_service = "system"

            def __init__(self) -> None:
                self.value = 65

            def display_brightness(self):
                return self.value

            def set_display_brightness(self, value):
                self.value = value

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            display = BrightnessDisplay()
            services = Services()
            app = OpenR4d10App(
                AppConfig(
                    log_level="INFO",
                    refresh_interval_seconds=1.0,
                    title="OpenR4d10 Test",
                    boot_manifest=root / "missing.toml",
                    boot_enabled=False,
                    runtime_directory=root,
                    state_directory=root,
                ),
                display=display,
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=services,  # type: ignore[arg-type]
            )
            self.assertEqual(display.values, [65])
            result = app.control(
                {"action": "display_brightness", "brightness_percent": 35}
            )
            self.assertEqual(display.values, [65, 35])
            self.assertEqual(services.value, 35)
            self.assertEqual(
                result["settings"]["display_brightness_percent"],
                35,
            )
            for invalid in (-1, 101, True, 35.0):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    app.control(
                        {
                            "action": "display_brightness",
                            "brightness_percent": invalid,
                        }
                    )

    def test_confirmed_system_update_uses_the_fixed_runtime_request(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            app = OpenR4d10App(
                AppConfig(
                    log_level="INFO",
                    refresh_interval_seconds=1.0,
                    title="OpenR4d10 Test",
                    boot_manifest=root / "missing.toml",
                    boot_enabled=False,
                    runtime_directory=root / "run",
                    state_directory=root / "state",
                ),
                display=FileDisplay(root / "frame.json"),
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
            )

            result = app.control(
                {"action": "system_update", "confirmed": True}
            )

            self.assertEqual(result["update"]["state"], "queued")
            self.assertEqual(
                (root / "run" / "update.request").read_bytes(),
                b"update\n",
            )

    def test_confirmed_wifi_repair_uses_only_the_fixed_runtime_request(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            app = OpenR4d10App(
                AppConfig(
                    log_level="INFO",
                    refresh_interval_seconds=1.0,
                    title="OpenR4d10 Test",
                    boot_manifest=root / "missing.toml",
                    boot_enabled=False,
                    runtime_directory=root / "run",
                    state_directory=root / "state",
                ),
                display=FileDisplay(root / "frame.json"),
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
            )

            result = app.control(
                {
                    "action": "wifi_repair",
                    "ssid": "Private WLAN",
                    "passphrase": "valid-passphrase",
                    "replace_existing": True,
                    "confirmed": True,
                }
            )

            self.assertEqual(result["wifi_repair"]["state"], "queued")
            self.assertNotIn("passphrase", result["wifi_repair"])
            request = json.loads(
                (root / "run" / "wifi-repair.request").read_text(encoding="utf-8")
            )
            self.assertEqual(request["ssid"], "Private WLAN")
            self.assertEqual(request["passphrase"], "valid-passphrase")

    def test_virtual_device_input_is_bounded_and_uses_display_adapter(self) -> None:
        class InputDisplay:
            def __init__(self) -> None:
                self.events = []

            def render(self, _frame) -> None:
                pass

            def apply_input(self, event):
                self.events.append(event)
                return {"volume": 37, "service": "SYSTEM"}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            display = InputDisplay()
            app = OpenR4d10App(
                AppConfig(
                    log_level="INFO",
                    refresh_interval_seconds=1.0,
                    title="OpenR4d10 Test",
                    boot_manifest=root / "missing.toml",
                    boot_enabled=False,
                    runtime_directory=root,
                    state_directory=root,
                ),
                display=display,
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
            )
            result = app.control(
                {"action": "device_input", "control": "left_outer", "steps": 1}
            )
            self.assertEqual(result["device_ui"]["volume"], 37)
            self.assertEqual(display.events[0].control, Control.LEFT_OUTER)
            ptt = app.control(
                {"action": "device_input", "control": "ptt", "active": True}
            )
            self.assertTrue(ptt["accepted"]["active"])
            self.assertEqual(display.events[1].control, Control.PTT)
            self.assertTrue(display.events[1].active)
            for request in (
                {"action": "device_input", "control": "missing", "steps": 1},
                {"action": "device_input", "control": "left_outer", "steps": 0},
                {"action": "device_input", "control": "left_outer", "steps": 11},
                {
                    "action": "device_input",
                    "control": "left_outer",
                    "steps": 1,
                    "held_seconds": 2,
                },
                {
                    "action": "device_input",
                    "control": "right_press",
                    "held_seconds": 6,
                },
                {"action": "device_input", "control": "ptt"},
                {"action": "device_input", "control": "ptt", "active": 1},
                {
                    "action": "device_input",
                    "control": "left_press",
                    "active": True,
                },
            ):
                with self.subTest(request=request), self.assertRaises(ValueError):
                    app.control(request)

    def test_right_short_press_toggles_real_media_before_display_state(self) -> None:
        class InputDisplay:
            def __init__(self) -> None:
                self.events = []

            def render(self, _frame) -> None:
                pass

            def apply_input(self, event):
                self.events.append(event)
                return {"playing": False, "right_action": "PLAY"}

        class Services:
            def __init__(self) -> None:
                self.requests = []
                self.active_service = "webradio"

            def control(self, request):
                self.requests.append(request)
                return {
                    "playback": {"state": "paused", "paused": True},
                    "recording": {"state": "stopped"},
                    "selected_preset": None,
                }

            def receiver_overlay(self, _view_service=None):
                return {
                    "service": "RADIO",
                    "station": "SWR3",
                    "title": "SWR3",
                    "playing": False,
                    "volume": 36,
                    "channel": 1,
                    "preset_id": "swr3",
                }

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            display = InputDisplay()
            services = Services()
            app = OpenR4d10App(
                AppConfig(
                    log_level="INFO",
                    refresh_interval_seconds=1.0,
                    title="OpenR4d10 Test",
                    boot_manifest=root / "missing.toml",
                    boot_enabled=False,
                    runtime_directory=root,
                    state_directory=root,
                ),
                display=display,
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=services,
            )

            paused = app.control(
                {"action": "device_input", "control": "right_press"}
            )
            menu = app.control(
                {
                    "action": "device_input",
                    "control": "right_press",
                    "held_seconds": 2,
                }
            )

        self.assertEqual(services.requests, [{"action": "radio_toggle"}])
        self.assertEqual(paused["playback"]["state"], "paused")
        self.assertEqual(menu["device_ui"]["right_action"], "PLAY")
        self.assertEqual(len(display.events), 2)

    def test_volume_and_channel_inputs_route_to_real_media_controls(self) -> None:
        class InputDisplay:
            def render(self, _frame) -> None:
                pass

            def apply_input(self, event):
                return {"control": event.control.value}

        class Services:
            def __init__(self) -> None:
                self.requests = []
                self.active_service = "webradio"

            def control(self, request):
                self.requests.append(request)
                selected = (
                    {"preset_id": "sunshine_live", "name": "sunshine live", "channel": 2}
                    if request["action"] == "preset_step"
                    else None
                )
                return {
                    "playback": {"state": "playing", "paused": False, "volume": 46},
                    "recording": {"state": "stopped"},
                    "selected_preset": selected,
                }

            def receiver_overlay(self, _view_service=None):
                return {}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            services = Services()
            app = OpenR4d10App(
                AppConfig(
                    log_level="INFO",
                    refresh_interval_seconds=1.0,
                    title="OpenR4d10 Test",
                    boot_manifest=root / "missing.toml",
                    boot_enabled=False,
                    runtime_directory=root,
                    state_directory=root,
                ),
                display=InputDisplay(),
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=services,
            )

            volume = app.control(
                {"action": "device_input", "control": "left_outer", "steps": 1}
            )
            station = app.control(
                {"action": "device_input", "control": "right_outer", "steps": 1}
            )

        self.assertEqual(
            services.requests,
            [
                {"action": "volume_step", "steps": 1},
                {"action": "preset_step", "steps": 1},
            ],
        )
        self.assertEqual(volume["playback"]["volume"], 46)
        self.assertEqual(station["selected_preset"]["name"], "sunshine live")

    def test_open_menu_owns_channel_and_enter_without_media_side_effects(self) -> None:
        class InputDisplay:
            def __init__(self) -> None:
                self.events = []

            def render(self, _frame) -> None:
                pass

            def snapshot(self):
                return {"menu_open": True, "service": "RADIO"}

            def apply_input(self, event):
                self.events.append(event)
                return self.snapshot()

        class Services:
            active_service = "webradio"

            def __init__(self) -> None:
                self.requests = []

            def control(self, request):
                self.requests.append(request)
                raise AssertionError("menu input reached media services")

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            display = InputDisplay()
            services = Services()
            app = OpenR4d10App(
                AppConfig(
                    log_level="INFO",
                    refresh_interval_seconds=1.0,
                    title="OpenR4d10 Test",
                    boot_manifest=root / "missing.toml",
                    boot_enabled=False,
                    runtime_directory=root,
                    state_directory=root,
                ),
                display=display,
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=services,  # type: ignore[arg-type]
            )
            app.control(
                {"action": "device_input", "control": "right_outer", "steps": 1}
            )
            app.control({"action": "device_input", "control": "right_press"})

        self.assertEqual(services.requests, [])
        self.assertEqual(
            [event.control for event in display.events],
            [Control.RIGHT_OUTER, Control.RIGHT_PRESS],
        )

    def test_weather_enter_and_channel_axis_use_weather_controls(self) -> None:
        class InputDisplay:
            def render(self, _frame) -> None:
                pass

            def snapshot(self):
                return {"service": "WEATHER", "menu_open": False}

            def apply_input(self, _event):
                return self.snapshot()

        class Services:
            active_service = "system"

            def __init__(self):
                self.requests = []

            def control(self, request):
                self.requests.append(request)
                return {"view_service": "weather", "channel_id": 2}

            def receiver_overlay(self, _view_service=None):
                return {"service": "WEATHER", "station": "Europa", "channel": 2}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            services = Services()
            app = OpenR4d10App(
                AppConfig(
                    log_level="INFO",
                    refresh_interval_seconds=1.0,
                    title="OpenR4d10 Test",
                    boot_manifest=root / "missing.toml",
                    boot_enabled=False,
                    runtime_directory=root,
                    state_directory=root,
                ),
                display=InputDisplay(),
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=services,
            )
            opened = app.control({"action": "device_input", "control": "right_press"})
            stepped = app.control(
                {"action": "device_input", "control": "right_outer", "steps": 1}
            )

        self.assertEqual(
            services.requests,
            [{"action": "weather_open"}, {"action": "weather_step", "steps": 1}],
        )
        self.assertEqual(opened["weather_channel_id"], 2)
        self.assertEqual(stepped["weather_channel_id"], 2)

    def test_service_navigation_survives_refresh_while_radio_keeps_playing(self) -> None:
        class InputDisplay:
            def __init__(self) -> None:
                self.service = "RADIO"
                self.playing = True

            def render(self, frame) -> None:
                receiver = frame.fields.get("receiver", {})
                self.service = str(receiver.get("service") or self.service)
                self.playing = bool(receiver.get("playing", self.playing))

            def snapshot(self):
                return {
                    "service": self.service,
                    "playing": self.playing,
                    "menu_open": False,
                }

            def apply_input(self, event):
                if event.control == Control.RIGHT_INNER:
                    self.service = "WEATHER"
                return self.snapshot()

        class Services:
            active_service = "webradio"

            def __init__(self) -> None:
                self.requests = []
                self.overlay_views = []

            def control(self, request):
                self.requests.append(request)
                raise AssertionError("view navigation reached the audio player")

            def receiver_overlay(self, view_service=None):
                self.overlay_views.append(view_service)
                return {
                    "service": view_service,
                    "station": "Regenradar Deutschland",
                    "title": "DWD",
                    "playing": True,
                }

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            display = InputDisplay()
            services = Services()
            app = OpenR4d10App(
                AppConfig(
                    log_level="INFO",
                    refresh_interval_seconds=1.0,
                    title="OpenR4d10 Test",
                    boot_manifest=root / "missing.toml",
                    boot_enabled=False,
                    runtime_directory=root,
                    state_directory=root,
                ),
                display=display,
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=services,  # type: ignore[arg-type]
            )
            app.control(
                {"action": "device_input", "control": "right_inner", "steps": 1}
            )
            app.render_once()

        self.assertEqual(display.service, "WEATHER")
        self.assertEqual(services.active_service, "webradio")
        self.assertEqual(services.requests, [])
        self.assertEqual(services.overlay_views, ["WEATHER"])

    def test_enter_starts_radio_when_radio_ui_is_selected_and_player_stopped(self) -> None:
        class InputDisplay:
            def render(self, _frame) -> None:
                pass

            def snapshot(self):
                return {"service": "RADIO", "playing": False}

            def apply_input(self, _event):
                return self.snapshot()

        class Services:
            active_service = "system"

            def __init__(self):
                self.requests = []

            def control(self, request):
                self.requests.append(request)
                self.active_service = "webradio"
                return {
                    "playback": {"state": "playing", "paused": False},
                    "recording": {"state": "stopped"},
                    "selected_preset": {"name": "SWR3", "channel": 1},
                }

            def receiver_overlay(self, _view_service=None):
                return {"service": "RADIO", "station": "SWR3", "playing": True}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            services = Services()
            app = OpenR4d10App(
                AppConfig(
                    log_level="INFO",
                    refresh_interval_seconds=1.0,
                    title="OpenR4d10 Test",
                    boot_manifest=root / "missing.toml",
                    boot_enabled=False,
                    runtime_directory=root,
                    state_directory=root,
                ),
                display=InputDisplay(),
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=services,
            )
            result = app.control(
                {"action": "device_input", "control": "right_press"}
            )

        self.assertEqual(services.requests, [{"action": "radio_toggle"}])
        self.assertEqual(result["selected_preset"]["name"], "SWR3")

    def test_application_unit_provides_display_handoff_runtime(self) -> None:
        unit = (
            Path(__file__).resolve().parents[1]
            / "systemd"
            / "openr4d10.service"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "RuntimeDirectory=openr4d10 openr4d10-boot",
            unit,
        )
        self.assertIn("RuntimeDirectoryMode=0770", unit)
        self.assertIn("RuntimeDirectoryPreserve=yes", unit)

    def test_render_once_surfaces_unconfigured_power(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output = root / "frame.json"
            config = AppConfig(
                log_level="INFO",
                refresh_interval_seconds=1.0,
                title="OpenR4d10 Test",
                boot_manifest=root / "missing.toml",
                boot_enabled=False,
                runtime_directory=root,
                state_directory=root,
            )
            app = OpenR4d10App(
                config,
                display=FileDisplay(output),
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
            )
            app.render_once()
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["severity"], "warning")
            self.assertEqual(payload["fields"]["power"]["state"], "unconfigured")


if __name__ == "__main__":
    unittest.main()
