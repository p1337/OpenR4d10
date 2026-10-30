from pathlib import Path
import tempfile
import unittest

from openr4d10.doctor import _whisplay_audio_checks


class WhisplayAudioDoctorTests(unittest.TestCase):
    def test_reports_active_whisplay_alsa_card(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cards = root / "cards"
            cards.write_text(
                " 0 [whisplaysound  ]: whisplay - Whisplay Sound Card\n",
                encoding="utf-8",
            )

            checks = _whisplay_audio_checks(cards, (root / "missing.dtbo",))

            self.assertEqual(checks[0].level, "OK")
            self.assertIn("whisplaysound", checks[0].message)

    def test_reports_installed_driver_waiting_for_reboot(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            overlay = root / "whisplay-soundcard.dtbo"
            overlay.write_bytes(b"overlay")

            checks = _whisplay_audio_checks(root / "cards", (overlay,))

            self.assertEqual(checks[0].level, "WARN")
            self.assertIn("reboot", checks[0].message)

    def test_reports_missing_driver(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)

            checks = _whisplay_audio_checks(
                root / "cards", (root / "missing.dtbo",)
            )

            self.assertEqual(checks[0].level, "WARN")
            self.assertIn("not installed", checks[0].message)


if __name__ == "__main__":
    unittest.main()
