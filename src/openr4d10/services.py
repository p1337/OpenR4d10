"""Central catalog and readiness model for OpenR4d10 service modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import shutil
from typing import Callable
from urllib.parse import urlsplit

from .content import CameraSnapshot, FeedReader
from .media import MpvEngine, StreamRecorder, public_source_label, validate_media_source
from .storage import StateStore


ExecutableLookup = Callable[[str], str | None]
MEDIA_EXTENSIONS = {
    ".aac", ".flac", ".m4a", ".mka", ".mp3", ".mp4", ".ogg", ".opus", ".wav",
}


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
        self.content_state: dict[str, object] = {
            "feed": None,
            "cameras": {},
        }
        self.active_service = "system"
        self.store.ensure_services(tuple(item.service_id for item in BUILTIN_SERVICES))

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
            if missing:
                readiness = "missing_dependency"
            elif manifest.implementation in {"external", "official_api"}:
                readiness = "configuration_required"
            elif manifest.requires_credentials and state["config_state"] != "ready":
                readiness = "configuration_required"
            else:
                readiness = "ready"
            item = asdict(manifest)
            item.update(state)
            item["missing_executables"] = missing
            item["readiness"] = readiness
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
            "schema_version": 1,
            "total": len(services),
            "ready": sum(item["readiness"] == "ready" for item in services),
            "active_service": self.active_service,
            "playback": self.player.state.as_dict(),
            "recording": self.recorder.state.as_dict(),
            "content": self.content_state,
            "stations": stations,
            "media": media,
            "items": services,
        }

    def control(self, request: dict[str, object]) -> dict[str, object]:
        action = request.get("action")
        if not isinstance(action, str):
            raise ValueError("control action is required")
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
            if not isinstance(source, str):
                raise ValueError("play action requires a media source")
            self.player.load(source)
            self.active_service = service_id
        elif action == "pause":
            self.player.toggle_pause()
        elif action == "stop":
            self.player.stop()
            self.active_service = "system"
        elif action == "volume":
            self.player.set_volume(request.get("value"))  # type: ignore[arg-type]
        elif action == "record_start":
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
            station_id = request.get("station_id")
            if isinstance(station_id, bool) or not isinstance(station_id, int):
                raise ValueError("station_play requires an integer station_id")
            station = self.store.station(station_id)
            if station is None:
                raise ValueError("station was not found")
            self.player.load(str(station["stream_url"]))
            self.active_service = "webradio"
        elif action == "media_scan":
            return {"scanned": self.scan_media()}
        elif action == "media_play":
            media_id = request.get("media_id")
            if isinstance(media_id, bool) or not isinstance(media_id, int):
                raise ValueError("media_play requires an integer media_id")
            media = self.store.media_item(media_id)
            if media is None:
                raise ValueError("media item was not found")
            self.player.load(str(media["path"]))
            self.active_service = "local_media"
        elif action == "feed_fetch":
            url = request.get("url")
            if not isinstance(url, str):
                raise ValueError("feed_fetch requires a URL")
            feed = self.feed_reader.fetch(url)
            self.content_state["feed"] = {
                "title": feed["title"],
                "item_count": feed["item_count"],
            }
            return {"feed": feed}
        elif action == "camera_snapshot":
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
        }

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
        if path not in {"camera-1.jpg", "camera-2.jpg"}:
            return None
        target = self.camera.cache_root / path
        try:
            return "image/jpeg", target.read_bytes()
        except OSError:
            return None

    def receiver_overlay(self) -> dict[str, object]:
        playback = self.player.state
        if playback.state not in {"playing", "paused"}:
            return {}
        service_label = {
            "local_media": "PLAYER",
            "recorder": "REC",
        }.get(self.active_service, "RADIO")
        return {
            "service": service_label,
            "station": playback.source or self.active_service,
            "title": playback.source or self.active_service,
            "subtitle": "Paused" if playback.paused else "Audio stream active",
            "playing": not playback.paused,
            "recording": self.recorder.state.state == "recording",
        }

    def close(self) -> None:
        self.recorder.close()
        self.player.close()
        self.store.close()
