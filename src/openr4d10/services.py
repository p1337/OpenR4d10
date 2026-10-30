"""Central catalog and readiness model for OpenR4d10 service modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
from pathlib import Path
import shutil
import threading
from typing import Callable
from urllib.parse import urlsplit

from .content import CameraSnapshot, ContentError, FeedReader, PresetArtwork
from .media import MpvEngine, StreamRecorder, public_source_label, validate_media_source
from .presets import FEED_BY_ID, FEED_PRESETS, RADIO_BY_ID, RADIO_PRESETS
from .service_adapters import ServiceAdapterError, ServiceAdapterRegistry
from .storage import SCHEMA_VERSION, StateStore


ExecutableLookup = Callable[[str], str | None]
MEDIA_EXTENSIONS = {
    ".aac", ".flac", ".m4a", ".mka", ".mp3", ".mp4", ".ogg", ".opus", ".wav",
}
DEFAULT_ENABLED_SERVICES = {
    "system", "webradio", "local_media", "recorder", "rss", "webcam",
}

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
        adapter_directory: Path | None = None,
        adapter_registry: ServiceAdapterRegistry | None = None,
    ) -> None:
        self.store = StateStore(state_directory / "openr4d10.sqlite3")
        self.executable_lookup = executable_lookup
        self.media_root = state_directory / "media"
        self.player = player or MpvEngine(media_roots=(self.media_root,))
        self.recorder = recorder or StreamRecorder(
            state_directory / "recordings",
            media_roots=(self.media_root,),
        )
        self.feed_reader = feed_reader or FeedReader()
        self.camera = camera or CameraSnapshot(state_directory / "cache")
        self.artwork = artwork or PresetArtwork(state_directory / "cache")
        self._artwork_pending: set[str] = set()
        self._artwork_guard = threading.Lock()
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
        self.store.ensure_services(
            tuple(item.service_id for item in BUILTIN_SERVICES),
            DEFAULT_ENABLED_SERVICES,
        )

    def snapshot(self) -> dict[str, object]:
        states = self.store.service_states()
        services: list[dict[str, object]] = []
        for manifest in BUILTIN_SERVICES:
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
        stations = [
            {
                "id": item["id"],
                "name": item["name"],
                "source": public_source_label(str(item["stream_url"])),
                "favorite": bool(item["favorite"]),
            }
            for item in self.store.stations()
        ]
        media = [
            {
                "id": item["id"],
                "title": item["title"],
                "size_bytes": item["size_bytes"],
            }
            for item in self.store.media_items()
        ]
        return {
            "schema_version": SCHEMA_VERSION,
            "total": len(services),
            "ready": sum(item["readiness"] == "ready" for item in services),
            "active_service": self.active_service,
            "selected_preset": self._selected_preset(),
            "playback": self.player.state.as_dict(),
            "recording": self.recorder.state.as_dict(),
            "content": self.content_state,
            "presets": {
                "stations": [item.public() for item in RADIO_PRESETS],
                "feeds": [item.public() for item in FEED_PRESETS],
            },
            "stations": stations,
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
                    self.active_service = "system"
                    self.active_preset_id = None
                if service_id == "recorder":
                    self.recorder.stop()
            self.store.set_service_enabled(service_id, enabled)
            return {"service_id": service_id, "enabled": enabled}
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
            self.active_service = service_id
            self.active_preset_id = None
        elif action == "pause":
            if self.player.state.state not in {"playing", "paused"}:
                raise ValueError("no active media to pause or resume")
            self.player.toggle_pause()
        elif action == "stop":
            self.player.stop()
            self.active_service = "system"
            self.active_preset_id = None
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
            return {"deleted": self.store.delete_station(station_id)}
        elif action == "station_play":
            self._require_enabled("webradio")
            station_id = request.get("station_id")
            if isinstance(station_id, bool) or not isinstance(station_id, int):
                raise ValueError("station_play requires an integer station_id")
            station = self.store.station(station_id)
            if station is None:
                raise ValueError("station was not found")
            self.player.load(str(station["stream_url"]))
            self.active_service = "webradio"
            self.active_preset_id = None
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
            preset_ids = tuple(RADIO_BY_ID)
            if self.active_preset_id in RADIO_BY_ID:
                current = preset_ids.index(self.active_preset_id)
            else:
                current = -1 if steps > 0 else 0
            self._play_preset(preset_ids[(current + steps) % len(preset_ids)])
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
        else:
            raise ValueError("unsupported control action")
        return {
            "active_service": self.active_service,
            "playback": self.player.state.as_dict(),
            "recording": self.recorder.state.as_dict(),
            "selected_preset": self._selected_preset(),
        }

    def _play_preset(self, preset_id: str) -> None:
        preset = RADIO_BY_ID[preset_id]
        self.player.load(preset.stream_url)
        self.active_service = "webradio"
        self.active_preset_id = preset_id
        self._cache_preset_artwork(preset_id)

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

        threading.Thread(
            target=cache,
            name=f"openr4d10-artwork-{preset_id}",
            daemon=True,
        ).start()

    def _selected_preset(self) -> dict[str, object] | None:
        preset = RADIO_BY_ID.get(self.active_preset_id or "")
        if preset is None:
            return None
        return {
            "preset_id": preset.preset_id,
            "name": preset.name,
            "channel": tuple(RADIO_BY_ID).index(preset.preset_id) + 1,
            "artwork": f"/api/radio-art/{preset.preset_id}",
        }

    def _require_enabled(self, service_id: str) -> None:
        if not self.store.service_enabled(service_id):
            raise ValueError(f"service is disabled: {service_id}")

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
        else:
            return None
        try:
            return "image/jpeg", target.read_bytes()
        except OSError:
            return None

    def receiver_overlay(self) -> dict[str, object]:
        playback = self.player.state
        if playback.state not in {"playing", "paused"}:
            return {}
        selected = self._selected_preset()
        station = (
            str(selected["name"])
            if selected is not None
            else playback.source or self.active_service
        )
        service_label = {
            "local_media": "PLAYER",
            "recorder": "REC",
        }.get(self.active_service, "RADIO")
        return {
            "service": service_label,
            "station": station,
            "title": station,
            "subtitle": "Paused" if playback.paused else "Audio stream active",
            "playing": not playback.paused,
            "recording": self.recorder.state.state == "recording",
            "volume": playback.volume,
            "preset_id": selected["preset_id"] if selected is not None else None,
            "channel": selected["channel"] if selected is not None else None,
        }

    def close(self) -> None:
        self.recorder.close()
        self.player.close()
        self.store.close()
