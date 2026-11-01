"""Safe local media process boundaries for playback and stream recording."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
import json
import math
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import threading
import time
from typing import Any, Callable
from urllib.parse import SplitResult, urlsplit, urlunsplit

from .cpu_affinity import (
    pin_current_thread_to_background_cores,
    pin_process_to_background_cores,
)


class MediaError(RuntimeError):
    pass


MPV_IPC_TIMEOUT_SECONDS = 15.0
MPV_LOCAL_START_TIMEOUT_SECONDS = 1.0


def _is_absolute_target_path(path: Path) -> bool:
    """Recognize native host paths and absolute Linux target paths in tests."""
    return path.is_absolute() or str(path).startswith(("/", "\\"))


def _target_path_string(path: Path) -> str:
    value = str(path)
    if value.startswith("\\"):
        return value.replace("\\", "/")
    return value


def validate_media_source(source: str, media_roots: tuple[Path, ...]) -> str:
    if not isinstance(source, str) or not source or len(source) > 4096:
        raise ValueError("media source must be a non-empty string")
    path = Path(source)
    if path.is_absolute():
        resolved = path.resolve(strict=False)
        if not any(resolved.is_relative_to(root.resolve()) for root in media_roots):
            raise ValueError("local media source is outside an approved media directory")
        return str(resolved)
    parsed = urlsplit(source)
    if parsed.scheme in {"http", "https"}:
        if not parsed.hostname:
            raise ValueError("network media source requires a host")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("credentials must not be embedded in a media URL")
        return source
    if parsed.scheme:
        raise ValueError("only http, https and approved absolute files are supported")
    raise ValueError("local media source must be absolute")


def public_source_label(source: str) -> str:
    parsed = urlsplit(source)
    if parsed.scheme in {"http", "https"}:
        clean = SplitResult(parsed.scheme, parsed.hostname or "", parsed.path, "", "")
        return urlunsplit(clean)
    return Path(source).name


@dataclass(slots=True)
class PlaybackState:
    state: str = "stopped"
    source: str | None = None
    volume: int = 30
    paused: bool = False
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class MpvEngine:
    """Control one isolated mpv process through its documented JSON IPC."""

    def __init__(
        self,
        executable: Path = Path("/usr/bin/mpv"),
        media_roots: tuple[Path, ...] = (Path("/var/lib/openr4d10/media"),),
    ) -> None:
        if not _is_absolute_target_path(executable):
            raise ValueError("mpv executable must be absolute")
        self.executable = executable
        self.media_roots = media_roots
        self.state = PlaybackState()
        self._process: subprocess.Popen[bytes] | None = None
        self._ipc: socket.socket | None = None
        self._buffer = b""
        self._events: deque[dict[str, Any]] = deque()
        self._request_id = 0
        self._lock = threading.Lock()

    def command_line(self, ipc_fd: int) -> list[str]:
        return [
            _target_path_string(self.executable),
            "--no-config",
            "--idle=yes",
            "--no-video",
            "--audio-display=no",
            "--terminal=no",
            "--really-quiet",
            "--user-agent=OpenR4d10 (+https://github.com/p1337/OpenR4d10)",
            "--ao=alsa",
            "--audio-device=alsa/whisplaysound",
            "--audio-fallback-to-null=no",
            f"--volume={self.state.volume}",
            f"--input-ipc-client=fd://{ipc_fd}",
        ]

    def _start(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return
        if os.name != "posix":
            raise MediaError("mpv playback runtime is supported only on the Linux target")
        if not self.executable.is_file() or not os.access(self.executable, os.X_OK):
            raise MediaError(f"mpv executable is unavailable: {self.executable}")
        parent, child = socket.socketpair()
        try:
            self._process = subprocess.Popen(
                self.command_line(child.fileno()),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                pass_fds=(child.fileno(),),
                start_new_session=True,
            )
            pin_process_to_background_cores(self._process.pid)
        except Exception:
            parent.close()
            child.close()
            raise
        child.close()
        parent.settimeout(MPV_IPC_TIMEOUT_SECONDS)
        self._ipc = parent
        self._buffer = b""
        self._events.clear()

    def _read_line(self) -> dict[str, Any]:
        if self._ipc is None:
            raise MediaError("mpv IPC is not connected")
        while b"\n" not in self._buffer:
            data = self._ipc.recv(65536)
            if not data:
                raise MediaError("mpv closed its IPC connection")
            self._buffer += data
        line, self._buffer = self._buffer.split(b"\n", 1)
        value = json.loads(line)
        if not isinstance(value, dict):
            raise MediaError("mpv returned an invalid IPC response")
        return value

    def _command(self, command: list[Any]) -> dict[str, Any]:
        self._start()
        assert self._ipc is not None
        self._request_id += 1
        request_id = self._request_id
        payload = json.dumps(
            {"command": command, "request_id": request_id},
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        self._ipc.sendall(payload)
        while True:
            response = self._read_line()
            if isinstance(response.get("event"), str):
                self._remember_event(response)
                continue
            if response.get("request_id") != request_id:
                continue
            if response.get("error") != "success":
                raise MediaError(f"mpv command failed: {response.get('error', 'unknown')}")
            return response

    def _remember_event(self, event: dict[str, Any]) -> None:
        """Keep asynchronous mpv truth instead of silently discarding it."""

        self._events.append(event)
        if event.get("event") != "end-file":
            return
        reason = str(event.get("reason") or "stopped")
        self.state.state = "stopped"
        self.state.paused = False
        if reason == "error":
            detail = str(event.get("file_error") or event.get("error") or "unknown")
            self.state.error = f"mpv playback failed: {detail}"

    def _wait_for_audio_start(self) -> None:
        """Wait for decoded output, rejecting delayed local-file failures."""

        if self._ipc is None:
            raise MediaError("mpv IPC is not connected")
        deadline = time.monotonic() + MPV_LOCAL_START_TIMEOUT_SECONDS
        previous_timeout = self._ipc.gettimeout()
        started = False
        loaded = False
        try:
            while time.monotonic() < deadline:
                if self._events:
                    event = self._events.popleft()
                else:
                    self._ipc.settimeout(max(0.001, deadline - time.monotonic()))
                    try:
                        event = self._read_line()
                    except TimeoutError as exc:
                        raise MediaError("mpv did not start local audio in time") from exc
                    if not isinstance(event.get("event"), str):
                        continue
                name = event.get("event")
                if name == "start-file":
                    started = True
                    loaded = False
                elif started and name == "file-loaded":
                    loaded = True
                elif started and name == "end-file":
                    self._remember_event(event)
                    detail = str(
                        event.get("file_error")
                        or event.get("error")
                        or event.get("reason")
                        or "unknown"
                    )
                    raise MediaError(f"mpv could not play local audio: {detail}")
                elif loaded and name == "playback-restart":
                    output = self._command(["get_property", "audio-out-params"]).get(
                        "data"
                    )
                    if not isinstance(output, dict) or not output:
                        raise MediaError("mpv started without a real audio output")
                    return
            raise MediaError("mpv did not start local audio in time")
        finally:
            self._ipc.settimeout(previous_timeout)

    def load(self, source: str) -> dict[str, Any]:
        approved = validate_media_source(source, self.media_roots)
        with self._lock:
            try:
                self._command(["loadfile", approved, "replace"])
            except (OSError, json.JSONDecodeError, MediaError) as exc:
                self.state.state = "error"
                self.state.error = str(exc)
                raise MediaError(str(exc)) from exc
            self.state.state = "playing"
            self.state.source = public_source_label(approved)
            self.state.paused = False
            self.state.error = None
            return self.state.as_dict()

    def load_at(self, source: str, start_seconds: float) -> dict[str, Any]:
        """Load one source atomically at its initial playback position."""

        if (
            isinstance(start_seconds, bool)
            or not isinstance(start_seconds, (int, float))
            or not math.isfinite(float(start_seconds))
        ):
            raise ValueError("start position must be a finite number")
        approved = validate_media_source(source, self.media_roots)
        position = max(0.0, float(start_seconds))
        with self._lock:
            try:
                self._events.clear()
                self._command(
                    [
                        "loadfile",
                        approved,
                        "replace",
                        -1,
                        {"start": f"{position:.3f}"},
                    ]
                )
                self._wait_for_audio_start()
            except (OSError, json.JSONDecodeError, MediaError) as exc:
                self.state.state = "error"
                self.state.error = str(exc)
                raise MediaError(str(exc)) from exc
            self.state.state = "playing"
            self.state.source = public_source_label(approved)
            self.state.paused = False
            self.state.error = None
            return self.state.as_dict()

    def load_playlist(
        self,
        sources: list[str],
        *,
        shuffle: bool = False,
        loop: bool = False,
    ) -> dict[str, Any]:
        if not sources:
            raise ValueError("playlist requires at least one media source")
        approved = [validate_media_source(item, self.media_roots) for item in sources]
        with self._lock:
            try:
                self._command(["loadfile", approved[0], "replace"])
                for source in approved[1:]:
                    self._command(["loadfile", source, "append"])
                if shuffle and len(approved) > 1:
                    self._command(["playlist-shuffle"])
                self._command(["set_property", "loop-playlist", "inf" if loop else "no"])
            except (OSError, json.JSONDecodeError, MediaError) as exc:
                self.state.state = "error"
                self.state.error = str(exc)
                raise MediaError(str(exc)) from exc
            self.state.state = "playing"
            self.state.source = public_source_label(approved[0])
            self.state.paused = False
            self.state.error = None
            return self.state.as_dict()

    def next(self) -> dict[str, Any]:
        with self._lock:
            self._command(["playlist-next", "force"])
            self.state.state = "playing"
            self.state.paused = False
            return self.state.as_dict()

    def previous(self) -> dict[str, Any]:
        with self._lock:
            self._command(["playlist-prev", "force"])
            self.state.state = "playing"
            self.state.paused = False
            return self.state.as_dict()

    def toggle_pause(self) -> dict[str, Any]:
        with self._lock:
            self._command(["cycle", "pause"])
            self.state.paused = not self.state.paused
            self.state.state = "paused" if self.state.paused else "playing"
            return self.state.as_dict()

    def property(self, name: str) -> Any:
        if not re.fullmatch(r"[a-z0-9-]{1,64}", name):
            raise ValueError("invalid mpv property")
        with self._lock:
            return self._command(["get_property", name]).get("data")

    def seek_absolute(self, seconds: float) -> dict[str, Any]:
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
            raise ValueError("seek position must be numeric")
        position = max(0.0, float(seconds))
        with self._lock:
            self._command(["seek", position, "absolute", "exact"])
            return self.state.as_dict()

    def position_seconds(self) -> float | None:
        try:
            value = self.property("time-pos")
        except (OSError, json.JSONDecodeError, MediaError):
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return max(0.0, float(value))

    def set_volume(self, volume: int) -> dict[str, Any]:
        if isinstance(volume, bool) or not isinstance(volume, int) or not 0 <= volume <= 100:
            raise ValueError("volume must be an integer from 0 to 100")
        with self._lock:
            self._command(["set_property", "volume", volume])
            self.state.volume = volume
            return self.state.as_dict()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                self._command(["stop"])
            self.state.state = "stopped"
            self.state.source = None
            self.state.paused = False
            return self.state.as_dict()

    def close(self) -> None:
        with self._lock:
            if self._ipc is not None:
                try:
                    self._ipc.close()
                except OSError:
                    pass
                self._ipc = None
            if self._process is not None:
                try:
                    self._process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._process.terminate()
                    try:
                        self._process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
                        self._process.wait(timeout=1)
                self._process = None
            self.state.state = "stopped"
            self.state.source = None


@dataclass(slots=True)
class RecordingState:
    state: str = "stopped"
    source: str | None = None
    output: str | None = None
    error: str | None = None
    mode: str = "stream"
    continuous: bool = False
    session_active: bool = False
    timeline: list[list[int]] = field(default_factory=list)
    position_ms: int = 0
    duration_ms: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


PopenFactory = Callable[..., subprocess.Popen[bytes]]
VoiceEditRunner = Callable[[list[str]], None]


class StreamRecorder:
    """Record one approved stream or one resumable Whisplay voice session."""

    def __init__(
        self,
        recordings_root: Path,
        executable: Path = Path("/usr/bin/ffmpeg"),
        media_roots: tuple[Path, ...] = (Path("/var/lib/openr4d10/media"),),
        voice_root: Path | None = None,
        capture_device: str = "whisplaysound",
        popen: PopenFactory = subprocess.Popen,
        edit_runner: VoiceEditRunner | None = None,
    ) -> None:
        if not recordings_root.is_absolute() or not _is_absolute_target_path(executable):
            raise ValueError("recorder paths must be absolute")
        self.recordings_root = recordings_root
        self.executable = executable
        self.media_roots = media_roots
        self.voice_root = voice_root or recordings_root / "VoiceRecorder"
        if not self.voice_root.is_absolute():
            raise ValueError("voice recorder root must be absolute")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", capture_device):
            raise ValueError("invalid ALSA capture device")
        self.capture_device = capture_device
        self.popen = popen
        self.edit_runner = edit_runner or self._run_voice_edit
        self.process: subprocess.Popen[bytes] | None = None
        self.state = RecordingState()
        self._voice_session_dir: Path | None = None
        self._voice_output: Path | None = None
        self._voice_segment_index = 0
        self._voice_working: Path | None = None
        self._voice_active_segment: Path | None = None
        self._voice_recording_started: float | None = None
        self._voice_recording_start_ms = 0
        self._voice_cursor_ms = 0
        self._voice_duration_ms = 0
        self._voice_timeline: deque[list[int]] = deque(maxlen=96)
        self._voice_levels: dict[int, int] = {1: 0, 2: 0}
        self._voice_stats_thread: threading.Thread | None = None
        self._voice_lock = threading.RLock()
        self._recover_voice_sessions()

    @staticmethod
    def _run_voice_edit(command: list[str]) -> None:
        try:
            subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise MediaError(f"cannot edit voice recording: {exc}") from exc

    def _probe_audio_duration_ms(self, source: Path) -> int:
        ffprobe = self.executable.with_name("ffprobe")
        try:
            result = subprocess.run(
                [
                    _target_path_string(ffprobe),
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(source),
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )
            return max(1, round(float(result.stdout.strip()) * 1000))
        except (OSError, ValueError, subprocess.SubprocessError):
            # Voice segments are fixed 160 kbit/s MP3. The bounded estimate is
            # only a last-resort crash recovery value when ffprobe cannot read
            # a partially closed file.
            return max(1, round(source.stat().st_size / 20))

    def command_line(self, source: str, output: Path) -> list[str]:
        return [
            _target_path_string(self.executable),
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-i",
            source,
            "-map",
            "0:a:0",
            "-c:a",
            "libopus",
            "-b:a",
            "64k",
            "-vn",
            str(output),
        ]

    def start(self, source: str) -> dict[str, Any]:
        if self.process is not None and self.process.poll() is None:
            raise MediaError("a recording is already active")
        approved = validate_media_source(source, self.media_roots)
        self.recordings_root.mkdir(parents=True, exist_ok=True, mode=0o750)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        output = self.recordings_root / f"recording-{stamp}.opus"
        try:
            self.process = self.popen(
                self.command_line(approved, output),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )
        except OSError as exc:
            self.state = RecordingState(state="error", error=str(exc))
            raise MediaError(f"cannot start ffmpeg recorder: {exc}") from exc
        self.state = RecordingState(
            state="recording",
            source=public_source_label(approved),
            output=output.name,
            mode="stream",
        )
        return self.state.as_dict()

    def voice_command_line(self, output: Path) -> list[str]:
        """Build the fixed stereo ALSA capture command and emit level metadata."""
        return [
            _target_path_string(self.executable),
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "info",
            "-f",
            "alsa",
            "-ac",
            "2",
            "-ar",
            "48000",
            "-i",
            self.capture_device,
            "-af",
            "asetpts=N/SR/TB,astats=metadata=1:reset=24,ametadata=print",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "160k",
            "-write_xing",
            "0",
            "-id3v2_version",
            "0",
            "-write_id3v1",
            "0",
            "-vn",
            str(output),
        ]

    def _new_voice_session(self) -> None:
        started = datetime.now()
        while True:
            day = started.strftime("%y%m%d")
            stem = started.strftime("%y%m%d_%H%M%S_VoiceRecorder")
            output = self.voice_root / day / f"{stem}.mp3"
            pending = self.voice_root / day / f".pending-{stem}"
            if not output.exists() and not pending.exists():
                break
            started += timedelta(seconds=1)
        pending.mkdir(parents=True, mode=0o750)
        self._voice_session_dir = pending
        self._voice_output = output
        self._voice_segment_index = 0
        self._voice_working = pending / "working.mp3"
        self._voice_active_segment = None
        self._voice_recording_started = None
        self._voice_recording_start_ms = 0
        self._voice_cursor_ms = 0
        self._voice_duration_ms = 0
        self._voice_timeline.clear()
        self._voice_levels = {1: 0, 2: 0}
        self._persist_voice_manifest()

    def _voice_manifest_path(self) -> Path | None:
        if self._voice_session_dir is None:
            return None
        return self._voice_session_dir / "edit.json"

    def _persist_voice_manifest(self) -> None:
        target = self._voice_manifest_path()
        if target is None:
            return
        payload = {
            "version": 1,
            "position_ms": self._voice_cursor_ms,
            "duration_ms": self._voice_duration_ms,
            "recording_start_ms": self._voice_recording_start_ms,
            "active_segment": (
                self._voice_active_segment.name
                if self._voice_active_segment is not None
                else None
            ),
        }
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, separators=(",", ":")), encoding="utf-8"
        )
        temporary.replace(target)

    def voice_seek(self, delta_ms: int) -> dict[str, Any]:
        if isinstance(delta_ms, bool) or not isinstance(delta_ms, int):
            raise ValueError("voice seek delta must be an integer")
        with self._voice_lock:
            if self.process is not None and self.process.poll() is None:
                raise MediaError("pause recording before changing position")
            self._voice_cursor_ms = max(
                0, min(self._voice_duration_ms, self._voice_cursor_ms + delta_ms)
            )
            self.state.position_ms = self._voice_cursor_ms
            self.state.duration_ms = self._voice_duration_ms
            self._persist_voice_manifest()
            return self.state.as_dict()

    def voice_boundary(self, *, end: bool) -> dict[str, Any]:
        with self._voice_lock:
            if self.process is not None and self.process.poll() is None:
                raise MediaError("pause recording before changing position")
            self._voice_cursor_ms = self._voice_duration_ms if end else 0
            self.state.position_ms = self._voice_cursor_ms
            self.state.duration_ms = self._voice_duration_ms
            self._persist_voice_manifest()
            return self.state.as_dict()

    def voice_set_position(self, position_ms: int) -> dict[str, Any]:
        if isinstance(position_ms, bool) or not isinstance(position_ms, int):
            raise ValueError("voice position must be an integer")
        with self._voice_lock:
            self._voice_cursor_ms = max(0, min(self._voice_duration_ms, position_ms))
            self.state.position_ms = self._voice_cursor_ms
            self.state.duration_ms = self._voice_duration_ms
            self._persist_voice_manifest()
            return self.state.as_dict()

    def voice_follow_playback(self, position_ms: int) -> dict[str, Any]:
        """Move the live playhead without writing the recovery manifest."""

        if isinstance(position_ms, bool) or not isinstance(position_ms, int):
            raise ValueError("voice position must be an integer")
        with self._voice_lock:
            self._voice_cursor_ms = max(0, min(self._voice_duration_ms, position_ms))
            self.state.position_ms = self._voice_cursor_ms
            self.state.duration_ms = self._voice_duration_ms
            return self.state.as_dict()

    def voice_playback_path(self) -> Path | None:
        with self._voice_lock:
            if self.process is not None and self.process.poll() is None:
                return None
            if self._voice_working is None or not self._voice_working.is_file():
                return None
            return self._voice_working

    def _voice_edit_command(
        self,
        working: Path,
        segment: Path,
        output: Path,
        *,
        cursor_ms: int,
        segment_ms: int,
        previous_duration_ms: int,
    ) -> list[str]:
        cursor = cursor_ms / 1000.0
        segment_duration = segment_ms / 1000.0
        suffix_start = min(previous_duration_ms / 1000.0, cursor + segment_duration)
        filters: list[str] = []
        inputs: list[str] = []
        if cursor_ms > 0:
            filters.append(
                f"[0:a]atrim=start=0:end={cursor:.3f},asetpts=PTS-STARTPTS[prefix]"
            )
            inputs.append("[prefix]")
        filters.append("[1:a]asetpts=PTS-STARTPTS[new]")
        inputs.append("[new]")
        if cursor_ms + segment_ms < previous_duration_ms:
            filters.append(
                f"[0:a]atrim=start={suffix_start:.3f},asetpts=PTS-STARTPTS[suffix]"
            )
            inputs.append("[suffix]")
        filters.append(f"{''.join(inputs)}concat=n={len(inputs)}:v=0:a=1[out]")
        return [
            _target_path_string(self.executable),
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-i",
            str(working),
            "-i",
            str(segment),
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[out]",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "160k",
            "-vn",
            str(output),
        ]

    def _commit_voice_segment(self, segment_ms: int) -> None:
        segment = self._voice_active_segment
        working = self._voice_working
        if segment is None or working is None or not segment.is_file():
            return
        segment_ms = max(1, segment_ms)
        start_ms = max(0, min(self._voice_duration_ms, self._voice_recording_start_ms))
        if not working.exists():
            segment.replace(working)
            self._voice_duration_ms = segment_ms
        elif start_ms >= self._voice_duration_ms:
            temporary = working.with_suffix(".append.tmp")
            with temporary.open("wb") as target:
                for source_path in (working, segment):
                    with source_path.open("rb") as source:
                        while chunk := source.read(1024 * 1024):
                            target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            temporary.replace(working)
            segment.unlink(missing_ok=True)
            self._voice_duration_ms += segment_ms
        else:
            temporary = working.with_suffix(".edit.tmp.mp3")
            command = self._voice_edit_command(
                working,
                segment,
                temporary,
                cursor_ms=start_ms,
                segment_ms=segment_ms,
                previous_duration_ms=self._voice_duration_ms,
            )
            self.edit_runner(command)
            if not temporary.is_file() or temporary.stat().st_size == 0:
                raise MediaError("voice edit did not create an output file")
            temporary.replace(working)
            segment.unlink(missing_ok=True)
            self._voice_duration_ms = max(
                self._voice_duration_ms, start_ms + segment_ms
            )
        self._voice_cursor_ms = min(
            self._voice_duration_ms, start_ms + segment_ms
        )
        self._voice_active_segment = None
        self._voice_recording_started = None
        self.state.position_ms = self._voice_cursor_ms
        self.state.duration_ms = self._voice_duration_ms
        self._persist_voice_manifest()

    @staticmethod
    def _level_percent(raw: str) -> int:
        try:
            decibels = float(raw)
        except ValueError:
            return 0
        if decibels == float("-inf"):
            return 0
        return max(0, min(100, round((decibels + 60.0) * (100.0 / 60.0))))

    def _consume_voice_level_line(self, raw: bytes | str) -> None:
        line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        match = re.search(
            r"lavfi\.astats\.(1|2)\.(?:RMS|Peak)_level=(-?(?:\d+(?:\.\d+)?|inf))",
            line,
            re.IGNORECASE,
        )
        if match is None:
            return
        channel = int(match.group(1))
        with self._voice_lock:
            self._voice_levels[channel] = self._level_percent(match.group(2))
            if channel == 2:
                # Channel 1 is the left microphone (drawn below), channel 2 is
                # the right microphone (drawn above).
                self._voice_timeline.append(
                    [self._voice_levels[1], self._voice_levels[2]]
                )
                self.state.timeline = list(self._voice_timeline)

    def _read_voice_levels(self, process: subprocess.Popen[bytes]) -> None:
        pin_current_thread_to_background_cores()
        stderr = getattr(process, "stderr", None)
        if stderr is None:
            return
        try:
            while True:
                raw = stderr.readline()
                if not raw:
                    break
                self._consume_voice_level_line(raw)
        except (OSError, ValueError):
            return

    def voice_start(self, *, continuous: bool = False) -> dict[str, Any]:
        with self._voice_lock:
            if self.process is not None and self.process.poll() is None:
                if self.state.mode == "voice":
                    self.state.continuous = continuous or self.state.continuous
                    return self.state.as_dict()
                raise MediaError("a stream recording is already active")
            if self._voice_session_dir is None or self._voice_output is None:
                self._new_voice_session()
            assert self._voice_session_dir is not None
            assert self._voice_output is not None
            self._voice_segment_index += 1
            segment = self._voice_session_dir / f"segment-{self._voice_segment_index:06d}.mp3"
            self._voice_active_segment = segment
            self._voice_recording_start_ms = self._voice_cursor_ms
            self._voice_recording_started = time.monotonic()
            self._persist_voice_manifest()
            try:
                self.process = self.popen(
                    self.voice_command_line(segment),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    close_fds=True,
                    start_new_session=True,
                )
                process_id = getattr(self.process, "pid", None)
                if isinstance(process_id, int):
                    pin_process_to_background_cores(process_id)
            except OSError as exc:
                self._voice_active_segment = None
                self._voice_recording_started = None
                self._persist_voice_manifest()
                self.state = RecordingState(
                    state="error", error=str(exc), mode="voice", session_active=True
                )
                raise MediaError(f"cannot start Whisplay voice recorder: {exc}") from exc
            self.state = RecordingState(
                state="recording",
                source="Whisplay microphones",
                output=self._voice_output.name,
                mode="voice",
                continuous=continuous,
                session_active=True,
                timeline=list(self._voice_timeline),
                position_ms=self._voice_cursor_ms,
                duration_ms=self._voice_duration_ms,
            )
            self._voice_stats_thread = threading.Thread(
                target=self._read_voice_levels,
                args=(self.process,),
                name="openr4d10-voice-levels",
                daemon=True,
            )
            self._voice_stats_thread.start()
            return self.state.as_dict()

    def _stop_active_process(self) -> None:
        process = self.process
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=0.35)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=0.35)
                except subprocess.TimeoutExpired:
                    killer = getattr(process, "kill", None)
                    if callable(killer):
                        killer()
                    process.wait(timeout=0.25)
        self.process = None
        thread = self._voice_stats_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1)
        self._voice_stats_thread = None

    def voice_pause(self) -> dict[str, Any]:
        with self._voice_lock:
            started = self._voice_recording_started
            estimated_ms = (
                max(1, round((time.monotonic() - started) * 1000))
                if started is not None
                else 1
            )
            self._stop_active_process()
            if self._voice_active_segment is not None:
                segment = self._voice_active_segment
                segment_ms = (
                    self._probe_audio_duration_ms(segment)
                    if segment.is_file() and segment.stat().st_size > 0
                    else estimated_ms
                )
                self._commit_voice_segment(segment_ms)
            self.state.state = "paused" if self._voice_session_dir is not None else "stopped"
            self.state.continuous = False
            self.state.session_active = self._voice_session_dir is not None
            self.state.timeline = list(self._voice_timeline)
            self.state.position_ms = self._voice_cursor_ms
            self.state.duration_ms = self._voice_duration_ms
            return self.state.as_dict()

    @staticmethod
    def _merge_voice_segments(session_dir: Path, output: Path) -> Path | None:
        working = session_dir / "working.mp3"
        segments = [item for item in sorted(session_dir.glob("segment-*.mp3")) if item.stat().st_size]
        if working.is_file() and working.stat().st_size:
            segments.insert(0, working)
        if not segments:
            return None
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
        temporary = output.with_suffix(".mp3.tmp")
        with temporary.open("wb") as target:
            for segment in segments:
                with segment.open("rb") as source:
                    while chunk := source.read(1024 * 1024):
                        target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        temporary.replace(output)
        for segment in segments:
            segment.unlink(missing_ok=True)
        (session_dir / "edit.json").unlink(missing_ok=True)
        (session_dir / "edit.json.tmp").unlink(missing_ok=True)
        try:
            session_dir.rmdir()
        except OSError:
            pass
        return output

    def _recover_voice_sessions(self) -> None:
        if not self.voice_root.exists():
            return
        for session_dir in sorted(self.voice_root.glob("[0-9][0-9][0-9][0-9][0-9][0-9]/.pending-*")):
            stem = session_dir.name.removeprefix(".pending-")
            if not re.fullmatch(r"\d{6}_\d{6}_VoiceRecorder", stem):
                continue
            try:
                manifest_path = session_dir / "edit.json"
                working = session_dir / "working.mp3"
                if manifest_path.is_file() and working.is_file():
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    active_name = manifest.get("active_segment")
                    cursor_ms = manifest.get("recording_start_ms")
                    duration_ms = manifest.get("duration_ms")
                    if (
                        isinstance(active_name, str)
                        and re.fullmatch(r"segment-\d{6}\.mp3", active_name)
                        and isinstance(cursor_ms, int)
                        and not isinstance(cursor_ms, bool)
                        and isinstance(duration_ms, int)
                        and not isinstance(duration_ms, bool)
                    ):
                        segment = session_dir / active_name
                        if segment.is_file() and segment.stat().st_size and cursor_ms < duration_ms:
                            segment_ms = self._probe_audio_duration_ms(segment)
                            temporary = working.with_suffix(".recover.tmp.mp3")
                            self.edit_runner(
                                self._voice_edit_command(
                                    working,
                                    segment,
                                    temporary,
                                    cursor_ms=max(0, cursor_ms),
                                    segment_ms=segment_ms,
                                    previous_duration_ms=max(0, duration_ms),
                                )
                            )
                            if not temporary.is_file() or temporary.stat().st_size == 0:
                                raise MediaError("voice recovery did not create an output file")
                            temporary.replace(working)
                            segment.unlink(missing_ok=True)
                self._merge_voice_segments(session_dir, session_dir.parent / f"{stem}.mp3")
            except (OSError, ValueError, json.JSONDecodeError, MediaError):
                continue

    def voice_finalize(self) -> dict[str, Any]:
        with self._voice_lock:
            self.voice_pause()
            output = self._voice_output
            session_dir = self._voice_session_dir
            finalized = None
            if output is not None and session_dir is not None:
                finalized = self._merge_voice_segments(session_dir, output)
            self._voice_session_dir = None
            self._voice_output = None
            self._voice_segment_index = 0
            self._voice_working = None
            self._voice_active_segment = None
            self._voice_recording_started = None
            self._voice_recording_start_ms = 0
            self._voice_cursor_ms = 0
            self._voice_duration_ms = 0
            self.state = RecordingState(
                state="stopped",
                output=finalized.name if finalized is not None else None,
                mode="voice",
                timeline=list(self._voice_timeline),
            )
            return self.state.as_dict()

    def voice_snapshot(self) -> dict[str, Any]:
        with self._voice_lock:
            self.state.timeline = list(self._voice_timeline)
            process_running = self.process is not None and self.process.poll() is None
            if (
                process_running
                and self.state.state == "recording"
                and self._voice_recording_started is not None
            ):
                elapsed_ms = max(
                    1,
                    round((time.monotonic() - self._voice_recording_started) * 1000),
                )
                live_position = self._voice_recording_start_ms + elapsed_ms
                self.state.position_ms = live_position
                self.state.duration_ms = max(self._voice_duration_ms, live_position)
            else:
                self.state.position_ms = self._voice_cursor_ms
                self.state.duration_ms = self._voice_duration_ms
                if self.state.state == "recording" and self.process is not None:
                    self.state.state = "error"
                    self.state.error = "microphone capture stopped unexpectedly"
                    self.state.continuous = False
            return self.state.as_dict()

    def stop(self) -> dict[str, Any]:
        self._stop_active_process()
        self.state.state = "stopped"
        self.state.source = None
        return self.state.as_dict()

    def close(self) -> None:
        if self._voice_session_dir is not None:
            self.voice_finalize()
        else:
            self.stop()
