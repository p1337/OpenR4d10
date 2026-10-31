from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from openr4d10.wifi import WifiRepairController


class WifiRepairControllerTests(unittest.TestCase):
    def test_request_is_confirmed_bounded_secret_and_single_use(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            runtime = root / "run"
            state = root / "state"
            runtime.mkdir()
            state.mkdir()
            controller = WifiRepairController(runtime, state)
            valid = {
                "action": "wifi_repair",
                "ssid": "Private WLAN",
                "passphrase": "correct-horse-battery-staple",
                "replace_existing": True,
                "confirmed": True,
            }

            result = controller.request(valid)

            self.assertEqual(result["wifi_repair"]["state"], "queued")
            self.assertNotIn("ssid", result["wifi_repair"])
            self.assertNotIn("passphrase", result["wifi_repair"])
            request_path = runtime / "wifi-repair.request"
            if os.name == "posix":
                self.assertEqual(os.stat(request_path).st_mode & 0o777, 0o600)
            stored = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["ssid"], valid["ssid"])
            self.assertEqual(stored["passphrase"], valid["passphrase"])
            with self.assertRaisesRegex(RuntimeError, "already"):
                controller.request(valid)

    def test_request_rejects_invalid_or_unconfirmed_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            runtime = root / "run"
            state = root / "state"
            runtime.mkdir()
            state.mkdir()
            controller = WifiRepairController(runtime, state)
            base = {
                "action": "wifi_repair",
                "ssid": "Private WLAN",
                "passphrase": "valid-passphrase",
                "replace_existing": True,
                "confirmed": True,
            }
            invalid = (
                {**base, "confirmed": False},
                {**base, "ssid": ""},
                {**base, "ssid": "x" * 33},
                {**base, "passphrase": "short"},
                {**base, "passphrase": "pässword"},
                {**base, "replace_existing": "yes"},
                {**base, "extra": "not allowed"},
            )
            for payload in invalid:
                with self.subTest(payload=payload), self.assertRaises(ValueError):
                    controller.request(payload)

    def test_public_status_is_bounded_and_contains_no_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            runtime = root / "run"
            state = root / "state"
            runtime.mkdir()
            state.mkdir()
            (state / "wifi-repair-status.json").write_text(
                json.dumps(
                    {
                        "state": "succeeded",
                        "message": "connected",
                        "ssid": "must-not-leak",
                        "passphrase": "must-not-leak",
                    }
                ),
                encoding="utf-8",
            )
            status = WifiRepairController(runtime, state).status()
            self.assertEqual(status, {"state": "succeeded", "message": "connected"})

    def test_previous_boot_running_repair_is_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            runtime = root / "run"
            state = root / "state"
            runtime.mkdir()
            state.mkdir()
            boot = root / "boot"
            boot.write_text("new-boot\n", encoding="ascii")
            (state / "wifi-repair-status.json").write_text(
                json.dumps(
                    {"state": "running", "message": "connecting", "boot_id": "old-boot"}
                ),
                encoding="utf-8",
            )
            controller = WifiRepairController(runtime, state, boot_id_path=boot)

            status = controller.status()
            result = controller.request(
                {
                    "action": "wifi_repair",
                    "ssid": "Private WLAN",
                    "passphrase": "valid-passphrase",
                    "replace_existing": True,
                    "confirmed": True,
                }
            )

            self.assertEqual(status["state"], "failed")
            self.assertNotIn("boot_id", status)
            self.assertEqual(result["wifi_repair"]["state"], "queued")


if __name__ == "__main__":
    unittest.main()
