from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from openr4d10.updates import UpdateController


class UpdateControllerTests(unittest.TestCase):
    def test_request_requires_exact_confirmation_and_is_single_use(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            runtime = root / "run"
            state = root / "state"
            runtime.mkdir()
            state.mkdir()
            controller = UpdateController(runtime, state, boot_id_path=root / "boot")

            for payload in (
                {"action": "system_update"},
                {"action": "system_update", "confirmed": False},
                {
                    "action": "system_update",
                    "confirmed": True,
                    "url": "https://example.invalid/update",
                },
            ):
                with self.subTest(payload=payload), self.assertRaises(ValueError):
                    controller.request(payload)

            result = controller.request(
                {"action": "system_update", "confirmed": True}
            )
            self.assertEqual(result["update"]["state"], "queued")
            self.assertEqual((runtime / "update.request").read_bytes(), b"update\n")
            with self.assertRaisesRegex(RuntimeError, "already"):
                controller.request({"action": "system_update", "confirmed": True})

    def test_status_is_bounded_and_marks_reboot_complete_on_new_boot(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            runtime = root / "run"
            state = root / "state"
            runtime.mkdir()
            state.mkdir()
            boot = root / "boot"
            boot.write_text("new-boot\n", encoding="ascii")
            (state / "update-status.json").write_text(
                json.dumps(
                    {
                        "state": "rebooting",
                        "message": "install complete",
                        "version": "0.10.9",
                        "boot_id": "old-boot",
                        "ignored": "not public",
                    }
                ),
                encoding="utf-8",
            )
            controller = UpdateController(runtime, state, boot_id_path=boot)

            status = controller.status()

            self.assertEqual(status["state"], "completed")
            self.assertEqual(status["version"], "0.10.9")
            self.assertNotIn("boot_id", status)
            self.assertNotIn("ignored", status)


if __name__ == "__main__":
    unittest.main()
