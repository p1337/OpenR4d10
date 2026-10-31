"""Bounded ICY radio pre-buffer and metadata-delimited track capture."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import re
import threading
from typing import Any, BinaryIO, Callable
from urllib.request import Request, urlopen

from .media import validate_media_source


_STREAM_TITLE = re.compile(r"(?:^|;)StreamTitle='((?:[^']|'')*)';?", re.IGNORECASE)
_SPACE = re.compile(r"\s+")


def parse_icy_metadata(payload: bytes) -> str | None:
    """Return the bounded ICY StreamTitle without trusting other metadata."""
    text = payload.rstrip(b"\0").decode("utf-8", errors="replace")[:4096]
    match = _STREAM_TITLE.search(text)
    if match is None:
        return None
    value = _SPACE.sub(" ", match.group(1).replace("''", "'")).strip()
    return value[:500] or None


def split_stream_title(value: str | None) -> tuple[str | None, str | None]:
    """Split the common ``Artist - Title`` form without inventing metadata."""
    if not value:
        return None, None
    for separator in (" - ", " – ", " — "):
        if separator in value:
            artist, title = value.split(separator, 1)
            artist = _SPACE.sub(" ", artist).strip()[:160]
            title = _SPACE.sub(" ", title).strip()[:240]
            if artist and title:
                return artist, title
    return None, None


@dataclass(frozen=True, slots=True)
class BufferedTrack:
    payload: bytes
    content_type: str
    stream_title: str | None
    artist: str | None
    title: str | None
    started_at: str
    truncated: bool


@dataclass(slots=True)
class RadioBufferState:
    state: str = "stopped"
    station: str | None = None
    stream_title: str | None = None
    artist: str | None = None
    title: str | None = None
    continuous: bool = False
    keep_current: bool = False
    buffered_bytes: int = 0
    saved_tracks: int = 0
    duplicate_tracks: int = 0
    error: str | None = None

    def public(self) -> dict[str, Any]:
        return asdict(self)


TrackHandler = Callable[[BufferedTrack], bool]
ResponseOpener = Callable[..., BinaryIO]


class IcyRadioBuffer:
    """Maintain one bounded raw-audio buffer and split it on ICY title changes."""

    def __init__(
        self,
        on_track: TrackHandler,
        *,
        opener: ResponseOpener = urlopen,
        max_track_bytes: int = 32 * 1024 * 1024,
    ) -> None:
        if max_track_bytes < 64 * 1024:
            raise ValueError("radio buffer must hold at least 64 KiB")
        self.on_track = on_track
        self.opener = opener
        self.max_track_bytes = max_track_bytes
        self.state = RadioBufferState()
        self._lock = threading.RLock()
        self._stop: threading.Event | None = None
        self._thread: threading.Thread | None = None
        self._response: BinaryIO | None = None
        self._buffer = bytearray()
        self._started_at = datetime.now(UTC).isoformat(timespec="seconds")
        self._truncated = False

    def set_continuous(self, enabled: bool) -> dict[str, Any]:
        if not isinstance(enabled, bool):
            raise ValueError("continuous recording state must be boolean")
        with self._lock:
            self.state.continuous = enabled
            return self.state.public()

    def tune(self, source: str, station: str) -> dict[str, Any]:
        approved = validate_media_source(source, ())
        if not isinstance(station, str) or not station.strip():
            raise ValueError("radio station name is required")
        self.stop(flush=True)
        stop = threading.Event()
        with self._lock:
            continuous = self.state.continuous
            saved = self.state.saved_tracks
            duplicates = self.state.duplicate_tracks
            self.state = RadioBufferState(
                state="connecting",
                station=station.strip()[:160],
                continuous=continuous,
                saved_tracks=saved,
                duplicate_tracks=duplicates,
            )
            self._stop = stop
            self._reset_track_locked()
        thread = threading.Thread(
            target=self._run,
            args=(approved, stop),
            name="openr4d10-radio-buffer",
            daemon=True,
        )
        self._thread = thread
        thread.start()
        return self.snapshot()

    def keep_current(self) -> dict[str, Any]:
        with self._lock:
            if self.state.state not in {"connecting", "buffering"}:
                raise RuntimeError("no radio stream is being buffered")
            self.state.keep_current = True
            return self.state.public()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self.state.public()

    def stop(self, *, flush: bool = True) -> dict[str, Any]:
        with self._lock:
            stop = self._stop
            response = self._response
            thread = self._thread
        if stop is not None:
            stop.set()
        if response is not None:
            try:
                response.close()
            except OSError:
                pass
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3)
        if flush:
            self._finalize_current()
        with self._lock:
            self._response = None
            self._stop = None
            self._thread = None
            self.state.state = "stopped"
            self.state.station = None
            self.state.keep_current = False
            self.state.buffered_bytes = 0
            self._buffer.clear()
            return self.state.public()

    def close(self) -> None:
        self.stop(flush=True)

    def _reset_track_locked(self) -> None:
        self._buffer.clear()
        self._started_at = datetime.now(UTC).isoformat(timespec="seconds")
        self._truncated = False
        self.state.stream_title = None
        self.state.artist = None
        self.state.title = None
        self.state.keep_current = False
        self.state.buffered_bytes = 0

    def _append_audio(self, payload: bytes) -> None:
        with self._lock:
            self._buffer.extend(payload)
            overflow = len(self._buffer) - self.max_track_bytes
            if overflow > 0:
                del self._buffer[:overflow]
                self._truncated = True
            self.state.buffered_bytes = len(self._buffer)

    def _metadata(self, stream_title: str | None) -> None:
        if stream_title is None:
            return
        with self._lock:
            current = self.state.stream_title
        if current is not None and stream_title != current:
            self._finalize_current()
            with self._lock:
                self._reset_track_locked()
        artist, title = split_stream_title(stream_title)
        with self._lock:
            self.state.stream_title = stream_title
            self.state.artist = artist
            self.state.title = title

    def _finalize_current(self) -> None:
        with self._lock:
            should_save = self.state.keep_current or self.state.continuous
            if not should_save or len(self._buffer) < 64 * 1024:
                return
            track = BufferedTrack(
                payload=bytes(self._buffer),
                content_type=getattr(self, "_content_type", "audio/mpeg"),
                stream_title=self.state.stream_title,
                artist=self.state.artist,
                title=self.state.title,
                started_at=self._started_at,
                truncated=self._truncated,
            )
            self.state.keep_current = False
        try:
            stored = self.on_track(track)
        except Exception as exc:  # keep the live buffer alive on storage failures
            with self._lock:
                self.state.error = f"cannot store buffered track: {exc}"
                self._buffer.clear()
                self.state.buffered_bytes = 0
            return
        with self._lock:
            self._buffer.clear()
            self.state.buffered_bytes = 0
            if stored:
                self.state.saved_tracks += 1
            else:
                self.state.duplicate_tracks += 1

    def _run(self, source: str, stop: threading.Event) -> None:
        request = Request(
            source,
            headers={
                "User-Agent": "OpenR4d10 (+https://github.com/p1337/OpenR4d10)",
                "Icy-MetaData": "1",
                "Accept": "audio/mpeg, audio/aac, audio/*;q=0.8",
            },
        )
        try:
            with self.opener(request, timeout=15) as response:
                with self._lock:
                    self._response = response
                    content_type = str(
                        response.headers.get("Content-Type", "audio/mpeg")
                    ).split(";", 1)[0].strip().lower()
                    if not content_type.startswith("audio/"):
                        raise ValueError(f"radio stream returned {content_type}")
                    self._content_type = content_type
                    self.state.state = "buffering"
                    self.state.error = None
                raw_interval = response.headers.get("icy-metaint")
                interval = int(raw_interval) if raw_interval else 0
                if interval <= 0:
                    while not stop.is_set():
                        payload = response.read(16 * 1024)
                        if not payload:
                            break
                        self._append_audio(payload)
                else:
                    while not stop.is_set():
                        audio = response.read(interval)
                        if not audio:
                            break
                        self._append_audio(audio)
                        size_byte = response.read(1)
                        if not size_byte:
                            break
                        metadata_size = size_byte[0] * 16
                        metadata = response.read(metadata_size) if metadata_size else b""
                        self._metadata(parse_icy_metadata(metadata))
        except Exception as exc:
            if not stop.is_set():
                with self._lock:
                    self.state.state = "error"
                    self.state.error = str(exc)[:500]
        finally:
            with self._lock:
                self._response = None
            self._finalize_current()

