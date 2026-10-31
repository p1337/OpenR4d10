from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from openr4d10.media import (
    MpvEngine,
    StreamRecorder,
    public_source_label,
    validate_media_source,
)


class FakeProcess:
    def __init__(self) -> None:
        self.returncode = None
        self.signal = None

    def poll(self):
        return self.returncode

    def send_signal(self, value):
        self.signal = value
        self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        self.returncode = -1


class MediaSourceTests(unittest.TestCase):
    def test_network_sources_are_validated_and_public_labels_drop_queries(self) -> None:
        source = "https://radio.example/live?private=local"
        self.assertEqual(validate_media_source(source, ()), source)
        self.assertEqual(public_source_label(source), "https://radio.example/live")
        for invalid in (
            "ftp://example.test/file",
            "https://user:password@example.test/live",
            "relative.mp3",
            "",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_media_source(invalid, ())

    def test_local_sources_must_stay_inside_media_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            inside = root / "track.mp3"
            self.assertEqual(validate_media_source(str(inside), (root,)), str(inside))
            with self.assertRaises(ValueError):
                validate_media_source(str(root.parent / "outside.mp3"), (root,))


class ProcessBoundaryTests(unittest.TestCase):
    def test_mpv_command_uses_documented_private_ipc_and_no_user_config(self) -> None:
        engine = MpvEngine(Path("/usr/bin/mpv"))
        command = engine.command_line(17)
        self.assertEqual(command[0], "/usr/bin/mpv")
        self.assertIn("--no-config", command)
        self.assertIn("--input-ipc-client=fd://17", command)
        self.assertNotIn("shell", " ".join(command))
        self.assertIn("--volume=30", command)

    def test_playlist_supports_shuffle_navigation_and_favorite_loop(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            first = root / "one.mp3"
            second = root / "two.mp3"
            first.write_bytes(b"one")
            second.write_bytes(b"two")
            commands = []
            engine = MpvEngine(Path("/usr/bin/mpv"), media_roots=(root,))
            engine._command = lambda command: commands.append(command) or {}
            state = engine.load_playlist([str(first), str(second)], shuffle=True, loop=True)
            engine.next()
            engine.previous()
            self.assertEqual(state["state"], "playing")
            self.assertIn(["playlist-shuffle"], commands)
            self.assertIn(["set_property", "loop-playlist", "inf"], commands)
            self.assertIn(["playlist-next", "force"], commands)
            self.assertIn(["playlist-prev", "force"], commands)

    def test_recorder_builds_argument_array_and_redacts_source_status(self) -> None:
        calls = []

        def fake_popen(command, **kwargs):
            calls.append((command, kwargs))
            return FakeProcess()

        with tempfile.TemporaryDirectory() as raw:
            recorder = StreamRecorder(
                Path(raw).resolve(),
                executable=Path("/usr/bin/ffmpeg"),
                popen=fake_popen,
            )
            state = recorder.start("https://radio.example/live?session=private")
            self.assertEqual(state["source"], "https://radio.example/live")
            command, kwargs = calls[0]
            self.assertEqual(command[0], "/usr/bin/ffmpeg")
            self.assertIn("libopus", command)
            self.assertNotIn("shell", kwargs)
            stopped = recorder.stop()
            self.assertEqual(stopped["state"], "stopped")
