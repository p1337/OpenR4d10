from contextlib import redirect_stdout
from pathlib import Path
import io
import json
import tempfile
import unittest

from openr4d10.cli import main


class CliTests(unittest.TestCase):
    def test_preview_ui_does_not_require_target_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "preview.png"
            with redirect_stdout(io.StringIO()):
                code = main(["preview-ui", "--output", str(output)])
            self.assertEqual(code, 0)
            self.assertTrue(output.is_file())

    def test_doctor_reports_placeholders_but_can_allow_development_mode(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        manifest = repository / "assets" / "boot" / "text-sequence.toml"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            app_config = root / "app.toml"
            app_config.write_text(
                "\n".join(
                    (
                        "[application]",
                        'log_level = "INFO"',
                        "refresh_interval_seconds = 1",
                        "[ui]",
                        'title = "Test"',
                        f"boot_manifest = {json.dumps(str(manifest))}",
                        "boot_enabled = true",
                        "[paths]",
                        f"runtime_directory = {json.dumps(str(root))}",
                        f"state_directory = {json.dumps(str(root))}",
                        "[web]",
                        "enabled = false",
                    )
                ),
                encoding="utf-8",
            )
            hardware_config = root / "hardware.toml"
            hardware_config.write_text(
                """
[display]
backend = "unconfigured"
[power]
backend = "unconfigured"
[receiver]
backend = "system"
""",
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(
                    [
                        "--config",
                        str(app_config),
                        "--hardware-config",
                        str(hardware_config),
                        "doctor",
                        "--allow-unsupported-platform",
                        "--allow-unconfigured",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("display backend is unconfigured", output.getvalue())


if __name__ == "__main__":
    unittest.main()
