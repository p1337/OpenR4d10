"""Central catalog and readiness model for OpenR4d10 service modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import logging
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import threading
import time
from typing import Callable
import unicodedata
import uuid
from urllib.parse import urlsplit

from .content import (
    CameraSnapshot,
    ContentError,
    DWD_RADAR_GIF_URL,
    DwdSatelliteFrames,
    FeedReader,
    PresetArtwork,
    TrackArtwork,
)
from .media import MpvEngine, StreamRecorder, public_source_label, validate_media_source
from .presets import FEED_BY_ID, FEED_PRESETS, RADIO_BY_ID, RADIO_PRESETS
from .radio_capture import BufferedTrack, IcyRadioBuffer
from .service_adapters import ServiceAdapterError, ServiceAdapterRegistry
from .storage import SCHEMA_VERSION, StateStore


ExecutableLookup = Callable[[str], str | None]
MEDIA_EXTENSIONS = {
    ".aac", ".flac", ".m4a", ".mka", ".mp3", ".mp4", ".ogg", ".opus", ".wav",
}
DEFAULT_ENABLED_SERVICES = {
    "system", "webradio", "weather", "local_media", "recorder", "rss", "webcam",
}
DISPLAY_BRIGHTNESS_KEY = "display.brightness_percent"
DEFAULT_DISPLAY_BRIGHTNESS = 100
UI_ACCENT_COLOR_KEY = "ui.accent_color"
DEFAULT_UI_ACCENT_COLOR = "#FDB813"
UI_LANGUAGE_KEY = "ui.language"
DEFAULT_UI_LANGUAGE = "en"
SUPPORTED_UI_LANGUAGES = frozenset({"en", "de", "pl", "fr", "es"})
RADAR_DEFAULT_MIGRATION_KEY = "weather.radar_default_v1"
GERMANY_SATELLITE_MIGRATION_KEY = "weather.germany_satellite_v1"
RADIO_DEFAULTS_V2_MIGRATION_KEY = "radio.defaults_seeded_v2"
RADIO_CONTINUOUS_KEY = "radio.continuous_recording"
LAST_VIEW_KEY = "ui.last_view_service"
RADIO_V2_PRESET_IDS = {"die_neue_1077", "afn_eagle", "rock_antenne", "rock_fm"}

LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ServiceManifest:
    service_id: str
    name: str
    category: str
    description: str
    capabilities: tuple[str, ...]
    implementation: str
    required_executables: tuple[str, ...] = ()
    requires_credentials: bool = False
    credential_hint: str | None = None


BUILTIN_SERVICES = (
    ServiceManifest("system", "System", "core", "Status, updates and diagnostics", ("status", "diagnostics"), "native"),
    ServiceManifest("webradio", "Web Radio", "audio", "Internet radio playback and favorites", ("playback", "favorites", "recording"), "process", ("mpv",)),
    ServiceManifest("weather", "Weather", "information", "DWD rain radar and satellite image loops", ("images", "channels"), "native"),
    ServiceManifest("local_media", "Local Media", "audio", "Local MP3, FLAC, MP4 and recordings", ("playback", "library"), "process", ("mpv",)),
    ServiceManifest("recorder", "Recorder", "audio", "Record supported audio sources", ("recording", "library"), "process", ("ffmpeg",)),
    ServiceManifest("brandmeister", "BrandMeister", "radio", "DMR audio over a configured lawful gateway", ("playback", "talkgroups", "recording"), "external", requires_credentials=True, credential_hint="Configure an individual BrandMeister-compatible account or gateway locally."),
    ServiceManifest("remote_sdr", "Remote SDR", "radio", "OpenWebRX or another configured remote receiver", ("playback", "channels", "squelch"), "external"),
    ServiceManifest("private_ptt", "Private PTT", "voice", "Private push-to-talk between explicitly paired devices", ("ptt", "playback", "recording"), "external", requires_credentials=True, credential_hint="Pair devices locally; never ship a shared key."),
    ServiceManifest("mumble", "Mumble", "voice", "Mumble voice and push-to-talk", ("ptt", "channels"), "external", requires_credentials=True, credential_hint="Enter the user's own server and account locally."),
    ServiceManifest("discord", "Discord", "voice", "Official Discord application/bot integration", ("ptt", "channels", "messages"), "official_api", requires_credentials=True, credential_hint="Use an individual official OAuth or app flow."),
    ServiceManifest("telegram", "Telegram", "messages", "Messages and voice notes through a local TDLib adapter", ("messages", "voice_notes", "tts"), "external", requires_credentials=True, credential_hint="Complete Telegram login locally through TDLib."),
    ServiceManifest("rss", "Feeds", "information", "RSS and Atom subscriptions with optional read-aloud", ("feeds", "tts"), "native"),
    ServiceManifest("webcam", "Webcams", "video", "Up to two configured still-image or live views", ("images", "video"), "process", ("ffmpeg",)),
    ServiceManifest("youtube_audio", "YouTube Audio", "media", "Audio access only where technically and legally permitted", ("playback", "library"), "external"),
    ServiceManifest("spotify", "Spotify", "media", "Spotify Connect through a user-configured compatible client", ("playback",), "external", requires_credentials=True, credential_hint="Use the user's own eligible Spotify account locally."),
    ServiceManifest("ard_mediathek", "ARD Mediathek", "media", "Officially accessible ARD audio and media", ("catalog", "playback"), "external"),
    ServiceManifest("zdf_mediathek", "ZDF Mediathek", "media", "Officially accessible ZDF audio and media", ("catalog", "playback"), "external"),
    ServiceManifest("international_media", "International Media", "media", "Configured public broadcasters and news sources", ("catalog", "playback"), "external"),
    ServiceManifest("speech", "Speech", "accessibility", "Offline German dictation, commands and read-aloud", ("stt", "tts"), "external"),
    ServiceManifest("bluetooth_audio", "Bluetooth Audio", "audio", "Bluetooth audio and HID routing", ("playback", "hid"), "external"),
    ServiceManifest("codex_remote", "Codex Remote", "tools", "Client for a user-configured remote Codex/API service", ("client",), "official_api", requires_credentials=True, credential_hint="Use the user's own account through an official login or API flow."),
    ServiceManifest("teamspeak", "TeamSpeak", "voice", "Optional supported external TeamSpeak integration", ("ptt", "channels"), "external", requires_credentials=True, credential_hint="Configure an individually licensed client/server locally."),
)


class ServiceCatalog:
    def __init__(
        self,
        state_directory: Path,
        *,
        executable_lookup: ExecutableLookup = shutil.which,
        player: MpvEngine | None = None,
        recorder: StreamRecorder | None = None,
        feed_reader: FeedReader | None = None,
        camera: CameraSnapshot | None = None,
        artwork: PresetArtwork | None = None,
        track_artwork: TrackArtwork | None = None,
        weather: DwdSatelliteFrames | None = None,
        radio_buffer: IcyRadioBuffer | None = None,
        adapter_directory: Path | None = None,
        adapter_registry: ServiceAdapterRegistry | None = None,
    ) -> None:
        self.store = StateStore(state_directory / "openr4d10.sqlite3")
        self.executable_lookup = executable_lookup
        self.media_root = state_directory / "media"
        self.cover_root = state_directory / "cache" / "track-covers"
        self.player = player or MpvEngine(media_roots=(self.media_root,))
        self.recorder = recorder or StreamRecorder(
            state_directory / "recordings",
            media_roots=(self.media_root,),
        )
        self.feed_reader = feed_reader or FeedReader()
        self.camera = camera or CameraSnapshot(state_directory / "cache")
        self.artwork = artwork or PresetArtwork(state_directory / "cache")
        self.track_artwork = track_artwork or TrackArtwork(self.cover_root)
        self.weather = weather or DwdSatelliteFrames(state_directory / "cache")
        self.radio_buffer = radio_buffer or (
            IcyRadioBuffer(self._store_buffered_track) if player is None else None
        )
        self._artwork_pending: set[str] = set()
        self._artwork_guard = threading.Lock()
        self._weather_pending: set[str] = set()
        self._weather_guard = threading.Lock()
        self._worker_threads: set[threading.Thread] = set()
        self._worker_guard = threading.Lock()
        external_ids = {
            item.service_id
            for item in BUILTIN_SERVICES
            if item.implementation in {"external", "official_api"}
        }
        self.adapters = adapter_registry or (
            ServiceAdapterRegistry.from_directory(adapter_directory, external_ids)
            if adapter_directory is not None
            else ServiceAdapterRegistry()
        )
        self.content_state: dict[str, object] = {
            "feed": None,
            "cameras": {},
        }
        self.active_service = "system"
        self.active_preset_id: str | None = None
        self.active_station_id: int | None = None
        self.active_weather_channel_id: int | None = None
        self.store.ensure_services(
            tuple(item.service_id for item in BUILTIN_SERVICES),
            DEFAULT_ENABLED_SERVICES,
        )
        self.store.seed_stations_once(
            "webradio",
            tuple((item.name, item.stream_url) for item in RADIO_PRESETS),
            marker="radio.defaults_seeded_v1",
        )
        self.store.seed_stations_once(
            "webradio",
            tuple(
                (item.name, item.stream_url)
                for item in RADIO_PRESETS
                if item.preset_id in RADIO_V2_PRESET_IDS
            ),
            marker=RADIO_DEFAULTS_V2_MIGRATION_KEY,
            append=True,
        )
        self.store.seed_channels_once(
            "weather",
            (
                (
                    "dwd-deutschland",
                    "Regenradar Deutschland",
                    {
                        "bbox": [47.0, 5.0, 55.5, 16.0],
                        "kind": "radar_gif",
                        "provider": "DWD",
                        "source_url": DWD_RADAR_GIF_URL,
                    },
                ),
                (
                    "dwd-deutschland-satellit",
                    "Satellit Deutschland",
                    {
                        "bbox": [47.0, 5.0, 55.5, 16.0],
                        "kind": "satellite_wms",
                        "provider": "DWD / EUMETSAT",
                    },
                ),
                (
                    "dwd-europa",
                    "Europa",
                    {
                        "bbox": [30.0, -25.0, 72.0, 45.0],
                        "kind": "satellite_wms",
                        "provider": "DWD / EUMETSAT",
                    },
                ),
            ),
            marker="weather.defaults_seeded_v1",
        )
        self._upgrade_germany_weather_default()
        self._seed_germany_satellite_upgrade()
        weather_channels = self.store.channels("weather")
        if weather_channels:
            self.active_weather_channel_id = int(weather_channels[0]["id"])
        if self.radio_buffer is not None:
            self.radio_buffer.set_continuous(
                self.store.get_setting(RADIO_CONTINUOUS_KEY, False) is True
            )
        self._initial_view_resolved = False

    def _upgrade_germany_weather_default(self) -> None:
        """Change only the untouched seeded Germany channel; never recreate it."""
        if self.store.get_setting(RADAR_DEFAULT_MIGRATION_KEY, False) is True:
            return
        germany = next(
            (
                item
                for item in self.store.channels("weather")
                if item["external_id"] == "dwd-deutschland"
            ),
            None,
        )
        if germany is not None:
            metadata = germany.get("metadata")
            if isinstance(metadata, dict) and metadata.get("kind") is None:
                name = (
                    "Regenradar Deutschland"
                    if germany["name"] == "Deutschland"
                    else str(germany["name"])
                )
                self.store.update_channel(
                    int(germany["id"]),
                    name,
                    {
                        "bbox": metadata.get("bbox", [47.0, 5.0, 55.5, 16.0]),
                        "kind": "radar_gif",
                        "provider": "DWD",
                        "source_url": DWD_RADAR_GIF_URL,
                    },
                )
        self.store.set_setting(RADAR_DEFAULT_MIGRATION_KEY, True)

    def _seed_germany_satellite_upgrade(self) -> None:
        """Append the retained satellite view once without resetting user order."""
        if self.store.get_setting(GERMANY_SATELLITE_MIGRATION_KEY, False) is True:
            return
        external_id = "dwd-deutschland-satellit"
        if not any(
            item["external_id"] == external_id
            for item in self.store.channels("weather")
        ):
            self.store.add_channel(
                "weather",
                external_id,
                "Satellit Deutschland",
                {
                    "bbox": [47.0, 5.0, 55.5, 16.0],
                    "kind": "satellite_wms",
                    "provider": "DWD / EUMETSAT",
                },
            )
        self.store.set_setting(GERMANY_SATELLITE_MIGRATION_KEY, True)

    def display_brightness(self) -> int:
        value = self.store.get_setting(
            DISPLAY_BRIGHTNESS_KEY,
            DEFAULT_DISPLAY_BRIGHTNESS,
        )
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            LOG.warning("Ignoring invalid persisted display brightness: %r", value)
            return DEFAULT_DISPLAY_BRIGHTNESS
        return value

    def set_display_brightness(self, brightness_percent: int) -> int:
        if (
            isinstance(brightness_percent, bool)
            or not isinstance(brightness_percent, int)
            or not 0 <= brightness_percent <= 100
        ):
            raise ValueError("display brightness must be an integer from 0 to 100")
        self.store.set_setting(DISPLAY_BRIGHTNESS_KEY, brightness_percent)
        return brightness_percent

    def display_appearance(self) -> dict[str, object]:
        accent = self.store.get_setting(UI_ACCENT_COLOR_KEY, DEFAULT_UI_ACCENT_COLOR)
        if not isinstance(accent, str) or re.fullmatch(r"#[0-9A-Fa-f]{6}", accent) is None:
            LOG.warning("Ignoring invalid persisted UI accent color: %r", accent)
            accent = DEFAULT_UI_ACCENT_COLOR
        return {"accent_color": accent.upper()}

    def set_display_appearance(
        self,
        accent_color: str,
    ) -> dict[str, object]:
        if not isinstance(accent_color, str) or re.fullmatch(
            r"#[0-9A-Fa-f]{6}", accent_color
        ) is None:
            raise ValueError("accent color must use #RRGGBB")
        normalized = accent_color.upper()
        self.store.set_setting(UI_ACCENT_COLOR_KEY, normalized)
        return {"accent_color": normalized}

    def display_language(self) -> str:
        value = self.store.get_setting(UI_LANGUAGE_KEY, DEFAULT_UI_LANGUAGE)
        if not isinstance(value, str) or value not in SUPPORTED_UI_LANGUAGES:
            LOG.warning("Ignoring invalid persisted UI language: %r", value)
            return DEFAULT_UI_LANGUAGE
        return value

    def set_display_language(self, language: str) -> str:
        if not isinstance(language, str):
            raise ValueError("display language must be a supported language code")
        normalized = language.casefold().split("-", 1)[0]
        if normalized not in SUPPORTED_UI_LANGUAGES:
            raise ValueError("display language must be one of en, de, pl, fr or es")
        self.store.set_setting(UI_LANGUAGE_KEY, normalized)
        return normalized

    @staticmethod
    def _track_part(value: str, fallback: str, limit: int) -> str:
        cleaned = unicodedata.normalize("NFKC", value or "")
        cleaned = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-")
        return (cleaned or fallback)[:limit].rstrip(" .")

    @staticmethod
    def _track_key(artist: str | None, title: str | None) -> str | None:
        if not artist or not title:
            return None
        value = unicodedata.normalize("NFKD", f"{artist}\0{title}").casefold()
        return "".join(character for character in value if character.isalnum())[:500]

    def _fingerprint(self, path: Path) -> str | None:
        executable = self.executable_lookup("fpcalc")
        if executable is None:
            return None
        try:
            result = subprocess.run(
                [executable, "-raw", "-length", "120", str(path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode != 0:
            return None
        fingerprint = next(
            (
                line.removeprefix(b"FINGERPRINT=")
                for line in result.stdout.splitlines()
                if line.startswith(b"FINGERPRINT=")
            ),
            b"",
        )
        return hashlib.sha256(fingerprint).hexdigest() if fingerprint else None

    def _store_buffered_track(self, track: BufferedTrack) -> bool:
        checksum = hashlib.sha256(track.payload).hexdigest()
        artist = self._track_part(track.artist or "", "Unbekannt", 120)
        title_fallback = "Aufnahme " + track.started_at.replace(":", "-")
        title = self._track_part(track.title or "", title_fallback, 180)
        normalized_key = self._track_key(track.artist, track.title)
        if self.store.media_duplicate(normalized_key, None, checksum) is not None:
            return False
        artist_root = (self.media_root / "recorded" / artist).resolve()
        media_root = self.media_root.resolve()
        if not artist_root.is_relative_to(media_root):
            raise ValueError("recorded track path escaped the media root")
        artist_root.mkdir(parents=True, exist_ok=True, mode=0o750)
        suffix = ".mp3" if "mpeg" in track.content_type else ".aac"
        basename = self._track_part(f"{artist} – {title}", "Unbekannt – Aufnahme", 220)
        output = artist_root / f"{basename}{suffix}"
        if output.exists():
            output = artist_root / f"{basename} – {checksum[:8]}{suffix}"
        temporary = output.with_name(output.stem + ".part" + output.suffix)
        temporary.write_bytes(track.payload)
        try:
            fingerprint = self._fingerprint(temporary)
            if self.store.media_duplicate(normalized_key, fingerprint, checksum) is not None:
                temporary.unlink(missing_ok=True)
                return False
            os.replace(temporary, output)
            media_id = self.store.add_recorded_media(
                output,
                artist=track.artist and artist,
                title=title,
                size_bytes=output.stat().st_size,
                checksum=checksum,
                normalized_key=normalized_key,
                fingerprint=fingerprint,
                review_required=(
                    track.artist is None or track.title is None or track.truncated
                ),
            )
        except Exception:
            temporary.unlink(missing_ok=True)
            output.unlink(missing_ok=True)
            raise
        if track.artist and track.title:
            self._cache_track_artwork(media_id, artist, title)
        return True

    def _cache_track_artwork(self, media_id: int, artist: str, title: str) -> None:
        def cache() -> None:
            try:
                path = self.track_artwork.ensure(media_id, artist, title)
                self.store.set_media_cover(media_id, path.name)
            except (ContentError, OSError, ValueError) as exc:
                LOG.info("Track cover unavailable for %s – %s: %s", artist, title, exc)

        self._start_worker(f"openr4d10-track-cover-{media_id}", cache)

    def snapshot(self) -> dict[str, object]:
        states = self.store.service_states()
        services: list[dict[str, object]] = []
        manifests = sorted(
            BUILTIN_SERVICES,
            key=lambda item: (int(states[item.service_id]["position"]), item.service_id),
        )
        for manifest in manifests:
            state = states[manifest.service_id]
            missing = [
                executable
                for executable in manifest.required_executables
                if self.executable_lookup(executable) is None
            ]
            adapter_state: dict[str, object] = {
                "configured": self.adapters.configured(manifest.service_id)
            }
            if not state["enabled"]:
                readiness = "disabled"
            elif missing:
                readiness = "missing_dependency"
            elif manifest.implementation in {"external", "official_api"}:
                if not self.adapters.configured(manifest.service_id):
                    readiness = "configuration_required"
                else:
                    try:
                        adapter_status = self.adapters.status(manifest.service_id)
                        adapter_state["status"] = adapter_status.get("status", "ready")
                        readiness = (
                            "ready" if adapter_status.get("ready") is True
                            else "configuration_required"
                        )
                    except ServiceAdapterError as exc:
                        adapter_state["status"] = "error"
                        adapter_state["error"] = str(exc)
                        readiness = "adapter_error"
            elif manifest.requires_credentials and state["config_state"] != "ready":
                readiness = "configuration_required"
            else:
                readiness = "ready"
            item = asdict(manifest)
            item.update(state)
            item["missing_executables"] = missing
            item["readiness"] = readiness
            if manifest.implementation in {"external", "official_api"}:
                item["adapter"] = adapter_state
            services.append(item)
        stations = []
        for channel, item in enumerate(self.store.stations(), start=1):
            preset = self._preset_for_station(item)
            stations.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "source": public_source_label(str(item["stream_url"])),
                    "favorite": bool(item["favorite"]),
                    "position": channel - 1,
                    "channel": channel,
                    "preset_id": preset.preset_id if preset is not None else None,
                    "country": preset.country if preset is not None else "Eigener Sender",
                    "genre": preset.genre if preset is not None else "Webradio",
                    "artwork": (
                        f"/api/radio-art/{preset.preset_id}"
                        if preset is not None else None
                    ),
                }
            )
        media = [
            {
                "id": item["id"],
                "artist": item["artist"],
                "title": item["title"],
                "size_bytes": item["size_bytes"],
                "favorite": bool(item["favorite"]),
                "review_required": bool(item["review_required"]),
                "source_kind": item["source_kind"],
                "cover": (
                    f"/api/media-cover/{item['id']}"
                    if item["cover_file"]
                    else None
                ),
            }
            for item in self.store.media_items()
        ]
        weather_channels = []
        for channel, item in enumerate(self.store.channels("weather"), start=1):
            metadata = item.get("metadata")
            bbox = metadata.get("bbox") if isinstance(metadata, dict) else None
            provider = (
                str(metadata.get("provider") or "DWD / EUMETSAT")
                if isinstance(metadata, dict)
                else "DWD / EUMETSAT"
            )
            kind = (
                str(metadata.get("kind") or "satellite_wms")
                if isinstance(metadata, dict)
                else "satellite_wms"
            )
            frames = self.weather.frames(str(item["external_id"]))
            weather_channels.append(
                {
                    "id": int(item["id"]),
                    "external_id": str(item["external_id"]),
                    "name": str(item["name"]),
                    "position": channel - 1,
                    "channel": channel,
                    "bbox": bbox,
                    "provider": provider,
                    "kind": kind,
                    "active": int(item["id"]) == self.active_weather_channel_id,
                    "frames": [
                        {
                            **frame,
                            "url": f"/api/weather-frame/{frame['file']}",
                        }
                        for frame in frames
                    ],
                }
            )
        return {
            "schema_version": SCHEMA_VERSION,
            "settings": {
                "display_brightness_percent": self.display_brightness(),
                "language": self.display_language(),
                **self.display_appearance(),
            },
            "total": len(services),
            "ready": sum(item["readiness"] == "ready" for item in services),
            "active_service": self.active_service,
            "selected_preset": self._selected_preset(),
            "playback": self.player.state.as_dict(),
            "recording": self.recorder.state.as_dict(),
            "radio_buffer": (
                self.radio_buffer.snapshot()
                if self.radio_buffer is not None
                else {
                    "state": "unavailable",
                    "continuous": False,
                    "error": "radio pre-buffer is unavailable",
                }
            ),
            "content": self.content_state,
            "presets": {
                "stations": [item.public() for item in RADIO_PRESETS],
                "feeds": [item.public() for item in FEED_PRESETS],
            },
            "stations": stations,
            "weather": {
                "active_channel_id": self.active_weather_channel_id,
                "channels": weather_channels,
                "provider": "DWD / EUMETSAT",
                "refresh_floor_seconds": 300,
            },
            "media": media,
            "items": services,
        }

    def control(self, request: dict[str, object]) -> dict[str, object]:
        action = request.get("action")
        if not isinstance(action, str):
            raise ValueError("control action is required")
        if action == "service_set_enabled":
            service_id = request.get("service_id")
            enabled = request.get("enabled")
            known = {item.service_id for item in BUILTIN_SERVICES}
            if not isinstance(service_id, str) or service_id not in known:
                raise ValueError("unknown service")
            if not isinstance(enabled, bool):
                raise ValueError("enabled must be true or false")
            if service_id == "system" and not enabled:
                raise ValueError("system service cannot be disabled")
            if not enabled:
                if self.active_service == service_id:
                    self.player.stop()
                    if service_id == "webradio" and self.radio_buffer is not None:
                        self.radio_buffer.stop(flush=True)
                    self.active_service = "system"
                    self.active_preset_id = None
                    self.active_station_id = None
                if service_id == "recorder":
                    self.recorder.stop()
            self.store.set_service_enabled(service_id, enabled)
            return {"service_id": service_id, "enabled": enabled}
        if action == "service_move":
            service_id = request.get("service_id")
            direction = request.get("direction")
            known = {item.service_id for item in BUILTIN_SERVICES}
            if not isinstance(service_id, str) or service_id not in known:
                raise ValueError("unknown service")
            if isinstance(direction, bool) or not isinstance(direction, int):
                raise ValueError("service_move requires an integer direction")
            return {"moved": self.store.move_service(service_id, direction)}
        if action == "play":
            service_id = request.get("service_id", "webradio")
            source = request.get("source")
            allowed = {
                "webradio", "local_media", "brandmeister", "remote_sdr",
                "youtube_audio", "spotify", "ard_mediathek", "zdf_mediathek",
                "international_media",
            }
            if not isinstance(service_id, str) or service_id not in allowed:
                raise ValueError("unsupported playback service")
            self._require_enabled(service_id)
            if not isinstance(source, str):
                raise ValueError("play action requires a media source")
            self.player.load(source)
            if service_id == "webradio" and self.radio_buffer is not None:
                self.radio_buffer.tune(source, "Direkte Radioquelle")
            self.active_service = service_id
            self.active_preset_id = None
            self.active_station_id = None
        elif action == "pause":
            if self.player.state.state not in {"playing", "paused"}:
                raise ValueError("no active media to pause or resume")
            self.player.toggle_pause()
        elif action == "stop":
            self.player.stop()
            if self.radio_buffer is not None:
                self.radio_buffer.stop(flush=True)
            self.active_service = "system"
            self.active_preset_id = None
            self.active_station_id = None
        elif action == "volume":
            self.player.set_volume(request.get("value"))  # type: ignore[arg-type]
        elif action == "volume_step":
            steps = request.get("steps")
            if (
                isinstance(steps, bool)
                or not isinstance(steps, int)
                or steps == 0
                or abs(steps) > 10
            ):
                raise ValueError("volume steps must be between -10 and 10, excluding zero")
            volume = max(0, min(100, self.player.state.volume + steps * 10))
            self.player.set_volume(volume)
        elif action == "record_start":
            self._require_enabled("recorder")
            source = request.get("source")
            if not isinstance(source, str):
                raise ValueError("record_start requires a media source")
            self.recorder.start(source)
        elif action == "record_stop":
            self.recorder.stop()
        elif action == "radio_keep_current":
            self._require_enabled("recorder")
            if self.radio_buffer is None:
                raise RuntimeError("radio pre-buffer is unavailable")
            return {"radio_buffer": self.radio_buffer.keep_current()}
        elif action == "radio_capture_mode":
            self._require_enabled("recorder")
            enabled = request.get("enabled")
            if not isinstance(enabled, bool):
                raise ValueError("radio_capture_mode requires boolean enabled")
            if self.radio_buffer is None:
                raise RuntimeError("radio pre-buffer is unavailable")
            self.store.set_setting(RADIO_CONTINUOUS_KEY, enabled)
            return {"radio_buffer": self.radio_buffer.set_continuous(enabled)}
        elif action == "station_add":
            name = request.get("name")
            source = request.get("source")
            if not isinstance(name, str) or not isinstance(source, str):
                raise ValueError("station_add requires name and source")
            approved = validate_media_source(source, (self.media_root,))
            if urlsplit(approved).query:
                raise ValueError(
                    "saved station URLs cannot contain a query; use direct playback for temporary URLs"
                )
            station_id = self.store.add_station("webradio", name, approved)
            return {"station_id": station_id}
        elif action == "station_delete":
            station_id = request.get("station_id")
            if isinstance(station_id, bool) or not isinstance(station_id, int):
                raise ValueError("station_delete requires an integer station_id")
            deleted = self.store.delete_station(station_id)
            if deleted and self.active_station_id == station_id:
                self.player.stop()
                if self.radio_buffer is not None:
                    self.radio_buffer.stop(flush=True)
                self.active_service = "system"
                self.active_station_id = None
                self.active_preset_id = None
            return {"deleted": deleted}
        elif action == "station_move":
            station_id = request.get("station_id")
            direction = request.get("direction")
            if isinstance(station_id, bool) or not isinstance(station_id, int):
                raise ValueError("station_move requires an integer station_id")
            if isinstance(direction, bool) or not isinstance(direction, int):
                raise ValueError("station_move requires an integer direction")
            return {"moved": self.store.move_station(station_id, direction)}
        elif action == "station_play":
            self._require_enabled("webradio")
            station_id = request.get("station_id")
            if isinstance(station_id, bool) or not isinstance(station_id, int):
                raise ValueError("station_play requires an integer station_id")
            station = self.store.station(station_id)
            if station is None:
                raise ValueError("station was not found")
            self._play_station(station)
        elif action == "radio_toggle":
            self._require_enabled("webradio")
            if (
                self.active_service == "webradio"
                and self.player.state.state in {"playing", "paused"}
            ):
                self.player.toggle_pause()
            else:
                stations = self.store.stations()
                if not stations:
                    raise ValueError("the radio station list is empty")
                self._play_station(stations[0])
        elif action == "preset_play":
            self._require_enabled("webradio")
            preset_id = request.get("preset_id")
            if not isinstance(preset_id, str) or preset_id not in RADIO_BY_ID:
                raise ValueError("unknown radio preset")
            self._play_preset(preset_id)
        elif action == "preset_step":
            self._require_enabled("webradio")
            steps = request.get("steps")
            if (
                isinstance(steps, bool)
                or not isinstance(steps, int)
                or steps == 0
                or abs(steps) > 10
            ):
                raise ValueError("preset steps must be between -10 and 10, excluding zero")
            stations = self.store.stations()
            if not stations:
                raise ValueError("the radio station list is empty")
            station_ids = [int(item["id"]) for item in stations]
            if self.active_station_id in station_ids:
                current = station_ids.index(self.active_station_id)
            else:
                current = -1 if steps > 0 else 0
            self._play_station(stations[(current + steps) % len(stations)])
        elif action == "preset_save":
            self._require_enabled("webradio")
            preset_id = request.get("preset_id")
            if not isinstance(preset_id, str) or preset_id not in RADIO_BY_ID:
                raise ValueError("unknown radio preset")
            preset = RADIO_BY_ID[preset_id]
            station_id = self.store.add_station(
                "webradio", preset.name, preset.stream_url
            )
            return {"station_id": station_id, "preset_id": preset_id}
        elif action == "media_scan":
            self._require_enabled("local_media")
            return {"scanned": self.scan_media()}
        elif action == "media_play":
            self._require_enabled("local_media")
            media_id = request.get("media_id")
            if isinstance(media_id, bool) or not isinstance(media_id, int):
                raise ValueError("media_play requires an integer media_id")
            media = self.store.media_item(media_id)
            if media is None:
                raise ValueError("media item was not found")
            self.player.load(str(media["path"]))
            self.active_service = "local_media"
            self.active_preset_id = None
            self.active_station_id = None
        elif action == "media_favorite":
            self._require_enabled("local_media")
            media_id = request.get("media_id")
            favorite = request.get("favorite")
            if isinstance(media_id, bool) or not isinstance(media_id, int):
                raise ValueError("media_favorite requires an integer media_id")
            if not isinstance(favorite, bool):
                raise ValueError("media_favorite requires boolean favorite")
            return {"updated": self.store.set_media_favorite(media_id, favorite)}
        elif action == "media_delete":
            self._require_enabled("local_media")
            media_id = request.get("media_id")
            confirmed = request.get("confirmed")
            if isinstance(media_id, bool) or not isinstance(media_id, int):
                raise ValueError("media_delete requires an integer media_id")
            if confirmed is not True:
                raise ValueError("media deletion requires explicit confirmation")
            media = self.store.media_item(media_id)
            if media is None:
                return {"deleted": False}
            path = Path(str(media["path"])).resolve()
            root = self.media_root.resolve()
            if not path.is_relative_to(root):
                raise ValueError("media file is outside the approved media directory")
            deleted = self.store.delete_media(media_id)
            if deleted is None:
                return {"deleted": False}
            path.unlink(missing_ok=True)
            cover_file = deleted.get("cover_file")
            if isinstance(cover_file, str) and re.fullmatch(
                r"track-\d{1,10}\.jpg", cover_file
            ):
                (self.cover_root / cover_file).unlink(missing_ok=True)
            return {"deleted": True}
        elif action in {"media_shuffle", "media_soundmix"}:
            self._require_enabled("local_media")
            favorites_only = action == "media_soundmix"
            media = [
                item
                for item in self.store.media_items()
                if item["source_kind"] == "radio"
                and (not favorites_only or bool(item["favorite"]))
            ]
            if not media:
                raise ValueError(
                    "no favorite recordings are available"
                    if favorites_only
                    else "no recorded tracks are available"
                )
            paths = [str(item["path"]) for item in media]
            random.shuffle(paths)
            self.player.load_playlist(
                paths,
                shuffle=False,
                loop=favorites_only,
            )
            self.active_service = "local_media"
            self.active_preset_id = None
            self.active_station_id = None
        elif action == "media_next":
            self._require_enabled("local_media")
            self.player.next()
        elif action == "media_previous":
            self._require_enabled("local_media")
            self.player.previous()
        elif action == "adapter_call":
            service_id = request.get("service_id")
            operation = request.get("operation")
            if not isinstance(service_id, str) or not isinstance(operation, str):
                raise ValueError("adapter_call requires service_id and operation")
            external_ids = {
                item.service_id
                for item in BUILTIN_SERVICES
                if item.implementation in {"external", "official_api"}
            }
            if service_id not in external_ids:
                raise ValueError("service does not use an external adapter")
            self._require_enabled(service_id)
            result = self.adapters.call(
                service_id, operation, request.get("parameters")
            )
            return {"service_id": service_id, "adapter": result}
        elif action == "feed_fetch":
            self._require_enabled("rss")
            url = request.get("url")
            if not isinstance(url, str):
                raise ValueError("feed_fetch requires a URL")
            feed = self.feed_reader.fetch(url)
            self.content_state["feed"] = {
                "title": feed["title"],
                "item_count": feed["item_count"],
            }
            return {"feed": feed}
        elif action == "feed_fetch_preset":
            self._require_enabled("rss")
            preset_id = request.get("preset_id")
            if not isinstance(preset_id, str) or preset_id not in FEED_BY_ID:
                raise ValueError("unknown feed preset")
            preset = FEED_BY_ID[preset_id]
            feed = self.feed_reader.fetch(preset.feed_url)
            self.content_state["feed"] = {
                "title": feed["title"],
                "item_count": feed["item_count"],
                "preset_id": preset_id,
            }
            return {
                "feed": feed,
                "preset_id": preset_id,
                "credit": preset.credit,
                "homepage": preset.homepage,
            }
        elif action == "camera_snapshot":
            self._require_enabled("webcam")
            url = request.get("url")
            slot = request.get("slot", 1)
            if not isinstance(url, str):
                raise ValueError("camera_snapshot requires a URL")
            if isinstance(slot, bool) or not isinstance(slot, int):
                raise ValueError("camera slot must be an integer")
            camera = self.camera.fetch(url, slot)
            cameras = self.content_state["cameras"]
            assert isinstance(cameras, dict)
            cameras[str(slot)] = camera
            return {"camera": camera}
        elif action == "weather_channel_save":
            self._require_enabled("weather")
            channel_id = request.get("channel_id")
            name = request.get("name")
            bbox = self._weather_bbox(request.get("bbox"))
            if not isinstance(name, str):
                raise ValueError("weather_channel_save requires a name")
            metadata = {"bbox": list(bbox), "provider": "DWD / EUMETSAT"}
            if channel_id is None:
                external_id = f"custom-{uuid.uuid4().hex[:12]}"
                saved_id = self.store.add_channel("weather", external_id, name, metadata)
            else:
                if isinstance(channel_id, bool) or not isinstance(channel_id, int):
                    raise ValueError("weather channel id must be an integer")
                channel = self.store.channel(channel_id)
                if channel is None or channel["service_id"] != "weather":
                    raise ValueError("weather channel was not found")
                self.store.update_channel(channel_id, name, metadata)
                invalidate = getattr(self.weather, "invalidate", None)
                if callable(invalidate):
                    invalidate(str(channel["external_id"]))
                saved_id = channel_id
            return {"channel_id": saved_id}
        elif action == "weather_channel_delete":
            channel_id = request.get("channel_id")
            if isinstance(channel_id, bool) or not isinstance(channel_id, int):
                raise ValueError("weather_channel_delete requires an integer channel_id")
            channel = self.store.channel(channel_id)
            if channel is None or channel["service_id"] != "weather":
                return {"deleted": False}
            deleted = self.store.delete_channel(channel_id)
            invalidate = getattr(self.weather, "invalidate", None)
            if deleted and callable(invalidate):
                invalidate(str(channel["external_id"]))
            if deleted and self.active_weather_channel_id == channel_id:
                remaining = self.store.channels("weather")
                self.active_weather_channel_id = int(remaining[0]["id"]) if remaining else None
            return {"deleted": deleted}
        elif action == "weather_channel_move":
            channel_id = request.get("channel_id")
            direction = request.get("direction")
            if isinstance(channel_id, bool) or not isinstance(channel_id, int):
                raise ValueError("weather_channel_move requires an integer channel_id")
            if isinstance(direction, bool) or not isinstance(direction, int):
                raise ValueError("weather_channel_move requires an integer direction")
            channel = self.store.channel(channel_id)
            if channel is None or channel["service_id"] != "weather":
                raise ValueError("weather channel was not found")
            return {"moved": self.store.move_channel(channel_id, direction)}
        elif action == "weather_open":
            self._require_enabled("weather")
            channel_id = request.get("channel_id", self.active_weather_channel_id)
            self._select_weather_channel(channel_id)
            channel = self.store.channel(self.active_weather_channel_id)  # type: ignore[arg-type]
            assert channel is not None
            self._cache_weather(channel)
            return {"view_service": "weather", "channel_id": self.active_weather_channel_id}
        elif action == "weather_step":
            self._require_enabled("weather")
            steps = request.get("steps")
            if isinstance(steps, bool) or not isinstance(steps, int) or steps == 0 or abs(steps) > 10:
                raise ValueError("weather steps must be between -10 and 10, excluding zero")
            channels = self.store.channels("weather")
            if not channels:
                raise ValueError("the weather channel list is empty")
            ids = [int(item["id"]) for item in channels]
            current = ids.index(self.active_weather_channel_id) if self.active_weather_channel_id in ids else 0
            self.active_weather_channel_id = ids[(current + steps) % len(ids)]
            selected = self.store.channel(self.active_weather_channel_id)
            assert selected is not None
            self._cache_weather(selected)
            return {"view_service": "weather", "channel_id": self.active_weather_channel_id}
        elif action == "weather_refresh":
            self._require_enabled("weather")
            channel_id = request.get("channel_id", self.active_weather_channel_id)
            self._select_weather_channel(channel_id)
            channel = self.store.channel(self.active_weather_channel_id)  # type: ignore[arg-type]
            assert channel is not None
            frames = self._refresh_weather_channel(channel)
            return {"channel_id": self.active_weather_channel_id, "frames": len(frames)}
        else:
            raise ValueError("unsupported control action")
        return {
            "active_service": self.active_service,
            "playback": self.player.state.as_dict(),
            "recording": self.recorder.state.as_dict(),
            "radio_buffer": (
                self.radio_buffer.snapshot() if self.radio_buffer is not None else None
            ),
            "selected_preset": self._selected_preset(),
        }

    def _play_preset(self, preset_id: str) -> None:
        preset = RADIO_BY_ID[preset_id]
        station = next(
            (
                item for item in self.store.stations()
                if item["stream_url"] == preset.stream_url
            ),
            None,
        )
        if station is None:
            raise ValueError("radio preset is not in the personal station list")
        self._play_station(station)

    def _play_station(self, station: dict[str, object]) -> None:
        self.player.load(str(station["stream_url"]))
        if self.radio_buffer is not None:
            self.radio_buffer.tune(
                str(station["stream_url"]),
                str(station["name"]),
            )
        self.active_service = "webradio"
        self.active_station_id = int(station["id"])
        preset = self._preset_for_station(station)
        self.active_preset_id = preset.preset_id if preset is not None else None
        if preset is not None:
            self._cache_preset_artwork(preset.preset_id)

    def _cache_preset_artwork(self, preset_id: str) -> None:
        with self._artwork_guard:
            if preset_id in self._artwork_pending:
                return
            self._artwork_pending.add(preset_id)

        def cache() -> None:
            preset = RADIO_BY_ID[preset_id]
            try:
                self.artwork.ensure(preset_id, preset.artwork_url)
            except (ContentError, OSError, ValueError) as exc:
                LOG.warning("Station artwork unavailable for %s: %s", preset_id, exc)
            finally:
                with self._artwork_guard:
                    self._artwork_pending.discard(preset_id)

        self._start_worker(f"openr4d10-artwork-{preset_id}", cache)

    def _selected_preset(self) -> dict[str, object] | None:
        if self.active_station_id is None:
            return None
        station = self.store.station(self.active_station_id)
        if station is None:
            return None
        stations = self.store.stations()
        station_ids = [int(item["id"]) for item in stations]
        if self.active_station_id not in station_ids:
            return None
        preset = self._preset_for_station(station)
        return {
            "preset_id": preset.preset_id if preset is not None else None,
            "name": str(station["name"]),
            "channel": station_ids.index(self.active_station_id) + 1,
            "artwork": (
                f"/api/radio-art/{preset.preset_id}" if preset is not None else None
            ),
        }

    @staticmethod
    def _preset_for_station(station: dict[str, object]):
        stream_url = str(station["stream_url"])
        return next(
            (item for item in RADIO_PRESETS if item.stream_url == stream_url),
            None,
        )

    def _require_enabled(self, service_id: str) -> None:
        if not self.store.service_enabled(service_id):
            raise ValueError(f"service is disabled: {service_id}")

    @staticmethod
    def _weather_bbox(value: object) -> tuple[float, float, float, float]:
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            raise ValueError("weather bbox must contain south, west, north and east")
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
            raise ValueError("weather bbox values must be numbers")
        south, west, north, east = (float(item) for item in value)
        if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
            raise ValueError("weather bbox is outside valid latitude/longitude bounds")
        if not (23 <= south < north <= 77 and -54 <= west < east <= 54):
            raise ValueError("weather bbox is outside the DWD METEOSAT layer coverage")
        return south, west, north, east

    def _select_weather_channel(self, channel_id: object) -> None:
        if isinstance(channel_id, bool) or not isinstance(channel_id, int):
            raise ValueError("weather channel id must be an integer")
        channel = self.store.channel(channel_id)
        if channel is None or channel["service_id"] != "weather":
            raise ValueError("weather channel was not found")
        self.active_weather_channel_id = channel_id

    def _cache_weather(self, channel: dict[str, object]) -> None:
        key = str(channel["external_id"])
        with self._weather_guard:
            if key in self._weather_pending:
                return
            self._weather_pending.add(key)

        def cache() -> None:
            try:
                self._refresh_weather_channel(channel)
            except (ContentError, OSError, ValueError) as exc:
                LOG.warning("DWD weather frames unavailable for %s: %s", key, exc)
            finally:
                with self._weather_guard:
                    self._weather_pending.discard(key)

        self._start_worker(f"openr4d10-weather-{key}", cache)

    def _refresh_weather_channel(
        self,
        channel: dict[str, object],
    ) -> list[dict[str, object]]:
        metadata = channel.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("weather channel metadata is invalid")
        key = str(channel["external_id"])
        if metadata.get("kind") == "radar_gif":
            source_url = metadata.get("source_url")
            if source_url != DWD_RADAR_GIF_URL:
                raise ValueError("weather radar source is not the reviewed DWD URL")
            refresh_radar = getattr(self.weather, "refresh_radar", None)
            if not callable(refresh_radar):
                raise ValueError("weather backend does not support radar animations")
            return refresh_radar(key, DWD_RADAR_GIF_URL)
        return self.weather.refresh(key, self._weather_bbox(metadata.get("bbox")))

    def _start_worker(self, name: str, target: Callable[[], None]) -> None:
        def run() -> None:
            try:
                target()
            finally:
                with self._worker_guard:
                    self._worker_threads.discard(threading.current_thread())

        worker = threading.Thread(target=run, name=name, daemon=True)
        with self._worker_guard:
            self._worker_threads.add(worker)
        worker.start()

    def scan_media(self) -> int:
        self.media_root.mkdir(parents=True, exist_ok=True, mode=0o750)
        root = self.media_root.resolve()
        count = 0
        present: set[str] = set()
        for path in self.media_root.rglob("*"):
            if count >= 2000:
                break
            try:
                resolved = path.resolve(strict=True)
                if (
                    not resolved.is_file()
                    or not resolved.is_relative_to(root)
                    or resolved.suffix.lower() not in MEDIA_EXTENSIONS
                ):
                    continue
                size = resolved.stat().st_size
            except OSError:
                continue
            self.store.upsert_media("local_media", resolved, size)
            present.add(str(resolved))
            count += 1
        self.store.remove_missing_media("local_media", present)
        return count

    def content_asset(self, path: str) -> tuple[str, bytes] | None:
        if path in {"camera-1.jpg", "camera-2.jpg"}:
            target = self.camera.cache_root / path
        elif path.startswith("radio-art/"):
            preset_id = path.removeprefix("radio-art/")
            preset = RADIO_BY_ID.get(preset_id)
            if preset is None:
                return None
            try:
                target = self.artwork.ensure(preset_id, preset.artwork_url)
            except (ContentError, OSError, ValueError) as exc:
                LOG.warning("Station artwork unavailable for %s: %s", preset_id, exc)
                return None
        elif re.fullmatch(r"media-cover/\d{1,10}", path):
            media_id = int(path.rsplit("/", 1)[-1])
            media = self.store.media_item(media_id)
            if media is None or not isinstance(media.get("cover_file"), str):
                return None
            cover_file = str(media["cover_file"])
            if not re.fullmatch(r"track-\d{1,10}\.jpg", cover_file):
                return None
            target = self.cover_root / cover_file
        elif re.fullmatch(r"weather-[a-z][a-z0-9_-]{1,63}-\d{8}T\d{6}Z\.jpg", path):
            target = self.weather.cache_root / path
        else:
            return None
        try:
            return "image/jpeg", target.read_bytes()
        except OSError:
            return None

    def receiver_overlay(self, view_service: str | None = None) -> dict[str, object]:
        """Return metadata for the selected view without changing audio ownership."""
        requested = str(view_service or "").upper()
        valid_views = {"SYSTEM", "RADIO", "WEATHER", "DMR", "PLAYER", "REC"}
        if not self._initial_view_resolved:
            if requested not in valid_views:
                remembered = str(self.store.get_setting(LAST_VIEW_KEY, "RADIO")).upper()
                requested = remembered if remembered in valid_views else "RADIO"
            self._initial_view_resolved = True
        elif requested in valid_views:
            if self.store.get_setting(LAST_VIEW_KEY, None) != requested:
                self.store.set_setting(LAST_VIEW_KEY, requested)
        if requested == "WEATHER" and self.active_weather_channel_id is not None:
            channel = self.store.channel(self.active_weather_channel_id)
            if channel is not None:
                channels = self.store.channels("weather")
                ids = [int(item["id"]) for item in channels]
                frames = self.weather.frames(str(channel["external_id"]))
                frame = frames[int(time.monotonic() / 2) % len(frames)] if frames else None
                metadata = channel.get("metadata")
                provider = (
                    str(metadata.get("provider") or "DWD / EUMETSAT")
                    if isinstance(metadata, dict)
                    else "DWD / EUMETSAT"
                )
                loading = (
                    "Regenradar wird geladen"
                    if isinstance(metadata, dict) and metadata.get("kind") == "radar_gif"
                    else "Satellitenbilder werden geladen"
                )
                return {
                    "service": "WEATHER",
                    "station": str(channel["name"]),
                    "title": provider,
                    "subtitle": (
                        str(frame["timestamp"]) if frame is not None else loading
                    ),
                    "playing": bool(frames),
                    "channel": ids.index(self.active_weather_channel_id) + 1 if self.active_weather_channel_id in ids else 1,
                    "image_file": str(frame["file"]) if frame is not None else None,
                }
        playback = self.player.state
        service_label = {
            "webradio": "RADIO",
            "local_media": "PLAYER",
            "youtube_audio": "PLAYER",
            "spotify": "PLAYER",
            "ard_mediathek": "PLAYER",
            "zdf_mediathek": "PLAYER",
            "international_media": "PLAYER",
            "brandmeister": "DMR",
            "remote_sdr": "DMR",
            "private_ptt": "DMR",
            "mumble": "DMR",
            "discord": "DMR",
            "teamspeak": "DMR",
            "recorder": "REC",
        }.get(self.active_service, "SYSTEM")
        if requested and requested != service_label:
            if requested == "RADIO":
                stations = self.store.stations()
                station = stations[0] if stations else None
                preset = self._preset_for_station(station) if station is not None else None
                return {
                    "service": "RADIO",
                    "station": str(station["name"]) if station is not None else "Radio",
                    "title": str(station["name"]) if station is not None else "Radio",
                    "subtitle": "Play starts this audio service",
                    "playing": False,
                    "volume": playback.volume,
                    "preset_id": preset.preset_id if preset is not None else None,
                    "channel": 1 if station is not None else None,
                }
            defaults = {
                "SYSTEM": ("OPENR4D10", "System online", "Receiver ready"),
                "PLAYER": ("LOCAL MEDIA", "Local media", "Select media and press play"),
                "DMR": ("DMR", "Digital radio", "Select a channel and press play"),
                "REC": ("RECORDER", "Recorder", "Recording controls"),
            }
            station, title, subtitle = defaults.get(
                requested,
                (requested or "OPENR4D10", requested or "System online", "Ready"),
            )
            return {
                "service": requested or "SYSTEM",
                "station": station,
                "title": title,
                "subtitle": subtitle,
                "playing": False,
                "volume": playback.volume,
            }
        if playback.state not in {"playing", "paused"}:
            return {"service": requested or "SYSTEM", "playing": False, "volume": playback.volume}
        selected = self._selected_preset() if self.active_service == "webradio" else None
        station = (
            str(selected["name"])
            if selected is not None
            else playback.source or self.active_service
        )
        track_line = "Paused" if playback.paused else "Audio stream active"
        buffered_recording = False
        if self.active_service == "webradio" and self.radio_buffer is not None:
            buffered = self.radio_buffer.snapshot()
            buffered_recording = (
                buffered.get("keep_current") is True
                or buffered.get("continuous") is True
            )
            artist = buffered.get("artist")
            title = buffered.get("title")
            stream_title = buffered.get("stream_title")
            if isinstance(artist, str) and isinstance(title, str):
                track_line = f"{artist} – {title}"
            elif isinstance(stream_title, str) and stream_title.strip():
                track_line = stream_title.strip()[:500]
        return {
            "service": service_label,
            "station": station,
            "title": track_line,
            "subtitle": track_line,
            "playing": not playback.paused,
            "recording": (
                self.recorder.state.state == "recording" or buffered_recording
            ),
            "volume": playback.volume,
            "preset_id": selected["preset_id"] if selected is not None else None,
            "channel": selected["channel"] if selected is not None else None,
        }

    def close(self) -> None:
        deadline = time.monotonic() + 15.0
        while True:
            with self._worker_guard:
                workers = tuple(self._worker_threads)
            if not workers:
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            for worker in workers:
                worker.join(timeout=max(0.0, remaining / len(workers)))
        self.recorder.close()
        if self.radio_buffer is not None:
            self.radio_buffer.close()
        self.player.close()
        self.store.close()
