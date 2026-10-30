from pathlib import Path
import json
import tempfile
import unittest

from openr4d10.config import ConfigError, load_app_config, load_hardware_config


class ConfigTests(unittest.TestCase):
    def write(self, directory: Path, name: str, content: str) -> Path:
        path = directory / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_valid_app_config(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = self.write(
                root,
                "app.toml",
                f"""
[application]
log_level = "debug"
refresh_interval_seconds = 1
[ui]
title = "Test"
boot_manifest = {json.dumps(str(root / "boot.toml"))}
boot_enabled = false
[paths]
runtime_directory = {json.dumps(str(root / "run"))}
state_directory = {json.dumps(str(root / "state"))}
[web]
enabled = true
host = "127.0.0.1"
port = 8080
static_directory = {json.dumps(str(root / "web"))}
""",
            )
            config = load_app_config(path)
            self.assertEqual(config.log_level, "DEBUG")
            self.assertEqual(config.title, "Test")
            self.assertEqual(config.web.port, 8080)
            self.assertEqual(config.web.host, "127.0.0.1")

    def test_command_requires_absolute_executable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = self.write(
                Path(raw),
                "hardware.toml",
                """
[display]
backend = "command"
command = ["relative-helper"]
[power]
backend = "unconfigured"
[receiver]
backend = "system"
""",
            )
            with self.assertRaisesRegex(ConfigError, "absolute path"):
                load_hardware_config(path)

    def test_repository_hardware_defaults_are_explicit(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_hardware_config(root / "config" / "hardware.toml")
        self.assertEqual(config.display.backend, "whisplay")
        self.assertEqual(config.power.backend, "unconfigured")
        self.assertEqual(config.receiver.backend, "system")


if __name__ == "__main__":
    unittest.main()
