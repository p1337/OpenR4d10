"""Central catalog and readiness model for OpenR4d10 service modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import shutil
from typing import Callable

from .storage import StateStore


ExecutableLookup = Callable[[str], str | None]


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
    ) -> None:
        self.store = StateStore(state_directory / "openr4d10.sqlite3")
        self.executable_lookup = executable_lookup
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
        return {
            "schema_version": 1,
            "total": len(services),
            "ready": sum(item["readiness"] == "ready" for item in services),
            "items": services,
        }

    def close(self) -> None:
        self.store.close()
