from pathlib import Path
import json
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from openr4d10.adapters import AdapterError, FileDisplay, PiSugar3Telemetry, SystemTelemetry
from openr4d10.models import Frame


class AdapterTests(unittest.TestCase):
    def test_file_display_writes_semantic_frame_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "display.json"
            FileDisplay(output).render(
                Frame(screen="dashboard", title="Test", fields={"value": 42})
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["screen"], "dashboard")
            self.assertEqual(payload["fields"]["value"], 42)
            self.assertEqual(list(output.parent.glob(".display.json.*")), [])

    def test_system_telemetry_reports_the_actual_active_ssid(self) -> None:
        calls = [
            subprocess.CompletedProcess([], 0, "4c02e8ae-7ddf-3fde-b716-e8e2102cc34c\n", ""),
            subprocess.CompletedProcess([], 0, "p1337\ninfrastructure\n", ""),
        ]
        with (
            patch("openr4d10.adapters.subprocess.run", side_effect=calls) as run,
            patch.object(SystemTelemetry, "_local_ipv4", return_value="192.168.1.64"),
        ):
            telemetry = SystemTelemetry().read()
        self.assertEqual(telemetry["wifi"], "p1337")
        self.assertEqual(telemetry["wifi_mode"], "client")
        self.assertEqual(telemetry["ip_address"], "192.168.1.64")
        self.assertEqual(run.call_count, 2)
        self.assertIn("GENERAL.CON-UUID", run.call_args_list[0].args[0])
        self.assertIn("802-11-wireless.ssid,802-11-wireless.mode", run.call_args_list[1].args[0])

    def test_system_telemetry_reports_offline_instead_of_generic_wlan(self) -> None:
        with (
            patch("openr4d10.adapters.subprocess.run", side_effect=OSError("missing")),
            patch.object(SystemTelemetry, "_local_ipv4", return_value=None),
        ):
            telemetry = SystemTelemetry().read()
        self.assertEqual(telemetry["wifi"], "OFFLINE")
        self.assertEqual(telemetry["wifi_mode"], "disconnected")

    def test_pisugar3_reads_only_identity_mode_and_capacity(self) -> None:
        ioctl = Mock()
        with (
            patch.dict(sys.modules, {"fcntl": SimpleNamespace(ioctl=ioctl)}),
            patch("openr4d10.adapters.os.open", return_value=17),
            patch("openr4d10.adapters.os.write", return_value=1) as write,
            patch("openr4d10.adapters.os.read", side_effect=[b"\x03", b"\x0f", b"\x51"]),
            patch("openr4d10.adapters.os.close") as close,
        ):
            value = PiSugar3Telemetry().read()
        self.assertEqual(value, {"state": "ready", "model": "PiSugar 3", "battery_percent": 81})
        ioctl.assert_called_once_with(17, PiSugar3Telemetry.I2C_SLAVE, 0x57)
        self.assertEqual(
            [call.args[1] for call in write.call_args_list],
            [b"\x00", b"\x01", b"\x2a"],
        )
        close.assert_called_once_with(17)

    def test_pisugar3_rejects_an_unverified_device_identity(self) -> None:
        with (
            patch.dict(sys.modules, {"fcntl": SimpleNamespace(ioctl=Mock())}),
            patch("openr4d10.adapters.os.open", return_value=17),
            patch("openr4d10.adapters.os.write", return_value=1),
            patch("openr4d10.adapters.os.read", side_effect=[b"\x02", b"\x0f"]),
            patch("openr4d10.adapters.os.close"),
            self.assertRaisesRegex(AdapterError, "did not identify a PiSugar 3"),
        ):
            PiSugar3Telemetry().read()


if __name__ == "__main__":
    unittest.main()
