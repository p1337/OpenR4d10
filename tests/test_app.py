from pathlib import Path
import json
import tempfile
import unittest

from openr4d10.adapters import FileDisplay, SystemTelemetry, UnconfiguredTelemetry
from openr4d10.app import OpenR4d10App
from openr4d10.config import AppConfig
from openr4d10.input_events import Control


class AppTests(unittest.TestCase):
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
            ):
                with self.subTest(request=request), self.assertRaises(ValueError):
                    app.control(request)

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
