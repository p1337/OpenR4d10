"""Receive-only BrandMeister HoseLine audio for the physical device."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import struct
import subprocess
import threading
from typing import Any, Callable
from urllib.request import Request, urlopen


LOG = logging.getLogger(__name__)

HOSELINE_ENDPOINT = "wss://hose.brandmeister.network/spotter/?token=test%3Atest"
HOSELINE_PROTOCOL = "spotter"
MAX_TALKGROUPS = 5
TALKGROUP_CATALOG_URL = "https://api.brandmeister.network/v2/talkgroup"


def _encode_unsigned(value: int) -> bytes:
    if value <= 0x7F:
        return bytes((value,))
    if value <= 0xFF:
        return bytes((0xCC, value))
    if value <= 0xFFFF:
        return bytes((0xCD, value >> 8, value & 0xFF))
    return bytes((0xCE,)) + value.to_bytes(4, "big")


def group_message(message_type: int, talkgroups: tuple[int, ...]) -> bytes:
    if not 0 <= len(talkgroups) <= MAX_TALKGROUPS:
        raise ValueError("one to five talkgroups are supported")
    return bytes((0x92, message_type, 0x90 + len(talkgroups))) + b"".join(
        _encode_unsigned(talkgroup) for talkgroup in talkgroups
    )


def country_code(talkgroup: int) -> str | None:
    """Return a conservative ISO code from a known DMR MCC prefix."""

    return {
        "204": "NL",
        "208": "FR",
        "214": "ES",
        "222": "IT",
        "228": "CH",
        "232": "AT",
        "234": "GB",
        "235": "GB",
        "260": "PL",
        "262": "DE",
        "268": "PT",
        "302": "CA",
        "310": "US",
        "311": "US",
        "312": "US",
        "313": "US",
        "314": "US",
        "315": "US",
        "316": "US",
        "505": "AU",
    }.get(str(talkgroup)[:3])


@dataclass(slots=True)
class BrandmeisterState:
    status: str = "stopped"
    talkgroups: tuple[int, ...] = ()
    destination: int | None = None
    source: int | None = None
    alias: str = ""
    volume: int = 30
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["talkgroups"] = list(self.talkgroups)
        value["country_code"] = (
            country_code(self.destination) if self.destination is not None else None
        )
        return value


Connector = Callable[..., Any]
Unpacker = Callable[[bytes], object]
PopenFactory = Callable[..., subprocess.Popen[bytes]]
StateCallback = Callable[[dict[str, object]], None]


def _default_connector(*args: object, **kwargs: object) -> Any:
    from websockets.sync.client import connect

    return connect(*args, **kwargs)


def _default_unpacker(payload: bytes) -> object:
    import msgpack

    return msgpack.unpackb(payload, raw=False, strict_map_key=False)


class BrandmeisterReceiver:
    """One bounded HoseLine subscription feeding the verified ALSA card."""

    def __init__(
        self,
        *,
        connector: Connector = _default_connector,
        unpacker: Unpacker = _default_unpacker,
        popen: PopenFactory = subprocess.Popen,
        audio_device: str = "whisplaysound",
        on_state: StateCallback | None = None,
    ) -> None:
        if not audio_device or len(audio_device) > 64:
            raise ValueError("a bounded ALSA device name is required")
        self.connector = connector
        self.unpacker = unpacker
        self.popen = popen
        self.audio_device = audio_device
        self.on_state = on_state
        self.state = BrandmeisterState()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._connection: Any = None
        self._audio: subprocess.Popen[bytes] | None = None

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return self.state.as_dict()

    def set_volume(self, volume: int) -> dict[str, object]:
        if isinstance(volume, bool) or not isinstance(volume, int) or not 0 <= volume <= 100:
            raise ValueError("volume must be an integer from 0 to 100")
        with self._lock:
            self.state.volume = volume
            snapshot = self.state.as_dict()
        self._notify(snapshot)
        return snapshot

    def listen(self, talkgroups: list[int] | tuple[int, ...]) -> dict[str, object]:
        normalized = tuple(dict.fromkeys(talkgroups))
        if not normalized or len(normalized) > MAX_TALKGROUPS:
            raise ValueError("one to five talkgroups are required")
        if any(
            isinstance(item, bool)
            or not isinstance(item, int)
            or item <= 90
            or item > 9_999_999
            for item in normalized
        ):
            raise ValueError("talkgroups must be integers from 91 through 9999999")
        self.stop()
        with self._lock:
            self._stop = threading.Event()
            self.state = BrandmeisterState(
                status="connecting",
                talkgroups=normalized,
                volume=self.state.volume,
            )
            thread = threading.Thread(
                target=self._run,
                args=(normalized, self._stop),
                name="openr4d10-brandmeister",
                daemon=True,
            )
            self._thread = thread
            snapshot = self.state.as_dict()
        self._notify(snapshot)
        thread.start()
        return snapshot

    def stop(self) -> dict[str, object]:
        with self._lock:
            stop = self._stop
            connection = self._connection
            thread = self._thread
        stop.set()
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3)
        self._stop_audio()
        with self._lock:
            volume = self.state.volume
            self._thread = None
            self._connection = None
            self.state = BrandmeisterState(volume=volume)
            snapshot = self.state.as_dict()
        self._notify(snapshot)
        return snapshot

    def close(self) -> None:
        self.stop()

    def _run(self, talkgroups: tuple[int, ...], stop: threading.Event) -> None:
        delay = 1.0
        while not stop.is_set():
            try:
                with self.connector(
                    HOSELINE_ENDPOINT,
                    subprotocols=[HOSELINE_PROTOCOL],
                    open_timeout=10,
                    close_timeout=3,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=1_048_576,
                    max_queue=16,
                    proxy=None,
                ) as connection:
                    with self._lock:
                        if stop.is_set():
                            return
                        self._connection = connection
                    connection.send(group_message(1, talkgroups))
                    self._set_state("listening", talkgroups=talkgroups, error=None)
                    delay = 1.0
                    while not stop.is_set():
                        try:
                            payload = connection.recv(timeout=1)
                        except TimeoutError:
                            continue
                        if isinstance(payload, bytes):
                            self._receive(payload)
            except Exception as exc:
                if stop.is_set():
                    break
                LOG.warning("BrandMeister HoseLine connection unavailable: %s", exc)
                self._set_state(
                    "reconnecting",
                    talkgroups=talkgroups,
                    error="HoseLine connection unavailable",
                )
                stop.wait(delay)
                delay = min(15.0, delay * 2)
            finally:
                with self._lock:
                    self._connection = None
                self._stop_audio()

    def _receive(self, payload: bytes) -> None:
        try:
            message = self.unpacker(payload)
        except Exception as exc:
            LOG.debug("Ignored malformed HoseLine packet: %s", exc)
            return
        if not isinstance(message, (list, tuple)) or not message:
            return
        kind = message[0]
        if kind == 11 and len(message) >= 4:
            source = message[2] if isinstance(message[2], int) else None
            destination = message[3] if isinstance(message[3], int) else None
            self._set_state(
                "call",
                source=source,
                destination=destination,
                alias="",
                error=None,
            )
        elif kind == 13:
            self._set_state(
                "listening",
                source=None,
                destination=None,
                alias="",
                error=None,
            )
        elif kind == 20 and len(message) >= 2 and isinstance(message[1], bytes):
            self._play(message[1])
        elif kind == 21 and len(message) >= 2:
            self._set_state("call", alias=str(message[1] or "")[:80])
        elif kind == 80:
            self._set_state("error", error="HoseLine rejected the subscription")

    def _set_state(self, status: str, **changes: object) -> None:
        with self._lock:
            self.state.status = status
            for key, value in changes.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)
            snapshot = self.state.as_dict()
        self._notify(snapshot)

    def _notify(self, snapshot: dict[str, object]) -> None:
        if self.on_state is not None:
            try:
                self.on_state(snapshot)
            except Exception:
                LOG.exception("BrandMeister state callback failed")

    def _audio_process(self) -> subprocess.Popen[bytes]:
        with self._lock:
            if self._audio is not None and self._audio.poll() is None:
                return self._audio
            self._audio = self.popen(
                [
                    "/usr/bin/aplay",
                    "-q",
                    "-D",
                    self.audio_device,
                    "-t",
                    "raw",
                    "-f",
                    "S16_LE",
                    "-r",
                    "8000",
                    "-c",
                    "1",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )
            return self._audio

    def _play(self, packet: bytes) -> None:
        if not packet:
            return
        with self._lock:
            gain = self.state.volume / 100.0
        pcm = bytearray(len(packet) * 2)
        for index, value in enumerate(packet):
            sample = (~value) & 0xFF
            sign = sample & 0x80
            exponent = (sample >> 4) & 0x07
            mantissa = sample & 0x0F
            base = (0, 132, 396, 924, 1980, 4092, 8316, 16764)[exponent]
            magnitude = base + (mantissa << (exponent + 3))
            decoded = -magnitude if sign else magnitude
            scaled = max(-32768, min(32767, round(decoded * gain)))
            struct.pack_into("<h", pcm, index * 2, scaled)
        try:
            process = self._audio_process()
            if process.stdin is None:
                raise BrokenPipeError("aplay stdin is unavailable")
            process.stdin.write(pcm)
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            LOG.warning("BrandMeister audio output unavailable: %s", exc)
            self._stop_audio()
            self._set_state("error", error="Whisplay audio output unavailable")

    def _stop_audio(self) -> None:
        with self._lock:
            process = self._audio
            self._audio = None
        if process is None:
            return
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)


class BrandmeisterTalkgroupCatalog:
    """Bounded cache of the official public BrandMeister talkgroup names."""

    def __init__(self, cache_file: Path, *, max_age_seconds: int = 86_400) -> None:
        if not cache_file.is_absolute():
            raise ValueError("BrandMeister catalog cache path must be absolute")
        self.cache_file = cache_file
        self.max_age_seconds = max_age_seconds
        self._lock = threading.Lock()

    def payload(self) -> bytes:
        with self._lock:
            cached = self._cached(fresh_only=True)
            if cached is not None:
                return cached
            try:
                request = Request(
                    TALKGROUP_CATALOG_URL,
                    headers={"User-Agent": "OpenR4d10 (+https://github.com/p1337/OpenR4d10)"},
                )
                with urlopen(request, timeout=15) as response:
                    if response.status != 200:
                        raise OSError(f"BrandMeister catalog HTTP {response.status}")
                    raw = response.read(262_145)
                if len(raw) > 262_144:
                    raise ValueError("BrandMeister catalog exceeds the size limit")
                decoded = json.loads(raw)
                if not isinstance(decoded, dict):
                    raise ValueError("BrandMeister catalog must be an object")
                entries = []
                for raw_id, raw_name in decoded.items():
                    try:
                        talkgroup = int(raw_id)
                    except (TypeError, ValueError):
                        continue
                    if not 90 < talkgroup <= 9_999_999 or not isinstance(raw_name, str):
                        continue
                    name = " ".join(raw_name.split())[:160]
                    if name:
                        entries.append(
                            {
                                "talkgroup": talkgroup,
                                "name": name,
                                "country_code": country_code(talkgroup),
                            }
                        )
                entries.sort(key=lambda item: int(item["talkgroup"]))
                payload = json.dumps(
                    {
                        "source": TALKGROUP_CATALOG_URL,
                        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                        "talkgroups": entries[:10_000],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                self.cache_file.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
                temporary = self.cache_file.with_suffix(".tmp")
                temporary.write_bytes(payload)
                try:
                    temporary.chmod(0o640)
                except OSError:
                    pass
                os.replace(temporary, self.cache_file)
                return payload
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                cached = self._cached(fresh_only=False)
                if cached is not None:
                    LOG.warning("Using stale BrandMeister talkgroup catalog: %s", exc)
                    return cached
                raise OSError("BrandMeister talkgroup catalog is unavailable") from exc

    def _cached(self, *, fresh_only: bool) -> bytes | None:
        try:
            stat = self.cache_file.stat()
            if fresh_only and datetime.now().timestamp() - stat.st_mtime > self.max_age_seconds:
                return None
            payload = self.cache_file.read_bytes()
            decoded = json.loads(payload)
            if not isinstance(decoded, dict) or not isinstance(decoded.get("talkgroups"), list):
                return None
            return payload
        except (OSError, ValueError, json.JSONDecodeError):
            return None
