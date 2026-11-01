from pathlib import Path
import tempfile
import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from openr4d10.doctor import _whisplay_audio_checks, _whisplay_backlight_checks


class WhisplayAudioDoctorTests(unittest.TestCase):
    def test_reports_active_whisplay_alsa_card(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cards = root / "cards"
            cards.write_text(
                " 0 [whisplaysound  ]: whisplay - Whisplay Sound Card\n",
                encoding="utf-8",
            )

            with patch(
                "openr4d10.doctor.subprocess.run",
                return_value=CompletedProcess(
                    [], 0, "numid=44,iface=MIXER,name='speaker'\n  : values=100\n", ""
                ),
            ):
                checks = _whisplay_audio_checks(cards, (root / "missing.dtbo",))

            self.assertEqual(checks[0].level, "OK")
            self.assertIn("whisplaysound", checks[0].message)
            self.assertEqual(checks[1].level, "OK")
            self.assertIn("maximum: 100", checks[1].message)

    def test_warns_when_active_whisplay_gain_is_below_maximum(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cards = root / "cards"
            cards.write_text("whisplaysound\n", encoding="utf-8")
            with patch(
                "openr4d10.doctor.subprocess.run",
                return_value=CompletedProcess([], 0, "  : values=80\n", ""),
            ):
                checks = _whisplay_audio_checks(cards, (root / "missing.dtbo",))

            self.assertEqual(checks[1].level, "WARN")
            self.assertIn("is 80", checks[1].message)

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


class WhisplayBacklightDoctorTests(unittest.TestCase):
    def test_reports_active_kernel_pwm(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            ready = Path(raw) / "kernel-pwm.ready"
            ready.write_text("pwm_gpio@22\n", encoding="ascii")

            checks = _whisplay_backlight_checks(ready)

            self.assertEqual(checks[0].level, "OK")
            self.assertIn("kernel-timed PWM", checks[0].message)

    def test_reports_reboot_required_before_kernel_pwm_is_active(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            checks = _whisplay_backlight_checks(Path(raw) / "missing")

            self.assertEqual(checks[0].level, "WARN")
            self.assertIn("reboot", checks[0].message)


if __name__ == "__main__":
    unittest.main()
