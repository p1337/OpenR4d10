from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from openr4d10.adapters import FileDisplay, SystemTelemetry, UnconfiguredTelemetry
from openr4d10.app import OpenR4d10App, PLAYER_FRAME_INTERVAL_SECONDS
from openr4d10.config import AppConfig, WebConfig
from openr4d10.input_events import Control, InputEvent


class AppTests(unittest.TestCase):
    def test_running_video_uses_a_dedicated_25_fps_partial_frame_clock(self) -> None:
        self.assertEqual(PLAYER_FRAME_INTERVAL_SECONDS, 0.04)

    def test_device_language_restores_and_persists_through_app_control(self) -> None:
        class LanguageDisplay:
            def __init__(self) -> None:
                self.values = []

            def render(self, _frame) -> None:
                pass

            def set_language(self, value, *, redraw=False):
                if value not in {"en", "de", "pl", "fr", "es"}:
                    raise ValueError("invalid language")
                self.values.append((value, redraw))

            def snapshot(self):
                return {"language": self.values[-1][0]}

        class Services:
            active_service = "system"

            def __init__(self) -> None:
                self.value = "de"

            def display_language(self):
                return self.value

            def set_display_language(self, value):
                if value not in {"en", "de", "pl", "fr", "es"}:
                    raise ValueError("invalid language")
                self.value = value
                return value

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            display = LanguageDisplay()
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
            self.assertEqual(display.values, [("de", False)])
            result = app.control({"action": "display_language", "language": "pl"})
            self.assertEqual(display.values[-1], ("pl", True))
            self.assertEqual(services.value, "pl")
            self.assertEqual(result["settings"], {"language": "pl"})
            self.assertEqual(result["device_ui"]["language"], "pl")
            with self.assertRaises(ValueError):
                app.control({"action": "display_language", "language": "it"})
            self.assertEqual(services.value, "pl")

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

    def test_display_appearance_restores_and_persists_through_app_control(self) -> None:
        class AppearanceDisplay:
            def __init__(self) -> None:
                self.values = []

            def render(self, _frame) -> None:
                pass

            def set_appearance(self, accent, *, redraw=False):
                self.values.append((accent, redraw))

            def snapshot(self):
                accent, _redraw = self.values[-1]
                return {"accent_color": accent}

        class Services:
            active_service = "system"

            def __init__(self) -> None:
                self.value = {"accent_color": "#FDB813"}

            def display_appearance(self):
                return dict(self.value)

            def set_display_appearance(self, accent):
                if not isinstance(accent, str):
                    raise ValueError("invalid appearance")
                self.value = {"accent_color": accent.upper()}
                return dict(self.value)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            display = AppearanceDisplay()
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
            self.assertEqual(display.values, [("#FDB813", False)])
            result = app.control(
                {
                    "action": "display_appearance",
                    "accent_color": "#12abef",
                }
            )
            self.assertEqual(display.values[-1], ("#12abef", True))
            self.assertEqual(
                result["settings"],
                {"accent_color": "#12ABEF"},
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
                self.render_count = 0

            def render(self, _frame) -> None:
                self.render_count += 1

            def apply_input(self, event):
                self.events.append(("present", event))
                return {"playing": False, "right_action": "PLAY"}

            def apply_input_state(self, event):
                self.events.append(("state", event))
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
            app._last_receiver_telemetry = {"service": "RADIO"}
            app._last_power_telemetry = {}
            with patch.object(
                app,
                "render_once",
                side_effect=AssertionError("media input requested live telemetry"),
            ):
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
        self.assertEqual(display.events[0][0], "state")
        self.assertEqual(display.events[1][0], "present")
        self.assertEqual(display.render_count, 1)

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

    def test_dmr_axes_browse_ptt_toggles_talkgroup_and_enter_controls_playback(self) -> None:
        class InputDisplay:
            def __init__(self):
                self.input_handler = None

            def render(self, _frame) -> None:
                pass

            def snapshot(self):
                return {"service": "DMR", "menu_open": False}

            def apply_input(self, _event):
                return self.snapshot()

            def set_input_handler(self, handler):
                self.input_handler = handler

        class Services:
            active_service = "brandmeister"

            def __init__(self):
                self.requests = []

            def control(self, request):
                self.requests.append(request)
                return {"talkgroup": 262, "enabled": True}

            def receiver_overlay(self, _view_service=None):
                return {
                    "service": "DMR", "station": "TG 262", "channel": 25,
                    "channel_label": "262",
                }

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            services = Services()
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
                services=services,
            )
            app.control({"action": "device_input", "control": "right_outer", "steps": 1})
            app.control({"action": "device_input", "control": "left_inner", "steps": -1})
            self.assertIsNotNone(display.input_handler)
            display.input_handler(InputEvent(Control.PTT, active=True))
            display.input_handler(InputEvent(Control.PTT, active=False))
            app.control({"action": "device_input", "control": "right_press"})

        self.assertEqual(
            services.requests,
            [
                {"action": "brandmeister_step", "steps": 1},
                {"action": "brandmeister_step", "steps": -25},
                {"action": "brandmeister_toggle_selected"},
                {"action": "brandmeister_toggle"},
            ],
        )

    def test_dmr_hold_opens_country_list_before_release_and_consumes_release(self) -> None:
        class InputDisplay:
            def __init__(self):
                self.menu_open = False

            def render(self, _frame) -> None:
                pass

            def snapshot(self):
                return {
                    "service": "DMR",
                    "menu_open": self.menu_open,
                    "menu_kind": "dmr_countries" if self.menu_open else None,
                }

            def apply_input(self, event):
                if (
                    event.control == Control.PTT
                    and event.active is False
                    and event.held_seconds >= 2.0
                ):
                    self.menu_open = True
                return self.snapshot()

            def set_input_handler(self, _handler):
                pass

        class Services:
            active_service = "brandmeister"

            def __init__(self):
                self.requests = []

            def control(self, request):
                self.requests.append(request)
                return {"country_menu": True}

            def receiver_overlay(self, _view_service=None):
                return {"service": "DMR", "station": "TG 91"}

        class ManualTimer:
            def __init__(self, _interval, callback, args=()):
                self.callback = callback
                self.args = args
                self.cancelled = False
                self.daemon = False

            def start(self):
                pass

            def cancel(self):
                self.cancelled = True

            def fire(self):
                if not self.cancelled:
                    self.callback(*self.args)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            services = Services()
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
                services=services,
            )
            timers = []

            def timer_factory(interval, callback, args=()):
                timer = ManualTimer(interval, callback, args)
                timers.append(timer)
                return timer

            with patch("openr4d10.app.threading.Timer", side_effect=timer_factory):
                app.control({"action": "device_input", "control": "ptt", "active": True})
                self.assertEqual(services.requests, [])
                self.assertFalse(display.menu_open)

                timers[0].fire()
                self.assertEqual(
                    services.requests,
                    [{"action": "brandmeister_country_menu_open"}],
                )
                self.assertTrue(display.menu_open)

                app.control({"action": "device_input", "control": "ptt", "active": False})
                self.assertEqual(
                    services.requests,
                    [{"action": "brandmeister_country_menu_open"}],
                )
                self.assertTrue(display.menu_open)

                display.menu_open = False
                app.control({"action": "device_input", "control": "ptt", "active": True})
                app.control({"action": "device_input", "control": "ptt", "active": False})
                self.assertTrue(timers[1].cancelled)
                timers[1].fire()

        self.assertEqual(
            services.requests,
            [
                {"action": "brandmeister_country_menu_open"},
                {"action": "brandmeister_toggle_selected"},
            ],
        )

    def test_ambient_quick_menu_routes_selection_toggle_and_layer_volume(self) -> None:
        class InputDisplay:
            def render(self, _frame) -> None:
                pass

            def snapshot(self):
                return {
                    "service": "AMBIENT",
                    "menu_open": True,
                    "menu_kind": "ambient_layers",
                }

            def apply_input(self, _event):
                return self.snapshot()

            def set_input_handler(self, _handler):
                pass

        class Services:
            active_service = "ambient"

            def __init__(self):
                self.requests = []

            def control(self, request):
                self.requests.append(request)
                return {"layer_id": "orchard_birds"}

            def receiver_overlay(self, _view_service=None):
                return {"service": "AMBIENT", "station": "Forest"}

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
            app.control({"action": "device_input", "control": "right_outer", "steps": 1})
            app.control({"action": "device_input", "control": "left_inner", "steps": -1})
            app.control({"action": "device_input", "control": "right_press"})

        self.assertEqual(
            services.requests,
            [
                {"action": "ambient_layer_step", "steps": 1},
                {"action": "ambient_layer_volume_step", "steps": -1},
                {"action": "ambient_layer_toggle"},
            ],
        )

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

    def test_web_mediathek_play_focuses_player_and_device_controls_same_results(self) -> None:
        class InputDisplay:
            def __init__(self) -> None:
                self.service = "DMR"

            def render(self, frame) -> None:
                receiver = frame.fields.get("receiver", {})
                self.service = str(receiver.get("service") or self.service)

            def snapshot(self):
                return {"service": self.service, "menu_open": False}

            def apply_input(self, _event):
                return self.snapshot()

        class Services:
            active_service = "brandmeister"

            def __init__(self) -> None:
                self.requests = []

            def control(self, request):
                self.requests.append(request)
                if request["action"] in {"mediathek_play", "mediathek_step"}:
                    self.active_service = "public_mediatheken"
                return {
                    "playback": {"state": "playing", "paused": False},
                    "provider": "all",
                    "item_id": "0123456789abcdef01234567",
                }

            def receiver_overlay(self, view_service=None):
                return {
                    "service": view_service,
                    "station": "ARD-alpha",
                    "title": "Warum fällt der Mond nicht auf die Erde?",
                    "playing": True,
                    "channel": 1,
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
                display=display,  # type: ignore[arg-type]
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=services,  # type: ignore[arg-type]
            )
            app._last_receiver_telemetry = {"hostname": "OpenR4d10"}
            app._last_power_telemetry = {"battery_percent": 90}

            played = app.control({
                "action": "mediathek_play",
                "provider": "all",
                "item_id": "0123456789abcdef01234567",
                "mode": "video",
            })
            stepped = app.control({
                "action": "device_input",
                "control": "right_outer",
                "steps": 1,
            })
            paused = app.control({
                "action": "device_input",
                "control": "right_press",
            })

        self.assertEqual(played["device_ui"]["service"], "PLAYER")
        self.assertEqual(stepped["device_ui"]["service"], "PLAYER")
        self.assertEqual(paused["device_ui"]["service"], "PLAYER")
        self.assertEqual(
            services.requests,
            [
                {
                    "action": "mediathek_play",
                    "provider": "all",
                    "item_id": "0123456789abcdef01234567",
                    "mode": "video",
                },
                {"action": "mediathek_step", "steps": 1},
                {"action": "pause"},
            ],
        )

    def test_stale_periodic_dmr_frame_cannot_restore_dmr_after_navigation(self) -> None:
        class InputDisplay:
            def __init__(self) -> None:
                self.service = "PLAYER"
                self.render_calls = 0

            def render(self, frame) -> None:
                self.render_calls += 1
                receiver = frame.fields.get("receiver", {})
                self.service = str(receiver.get("service") or self.service)

        class Services:
            active_service = "brandmeister"

            def __init__(self) -> None:
                self.invalidate = None

            def receiver_overlay(self, view_service=None):
                if view_service == "DMR" and self.invalidate is not None:
                    self.invalidate()
                return {
                    "service": view_service,
                    "station": view_service,
                    "title": view_service,
                    "playing": view_service == "DMR",
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
                display=display,  # type: ignore[arg-type]
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=services,  # type: ignore[arg-type]
            )
            app._last_receiver_telemetry = {"hostname": "OpenR4d10"}
            app._last_power_telemetry = {"battery_percent": 90}
            app._interaction_generation = 2
            services.invalidate = lambda: setattr(app, "_interaction_generation", 4)

            app.render_interaction_once("DMR", periodic_generation=2)
            app.render_interaction_once("PLAYER")

        self.assertEqual(display.render_calls, 1)
        self.assertEqual(display.service, "PLAYER")

    def test_service_navigation_uses_one_resolved_cached_frame(self) -> None:
        class InputDisplay:
            def __init__(self) -> None:
                self.service = "RADIO"
                self.state_only_calls = 0
                self.presentation_calls = 0
                self.render_calls = 0

            def snapshot(self):
                return {"service": self.service, "menu_open": False}

            def apply_input_state(self, event):
                self.state_only_calls += 1
                self.assert_navigation(event)
                self.service = "REC"
                return self.snapshot()

            def apply_input(self, _event):
                self.presentation_calls += 1
                raise AssertionError("service navigation drew a stale frame")

            def render(self, frame):
                self.render_calls += 1
                receiver = frame.fields.get("receiver", {})
                self.service = str(receiver.get("service") or self.service)

            @staticmethod
            def assert_navigation(event):
                if event.control != Control.RIGHT_INNER:
                    raise AssertionError("unexpected control")

        class Services:
            active_service = "webradio"

            def __init__(self) -> None:
                self.requests = []
                self.overlay_views = []

            def control(self, request):
                self.requests.append(request)
                return {"recording": {"state": "paused"}}

            def receiver_overlay(self, view_service=None):
                self.overlay_views.append(view_service)
                return {"service": view_service, "station": "Voice Recorder"}

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
                display=display,  # type: ignore[arg-type]
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=services,  # type: ignore[arg-type]
            )
            app._last_receiver_telemetry = {"hostname": "OpenR4d10"}
            app._last_power_telemetry = {"battery_percent": 90}
            result = app.control(
                {"action": "device_input", "control": "right_inner", "steps": 5}
            )

        self.assertEqual(result["device_ui"]["service"], "REC")
        self.assertEqual(display.state_only_calls, 1)
        self.assertEqual(display.presentation_calls, 0)
        self.assertEqual(display.render_calls, 1)
        self.assertEqual(services.requests, [{"action": "voice_recorder_open"}])
        self.assertEqual(services.overlay_views, ["REC"])

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

    def test_radio_ptt_requests_the_buffered_current_song_once_on_press(self) -> None:
        class InputDisplay:
            def render(self, _frame) -> None:
                pass

            def snapshot(self):
                return {"service": "RADIO", "playing": True, "menu_open": False}

            def apply_input(self, _event):
                return self.snapshot()

        class Services:
            active_service = "webradio"

            def __init__(self):
                self.requests = []

            def control(self, request):
                self.requests.append(request)
                return {"radio_buffer": {"keep_current": True}}

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
            pressed = app.control(
                {"action": "device_input", "control": "ptt", "active": True}
            )
            app.control(
                {"action": "device_input", "control": "ptt", "active": False}
            )

        self.assertEqual(services.requests, [{"action": "radio_keep_current"}])
        self.assertTrue(pressed["radio_buffer"]["keep_current"])

    def test_voice_recorder_ptt_hold_double_click_and_continuous_stop(self) -> None:
        class Recorder:
            def __init__(self) -> None:
                self.continuous = False

            def voice_snapshot(self):
                return {"continuous": self.continuous}

        class InputDisplay:
            def render(self, _frame) -> None:
                pass

            def snapshot(self):
                return {"service": "REC", "menu_open": False}

            def apply_input(self, _event):
                return self.snapshot()

        class Services:
            active_service = "recorder"

            def __init__(self) -> None:
                self.requests = []
                self.recorder = Recorder()

            def control(self, request):
                self.requests.append(request)
                action = request["action"]
                if action == "voice_recorder_continuous":
                    self.recorder.continuous = True
                elif action == "voice_recorder_pause":
                    self.recorder.continuous = False
                return {
                    "recording": {
                        "continuous": self.recorder.continuous,
                        "state": "recording" if self.recorder.continuous else "paused",
                    }
                }

            def receiver_overlay(self, _view_service=None):
                return {"service": "REC", "recording": self.recorder.continuous}

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
            with patch(
                "openr4d10.app.time.monotonic",
                side_effect=[10.0, 10.1, 10.2, 10.3, 11.0, 11.1],
            ):
                for active in (True, False, True, False, True, False):
                    app.control(
                        {
                            "action": "device_input",
                            "control": "ptt",
                            "active": active,
                        }
                    )

        self.assertEqual(
            services.requests,
            [
                {"action": "voice_recorder_hold"},
                {"action": "voice_recorder_pause"},
                {"action": "voice_recorder_continuous"},
                {"action": "voice_recorder_pause"},
            ],
        )

    def test_voice_ptt_edges_skip_full_display_and_queue_priority_glow(self) -> None:
        class Recorder:
            def __init__(self) -> None:
                self.state = "paused"

            def voice_snapshot(self):
                return {"state": self.state, "continuous": False}

        class InputDisplay:
            def __init__(self) -> None:
                self.render_count = 0
                self.apply_count = 0
                self.glows = []

            def render(self, _frame) -> None:
                self.render_count += 1

            def input_context(self):
                return {"service": "REC", "menu_open": False, "menu_kind": None}

            def snapshot(self):
                raise AssertionError("PTT fast path must not wait for display snapshot")

            def apply_input(self, _event):
                self.apply_count += 1
                return self.input_context()

            def request_recorder_glow(self, *, recording, continuous):
                self.glows.append((recording, continuous))

        class Services:
            active_service = "recorder"

            def __init__(self) -> None:
                self.recorder = Recorder()
                self.requests = []

            def control(self, request):
                self.requests.append(request)
                if request["action"] == "voice_recorder_hold":
                    self.recorder.state = "recording"
                elif request["action"] == "voice_recorder_pause":
                    self.recorder.state = "paused"
                return {"recording": self.recorder.voice_snapshot()}

            def receiver_overlay(self, _view_service=None):
                return {"service": "REC", "recording": self.recorder.state == "recording"}

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
            with patch("openr4d10.app.time.monotonic", side_effect=[10.0, 11.0]):
                app.control(
                    {"action": "device_input", "control": "ptt", "active": True}
                )
                app.control(
                    {"action": "device_input", "control": "ptt", "active": False}
                )

        self.assertEqual(
            services.requests,
            [
                {"action": "voice_recorder_hold"},
                {"action": "voice_recorder_pause"},
            ],
        )
        self.assertEqual(display.apply_count, 0)
        self.assertEqual(display.render_count, 0)
        self.assertEqual(display.glows, [(True, False), (False, False)])

    def test_radio_ptt_double_click_starts_and_next_click_stops_keep_all(self) -> None:
        class Buffer:
            def __init__(self) -> None:
                self.continuous = False

            def snapshot(self):
                return {"continuous": self.continuous}

        class InputDisplay:
            def render(self, _frame) -> None:
                pass

            def snapshot(self):
                return {"service": "RADIO", "menu_open": False}

            def apply_input(self, _event):
                return self.snapshot()

        class Services:
            active_service = "webradio"

            def __init__(self) -> None:
                self.requests = []
                self.radio_buffer = Buffer()

            def control(self, request):
                self.requests.append(request)
                if request["action"] == "radio_capture_mode":
                    self.radio_buffer.continuous = request["enabled"]
                return {"radio_buffer": self.radio_buffer.snapshot()}

            def receiver_overlay(self, _view_service=None):
                return {"service": "RADIO", "recording": self.radio_buffer.continuous}

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
            with patch(
                "openr4d10.app.time.monotonic",
                side_effect=[20.0, 20.1, 20.2, 20.3, 21.0, 21.1],
            ):
                for active in (True, False, True, False, True, False):
                    app.control(
                        {"action": "device_input", "control": "ptt", "active": active}
                    )

        self.assertEqual(
            services.requests,
            [
                {"action": "radio_keep_current"},
                {"action": "radio_capture_mode", "enabled": True},
                {"action": "radio_capture_mode", "enabled": False},
            ],
        )

    def test_entering_and_leaving_voice_recorder_uses_service_lifecycle(self) -> None:
        class InputDisplay:
            def __init__(self) -> None:
                self.service = "PLAYER"

            def render(self, _frame) -> None:
                pass

            def snapshot(self):
                return {"service": self.service, "menu_open": False}

            def apply_input(self, _event):
                self.service = "REC" if self.service == "PLAYER" else "SYSTEM"
                return self.snapshot()

        class Services:
            active_service = "local_media"

            def __init__(self) -> None:
                self.requests = []

            def control(self, request):
                self.requests.append(request)
                return {"recording": {"state": "stopped"}}

            def receiver_overlay(self, view_service=None):
                return {"service": view_service or "SYSTEM", "playing": False}

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
            app.control(
                {"action": "device_input", "control": "right_inner", "steps": 1}
            )
            app.control(
                {"action": "device_input", "control": "right_inner", "steps": 1}
            )

        self.assertEqual(
            services.requests,
            [
                {"action": "voice_recorder_open"},
                {"action": "voice_recorder_close"},
            ],
        )

    def test_voice_recorder_encoders_seek_boundaries_and_play_from_cursor(self) -> None:
        class InputDisplay:
            def __init__(self) -> None:
                self.apply_calls = 0
                self.render_calls = 0

            def render(self, _frame) -> None:
                self.render_calls += 1

            def snapshot(self):
                return {"service": "REC", "menu_open": False}

            def apply_input(self, _event):
                self.apply_calls += 1
                return self.snapshot()

        class Services:
            active_service = "recorder"

            def __init__(self) -> None:
                self.requests = []

            def control(self, request):
                self.requests.append(request)
                return {"recording": {"state": "paused"}}

            def receiver_overlay(self, view_service=None):
                return {"service": view_service or "REC", "playing": False}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            services = Services()
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
                services=services,
            )
            app.control({"action": "device_input", "control": "right_outer", "steps": -2})
            app.control({"action": "device_input", "control": "left_outer", "steps": 1})
            app.control({"action": "device_input", "control": "left_inner", "steps": -1})
            app.control({"action": "device_input", "control": "left_inner", "steps": 1})
            app.control({"action": "device_input", "control": "right_press"})

        self.assertEqual(
            services.requests,
            [
                {"action": "voice_recorder_seek", "delta_ms": -2000},
                {"action": "voice_recorder_seek", "delta_ms": 100},
                {"action": "voice_recorder_boundary", "end": False},
                {"action": "voice_recorder_boundary", "end": True},
                {"action": "voice_recorder_play_toggle"},
            ],
        )
        self.assertEqual(display.apply_calls, 0)
        self.assertEqual(display.render_calls, 5)
        with patch("openr4d10.app.time.perf_counter", return_value=app._last_device_input_at + 0.1):
            self.assertTrue(app._recorder_interaction_active())
        with patch("openr4d10.app.time.perf_counter", return_value=app._last_device_input_at + 0.21):
            self.assertFalse(app._recorder_interaction_active())

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

    def test_restored_voice_recorder_runs_exclusive_entry_before_first_frame(self) -> None:
        events = []

        class InputDisplay:
            def __init__(self) -> None:
                self.service = "SYSTEM"
                self.app = None

            def render(self, frame) -> None:
                receiver = frame.fields.get("receiver", {})
                self.service = str(receiver.get("service") or self.service)
                events.append(("render", self.service, receiver.get("audio_active")))
                self.app.stop_event.set()

            def snapshot(self):
                return {"service": self.service, "menu_open": False}

            def close(self) -> None:
                events.append(("display_close",))

        class Services:
            active_service = "brandmeister"

            def receiver_overlay(self, view_service=None):
                events.append(("overlay", view_service))
                return {
                    "service": "REC",
                    "station": "Voice Recorder",
                    "title": "Voice Recorder",
                    "subtitle": "Hold PTT to record",
                    "playing": False,
                    "audio_active": self.active_service == "brandmeister",
                }

            def control(self, request):
                events.append(("control", request["action"]))
                self.active_service = "recorder"
                return {"recording": {"state": "stopped"}}

            def close(self) -> None:
                events.append(("services_close",))

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
                    web=WebConfig(enabled=False),
                ),
                display=display,
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=services,  # type: ignore[arg-type]
            )
            display.app = app
            app.install_signal_handlers = lambda: None  # type: ignore[method-assign]
            app.run()

        self.assertEqual(
            events[:4],
            [
                ("overlay", None),
                ("control", "voice_recorder_open"),
                ("overlay", "REC"),
                ("render", "REC", False),
            ],
        )
        self.assertEqual(
            [event for event in events if event == ("control", "voice_recorder_open")],
            [("control", "voice_recorder_open")],
        )

    def test_visible_dmr_view_uses_capped_ten_fps_interaction_refresh(self) -> None:
        class TwoCycleEvent:
            def __init__(self) -> None:
                self.waits = []
                self.stopped = False

            def is_set(self) -> bool:
                return self.stopped

            def set(self) -> None:
                self.stopped = True

            def wait(self, delay: float) -> bool:
                self.waits.append(delay)
                if len(self.waits) >= 2:
                    self.stopped = True
                return self.stopped

        class DmrDisplay:
            def __init__(self) -> None:
                self.frames = 0

            def input_context(self):
                return {"service": "DMR", "menu_open": False}

            def snapshot(self):
                return {"service": "DMR", "menu_open": False}

            def render(self, _frame) -> None:
                self.frames += 1

            def close(self) -> None:
                pass

        class Services:
            def receiver_overlay(self, _view_service=None):
                return {
                    "service": "DMR",
                    "station": "BrandMeister",
                    "title": "TG 91",
                    "subtitle": "Ready",
                    "playing": True,
                    "activity_rows": [],
                }

            def close(self) -> None:
                pass

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            display = DmrDisplay()
            app = OpenR4d10App(
                AppConfig(
                    log_level="INFO",
                    refresh_interval_seconds=1.0,
                    title="OpenR4d10 Test",
                    boot_manifest=root / "missing.toml",
                    boot_enabled=False,
                    runtime_directory=root,
                    state_directory=root,
                    web=WebConfig(enabled=False),
                ),
                display=display,
                power=UnconfiguredTelemetry("power"),
                receiver=SystemTelemetry(),
                services=Services(),  # type: ignore[arg-type]
            )
            stop_event = TwoCycleEvent()
            app.stop_event = stop_event  # type: ignore[assignment]
            app.install_signal_handlers = lambda: None  # type: ignore[method-assign]
            app.run()

        self.assertGreaterEqual(display.frames, 2)
        self.assertEqual(stop_event.waits[0], 1.0)
        self.assertGreater(stop_event.waits[1], 0.0)
        self.assertLessEqual(stop_event.waits[1], 0.1)

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
