"""Safe local media process boundaries for playback and stream recording."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import threading
from typing import Any, Callable
from urllib.parse import SplitResult, urlsplit, urlunsplit


class MediaError(RuntimeError):
    pass


MPV_IPC_TIMEOUT_SECONDS = 15.0


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
        except Exception:
            parent.close()
            child.close()
            raise
        child.close()
        parent.settimeout(MPV_IPC_TIMEOUT_SECONDS)
        self._ipc = parent
        self._buffer = b""

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
            if response.get("request_id") != request_id:
                continue
            if response.get("error") != "success":
                raise MediaError(f"mpv command failed: {response.get('error', 'unknown')}")
            return response

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

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


PopenFactory = Callable[..., subprocess.Popen[bytes]]


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
        self.process: subprocess.Popen[bytes] | None = None
        self.state = RecordingState()
        self._voice_session_dir: Path | None = None
        self._voice_output: Path | None = None
        self._voice_segment_index = 0
        self._voice_timeline: deque[list[int]] = deque(maxlen=96)
        self._voice_levels: dict[int, int] = {1: 0, 2: 0}
        self._voice_stats_thread: threading.Thread | None = None
        self._voice_lock = threading.RLock()
        self._recover_voice_sessions()

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
        self._voice_timeline.clear()
        self._voice_levels = {1: 0, 2: 0}

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
            try:
                self.process = self.popen(
                    self.voice_command_line(segment),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    close_fds=True,
                    start_new_session=True,
                )
            except OSError as exc:
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
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=2)
        self.process = None
        thread = self._voice_stats_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1)
        self._voice_stats_thread = None

    def voice_pause(self) -> dict[str, Any]:
        with self._voice_lock:
            self._stop_active_process()
            self.state.state = "paused" if self._voice_session_dir is not None else "stopped"
            self.state.continuous = False
            self.state.session_active = self._voice_session_dir is not None
            self.state.timeline = list(self._voice_timeline)
            return self.state.as_dict()

    @staticmethod
    def _merge_voice_segments(session_dir: Path, output: Path) -> Path | None:
        segments = [item for item in sorted(session_dir.glob("segment-*.mp3")) if item.stat().st_size]
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
                self._merge_voice_segments(session_dir, session_dir.parent / f"{stem}.mp3")
            except OSError:
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
