"""Native boot-asset integrity and display ownership tests without Pi hardware."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import unittest

from openr4d10.boot_display import claim_display

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows development host
    fcntl = None


ROOT = Path(__file__).resolve().parents[1]


class BootManifestTests(unittest.TestCase):
    def test_approved_source_matches_recorded_hash(self) -> None:
        manifest = json.loads(
            (ROOT / "boot/assets/manifest.json").read_text(encoding="utf-8")
        )
        source = ROOT / "assets/boot/OpenR4d10_APPROVED_ORIGINAL.mp4"
        self.assertEqual(
            hashlib.sha256(source.read_bytes()).hexdigest(),
            manifest["source_sha256"],
        )
        self.assertEqual(manifest["width"], 240)
        self.assertEqual(manifest["height"], 280)
        self.assertEqual(manifest["frame_count"], 73)


@unittest.skipUnless(shutil.which("gcc"), "C compiler not installed")
class NativeBootIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = tempfile.TemporaryDirectory()
        cls.player = Path(cls.directory.name) / "boot-check"
        subprocess.run(
            [
                "gcc",
                "-O2",
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(ROOT / "boot/native/openr4d10_boot.c"),
                "-lz",
                "-o",
                str(cls.player),
            ],
            check=True,
            capture_output=True,
        )
        cls.asset = ROOT / "boot/assets/boot.opb"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.directory.cleanup()

    def verify(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.player), "--verify", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_real_native_assets_decode_without_gpio(self) -> None:
        for name, count in (("boot.opb", 73), ("first.opb", 1)):
            result = self.verify(ROOT / "boot/assets" / name)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                f"verified={count} frames, 240x280 RGB565", result.stdout
            )

    def test_damaged_files_rejected_before_hardware(self) -> None:
        original = self.asset.read_bytes()
        variants = {
            "truncated": original[:-1],
            "trailing": original + b"unexpected",
            "wrong-size": original[:8] + struct.pack("<H", 320) + original[10:],
            "crc": original[:36] + bytes([original[36] ^ 1]) + original[37:],
            "compressed": original[:45]
            + bytes([original[45] ^ 255])
            + original[46:],
        }
        for name, data in variants.items():
            with self.subTest(name=name):
                path = Path(self.directory.name) / f"{name}.opb"
                path.write_bytes(data)
                result = self.verify(path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("boot asset:", result.stderr)
                self.assertNotIn("hardware required", result.stderr)


@unittest.skipUnless(fcntl is not None, "Linux fcntl is required")
class DisplayHandoffTests(unittest.TestCase):
    def test_ui_waits_for_existing_display_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            with (runtime / "display.lock").open("w") as owner:
                fcntl.flock(owner, fcntl.LOCK_EX)
                released = threading.Event()

                def boot_player() -> None:
                    deadline = time.monotonic() + 1.5
                    while not (runtime / "release").exists():
                        if time.monotonic() > deadline:
                            return
                        time.sleep(0.005)
                    fcntl.flock(owner, fcntl.LOCK_UN)
                    released.set()

                worker = threading.Thread(target=boot_player)
                worker.start()
                try:
                    with claim_display(runtime=runtime):
                        self.assertTrue(released.wait(0.2))
                        with (runtime / "display.lock").open("r+") as contender:
                            with self.assertRaises(BlockingIOError):
                                fcntl.flock(
                                    contender, fcntl.LOCK_EX | fcntl.LOCK_NB
                                )
                finally:
                    worker.join(timeout=2)

    def test_missing_runtime_and_busy_owner_fail_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            with self.assertRaises(RuntimeError):
                with claim_display(runtime=runtime / "absent"):
                    self.fail("unexpected ownership")
            with (runtime / "display.lock").open("w") as owner:
                fcntl.flock(owner, fcntl.LOCK_EX)
                with self.assertRaises(TimeoutError):
                    with claim_display(timeout=0.02, runtime=runtime):
                        self.fail("unexpected ownership")


if __name__ == "__main__":
    unittest.main()
