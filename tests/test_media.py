from __future__ import annotations

import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch

from openr4d10.media import (
    MPV_IPC_TIMEOUT_SECONDS,
    MPV_LOCAL_START_TIMEOUT_SECONDS,
    MediaError,
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
        self.assertIn("--audio-device=alsa/whisplaysound", command)
        self.assertIn("--audio-fallback-to-null=no", command)
        self.assertNotIn("--no-video", command)
        self.assertIn("--video=auto", command)
        self.assertNotIn("--video=yes", command)
        self.assertIn("--vo=null", command)
        self.assertIn("--vo-null-fps=25", command)
        self.assertIn("--video-sync=audio", command)
        self.assertIn("--screenshot-sw=yes", command)
        self.assertIn("--screenshot-jpeg-quality=45", command)
        self.assertIn(
            "--user-agent=OpenR4d10 (+https://github.com/p1337/OpenR4d10)",
            command,
        )

    def test_video_frame_uses_one_nonblocking_runtime_screenshot(self) -> None:
        class Ipc:
            def __init__(self):
                self.payloads = []

            def sendall(self, payload):
                self.payloads.append(payload)

        with tempfile.TemporaryDirectory() as raw:
            runtime = Path(raw).resolve()
            engine = MpvEngine(
                Path("/usr/bin/mpv"),
                runtime_directory=runtime,
            )
            engine._process = FakeProcess()
            engine._ipc = Ipc()  # type: ignore[assignment]
            engine.state.state = "playing"

            self.assertIsNone(engine.video_frame())
            self.assertEqual(len(engine._ipc.payloads), 1)  # type: ignore[union-attr]
            request = json.loads(engine._ipc.payloads[0])  # type: ignore[union-attr]
            self.assertEqual(request["command"][0], "screenshot-to-file")
            self.assertEqual(request["command"][2], "video")
            self.assertTrue(
                Path(request["command"][1]).is_relative_to(runtime)
            )

            payload = b"\xff\xd8same-player-frame\xff\xd9"
            engine._video_capture_path.write_bytes(payload)
            engine.state.paused = True
            frame = engine.video_frame()

            self.assertEqual(frame, payload)
            self.assertEqual(len(engine._ipc.payloads), 1)  # type: ignore[union-attr]
            self.assertFalse(engine._video_capture_path.exists())

    def test_video_screenshot_replies_are_drained_without_blocking(self) -> None:
        engine = MpvEngine(Path("/usr/bin/mpv"))
        local, remote = socket.socketpair()
        try:
            engine._ipc = local
            remote.sendall(
                b'{"request_id":1,"error":"success"}\n'
                b'{"event":"end-file","reason":"eof"}\n'
            )

            engine._drain_video_capture_responses()

            self.assertEqual(engine._buffer, b"")
            self.assertEqual(engine.state.state, "stopped")
        finally:
            local.close()
            remote.close()

    def test_stale_end_file_cannot_stop_newer_playlist_entry(self) -> None:
        engine = MpvEngine(Path("/usr/bin/mpv"))
        engine._remember_loaded_entry(
            {"data": {"playlist_entry_id": 22}, "error": "success"}
        )
        engine.state.state = "playing"

        engine._remember_event(
            {
                "event": "end-file",
                "playlist_entry_id": 21,
                "reason": "stop",
            }
        )

        self.assertEqual(engine.state.state, "playing")
        self.assertEqual(engine._active_playlist_entry_id, 22)
        self.assertFalse(
            any(
                event.get("playlist_entry_id") == 21
                for event in engine._events
            )
        )

        engine.state.state = "stopped"
        engine._remember_event(
            {"event": "start-file", "playlist_entry_id": 22}
        )
        self.assertEqual(engine.state.state, "playing")

        engine._remember_event(
            {
                "event": "end-file",
                "playlist_entry_id": 22,
                "reason": "eof",
            }
        )
        self.assertEqual(engine.state.state, "stopped")
        self.assertIsNone(engine._active_playlist_entry_id)

    def test_mpv_network_open_timeout_is_bounded_for_long_ambient_sources(self) -> None:
        self.assertEqual(MPV_IPC_TIMEOUT_SECONDS, 15.0)
        self.assertEqual(MPV_LOCAL_START_TIMEOUT_SECONDS, 1.0)

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

    def test_mpv_uses_exact_absolute_seek_for_voice_playback(self) -> None:
        commands = []
        engine = MpvEngine(Path("/usr/bin/mpv"))
        engine._command = lambda command: commands.append(command) or {}
        engine.seek_absolute(1.2)
        self.assertEqual(commands, [["seek", 1.2, "absolute", "exact"]])

    def test_load_enables_video_only_when_explicitly_requested(self) -> None:
        engine = MpvEngine(Path("/usr/bin/mpv"))
        commands = []
        engine._command = lambda command: commands.append(command) or {}

        engine.load("https://media.example/audio.mp3")
        engine.load("https://media.example/video.mp4", video_enabled=True)

        self.assertEqual(commands[0], ["set_property", "vid", "no"])
        self.assertEqual(commands[4], ["set_property", "vid", "auto"])
        with self.assertRaises(ValueError):
            engine.load("https://media.example/video.mp4", video_enabled=1)

    def test_mpv_load_at_sets_initial_position_in_one_atomic_command(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            voice = root / "voice.mp3"
            voice.write_bytes(b"voice")
            commands = []
            engine = MpvEngine(Path("/usr/bin/mpv"), media_roots=(root,))
            engine._command = lambda command: commands.append(command) or {}
            engine._wait_for_audio_start = lambda: None

            state = engine.load_at(str(voice), 1.2346)

        self.assertEqual(
            commands,
            [
                ["set_property", "loop-playlist", "no"],
                ["loadfile", str(voice), "replace", -1, {"start": "1.235"}],
                ["set_property", "pause", False],
            ],
        )
        self.assertEqual(state["state"], "playing")
        self.assertFalse(state["paused"])

    def test_local_audio_start_requires_loaded_playback_and_real_output(self) -> None:
        engine = MpvEngine(Path("/usr/bin/mpv"))
        ipc = Mock()
        ipc.gettimeout.return_value = 15.0
        engine._ipc = ipc
        engine._events.extend(
            (
                {"event": "start-file"},
                {"event": "file-loaded"},
                {"event": "playback-restart"},
            )
        )
        engine._command = Mock(
            return_value={"data": {"format": "s16", "samplerate": 48000}}
        )

        engine._wait_for_audio_start()

        engine._command.assert_called_once_with(
            ["get_property", "audio-out-params"]
        )
        ipc.settimeout.assert_called_with(15.0)

    def test_local_audio_start_rejects_delayed_file_error(self) -> None:
        engine = MpvEngine(Path("/usr/bin/mpv"))
        ipc = Mock()
        ipc.gettimeout.return_value = 15.0
        engine._ipc = ipc
        engine._events.extend(
            (
                {"event": "start-file"},
                {
                    "event": "end-file",
                    "reason": "error",
                    "file_error": "loading failed",
                },
            )
        )

        with self.assertRaisesRegex(MediaError, "loading failed"):
            engine._wait_for_audio_start()

        self.assertEqual(engine.state.state, "stopped")
        self.assertIn("loading failed", str(engine.state.error))

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
        edit_commands = []

        def fake_popen(command, **kwargs):
            calls.append((command, kwargs))
            Path(command[-1]).write_bytes(
                b"first" if len(calls) == 1 else b"second"
            )
            return FakeProcess()

        def fake_edit(command):
            edit_commands.append(command)
            Path(command[-1]).write_bytes(b"joined")

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            voice_root = root / "media" / "VoiceRecorder"
            recorder = StreamRecorder(
                root / "recordings",
                voice_root=voice_root,
                popen=fake_popen,
                edit_runner=fake_edit,
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
            self.assertEqual(output.read_bytes(), b"joined")
            self.assertEqual(finalized["output"], output.name)
            self.assertFalse(any(voice_root.rglob(".pending-*")))
            self.assertEqual(len(edit_commands), 1)
            self.assertIn("concat", edit_commands[0])
            self.assertIn("copy", edit_commands[0])
            self.assertFalse(any(voice_root.rglob("*.concat.txt")))

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

    def test_voice_recovery_replays_pending_overwrite_manifest(self) -> None:
        commands = []

        def edit_runner(command):
            commands.append(command)
            Path(command[-1]).write_bytes(b"recovered-edit")

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
            (pending / "working.mp3").write_bytes(b"old")
            (pending / "segment-000001.mp3").write_bytes(b"new")
            (pending / "edit.json").write_text(
                '{"version":1,"position_ms":2000,"duration_ms":5000,'
                '"recording_start_ms":2000,"active_segment":"segment-000001.mp3"}',
                encoding="utf-8",
            )
            StreamRecorder(
                root / "recordings",
                voice_root=root / "media" / "VoiceRecorder",
                edit_runner=edit_runner,
            )
            recovered = pending.parent / "261101_082159_VoiceRecorder.mp3"
            self.assertEqual(recovered.read_bytes(), b"recovered-edit")
            self.assertTrue(commands)
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

    def test_live_voice_snapshot_advances_playhead_before_pause(self) -> None:
        def fake_popen(command, **_kwargs):
            Path(command[-1]).write_bytes(b"live-audio")
            return FakeProcess()

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            recorder = StreamRecorder(root / "recordings", popen=fake_popen)
            with patch("openr4d10.media.time.monotonic", side_effect=[10.0, 12.0]):
                recorder.voice_start()
                snapshot = recorder.voice_snapshot()
            self.assertEqual(snapshot["position_ms"], 2000)
            self.assertEqual(snapshot["duration_ms"], 2000)
            recorder.voice_pause()

    def test_voice_pause_uses_closed_file_duration_not_blocked_wall_time(self) -> None:
        def fake_popen(command, **_kwargs):
            Path(command[-1]).write_bytes(b"closed-audio")
            return FakeProcess()

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            recorder = StreamRecorder(root / "recordings", popen=fake_popen)
            recorder._probe_audio_duration_ms = Mock(return_value=1234)  # type: ignore[method-assign]
            recorder.voice_start()
            snapshot = recorder.voice_pause()
            self.assertEqual(snapshot["position_ms"], 1234)
            self.assertEqual(snapshot["duration_ms"], 1234)

    def test_voice_cursor_boundaries_and_overwrite_preserve_the_unreached_tail(self) -> None:
        commands = []

        def edit_runner(command):
            commands.append(command)
            Path(command[-1]).write_bytes(b"edited")

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            recorder = StreamRecorder(
                root / "recordings",
                voice_root=root / "media" / "VoiceRecorder",
                edit_runner=edit_runner,
            )
            recorder._new_voice_session()
            assert recorder._voice_working is not None
            assert recorder._voice_session_dir is not None
            recorder._voice_working.write_bytes(b"old-audio")
            recorder._voice_duration_ms = 5000
            recorder._voice_cursor_ms = 2500

            manifest = recorder._voice_session_dir / "edit.json"
            manifest_before_follow = manifest.read_text(encoding="utf-8")
            self.assertEqual(
                recorder.voice_follow_playback(2700)["position_ms"],
                2700,
            )
            self.assertEqual(
                manifest.read_text(encoding="utf-8"),
                manifest_before_follow,
            )

            self.assertEqual(recorder.voice_seek(-100)["position_ms"], 2600)
            self.assertEqual(recorder.voice_boundary(end=False)["position_ms"], 0)
            self.assertEqual(recorder.voice_boundary(end=True)["position_ms"], 5000)
            recorder.voice_set_position(2000)

            segment = recorder._voice_session_dir / "segment-000001.mp3"
            segment.write_bytes(b"replacement")
            recorder._voice_active_segment = segment
            recorder._voice_recording_start_ms = 2000
            recorder._commit_voice_segment(1000)

            snapshot = recorder.voice_snapshot()
            self.assertEqual(snapshot["position_ms"], 3000)
            self.assertEqual(snapshot["duration_ms"], 5000)
            self.assertEqual(recorder._voice_working.read_bytes(), b"edited")
            command = commands[0]
            filter_graph = command[command.index("-filter_complex") + 1]
            self.assertIn("atrim=start=0:end=2.000", filter_graph)
            self.assertIn("atrim=start=3.000", filter_graph)
            self.assertIn("concat=n=3", filter_graph)
