import unittest

from openr4d10.ui import dashboard_frame


class DashboardFrameTests(unittest.TestCase):
    def test_unconfigured_power_names_only_missing_pisugar_telemetry(self) -> None:
        frame = dashboard_frame(
            "OpenR4d10",
            {"state": "online"},
            {"state": "unconfigured"},
        )
        self.assertEqual(frame.body, "PiSugar telemetry is not configured.")
        self.assertEqual(frame.severity, "warning")
        self.assertNotIn("Hardware", frame.body)

    def test_configured_power_is_ready(self) -> None:
        frame = dashboard_frame(
            "OpenR4d10",
            {"state": "online"},
            {"state": "ready", "battery_percent": 80},
        )
        self.assertEqual(frame.body, "Empfänger bereit")
        self.assertEqual(frame.severity, "info")


if __name__ == "__main__":
    unittest.main()
