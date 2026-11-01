from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from openr4d10.media import (
    MPV_IPC_TIMEOUT_SECONDS,
    MpvEngine,
    StreamRecorder,
    public_source_label,
    validate_media_source,
)


class FakeProcess:
    def __init__(self) -> None:
        self.returncode = None
        self.signal = None
        self.stderr = None

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
        self.assertIn(
            "--user-agent=OpenR4d10 (+https://github.com/p1337/OpenR4d10)",
            command,
        )

    def test_mpv_network_open_timeout_is_bounded_for_long_ambient_sources(self) -> None:
        self.assertEqual(MPV_IPC_TIMEOUT_SECONDS, 15.0)

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

    def test_voice_recorder_uses_stereo_whisplay_alsa_and_resumable_mp3_segments(self) -> None:
        calls = []

        def fake_popen(command, **kwargs):
            calls.append((command, kwargs))
            Path(command[-1]).write_bytes(
                b"first" if len(calls) == 1 else b"second"
            )
            return FakeProcess()

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            voice_root = root / "media" / "VoiceRecorder"
            recorder = StreamRecorder(
                root / "recordings",
                voice_root=voice_root,
                popen=fake_popen,
            )
            started = recorder.voice_start()
            self.assertEqual(started["state"], "recording")
            self.assertEqual(started["mode"], "voice")
            command, kwargs = calls[0]
            self.assertIn("alsa", command)
            self.assertIn("whisplaysound", command)
            self.assertIn("libmp3lame", command)
            self.assertIn("2", command)
            self.assertNotIn("shell", kwargs)
            recorder.voice_pause()
            recorder.voice_start()
            recorder.voice_pause()
            finalized = recorder.voice_finalize()
            output = next(voice_root.glob("??????/??????_??????_VoiceRecorder.mp3"))
            self.assertEqual(output.read_bytes(), b"firstsecond")
            self.assertEqual(finalized["output"], output.name)
            self.assertFalse(any(voice_root.rglob(".pending-*")))

    def test_voice_recorder_recovers_pending_segments_after_restart(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            pending = (
                root
                / "media"
                / "VoiceRecorder"
                / "261101"
                / ".pending-261101_082159_VoiceRecorder"
            )
            pending.mkdir(parents=True)
            (pending / "segment-000001.mp3").write_bytes(b"recoverable")
            StreamRecorder(
                root / "recordings",
                voice_root=root / "media" / "VoiceRecorder",
            )
            recovered = pending.parent / "261101_082159_VoiceRecorder.mp3"
            self.assertEqual(recovered.read_bytes(), b"recoverable")
            self.assertFalse(pending.exists())

    def test_voice_level_metadata_keeps_left_and_right_channels_separate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            recorder = StreamRecorder(root / "recordings")
            recorder._consume_voice_level_line(
                "lavfi.astats.1.RMS_level=-30.0"
            )
            recorder._consume_voice_level_line(
                "lavfi.astats.2.RMS_level=-12.0"
            )
            timeline = recorder.voice_snapshot()["timeline"]
            self.assertEqual(len(timeline), 1)
            self.assertLess(timeline[0][0], timeline[0][1])
