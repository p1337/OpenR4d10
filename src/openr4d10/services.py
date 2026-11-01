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

from .ambient import (
    AMBIENT_ARTWORK_ROOT,
    AMBIENT_BY_ID,
    AMBIENT_LAYER_DEFAULTS,
    AMBIENT_LAYER_IDS,
    AMBIENT_PRESETS,
    ambient_text,
)
from .brandmeister import (
    BrandmeisterReceiver,
    BrandmeisterTalkgroupCatalog,
    MAX_TALKGROUPS,
    country_code,
)
from .content import (
    AmbientAudioCache,
    CameraSnapshot,
    ContentError,
    DWD_RADAR_GIF_URL,
    DwdSatelliteFrames,
    FeedReader,
    MediathekCatalog,
    MediathekEntry,
    PodcastReader,
    PresetArtwork,
    TrackArtwork,
    validate_content_url,
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
    "system", "webradio", "weather", "ambient", "local_media", "recorder", "rss", "podcasts", "webcam", "brandmeister",
    "ard_mediathek", "zdf_mediathek", "public_mediatheken",
}
MEDIATHEK_SERVICE_IDS = {
    "ard_mediathek", "zdf_mediathek", "public_mediatheken",
}
DISPLAY_BRIGHTNESS_KEY = "display.brightness_percent"
DEFAULT_DISPLAY_BRIGHTNESS = 100
AMBIENT_SOURCE_MIGRATION_KEY = "ambient.direct_sources_v1"
QUIET_CAFE_MIGRATION_KEY = "ambient.quiet_cafe_v1"
AMBIENT_SCENE_UPGRADE_KEY = "ambient.layer_scenes_v1"
AMBIENT_LAYER_STATE_KEY = "ambient.layer_state_v1"
AMBIENT_SAVE_ACTION = "__save_favorite__"
OLD_CAFE_AUDIO_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/5/54/Cafe_ambiance.ogg"
)
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
BRANDMEISTER_NATIVE_MIGRATION_KEY = "brandmeister.native_receiver_v1"
RADIO_V2_PRESET_IDS = {"die_neue_1077", "afn_eagle", "rock_antenne", "rock_fm"}
SOLIX_METRIC_RANGES = {
    "solar_w": (0.0, 100_000.0),
    "home_w": (0.0, 100_000.0),
    "grid_w": (-100_000.0, 100_000.0),
    "battery_w": (-100_000.0, 100_000.0),
    "battery_percent": (0.0, 100.0),
    "energy_today_kwh": (0.0, 10_000.0),
}
BRANDMEISTER_COUNTRY_NAMES = {
    "AU": "Australia", "AT": "Austria", "CA": "Canada", "CH": "Switzerland",
    "DE": "Germany", "ES": "Spain", "FR": "France", "GB": "United Kingdom",
    "IT": "Italy", "NL": "Netherlands", "PL": "Poland", "PT": "Portugal",
    "US": "United States",
}
BRANDMEISTER_COUNTRY_NAMES_DE = {
    "AU": "Australien", "AT": "Österreich", "CA": "Kanada", "CH": "Schweiz",
    "DE": "Deutschland", "ES": "Spanien", "FR": "Frankreich", "GB": "Großbritannien",
    "IT": "Italien", "NL": "Niederlande", "PL": "Polen", "PT": "Portugal",
    "US": "Vereinigte Staaten",
}
BRANDMEISTER_ALL_COUNTRIES = "*"
BRANDMEISTER_OTHER_COUNTRIES = "--"

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
    ServiceManifest("ambient", "AmbientR4D10", "audio", "Looping café, nature, water, rain and night soundscapes", ("playback", "scenes", "loop"), "process", ("mpv",)),
    ServiceManifest("anker_solix", "Anker SOLIX", "energy", "Live photovoltaic, home, grid and battery telemetry", ("energy", "solar", "battery"), "external", requires_credentials=True, credential_hint="Prefer supported local Modbus TCP devices; otherwise configure the isolated community cloud adapter locally."),
    ServiceManifest("local_media", "Local Media", "audio", "Local MP3, FLAC, MP4 and recordings", ("playback", "library"), "process", ("mpv",)),
    ServiceManifest("recorder", "Voice Recorder", "audio", "Stereo PTT voice recording from the Whisplay microphones", ("recording", "library"), "process", ("ffmpeg",)),
    ServiceManifest("brandmeister", "BrandMeister", "radio", "Receive-only DMR audio through native HoseLine", ("playback", "talkgroups"), "process", ("aplay",)),
    ServiceManifest("remote_sdr", "Remote SDR", "radio", "OpenWebRX or another configured remote receiver", ("playback", "channels", "squelch"), "external"),
    ServiceManifest("private_ptt", "Private PTT", "voice", "Private push-to-talk between explicitly paired devices", ("ptt", "playback", "recording"), "external", requires_credentials=True, credential_hint="Pair devices locally; never ship a shared key."),
    ServiceManifest("mumble", "Mumble", "voice", "Mumble voice and push-to-talk", ("ptt", "channels"), "external", requires_credentials=True, credential_hint="Enter the user's own server and account locally."),
    ServiceManifest("discord", "Discord", "voice", "Official Discord application/bot integration", ("ptt", "channels", "messages"), "official_api", requires_credentials=True, credential_hint="Use an individual official OAuth or app flow."),
    ServiceManifest("telegram", "Telegram", "messages", "Messages and voice notes through a local TDLib adapter", ("messages", "voice_notes", "tts"), "external", requires_credentials=True, credential_hint="Complete Telegram login locally through TDLib."),
    ServiceManifest("rss", "Feeds", "information", "RSS and Atom subscriptions with optional read-aloud", ("feeds", "tts"), "native"),
    ServiceManifest("podcasts", "Podcasts", "audio", "Podcast subscriptions and episode playback", ("subscriptions", "episodes", "playback"), "process", ("mpv",)),
    ServiceManifest("webcam", "Webcams", "video", "Persistent snapshot, MJPEG and RTSP camera library", ("images", "video", "channels"), "process", ("ffmpeg",)),
    ServiceManifest("youtube_audio", "YouTube Audio", "media", "Audio access only where technically and legally permitted", ("playback", "library"), "external"),
    ServiceManifest("spotify", "Spotify", "media", "Spotify Connect through a user-configured compatible client", ("playback",), "external", requires_credentials=True, credential_hint="Use the user's own eligible Spotify account locally."),
    ServiceManifest("ard_mediathek", "ARD Mediathek", "media", "Officially accessible ARD audio and media", ("catalog", "playback"), "process", ("mpv",)),
    ServiceManifest("zdf_mediathek", "ZDF Mediathek", "media", "Officially accessible ZDF audio and media", ("catalog", "playback"), "process", ("mpv",)),
    ServiceManifest("public_mediatheken", "Public Mediatheques", "media", "German public documentary, information and regional media libraries", ("catalog", "playback", "video"), "process", ("mpv",)),
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
        podcast_reader: PodcastReader | None = None,
        mediathek_catalog: MediathekCatalog | None = None,
        camera: CameraSnapshot | None = None,
        artwork: PresetArtwork | None = None,
        track_artwork: TrackArtwork | None = None,
        weather: DwdSatelliteFrames | None = None,
        radio_buffer: IcyRadioBuffer | None = None,
        adapter_directory: Path | None = None,
        adapter_registry: ServiceAdapterRegistry | None = None,
        ambient_artwork_root: Path | None = None,
        ambient_audio_cache: AmbientAudioCache | None = None,
        ambient_layer_player_factory: Callable[[], MpvEngine] | None = None,
        brandmeister: BrandmeisterReceiver | None = None,
        brandmeister_catalog: BrandmeisterTalkgroupCatalog | None = None,
    ) -> None:
        self.store = StateStore(state_directory / "openr4d10.sqlite3")
        self.executable_lookup = executable_lookup
        self.media_root = state_directory / "media"
        self.music_root = self.media_root / "Music"
        self.cover_root = state_directory / "cache" / "track-covers"
        self.player = player or MpvEngine(media_roots=(self.media_root,))
        self.recorder = recorder or StreamRecorder(
            state_directory / "recordings",
            media_roots=(self.media_root,),
            voice_root=self.media_root / "VoiceRecorder",
        )
        self.feed_reader = feed_reader or FeedReader()
        self.podcast_reader = podcast_reader or PodcastReader()
        self.mediathek_catalog = mediathek_catalog or MediathekCatalog()
        self.camera = camera or CameraSnapshot(state_directory / "cache")
        self.artwork = artwork or PresetArtwork(state_directory / "cache")
        self.track_artwork = track_artwork or TrackArtwork(self.cover_root)
        self.weather = weather or DwdSatelliteFrames(state_directory / "cache")
        self.ambient_artwork_root = ambient_artwork_root or AMBIENT_ARTWORK_ROOT
        self.ambient_audio = ambient_audio_cache or AmbientAudioCache(
            self.media_root / "ambient"
        )
        self._ambient_layer_player_factory = ambient_layer_player_factory or (
            lambda: MpvEngine(
                executable=getattr(self.player, "executable", Path("/usr/bin/mpv")),
                media_roots=getattr(self.player, "media_roots", (self.media_root,)),
            )
        )
        self._ambient_layer_players: dict[str, MpvEngine] = {}
        self.brandmeister = brandmeister or BrandmeisterReceiver()
        self.brandmeister_catalog = brandmeister_catalog or BrandmeisterTalkgroupCatalog(
            state_directory / "cache" / "brandmeister-talkgroups.json"
        )
        self.radio_buffer = radio_buffer or (
            IcyRadioBuffer(self._store_buffered_track) if player is None else None
        )
        self._artwork_pending: set[str] = set()
        self._artwork_guard = threading.Lock()
        self._weather_pending: set[str] = set()
        self._weather_guard = threading.Lock()
        self._worker_threads: set[threading.Thread] = set()
        self._worker_guard = threading.Lock()
        self._podcast_cache: dict[int, dict[str, object]] = {}
        self._active_podcast_subscription_id: int | None = None
        self._active_podcast_episode: dict[str, object] | None = None
        mediathek_provider_ids = [
            str(provider["provider_id"])
            for provider in MediathekCatalog.providers()
        ]
        self._mediathek_results: dict[str, list[MediathekEntry]] = {
            provider_id: [] for provider_id in mediathek_provider_ids
        }
        self._mediathek_queries = {
            provider_id: "" for provider_id in mediathek_provider_ids
        }
        self._mediathek_selected: dict[str, str | None] = {
            provider_id: None for provider_id in mediathek_provider_ids
        }
        self._active_mediathek_provider: str | None = None
        self._active_mediathek_results: tuple[MediathekEntry, ...] = ()
        self._active_mediathek_item: dict[str, object] | None = None
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
        self._voice_playback_active = False
        self._voice_previous_volume: int | None = None
        self.selected_ambient_scene_id: int | None = None
        self.active_ambient_scene_id: int | None = None
        self.selected_ambient_layer_id = AMBIENT_LAYER_IDS[0]
        self._ambient_layer_state: dict[str, dict[str, object]] = {}
        self.selected_brandmeister_channel_id: int | None = None
        self.selected_brandmeister_talkgroup: int | None = None
        self.brandmeister_country_filter: str | None = None
        self.selected_brandmeister_country = BRANDMEISTER_ALL_COUNTRIES
        self._pending_brandmeister_talkgroup: int | None = None
        self._selected_brandmeister_replacement: int | None = None
        self.selected_camera_id: int | None = None
        self._brandmeister_catalog_entries_cache: list[dict[str, object]] = []
        self._brandmeister_catalog_guard = threading.Lock()
        self.store.ensure_services(
            tuple(item.service_id for item in BUILTIN_SERVICES),
            DEFAULT_ENABLED_SERVICES,
        )
        self.store.seed_stations_once(
            "webradio",
            tuple(
                (item.name, item.stream_url)
                for item in RADIO_PRESETS
                if item.default_enabled
            ),
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
        self.store.seed_channels_once(
            "ambient",
            tuple(
                (
                    item.preset_id,
                    item.name,
                    {
                        "source_url": item.audio_url,
                        "description": item.description,
                        "source_page": item.source_page,
                        "credit": item.credit,
                        "license_name": item.license_name,
                        "license_url": item.license_url,
                        **({"sha256": item.sha256} if item.sha256 else {}),
                    },
                )
                for item in AMBIENT_PRESETS
            ),
            marker="ambient.defaults_seeded_v1",
        )
        self.store.seed_channels_once(
            "brandmeister",
            (("91", "Worldwide", {"talkgroup": 91, "enabled": True}),),
            marker="brandmeister.defaults_seeded_v1",
        )
        if self.store.get_setting(BRANDMEISTER_NATIVE_MIGRATION_KEY, False) is not True:
            self.store.set_service_enabled("brandmeister", True)
            self.store.set_setting(BRANDMEISTER_NATIVE_MIGRATION_KEY, True)
        self._upgrade_germany_weather_default()
        self._seed_germany_satellite_upgrade()
        self._upgrade_ambient_source_urls()
        self._upgrade_quiet_cafe_source()
        self._seed_ambient_layer_scenes()
        self._ambient_layer_state = self._load_ambient_layer_state()
        weather_channels = self.store.channels("weather")
        if weather_channels:
            self.active_weather_channel_id = int(weather_channels[0]["id"])
        ambient_scenes = self.store.channels("ambient")
        if ambient_scenes:
            self.selected_ambient_scene_id = int(ambient_scenes[0]["id"])
        brandmeister_channels = self.store.channels("brandmeister")
        if brandmeister_channels:
            self.selected_brandmeister_channel_id = int(brandmeister_channels[0]["id"])
            metadata = brandmeister_channels[0].get("metadata")
            talkgroup = metadata.get("talkgroup") if isinstance(metadata, dict) else None
            if isinstance(talkgroup, int) and not isinstance(talkgroup, bool):
                self.selected_brandmeister_talkgroup = talkgroup
        camera_channels = self.store.channels("webcam")
        if camera_channels:
            self.selected_camera_id = int(camera_channels[0]["id"])
        if self.radio_buffer is not None:
            self.radio_buffer.set_continuous(
                self.store.get_setting(RADIO_CONTINUOUS_KEY, False) is True
            )
        self._initial_view_resolved = False
        self._ambient_prefetch_started = False
        # Keep the documented media layout stable before rebuilding the index.
        self._migrate_legacy_recorded_music()
        # Index finalized/recovered voice recordings on every startup so a
        # power loss never leaves an existing MP3 invisible in the player.
        self.scan_media()

    def start_brandmeister_receiver(self) -> None:
        """Restore the persisted receive-only scanner in the real service process."""

        if not self.store.service_enabled("brandmeister"):
            return
        talkgroups = self._enabled_brandmeister_talkgroups()
        if talkgroups:
            self.brandmeister.set_volume(self.player.state.volume)
            self.brandmeister.listen(talkgroups)
            self.active_service = "brandmeister"

    def prefetch_ambient_audio(self) -> None:
        """Populate the reviewed offline cache once in the real service process."""

        if self._ambient_prefetch_started:
            return
        self._ambient_prefetch_started = True
        self._start_worker(
            "openr4d10-ambient-offline-cache",
            self._cache_builtin_ambient_audio,
        )

    def prefetch_brandmeister_catalog(self) -> None:
        """Warm the official catalog without delaying device rendering."""

        self._start_worker(
            "openr4d10-brandmeister-catalog",
            self._load_brandmeister_catalog,
        )

    def _load_brandmeister_catalog(self) -> None:
        try:
            entries = self.brandmeister_catalog.entries()
        except OSError as exc:
            LOG.warning("BrandMeister talkgroup catalog unavailable: %s", exc)
            return
        with self._brandmeister_catalog_guard:
            self._brandmeister_catalog_entries_cache = entries

    def _brandmeister_catalog_entries(self, *, allow_network: bool) -> list[dict[str, object]]:
        with self._brandmeister_catalog_guard:
            cached = list(self._brandmeister_catalog_entries_cache)
        if cached or not allow_network:
            return cached
        self._load_brandmeister_catalog()
        with self._brandmeister_catalog_guard:
            return list(self._brandmeister_catalog_entries_cache)

    def _brandmeister_device_entries(self, *, allow_network: bool) -> list[dict[str, object]]:
        """Return the complete device browsing order without exposing it publicly.

        Enabled saved groups come first, followed by disabled saved groups and
        then the remaining official catalog.  The renderer receives only a
        small window around the selected entry, so even the full official
        catalog stays bounded in status frames.
        """

        official = self._brandmeister_catalog_entries(allow_network=allow_network)
        official_by_talkgroup = {
            int(item["talkgroup"]): item
            for item in official
            if isinstance(item.get("talkgroup"), int)
            and not isinstance(item.get("talkgroup"), bool)
        }
        saved: list[dict[str, object]] = []
        for channel in self.store.channels("brandmeister"):
            metadata = channel.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            talkgroup = metadata.get("talkgroup")
            if not isinstance(talkgroup, int) or isinstance(talkgroup, bool):
                continue
            official_entry = official_by_talkgroup.get(talkgroup, {})
            saved.append(
                {
                    "talkgroup": talkgroup,
                    "name": str(official_entry.get("name") or channel["name"]),
                    "country_code": str(
                        official_entry.get("country_code")
                        or country_code(talkgroup)
                        or ""
                    )[:2].upper(),
                    "enabled": metadata.get("enabled") is True,
                    "channel_id": int(channel["id"]),
                }
            )

        enabled_entries: list[dict[str, object]] = []
        inactive_entries: list[dict[str, object]] = []
        seen: set[int] = set()
        for item in saved:
            talkgroup = int(item["talkgroup"])
            if item["enabled"] is True and talkgroup not in seen:
                enabled_entries.append(item)
                seen.add(talkgroup)
        for item in saved:
            talkgroup = int(item["talkgroup"])
            if item["enabled"] is False and talkgroup not in seen:
                inactive_entries.append(item)
                seen.add(talkgroup)
        for item in official:
            talkgroup = item.get("talkgroup")
            if (
                not isinstance(talkgroup, int)
                or isinstance(talkgroup, bool)
                or talkgroup in seen
            ):
                continue
            inactive_entries.append(
                {
                    "talkgroup": talkgroup,
                    "name": str(item.get("name") or f"TG {talkgroup}"),
                    "country_code": str(
                        item.get("country_code") or country_code(talkgroup) or ""
                    )[:2].upper(),
                    "enabled": False,
                    "channel_id": None,
                }
            )
            seen.add(talkgroup)
        if self.brandmeister_country_filter is None:
            return enabled_entries + inactive_entries
        country_filter = self.brandmeister_country_filter
        filtered_inactive = [
            item
            for item in inactive_entries
            if (
                str(item.get("country_code") or "") == country_filter
                if country_filter != BRANDMEISTER_OTHER_COUNTRIES
                else not str(item.get("country_code") or "")
            )
        ]
        return enabled_entries + filtered_inactive

    def _brandmeister_country_entries(
        self, *, allow_network: bool
    ) -> list[dict[str, object]]:
        entries = self._brandmeister_catalog_entries(allow_network=allow_network)
        codes = sorted(
            {
                str(item.get("country_code") or BRANDMEISTER_OTHER_COUNTRIES)
                for item in entries
            }
        )
        names = (
            BRANDMEISTER_COUNTRY_NAMES_DE
            if self.display_language() == "de"
            else BRANDMEISTER_COUNTRY_NAMES
        )
        all_name = "Alle Länder" if self.display_language() == "de" else "All countries"
        other_name = "Andere" if self.display_language() == "de" else "Other"
        rows = [
            {
                "code": BRANDMEISTER_ALL_COUNTRIES,
                "name": all_name,
                "selected": self.selected_brandmeister_country == BRANDMEISTER_ALL_COUNTRIES,
            }
        ]
        for code in codes:
            rows.append(
                {
                    "code": code,
                    "name": other_name if code == BRANDMEISTER_OTHER_COUNTRIES else names.get(code, code),
                    "selected": self.selected_brandmeister_country == code,
                }
            )
        return rows

    @staticmethod
    def _bounded_selection_window(
        rows: list[dict[str, object]], *, size: int = 5
    ) -> tuple[list[dict[str, object]], int, int]:
        if not rows:
            return [], 0, 0
        selected = next(
            (index for index, item in enumerate(rows) if item.get("selected") is True),
            0,
        )
        window_size = max(1, min(size, len(rows)))
        start = max(0, min(selected - window_size // 2, len(rows) - window_size))
        visible = []
        for index, item in enumerate(rows[start : start + window_size], start=start):
            row = dict(item)
            row["position"] = index + 1
            visible.append(row)
        return visible, selected + 1, len(rows)

    def _brandmeister_replacement_rows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for channel in self.store.channels("brandmeister"):
            metadata = channel.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            talkgroup = metadata.get("talkgroup")
            if (
                metadata.get("enabled") is not True
                or not isinstance(talkgroup, int)
                or isinstance(talkgroup, bool)
            ):
                continue
            rows.append(
                {
                    "talkgroup": talkgroup,
                    "name": str(channel["name"]),
                    "country_code": country_code(talkgroup) or "",
                    "selected": talkgroup == self._selected_brandmeister_replacement,
                }
            )
        if rows and not any(item["selected"] is True for item in rows):
            rows[0]["selected"] = True
            self._selected_brandmeister_replacement = int(rows[0]["talkgroup"])
        return rows[:MAX_TALKGROUPS]

    def _brandmeister_device_window(
        self, entries: list[dict[str, object]], *, size: int = MAX_TALKGROUPS
    ) -> tuple[list[dict[str, object]], int, int]:
        """Return a bounded, scrollable catalog window for the 240x280 UI."""

        total = len(entries)
        if total == 0:
            return [], 0, 0
        talkgroups = [int(item["talkgroup"]) for item in entries]
        selected_index = (
            talkgroups.index(self.selected_brandmeister_talkgroup)
            if self.selected_brandmeister_talkgroup in talkgroups
            else 0
        )
        if self.selected_brandmeister_talkgroup not in talkgroups:
            self.selected_brandmeister_talkgroup = talkgroups[selected_index]
        window_size = max(1, min(size, total))
        start = max(0, min(selected_index - window_size // 2, total - window_size))
        rows = []
        for absolute_index, item in enumerate(
            entries[start : start + window_size], start=start
        ):
            row = dict(item)
            row["selected"] = absolute_index == selected_index
            row["position"] = absolute_index + 1
            rows.append(row)
        return rows, selected_index + 1, total

    def _saved_brandmeister_channel_for_talkgroup(
        self, talkgroup: int | None
    ) -> dict[str, object] | None:
        if talkgroup is None:
            return None
        for channel in self.store.channels("brandmeister"):
            metadata = channel.get("metadata")
            if isinstance(metadata, dict) and metadata.get("talkgroup") == talkgroup:
                return channel
        return None

    def _selected_brandmeister_entry(self) -> dict[str, object] | None:
        talkgroup = self.selected_brandmeister_talkgroup
        for entry in self._brandmeister_catalog_entries(allow_network=False):
            if entry.get("talkgroup") == talkgroup:
                return entry
        channel = self._saved_brandmeister_channel_for_talkgroup(talkgroup)
        if channel is None:
            return None
        return {
            "talkgroup": talkgroup,
            "name": str(channel["name"]),
            "country_code": country_code(talkgroup) if talkgroup is not None else None,
        }

    def _enabled_brandmeister_talkgroups(self) -> list[int]:
        enabled: list[int] = []
        for channel in self.store.channels("brandmeister"):
            metadata = channel.get("metadata")
            talkgroup = metadata.get("talkgroup") if isinstance(metadata, dict) else None
            if (
                isinstance(talkgroup, int)
                and not isinstance(talkgroup, bool)
                and metadata.get("enabled") is True
            ):
                enabled.append(talkgroup)
            if len(enabled) == MAX_TALKGROUPS:
                break
        return enabled

    def _replace_brandmeister_talkgroup(
        self,
        old_talkgroup: int,
        new_talkgroup: int,
        new_name: str,
    ) -> dict[str, object]:
        old_channel = self._saved_brandmeister_channel_for_talkgroup(old_talkgroup)
        if old_channel is None:
            raise ValueError("the talkgroup selected for replacement is not saved")
        old_metadata = old_channel.get("metadata")
        old_metadata = dict(old_metadata) if isinstance(old_metadata, dict) else {}
        if old_metadata.get("enabled") is not True:
            raise ValueError("the talkgroup selected for replacement is not active")

        new_channel = self._saved_brandmeister_channel_for_talkgroup(new_talkgroup)
        if new_channel is None:
            if len(self.store.channels("brandmeister")) >= 30:
                raise ValueError("at most 30 BrandMeister talkgroups can be saved")
            new_channel_id = self.store.add_channel(
                "brandmeister",
                str(new_talkgroup),
                new_name,
                {"talkgroup": new_talkgroup, "enabled": False},
            )
            new_channel = self.store.channel(new_channel_id)
        if new_channel is None:
            raise RuntimeError("replacement talkgroup could not be saved")

        old_metadata["enabled"] = False
        self.store.update_channel(
            int(old_channel["id"]), str(old_channel["name"]), old_metadata
        )
        new_metadata = new_channel.get("metadata")
        new_metadata = dict(new_metadata) if isinstance(new_metadata, dict) else {}
        new_metadata.update({"talkgroup": new_talkgroup, "enabled": True})
        self.store.update_channel(
            int(new_channel["id"]), str(new_channel["name"]), new_metadata
        )
        self.selected_brandmeister_talkgroup = new_talkgroup
        self.selected_brandmeister_channel_id = int(new_channel["id"])
        self._pending_brandmeister_talkgroup = None
        self._selected_brandmeister_replacement = None
        state = self._reconfigure_brandmeister_receiver()
        return {
            "channel_id": int(new_channel["id"]),
            "talkgroup": new_talkgroup,
            "enabled": True,
            "replaced_talkgroup": old_talkgroup,
            "brandmeister": state,
        }

    def _brandmeister_activity_rows(
        self, state: dict[str, object] | None = None
    ) -> list[dict[str, object]]:
        state = state or self.brandmeister.snapshot()
        raw_activity = state.get("activity")
        activity_by_talkgroup: dict[int, dict[str, object]] = {}
        if isinstance(raw_activity, list):
            for item in raw_activity:
                if not isinstance(item, dict):
                    continue
                talkgroup = item.get("talkgroup")
                if isinstance(talkgroup, int) and not isinstance(talkgroup, bool):
                    activity_by_talkgroup[talkgroup] = item
        rows: list[dict[str, object]] = []
        for channel in self.store.channels("brandmeister"):
            metadata = channel.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            talkgroup = metadata.get("talkgroup")
            if (
                metadata.get("enabled") is not True
                or not isinstance(talkgroup, int)
                or isinstance(talkgroup, bool)
            ):
                continue
            heard = activity_by_talkgroup.get(talkgroup, {})
            source = heard.get("source")
            rows.append(
                {
                    "talkgroup": talkgroup,
                    "name": str(channel["name"]),
                    "country_code": country_code(talkgroup),
                    "active": heard.get("active") is True,
                    "source": source if isinstance(source, int) and not isinstance(source, bool) else None,
                    "alias": str(heard.get("alias") or "")[:80],
                    "updated_at": str(heard.get("updated_at") or ""),
                }
            )
            if len(rows) == MAX_TALKGROUPS:
                break
        rows.sort(key=lambda item: not bool(item["active"]))
        return rows

    def _selected_brandmeister_channel(self) -> dict[str, object] | None:
        channels = self.store.channels("brandmeister")
        if not channels:
            return None
        selected = (
            self.store.channel(self.selected_brandmeister_channel_id)
            if self.selected_brandmeister_channel_id is not None
            else None
        )
        if selected is None or selected.get("service_id") != "brandmeister":
            selected = channels[0]
            self.selected_brandmeister_channel_id = int(selected["id"])
        return selected

    def _restart_brandmeister_receiver(self) -> dict[str, object]:
        talkgroups = self._enabled_brandmeister_talkgroups()
        if not talkgroups:
            self.brandmeister.stop()
            if self.active_service == "brandmeister":
                self.active_service = "system"
            return self.brandmeister.snapshot()
        self._stop_ambient_layers()
        self.player.stop()
        if self.radio_buffer is not None:
            self.radio_buffer.stop(flush=True)
        self.brandmeister.set_volume(self.player.state.volume)
        state = self.brandmeister.listen(talkgroups)
        self.active_service = "brandmeister"
        self.active_preset_id = None
        self.active_station_id = None
        self._active_podcast_episode = None
        self.active_ambient_scene_id = None
        return state

    def _reconfigure_brandmeister_receiver(self) -> dict[str, object]:
        """Apply TG changes without stealing audio from another active service."""

        state = self.brandmeister.snapshot()
        status = str(state.get("status") or "stopped")
        if self.active_service == "brandmeister" or status in {
            "connecting",
            "listening",
            "call",
            "reconnecting",
        }:
            return self._restart_brandmeister_receiver()
        return state

    def _stop_brandmeister_for_audio_owner(self) -> None:
        if self.active_service == "ambient":
            self._stop_ambient_layers()
        if self.active_service == "brandmeister":
            self.brandmeister.stop()

    def _open_voice_recorder(self) -> dict[str, object]:
        """Give microphone capture exclusive ownership and silence playback."""
        self._require_enabled("recorder")
        if self.active_service != "recorder" and self._voice_previous_volume is None:
            self._voice_previous_volume = int(self.player.state.volume)
        self.brandmeister.stop()
        self._stop_ambient_layers()
        self.player.stop()
        volume_setter = getattr(self.player, "set_volume", None)
        if callable(volume_setter):
            volume_setter(100)
        else:
            self.player.state.volume = 100
        self._voice_playback_active = False
        if self.radio_buffer is not None:
            self.radio_buffer.stop(flush=True)
        self.active_service = "recorder"
        self.active_preset_id = None
        self.active_station_id = None
        self._active_podcast_episode = None
        self.active_ambient_scene_id = None
        snapshot = getattr(self.recorder, "voice_snapshot", None)
        return snapshot() if callable(snapshot) else self.recorder.state.as_dict()

    def _sync_voice_playback_position(self, *, persist: bool = False) -> None:
        if not self._voice_playback_active:
            return
        position_reader = getattr(self.player, "position_seconds", None)
        position = position_reader() if callable(position_reader) else None
        setter = getattr(
            self.recorder,
            "voice_set_position" if persist else "voice_follow_playback",
            None,
        )
        if not callable(setter):
            setter = getattr(self.recorder, "voice_set_position", None)
        if (
            isinstance(position, (int, float))
            and not isinstance(position, bool)
            and callable(setter)
        ):
            setter(round(float(position) * 1000))
            return
        # A missing time position after a confirmed start is not a synthetic
        # clock tick. Mpv records asynchronous EOF/output failures in its
        # state; detach the Recorder playhead immediately so UI and ALSA stay
        # one truth.
        if str(getattr(self.player.state, "state", "stopped")) in {
            "stopped",
            "error",
        }:
            self._voice_playback_active = False

    def _stop_voice_playback(self, *, sync: bool = True) -> None:
        if sync:
            self._sync_voice_playback_position(persist=True)
        if self._voice_playback_active:
            self.player.stop()
        self._voice_playback_active = False

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

    def _upgrade_ambient_source_urls(self) -> None:
        """Replace only existing built-in redirect URLs; never recreate scenes."""
        if self.store.get_setting(AMBIENT_SOURCE_MIGRATION_KEY, False) is True:
            return
        for scene in self.store.channels("ambient"):
            preset = AMBIENT_BY_ID.get(str(scene["external_id"]))
            metadata = scene.get("metadata")
            if preset is None or not isinstance(metadata, dict):
                continue
            source = metadata.get("source_url")
            if not isinstance(source, str) or "commons.wikimedia.org/wiki/Special:Redirect/file/" not in source:
                continue
            updated = dict(metadata)
            updated["source_url"] = preset.audio_url
            self.store.update_channel(int(scene["id"]), str(scene["name"]), updated)
        self.store.set_setting(AMBIENT_SOURCE_MIGRATION_KEY, True)

    def _upgrade_quiet_cafe_source(self) -> None:
        """Replace only the untouched busy built-in café recording once."""
        if self.store.get_setting(QUIET_CAFE_MIGRATION_KEY, False) is True:
            return
        preset = AMBIENT_BY_ID["cafe"]
        scene = next(
            (
                item
                for item in self.store.channels("ambient")
                if item["external_id"] == "cafe"
            ),
            None,
        )
        if scene is not None:
            metadata = scene.get("metadata")
            if (
                isinstance(metadata, dict)
                and (
                    metadata.get("source_url") == OLD_CAFE_AUDIO_URL
                    or (
                        isinstance(metadata.get("source_url"), str)
                        and "Special:Redirect/file/Cafe_ambiance.ogg"
                        in str(metadata["source_url"])
                    )
                    or (
                        metadata.get("source_url") == preset.audio_url
                        and metadata.get("source_page")
                        == "https://commons.wikimedia.org/wiki/File:Cafe_ambiance.ogg"
                    )
                )
            ):
                updated = dict(metadata)
                updated.update(
                    {
                        "source_url": preset.audio_url,
                        "description": preset.description,
                        "source_page": preset.source_page,
                        "credit": preset.credit,
                        "license_name": preset.license_name,
                        "license_url": preset.license_url,
                        "sha256": preset.sha256,
                    }
                )
                self.store.update_channel(
                    int(scene["id"]),
                    str(scene["name"]),
                    updated,
                )
        self.store.set_setting(QUIET_CAFE_MIGRATION_KEY, True)

    def _seed_ambient_layer_scenes(self) -> None:
        """Append the four new reviewed scenes once without resetting user order."""

        if self.store.get_setting(AMBIENT_SCENE_UPGRADE_KEY, False) is True:
            return
        existing = {
            str(item["external_id"]) for item in self.store.channels("ambient")
        }
        for preset_id in AMBIENT_LAYER_IDS:
            if preset_id in existing:
                continue
            item = AMBIENT_BY_ID[preset_id]
            self.store.add_channel(
                "ambient",
                item.preset_id,
                item.name,
                {
                    "source_url": item.audio_url,
                    "description": item.description,
                    "source_page": item.source_page,
                    "credit": item.credit,
                    "license_name": item.license_name,
                    "license_url": item.license_url,
                    "sha256": item.sha256,
                },
            )
        self.store.set_setting(AMBIENT_SCENE_UPGRADE_KEY, True)

    def _load_ambient_layer_state(self) -> dict[str, dict[str, object]]:
        raw = self.store.get_setting(AMBIENT_LAYER_STATE_KEY, {})
        raw = raw if isinstance(raw, dict) else {}
        state: dict[str, dict[str, object]] = {}
        for layer_id in AMBIENT_LAYER_IDS:
            item = raw.get(layer_id)
            item = item if isinstance(item, dict) else {}
            enabled = item.get("enabled") is True
            volume = item.get("volume", AMBIENT_LAYER_DEFAULTS[layer_id])
            if isinstance(volume, bool) or not isinstance(volume, int):
                volume = AMBIENT_LAYER_DEFAULTS[layer_id]
            state[layer_id] = {
                "enabled": enabled,
                "volume": max(0, min(100, volume)),
            }
        return state

    def _persist_ambient_layer_state(self) -> None:
        self.store.set_setting(AMBIENT_LAYER_STATE_KEY, self._ambient_layer_state)

    def _ambient_layer_source(self, layer_id: str) -> str:
        preset = AMBIENT_BY_ID[layer_id]
        if preset.sha256 is not None:
            cached = self.ambient_audio.cached(preset.preset_id, preset.sha256)
            if cached is not None:
                return validate_media_source(str(cached), (self.media_root,))
        return validate_media_source(preset.audio_url, (self.media_root,))

    def _ambient_layer_output_volume(self, layer_id: str) -> int:
        relative = int(self._ambient_layer_state[layer_id]["volume"])
        return round(self.player.state.volume * relative / 100)

    def _stop_ambient_layers(self) -> None:
        players = tuple(self._ambient_layer_players.values())
        self._ambient_layer_players.clear()
        for player in players:
            player.close()

    def _sync_ambient_layers(self, *, restart: bool = False) -> None:
        if self.active_service != "ambient" or self.active_ambient_scene_id is None:
            self._stop_ambient_layers()
            return
        if restart:
            self._stop_ambient_layers()
        for layer_id in AMBIENT_LAYER_IDS:
            enabled = self._ambient_layer_state[layer_id]["enabled"] is True
            player = self._ambient_layer_players.get(layer_id)
            if not enabled:
                if player is not None:
                    player.close()
                    del self._ambient_layer_players[layer_id]
                continue
            volume = self._ambient_layer_output_volume(layer_id)
            if player is None:
                player = self._ambient_layer_player_factory()
                player.state.volume = volume
                try:
                    player.load_playlist(
                        [self._ambient_layer_source(layer_id)],
                        loop=True,
                    )
                    if self.player.state.paused:
                        player.toggle_pause()
                except Exception:
                    player.close()
                    raise
                self._ambient_layer_players[layer_id] = player
            elif player.state.volume != volume:
                player.set_volume(volume)

    def _set_ambient_layer_state(
        self,
        layer_id: str,
        *,
        enabled: bool | None = None,
        volume: int | None = None,
    ) -> dict[str, object]:
        if layer_id not in AMBIENT_LAYER_IDS:
            raise ValueError("unknown ambient sound layer")
        state = self._ambient_layer_state[layer_id]
        if (
            enabled is True
            and state["enabled"] is not True
            and sum(
                item["enabled"] is True
                for item in self._ambient_layer_state.values()
            ) >= 2
        ):
            raise ValueError("at most two ambient sound layers can be active")
        if enabled is not None:
            state["enabled"] = enabled
        if volume is not None:
            state["volume"] = max(0, min(100, volume))
        self._persist_ambient_layer_state()
        self._sync_ambient_layers()
        return dict(state)

    def _ambient_layer_rows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        language = self.display_language()
        for position, layer_id in enumerate(AMBIENT_LAYER_IDS, start=1):
            preset = AMBIENT_BY_ID[layer_id]
            translated = ambient_text(layer_id, language)
            name, description = translated or (preset.name, preset.description)
            state = self._ambient_layer_state[layer_id]
            rows.append(
                {
                    "id": layer_id,
                    "name": name,
                    "description": description,
                    "enabled": state["enabled"] is True,
                    "volume": int(state["volume"]),
                    "active": layer_id in self._ambient_layer_players,
                    "selected": layer_id == self.selected_ambient_layer_id,
                    "position": position,
                    "source_page": preset.source_page,
                    "credit": preset.credit,
                    "license_name": preset.license_name,
                    "license_url": preset.license_url,
                }
            )
        rows.append(
            {
                "id": AMBIENT_SAVE_ACTION,
                "name": {
                    "de": "Mix speichern",
                    "pl": "Zapisz miks",
                    "fr": "Enregistrer le mix",
                    "es": "Guardar mezcla",
                }.get(language, "Save favorite mix"),
                "description": "",
                "enabled": False,
                "volume": None,
                "active": False,
                "selected": self.selected_ambient_layer_id == AMBIENT_SAVE_ACTION,
                "position": len(AMBIENT_LAYER_IDS) + 1,
            }
        )
        return rows

    def _save_ambient_favorite(self, requested_name: object = None) -> int:
        if self.selected_ambient_scene_id is None:
            raise ValueError("select an ambient base scene first")
        base = self._ambient_scene(self.selected_ambient_scene_id)
        metadata = base.get("metadata")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("source_url"), str):
            raise ValueError("ambient base scene has no media source")
        name = requested_name.strip() if isinstance(requested_name, str) else ""
        if not name:
            number = 1 + sum(
                str(item["external_id"]).startswith("mix-")
                for item in self.store.channels("ambient")
            )
            name = f"Favorite mix {number}"
        if len(name) > 160:
            raise ValueError("favorite mix name is too long")
        source_preset_id = str(
            metadata.get("source_preset_id") or base.get("external_id") or ""
        )
        favorite_metadata = {
            "source_url": str(metadata["source_url"]),
            "source_preset_id": source_preset_id,
            "description": "Favorite AmbientR4D10 sound mix",
            "mix_layers": {
                layer_id: dict(self._ambient_layer_state[layer_id])
                for layer_id in AMBIENT_LAYER_IDS
            },
        }
        scene_id = self.store.add_channel(
            "ambient",
            f"mix-{uuid.uuid4().hex[:16]}",
            name,
            favorite_metadata,
        )
        self.selected_ambient_scene_id = scene_id
        return scene_id

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
        artist_root = (self.music_root / artist).resolve()
        music_root = self.music_root.resolve()
        if not artist_root.is_relative_to(music_root):
            raise ValueError("recorded track path escaped the music root")
        artist_root.mkdir(parents=True, exist_ok=True, mode=0o750)
        basename = self._track_part(
            f"{artist} - {title}", "Unbekannt - Aufnahme", 220
        )
        output = artist_root / f"{basename}.mp3"
        if output.exists():
            output = artist_root / f"{basename} - {checksum[:8]}.mp3"
        temporary = output.with_name(output.stem + ".part.mp3")
        if "mpeg" in track.content_type or "mp3" in track.content_type:
            temporary.write_bytes(track.payload)
        else:
            executable = self.executable_lookup("ffmpeg")
            if executable is None:
                raise RuntimeError("ffmpeg is required to store radio tracks as MP3")
            input_format = "aac" if "aac" in track.content_type else None
            command = [
                executable,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
            ]
            if input_format is not None:
                command.extend(("-f", input_format))
            command.extend(
                (
                    "-i",
                    "pipe:0",
                    "-map",
                    "0:a:0",
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "192k",
                    "-vn",
                    "-y",
                    str(temporary),
                )
            )
            result = subprocess.run(
                command,
                input=track.payload,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=180,
            )
            if result.returncode != 0 or not temporary.is_file():
                temporary.unlink(missing_ok=True)
                raise RuntimeError("radio track could not be encoded as MP3")
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
                        if manifest.service_id == "anker_solix":
                            metrics = adapter_status.get("metrics")
                            if isinstance(metrics, dict):
                                public_metrics: dict[str, int | float] = {}
                                for key, (minimum, maximum) in SOLIX_METRIC_RANGES.items():
                                    value = metrics.get(key)
                                    if (
                                        not isinstance(value, bool)
                                        and isinstance(value, (int, float))
                                        and minimum <= float(value) <= maximum
                                    ):
                                        public_metrics[key] = value
                                if public_metrics:
                                    adapter_state["metrics"] = public_metrics
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
                    "language": preset.language if preset is not None else "",
                    "categories": list(preset.categories) if preset is not None else [],
                    "description": preset.description if preset is not None else "",
                    "artwork": (
                        f"/api/radio-art/{preset.preset_id}"
                        if preset is not None else None
                    ),
                }
            )
        podcast_subscriptions = []
        for position, item in enumerate(self.store.channels("podcasts")):
            metadata = item.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            feed_url = metadata.get("feed_url")
            source = ""
            if isinstance(feed_url, str):
                source = urlsplit(feed_url).hostname or ""
            cached = self._podcast_cache.get(int(item["id"]))
            podcast_subscriptions.append(
                {
                    "id": int(item["id"]),
                    "name": str(item["name"]),
                    "description": str(metadata.get("description") or ""),
                    "homepage": str(metadata.get("homepage") or ""),
                    "source": source,
                    "position": position,
                    "selected": int(item["id"]) == self._active_podcast_subscription_id,
                    "episode_count": (
                        int(cached.get("episode_count", 0)) if cached is not None else None
                    ),
                }
            )
        selected_podcast = (
            self._podcast_cache.get(self._active_podcast_subscription_id)
            if self._active_podcast_subscription_id is not None
            else None
        )
        podcast_episodes = (
            self._public_podcast_episodes(selected_podcast)
            if selected_podcast is not None
            else []
        )
        media = []
        for item in self.store.media_items():
            folder = "Media"
            try:
                relative = Path(str(item["path"])).resolve().relative_to(
                    self.media_root.resolve()
                )
                if item["source_kind"] in {"radio", "voice"} and len(relative.parts) >= 2:
                    folder = "/".join(relative.parts[:-1])
            except (OSError, ValueError):
                pass
            media.append(
                {
                    "id": item["id"],
                    "artist": item["artist"],
                    "title": item["title"],
                    "size_bytes": item["size_bytes"],
                    "favorite": bool(item["favorite"]),
                    "review_required": bool(item["review_required"]),
                    "source_kind": item["source_kind"],
                    "folder": folder,
                    "cover": (
                        f"/api/media-cover/{item['id']}"
                        if item["cover_file"]
                        else None
                    ),
                }
            )
        media.sort(
            key=lambda item: (
                1 if item["source_kind"] == "voice" else 0,
                str(item["folder"]).casefold(),
                str(item["title"]).casefold(),
            )
        )
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
        ambient_scenes = []
        for channel, item in enumerate(self.store.channels("ambient"), start=1):
            preset_id = str(item["external_id"])
            metadata = item.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            source_url = metadata.get("source_url")
            source_host = (
                urlsplit(source_url).hostname or ""
                if isinstance(source_url, str)
                else ""
            )
            artwork_preset_id = str(
                metadata.get("source_preset_id") or preset_id
            )
            ambient_scenes.append(
                {
                    "id": int(item["id"]),
                    "preset_id": preset_id,
                    "name": str(item["name"]),
                    "artwork": (
                        f"/api/ambient-art/{artwork_preset_id}"
                        if artwork_preset_id in AMBIENT_BY_ID
                        else None
                    ),
                    "favorite_mix": preset_id.startswith("mix-"),
                    "description": str(metadata.get("description") or ""),
                    "credit": str(metadata.get("credit") or ""),
                    "license_name": str(metadata.get("license_name") or ""),
                    "license_url": str(metadata.get("license_url") or ""),
                    "source_page": str(metadata.get("source_page") or ""),
                    "source": source_host,
                    "position": channel - 1,
                    "channel": channel,
                    "selected": int(item["id"]) == self.selected_ambient_scene_id,
                    "active": int(item["id"]) == self.active_ambient_scene_id,
                }
            )
        brandmeister_state = self.brandmeister.snapshot()
        brandmeister_activity = self._brandmeister_activity_rows(brandmeister_state)
        activity_by_talkgroup = {
            int(item["talkgroup"]): item for item in brandmeister_activity
        }
        brandmeister_channels = []
        for channel, item in enumerate(self.store.channels("brandmeister"), start=1):
            metadata = item.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            talkgroup = metadata.get("talkgroup")
            if not isinstance(talkgroup, int) or isinstance(talkgroup, bool):
                continue
            public_channel = {
                    "id": int(item["id"]),
                    "talkgroup": talkgroup,
                    "name": str(item["name"]),
                    "enabled": metadata.get("enabled") is True,
                    "country_code": country_code(talkgroup),
                    "position": channel - 1,
                    "channel": channel,
                    "selected": talkgroup == self.selected_brandmeister_talkgroup,
                }
            public_channel.update(activity_by_talkgroup.get(talkgroup, {}))
            brandmeister_channels.append(public_channel)
        webcam_channels = []
        cached_cameras = self.content_state.get("cameras")
        cached_cameras = cached_cameras if isinstance(cached_cameras, dict) else {}
        for channel, item in enumerate(self.store.channels("webcam"), start=1):
            metadata = item.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            source_url = metadata.get("source_url")
            kind = str(metadata.get("kind") or "snapshot")
            camera_id = int(item["id"])
            webcam_channels.append(
                {
                    "id": camera_id,
                    "name": str(item["name"]),
                    "kind": kind,
                    "enabled": metadata.get("enabled") is not False,
                    "source": (
                        urlsplit(source_url).hostname or ""
                        if isinstance(source_url, str)
                        else ""
                    ),
                    "position": channel - 1,
                    "channel": channel,
                    "selected": camera_id == self.selected_camera_id,
                    "frame": cached_cameras.get(str(camera_id)),
                    "image": (
                        f"/api/camera/{camera_id}"
                        if (self.camera.cache_root / f"camera-{camera_id}.jpg").is_file()
                        else None
                    ),
                }
            )
        mediathek_providers = {}
        for provider in self._mediathek_results:
            results = self._mediathek_results[provider]
            mediathek_providers[provider] = {
                "query": self._mediathek_queries[provider],
                "selected_item_id": self._mediathek_selected[provider],
                "results": [item.public() for item in results],
            }
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
            "recording": (
                self.recorder.voice_snapshot()
                if callable(getattr(self.recorder, "voice_snapshot", None))
                else self.recorder.state.as_dict()
            ),
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
            "podcasts": {
                "selected_subscription_id": self._active_podcast_subscription_id,
                "subscriptions": podcast_subscriptions,
                "episodes": podcast_episodes,
                "active_episode": self._active_podcast_episode,
                "limits": {"subscriptions": 100, "episodes_per_feed": 50},
            },
            "mediathek": {
                "providers": mediathek_providers,
                "provider_catalog": MediathekCatalog.providers(),
                "collections": MediathekCatalog.collections(),
                "active_provider": (
                    self._active_mediathek_provider
                    if self.active_service in MEDIATHEK_SERVICE_IDS
                    else None
                ),
                "active_item": (
                    self._active_mediathek_item
                    if self.active_service in MEDIATHEK_SERVICE_IDS
                    else None
                ),
                "limits": {
                    "results_per_provider": MediathekCatalog.MAX_RESULTS,
                    "response_bytes": MediathekCatalog.MAX_RESPONSE_BYTES,
                },
            },
            "weather": {
                "active_channel_id": self.active_weather_channel_id,
                "channels": weather_channels,
                "provider": "DWD / EUMETSAT",
                "refresh_floor_seconds": 300,
            },
            "ambient": {
                "selected_scene_id": self.selected_ambient_scene_id,
                "active_scene_id": self.active_ambient_scene_id,
                "scenes": ambient_scenes,
                "selected_layer_id": self.selected_ambient_layer_id,
                "layers": self._ambient_layer_rows(),
                "max_active_layers": 2,
            },
            "webcams": {
                "selected_camera_id": self.selected_camera_id,
                "channels": webcam_channels,
                "limits": {"saved": 100, "frame_bytes": CameraSnapshot.MAX_BYTES},
            },
            "brandmeister": {
                **brandmeister_state,
                "selected_channel_id": self.selected_brandmeister_channel_id,
                "selected_talkgroup": self.selected_brandmeister_talkgroup,
                "channels": brandmeister_channels,
                "activity_rows": brandmeister_activity,
                "country_filter": self.brandmeister_country_filter,
                "replacement_required": self._pending_brandmeister_talkgroup is not None,
                "pending_talkgroup": self._pending_brandmeister_talkgroup,
                "replacement_rows": self._brandmeister_replacement_rows()
                if self._pending_brandmeister_talkgroup is not None
                else [],
                "limits": {"saved": 30, "enabled": MAX_TALKGROUPS},
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
                if service_id == "brandmeister":
                    self.brandmeister.stop()
                if self.active_service == service_id:
                    if service_id == "ambient":
                        self._stop_ambient_layers()
                    self.player.stop()
                    if service_id == "webradio" and self.radio_buffer is not None:
                        self.radio_buffer.stop(flush=True)
                    self.active_service = "system"
                    self.active_preset_id = None
                    self.active_station_id = None
                    self._active_podcast_episode = None
                    self.active_ambient_scene_id = None
                if service_id == "recorder":
                    finalize = getattr(self.recorder, "voice_finalize", None)
                    if callable(finalize):
                        finalize()
                    else:
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
                "webradio", "local_media", "remote_sdr",
                "youtube_audio", "spotify", "ard_mediathek", "zdf_mediathek",
                "public_mediatheken",
                "international_media",
            }
            if not isinstance(service_id, str) or service_id not in allowed:
                raise ValueError("unsupported playback service")
            self._require_enabled(service_id)
            if not isinstance(source, str):
                raise ValueError("play action requires a media source")
            self._stop_brandmeister_for_audio_owner()
            self.player.load(source)
            if service_id == "webradio" and self.radio_buffer is not None:
                self.radio_buffer.tune(source, "Direkte Radioquelle")
            self.active_service = service_id
            self.active_preset_id = None
            self.active_station_id = None
            self._active_podcast_episode = None
            self.active_ambient_scene_id = None
        elif action == "pause":
            if self.player.state.state not in {"playing", "paused"}:
                raise ValueError("no active media to pause or resume")
            self.player.toggle_pause()
            if self.active_service == "ambient":
                for layer_player in self._ambient_layer_players.values():
                    layer_player.toggle_pause()
        elif action == "stop":
            self.brandmeister.stop()
            self._stop_ambient_layers()
            self.player.stop()
            if self.radio_buffer is not None:
                self.radio_buffer.stop(flush=True)
            self.active_service = "system"
            self.active_preset_id = None
            self.active_station_id = None
            self._active_podcast_episode = None
            self.active_ambient_scene_id = None
        elif action == "volume":
            value = request.get("value")
            if self.active_service == "brandmeister":
                self.brandmeister.set_volume(value)  # type: ignore[arg-type]
                self.player.state.volume = value  # type: ignore[assignment]
            else:
                self.player.set_volume(value)  # type: ignore[arg-type]
                if self.active_service == "ambient":
                    self._sync_ambient_layers()
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
            if self.active_service == "brandmeister":
                self.brandmeister.set_volume(volume)
                self.player.state.volume = volume
            else:
                self.player.set_volume(volume)
                if self.active_service == "ambient":
                    self._sync_ambient_layers()
        elif action == "voice_recorder_open":
            return {"recording": self._open_voice_recorder()}
        elif action in {"voice_recorder_hold", "voice_recorder_continuous"}:
            self._require_enabled("recorder")
            if self.active_service != "recorder":
                self._open_voice_recorder()
            self._stop_voice_playback()
            start = getattr(self.recorder, "voice_start", None)
            if not callable(start):
                raise RuntimeError("voice recording is unavailable")
            return {
                "recording": start(
                    continuous=action == "voice_recorder_continuous"
                )
            }
        elif action == "voice_recorder_pause":
            pause = getattr(self.recorder, "voice_pause", None)
            if not callable(pause):
                raise RuntimeError("voice recording is unavailable")
            return {"recording": pause()}
        elif action == "voice_recorder_seek":
            self._require_enabled("recorder")
            delta_ms = request.get("delta_ms")
            if isinstance(delta_ms, bool) or not isinstance(delta_ms, int):
                raise ValueError("voice recorder seek requires integer delta_ms")
            self._stop_voice_playback()
            seek = getattr(self.recorder, "voice_seek", None)
            if not callable(seek):
                raise RuntimeError("voice recording seek is unavailable")
            return {"recording": seek(delta_ms)}
        elif action == "voice_recorder_boundary":
            self._require_enabled("recorder")
            end = request.get("end")
            if not isinstance(end, bool):
                raise ValueError("voice recorder boundary requires boolean end")
            self._stop_voice_playback()
            boundary = getattr(self.recorder, "voice_boundary", None)
            if not callable(boundary):
                raise RuntimeError("voice recording navigation is unavailable")
            return {"recording": boundary(end=end)}
        elif action == "voice_recorder_play_toggle":
            self._require_enabled("recorder")
            if self.active_service != "recorder":
                self._open_voice_recorder()
            if self._voice_playback_active and self.player.state.state == "playing":
                playback = self.player.toggle_pause()
                self._sync_voice_playback_position(persist=True)
                return {"playback": playback}
            if self._voice_playback_active and self.player.state.state == "paused":
                return {"playback": self.player.toggle_pause()}
            path_reader = getattr(self.recorder, "voice_playback_path", None)
            path = path_reader() if callable(path_reader) else None
            if not isinstance(path, Path):
                raise ValueError("record something before playback")
            voice = self.recorder.voice_snapshot()
            position_ms = int(voice.get("position_ms") or 0)
            duration_ms = int(voice.get("duration_ms") or 0)
            if duration_ms > 0 and position_ms >= duration_ms:
                boundary = getattr(self.recorder, "voice_boundary", None)
                if not callable(boundary):
                    raise RuntimeError("voice recording navigation is unavailable")
                voice = boundary(end=False)
                position_ms = int(voice.get("position_ms") or 0)
            start_seconds = position_ms / 1000.0
            load_at = getattr(self.player, "load_at", None)
            if callable(load_at):
                load_at(str(path), start_seconds)
            else:
                self.player.load(str(path))
                seek = getattr(self.player, "seek_absolute", None)
                if callable(seek):
                    seek(start_seconds)
            self._voice_playback_active = True
            return {"playback": self.player.state.as_dict()}
        elif action == "voice_recorder_close":
            self._stop_voice_playback()
            finalize = getattr(self.recorder, "voice_finalize", None)
            if not callable(finalize):
                raise RuntimeError("voice recording is unavailable")
            recording = finalize()
            self.scan_media()
            if self._voice_previous_volume is not None:
                restore_volume = self._voice_previous_volume
                self._voice_previous_volume = None
                volume_setter = getattr(self.player, "set_volume", None)
                if callable(volume_setter):
                    volume_setter(restore_volume)
                else:
                    self.player.state.volume = restore_volume
            if self.active_service == "recorder":
                self.active_service = "system"
            return {"recording": recording}
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
        elif action == "ambient_select":
            self._require_enabled("ambient")
            scene = self._ambient_scene(request.get("scene_id"))
            self.selected_ambient_scene_id = int(scene["id"])
            return {"scene_id": self.selected_ambient_scene_id}
        elif action == "ambient_step":
            self._require_enabled("ambient")
            steps = request.get("steps")
            if (
                isinstance(steps, bool)
                or not isinstance(steps, int)
                or steps == 0
                or abs(steps) > 10
            ):
                raise ValueError("ambient steps must be between -10 and 10, excluding zero")
            scenes = self.store.channels("ambient")
            if not scenes:
                raise ValueError("the ambient scene list is empty")
            ids = [int(item["id"]) for item in scenes]
            current = (
                ids.index(self.selected_ambient_scene_id)
                if self.selected_ambient_scene_id in ids
                else 0
            )
            self.selected_ambient_scene_id = ids[(current + steps) % len(ids)]
            self._play_ambient_scene(
                self._ambient_scene(self.selected_ambient_scene_id)
            )
            return {"scene_id": self.selected_ambient_scene_id}
        elif action == "ambient_play":
            self._require_enabled("ambient")
            scene_id = request.get("scene_id", self.selected_ambient_scene_id)
            scene = self._ambient_scene(scene_id)
            self._play_ambient_scene(scene)
        elif action == "ambient_toggle":
            self._require_enabled("ambient")
            if (
                self.active_service == "ambient"
                and self.active_ambient_scene_id == self.selected_ambient_scene_id
                and self.player.state.state in {"playing", "paused"}
            ):
                self.player.toggle_pause()
                for layer_player in self._ambient_layer_players.values():
                    layer_player.toggle_pause()
            else:
                scene = self._ambient_scene(self.selected_ambient_scene_id)
                self._play_ambient_scene(scene)
        elif action == "ambient_layer_step":
            self._require_enabled("ambient")
            steps = request.get("steps")
            if (
                isinstance(steps, bool)
                or not isinstance(steps, int)
                or steps == 0
                or abs(steps) > 10
            ):
                raise ValueError("ambient layer steps must be between -10 and 10")
            entries = [*AMBIENT_LAYER_IDS, AMBIENT_SAVE_ACTION]
            current = (
                entries.index(self.selected_ambient_layer_id)
                if self.selected_ambient_layer_id in entries
                else 0
            )
            self.selected_ambient_layer_id = entries[(current + steps) % len(entries)]
            return {"layer_id": self.selected_ambient_layer_id}
        elif action == "ambient_layer_toggle":
            self._require_enabled("ambient")
            layer_id = request.get("layer_id", self.selected_ambient_layer_id)
            if layer_id == AMBIENT_SAVE_ACTION:
                scene_id = self._save_ambient_favorite(request.get("name"))
                return {"favorite_scene_id": scene_id}
            if not isinstance(layer_id, str) or layer_id not in AMBIENT_LAYER_IDS:
                raise ValueError("unknown ambient sound layer")
            self.selected_ambient_layer_id = layer_id
            enabled = self._ambient_layer_state[layer_id]["enabled"] is not True
            state = self._set_ambient_layer_state(layer_id, enabled=enabled)
            return {"layer_id": layer_id, "layer": state}
        elif action == "ambient_layer_volume_step":
            self._require_enabled("ambient")
            steps = request.get("steps")
            if (
                isinstance(steps, bool)
                or not isinstance(steps, int)
                or steps == 0
                or abs(steps) > 10
            ):
                raise ValueError("ambient layer volume steps must be between -10 and 10")
            layer_id = self.selected_ambient_layer_id
            if layer_id == AMBIENT_SAVE_ACTION:
                return {"layer_id": layer_id}
            volume = int(self._ambient_layer_state[layer_id]["volume"]) + steps * 10
            state = self._set_ambient_layer_state(layer_id, volume=volume)
            return {"layer_id": layer_id, "layer": state}
        elif action == "ambient_layer_set":
            self._require_enabled("ambient")
            layer_id = request.get("layer_id")
            enabled = request.get("enabled")
            volume = request.get("volume")
            if not isinstance(layer_id, str) or layer_id not in AMBIENT_LAYER_IDS:
                raise ValueError("unknown ambient sound layer")
            if enabled is not None and not isinstance(enabled, bool):
                raise ValueError("ambient layer enabled must be boolean")
            if volume is not None and (
                isinstance(volume, bool)
                or not isinstance(volume, int)
                or not 0 <= volume <= 100
            ):
                raise ValueError("ambient layer volume must be from 0 to 100")
            self.selected_ambient_layer_id = layer_id
            state = self._set_ambient_layer_state(
                layer_id,
                enabled=enabled,
                volume=volume,
            )
            return {"layer_id": layer_id, "layer": state}
        elif action == "ambient_favorite_save":
            self._require_enabled("ambient")
            scene_id = self._save_ambient_favorite(request.get("name"))
            return {"favorite_scene_id": scene_id}
        elif action == "ambient_scene_save":
            self._require_enabled("ambient")
            name = request.get("name")
            source = request.get("source")
            if not isinstance(name, str) or not isinstance(source, str):
                raise ValueError("ambient_scene_save requires name and source")
            approved = validate_media_source(source, (self.media_root,))
            parsed = urlsplit(approved)
            if parsed.query:
                raise ValueError("ambient scene URLs with a query cannot be saved")
            external_id = f"custom-{hashlib.sha256(approved.encode('utf-8')).hexdigest()[:16]}"
            scene_id = self.store.add_channel(
                "ambient",
                external_id,
                name,
                {
                    "source_url": approved,
                    "description": "Custom ambient scene",
                    "credit": "User source",
                },
            )
            self.selected_ambient_scene_id = scene_id
            return {"scene_id": scene_id}
        elif action == "ambient_scene_delete":
            self._require_enabled("ambient")
            scene = self._ambient_scene(request.get("scene_id"))
            scene_id = int(scene["id"])
            if self.active_ambient_scene_id == scene_id:
                self.player.stop()
                self.active_service = "system"
                self.active_ambient_scene_id = None
            deleted = self.store.delete_channel(scene_id)
            remaining = self.store.channels("ambient")
            remaining_ids = [int(item["id"]) for item in remaining]
            if self.selected_ambient_scene_id not in remaining_ids:
                self.selected_ambient_scene_id = remaining_ids[0] if remaining_ids else None
            return {"deleted": deleted}
        elif action == "ambient_scene_move":
            self._require_enabled("ambient")
            scene = self._ambient_scene(request.get("scene_id"))
            direction = request.get("direction")
            if isinstance(direction, bool) or not isinstance(direction, int):
                raise ValueError("ambient_scene_move requires an integer direction")
            return {"moved": self.store.move_channel(int(scene["id"]), direction)}
        elif action == "brandmeister_step":
            self._require_enabled("brandmeister")
            steps = request.get("steps")
            if isinstance(steps, bool) or not isinstance(steps, int) or steps == 0 or abs(steps) > 250:
                raise ValueError("BrandMeister steps must be between -250 and 250")
            entries = self._brandmeister_device_entries(allow_network=True)
            if not entries:
                raise ValueError("the BrandMeister talkgroup catalog is empty")
            talkgroups = [int(entry["talkgroup"]) for entry in entries]
            current = (
                talkgroups.index(self.selected_brandmeister_talkgroup)
                if self.selected_brandmeister_talkgroup in talkgroups
                else 0
            )
            selected = entries[(current + steps) % len(entries)]
            talkgroup = int(selected["talkgroup"])
            self.selected_brandmeister_talkgroup = talkgroup
            saved = self._saved_brandmeister_channel_for_talkgroup(talkgroup)
            self.selected_brandmeister_channel_id = int(saved["id"]) if saved is not None else None
            return {
                "channel_id": self.selected_brandmeister_channel_id,
                "talkgroup": talkgroup,
                "name": str(selected["name"]),
            }
        elif action == "brandmeister_jump_first":
            self._require_enabled("brandmeister")
            entries = self._brandmeister_device_entries(allow_network=True)
            if not entries:
                raise ValueError("the BrandMeister talkgroup catalog is empty")
            selected = entries[0]
            talkgroup = int(selected["talkgroup"])
            self.selected_brandmeister_talkgroup = talkgroup
            saved = self._saved_brandmeister_channel_for_talkgroup(talkgroup)
            self.selected_brandmeister_channel_id = (
                int(saved["id"]) if saved is not None else None
            )
            return {
                "channel_id": self.selected_brandmeister_channel_id,
                "talkgroup": talkgroup,
                "name": str(selected["name"]),
            }
        elif action == "brandmeister_country_menu_open":
            self._require_enabled("brandmeister")
            self._brandmeister_catalog_entries(allow_network=True)
            self.selected_brandmeister_country = (
                self.brandmeister_country_filter or BRANDMEISTER_ALL_COUNTRIES
            )
            return {"country_menu": True}
        elif action == "brandmeister_country_step":
            self._require_enabled("brandmeister")
            steps = request.get("steps")
            if (
                isinstance(steps, bool)
                or not isinstance(steps, int)
                or steps == 0
                or abs(steps) > 10
            ):
                raise ValueError("BrandMeister country steps must be between -10 and 10")
            rows = self._brandmeister_country_entries(allow_network=True)
            codes = [str(item["code"]) for item in rows]
            current = (
                codes.index(self.selected_brandmeister_country)
                if self.selected_brandmeister_country in codes
                else 0
            )
            self.selected_brandmeister_country = codes[(current + steps) % len(codes)]
            return {"country_code": self.selected_brandmeister_country}
        elif action == "brandmeister_country_select":
            self._require_enabled("brandmeister")
            code = self.selected_brandmeister_country
            self.brandmeister_country_filter = (
                None if code == BRANDMEISTER_ALL_COUNTRIES else code
            )
            entries = self._brandmeister_device_entries(allow_network=True)
            if entries:
                selected = next(
                    (item for item in entries if item.get("enabled") is False),
                    entries[0],
                )
                talkgroup = int(selected["talkgroup"])
                self.selected_brandmeister_talkgroup = talkgroup
                saved = self._saved_brandmeister_channel_for_talkgroup(talkgroup)
                self.selected_brandmeister_channel_id = (
                    int(saved["id"]) if saved is not None else None
                )
            return {"country_code": code, "country_filter_applied": True}
        elif action == "brandmeister_replacement_step":
            self._require_enabled("brandmeister")
            steps = request.get("steps")
            if (
                isinstance(steps, bool)
                or not isinstance(steps, int)
                or steps == 0
                or abs(steps) > 10
            ):
                raise ValueError("BrandMeister replacement steps must be between -10 and 10")
            rows = self._brandmeister_replacement_rows()
            talkgroups = [int(item["talkgroup"]) for item in rows]
            if not talkgroups:
                raise ValueError("no active BrandMeister talkgroup can be replaced")
            current = (
                talkgroups.index(self._selected_brandmeister_replacement)
                if self._selected_brandmeister_replacement in talkgroups
                else 0
            )
            self._selected_brandmeister_replacement = talkgroups[(current + steps) % len(talkgroups)]
            return {"replace_talkgroup": self._selected_brandmeister_replacement}
        elif action == "brandmeister_replacement_confirm":
            self._require_enabled("brandmeister")
            new_talkgroup = self._pending_brandmeister_talkgroup
            old_talkgroup = self._selected_brandmeister_replacement
            if new_talkgroup is None or old_talkgroup is None:
                raise ValueError("no BrandMeister replacement is pending")
            entry = next(
                (
                    item
                    for item in self._brandmeister_catalog_entries(allow_network=True)
                    if item.get("talkgroup") == new_talkgroup
                ),
                None,
            )
            name = str(entry.get("name") or f"TG {new_talkgroup}") if entry else f"TG {new_talkgroup}"
            return self._replace_brandmeister_talkgroup(
                old_talkgroup, new_talkgroup, name
            )
        elif action == "brandmeister_replacement_cancel":
            self._pending_brandmeister_talkgroup = None
            self._selected_brandmeister_replacement = None
            return {"replacement_cancelled": True}
        elif action == "brandmeister_toggle":
            self._require_enabled("brandmeister")
            state = self.brandmeister.snapshot()
            status = str(state.get("status") or "stopped")
            if self.active_service == "brandmeister" and status in {
                "connecting",
                "listening",
                "call",
                "reconnecting",
            }:
                self.brandmeister.stop()
                self.active_service = "system"
                return {"brandmeister": self.brandmeister.snapshot()}
            if not self._enabled_brandmeister_talkgroups():
                raise ValueError("select at least one BrandMeister talkgroup before play")
            return {"brandmeister": self._restart_brandmeister_receiver()}
        elif action == "brandmeister_toggle_selected":
            self._require_enabled("brandmeister")
            entry = self._selected_brandmeister_entry()
            if entry is None:
                raise ValueError("no BrandMeister talkgroup is selected")
            talkgroup = int(entry["talkgroup"])
            channel = self._saved_brandmeister_channel_for_talkgroup(talkgroup)
            if channel is None:
                channels = self.store.channels("brandmeister")
                if len(channels) >= 30:
                    raise ValueError("at most 30 BrandMeister talkgroups can be saved")
                if len(self._enabled_brandmeister_talkgroups()) >= MAX_TALKGROUPS:
                    self._pending_brandmeister_talkgroup = talkgroup
                    self._selected_brandmeister_replacement = self._enabled_brandmeister_talkgroups()[0]
                    return {
                        "talkgroup": talkgroup,
                        "enabled": False,
                        "replacement_required": True,
                    }
                channel_id = self.store.add_channel(
                    "brandmeister",
                    str(talkgroup),
                    str(entry["name"]),
                    {"talkgroup": talkgroup, "enabled": True},
                )
                self.selected_brandmeister_channel_id = channel_id
                state = self._reconfigure_brandmeister_receiver()
                return {
                    "channel_id": channel_id,
                    "talkgroup": talkgroup,
                    "enabled": True,
                    "brandmeister": state,
                }
            metadata = channel.get("metadata")
            metadata = dict(metadata) if isinstance(metadata, dict) else {}
            enabled = metadata.get("enabled") is not True
            if enabled and len(self._enabled_brandmeister_talkgroups()) >= MAX_TALKGROUPS:
                self._pending_brandmeister_talkgroup = talkgroup
                self._selected_brandmeister_replacement = self._enabled_brandmeister_talkgroups()[0]
                return {
                    "channel_id": int(channel["id"]),
                    "talkgroup": talkgroup,
                    "enabled": False,
                    "replacement_required": True,
                }
            metadata["enabled"] = enabled
            self.store.update_channel(int(channel["id"]), str(channel["name"]), metadata)
            next_talkgroup = talkgroup
            next_channel = channel
            if not enabled:
                remaining_enabled = self._enabled_brandmeister_talkgroups()
                if remaining_enabled:
                    next_talkgroup = remaining_enabled[0]
                    remaining_channel = self._saved_brandmeister_channel_for_talkgroup(
                        next_talkgroup
                    )
                    if remaining_channel is not None:
                        next_channel = remaining_channel
            self.selected_brandmeister_talkgroup = next_talkgroup
            self.selected_brandmeister_channel_id = int(next_channel["id"])
            state = self._reconfigure_brandmeister_receiver()
            return {
                "channel_id": int(channel["id"]),
                "talkgroup": talkgroup,
                "enabled": enabled,
                "brandmeister": state,
            }
        elif action == "brandmeister_talkgroup_add":
            self._require_enabled("brandmeister")
            talkgroup = request.get("talkgroup")
            name = request.get("name")
            enabled = request.get("enabled", False)
            replace_talkgroup = request.get("replace_talkgroup")
            if (
                isinstance(talkgroup, bool)
                or not isinstance(talkgroup, int)
                or talkgroup <= 90
                or talkgroup > 9_999_999
            ):
                raise ValueError("talkgroup must be an integer from 91 through 9999999")
            if name is not None and (not isinstance(name, str) or not name.strip()):
                raise ValueError("talkgroup name must be text")
            if not isinstance(enabled, bool):
                raise ValueError("talkgroup enabled state must be boolean")
            if replace_talkgroup is not None and (
                isinstance(replace_talkgroup, bool)
                or not isinstance(replace_talkgroup, int)
            ):
                raise ValueError("replacement talkgroup must be an integer")
            channels = self.store.channels("brandmeister")
            if len(channels) >= 30 and not any(str(item["external_id"]) == str(talkgroup) for item in channels):
                raise ValueError("at most 30 BrandMeister talkgroups can be saved")
            if enabled and len(self._enabled_brandmeister_talkgroups()) >= MAX_TALKGROUPS:
                if isinstance(replace_talkgroup, int):
                    return self._replace_brandmeister_talkgroup(
                        replace_talkgroup,
                        talkgroup,
                        name.strip()[:160] if isinstance(name, str) else f"TG {talkgroup}",
                    )
                raise ValueError("select an active BrandMeister talkgroup to replace")
            channel_id = self.store.add_channel(
                "brandmeister",
                str(talkgroup),
                name.strip()[:160] if isinstance(name, str) else f"TG {talkgroup}",
                {"talkgroup": talkgroup, "enabled": enabled},
            )
            existing = self.store.channel(channel_id)
            if existing is not None and str(existing["external_id"]) == str(talkgroup):
                metadata = existing.get("metadata")
                metadata = dict(metadata) if isinstance(metadata, dict) else {}
                if metadata.get("talkgroup") != talkgroup or metadata.get("enabled") is not enabled:
                    metadata.update({"talkgroup": talkgroup, "enabled": enabled})
                    self.store.update_channel(channel_id, str(existing["name"]), metadata)
            self.selected_brandmeister_channel_id = channel_id
            self.selected_brandmeister_talkgroup = talkgroup
            if enabled:
                self._reconfigure_brandmeister_receiver()
            return {"channel_id": channel_id}
        elif action == "brandmeister_talkgroup_set":
            self._require_enabled("brandmeister")
            channel_id = request.get("channel_id")
            enabled = request.get("enabled")
            replace_talkgroup = request.get("replace_talkgroup")
            if isinstance(channel_id, bool) or not isinstance(channel_id, int):
                raise ValueError("BrandMeister channel id must be an integer")
            if not isinstance(enabled, bool):
                raise ValueError("talkgroup enabled state must be boolean")
            if replace_talkgroup is not None and (
                isinstance(replace_talkgroup, bool)
                or not isinstance(replace_talkgroup, int)
            ):
                raise ValueError("replacement talkgroup must be an integer")
            channel = self.store.channel(channel_id)
            if channel is None or channel.get("service_id") != "brandmeister":
                raise ValueError("BrandMeister talkgroup was not found")
            metadata = channel.get("metadata")
            metadata = dict(metadata) if isinstance(metadata, dict) else {}
            if (
                enabled
                and metadata.get("enabled") is not True
                and len(self._enabled_brandmeister_talkgroups()) >= MAX_TALKGROUPS
            ):
                talkgroup = metadata.get("talkgroup")
                if isinstance(replace_talkgroup, int) and isinstance(talkgroup, int):
                    return self._replace_brandmeister_talkgroup(
                        replace_talkgroup, talkgroup, str(channel["name"])
                    )
                raise ValueError("select an active BrandMeister talkgroup to replace")
            metadata["enabled"] = enabled
            self.store.update_channel(channel_id, str(channel["name"]), metadata)
            state = self._reconfigure_brandmeister_receiver()
            return {"channel_id": channel_id, "enabled": enabled, "brandmeister": state}
        elif action == "brandmeister_talkgroup_delete":
            self._require_enabled("brandmeister")
            channel_id = request.get("channel_id")
            if isinstance(channel_id, bool) or not isinstance(channel_id, int):
                raise ValueError("BrandMeister channel id must be an integer")
            channel = self.store.channel(channel_id)
            if channel is None or channel.get("service_id") != "brandmeister":
                return {"deleted": False}
            deleted = self.store.delete_channel(channel_id)
            remaining = self.store.channels("brandmeister")
            ids = [int(item["id"]) for item in remaining]
            if self.selected_brandmeister_channel_id not in ids:
                self.selected_brandmeister_channel_id = ids[0] if ids else None
                selected = self.store.channel(self.selected_brandmeister_channel_id) if self.selected_brandmeister_channel_id is not None else None
                metadata = selected.get("metadata") if selected is not None else None
                talkgroup = metadata.get("talkgroup") if isinstance(metadata, dict) else None
                self.selected_brandmeister_talkgroup = talkgroup if isinstance(talkgroup, int) else None
            self._reconfigure_brandmeister_receiver()
            return {"deleted": deleted}
        elif action == "brandmeister_talkgroup_move":
            self._require_enabled("brandmeister")
            channel_id = request.get("channel_id")
            direction = request.get("direction")
            if isinstance(channel_id, bool) or not isinstance(channel_id, int):
                raise ValueError("BrandMeister channel id must be an integer")
            if isinstance(direction, bool) or not isinstance(direction, int):
                raise ValueError("BrandMeister move direction must be an integer")
            return {"moved": self.store.move_channel(channel_id, direction)}
        elif action == "brandmeister_listen":
            self._require_enabled("brandmeister")
            return {"brandmeister": self._restart_brandmeister_receiver()}
        elif action == "brandmeister_stop":
            self.brandmeister.stop()
            if self.active_service == "brandmeister":
                self.active_service = "system"
            return {"brandmeister": self.brandmeister.snapshot()}
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
            self._stop_brandmeister_for_audio_owner()
            self.player.load(str(media["path"]))
            self.active_service = "local_media"
            self.active_preset_id = None
            self.active_station_id = None
            self._active_podcast_episode = None
            self.active_ambient_scene_id = None
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
            self._stop_brandmeister_for_audio_owner()
            self.player.load_playlist(
                paths,
                shuffle=False,
                loop=favorites_only,
            )
            self.active_service = "local_media"
            self.active_preset_id = None
            self.active_station_id = None
            self._active_podcast_episode = None
            self.active_ambient_scene_id = None
        elif action == "media_next":
            self._require_enabled("local_media")
            self.player.next()
        elif action == "media_previous":
            self._require_enabled("local_media")
            self.player.previous()
        elif action == "podcast_subscribe":
            self._require_enabled("podcasts")
            url = request.get("url")
            if not isinstance(url, str):
                raise ValueError("podcast_subscribe requires a URL")
            parsed = urlsplit(url)
            if parsed.query:
                raise ValueError("podcast feed URLs with a query cannot be saved")
            if len(self.store.channels("podcasts")) >= 100:
                raise ValueError("podcast subscription limit reached")
            feed = self.podcast_reader.fetch(url)
            external_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
            subscription_id = self.store.add_channel(
                "podcasts",
                external_id,
                str(feed["title"]),
                {
                    "feed_url": url,
                    "description": str(feed.get("description") or ""),
                    "homepage": str(feed.get("homepage") or ""),
                },
            )
            self._podcast_cache[subscription_id] = feed
            self._active_podcast_subscription_id = subscription_id
            return {
                "subscription_id": subscription_id,
                "episode_count": int(feed["episode_count"]),
            }
        elif action == "podcast_refresh":
            self._require_enabled("podcasts")
            subscription_id = request.get("subscription_id")
            self._podcast_subscription(subscription_id)
            feed = self._refresh_podcast(int(subscription_id))
            return {
                "subscription_id": int(subscription_id),
                "episode_count": int(feed["episode_count"]),
            }
        elif action == "podcast_play":
            self._require_enabled("podcasts")
            subscription_id = request.get("subscription_id")
            episode_id = request.get("episode_id")
            if not isinstance(episode_id, str):
                raise ValueError("podcast_play requires an episode id")
            self._podcast_subscription(subscription_id)
            subscription_id = int(subscription_id)
            feed = self._podcast_cache.get(subscription_id)
            if feed is None:
                feed = self._refresh_podcast(subscription_id)
            episodes = feed.get("episodes")
            episode = next(
                (
                    item for item in episodes
                    if isinstance(item, dict) and self._podcast_episode_id(item) == episode_id
                ),
                None,
            ) if isinstance(episodes, list) else None
            if episode is None:
                raise ValueError("podcast episode was not found")
            source = validate_media_source(str(episode["enclosure_url"]), (self.media_root,))
            if self.radio_buffer is not None:
                self.radio_buffer.stop(flush=True)
            self._stop_brandmeister_for_audio_owner()
            self.player.load(source)
            self.active_service = "podcasts"
            self.active_preset_id = None
            self.active_station_id = None
            self._active_podcast_subscription_id = subscription_id
            self._active_podcast_episode = {
                "subscription_id": subscription_id,
                "episode_id": episode_id,
                "podcast": str(feed.get("title") or "Podcast"),
                "title": str(episode.get("title") or "Untitled episode"),
            }
            self.active_ambient_scene_id = None
        elif action == "podcast_unsubscribe":
            subscription_id = request.get("subscription_id")
            self._podcast_subscription(subscription_id)
            subscription_id = int(subscription_id)
            deleted = self.store.delete_channel(subscription_id)
            self._podcast_cache.pop(subscription_id, None)
            if self._active_podcast_subscription_id == subscription_id:
                self._active_podcast_subscription_id = None
                self._active_podcast_episode = None
                if self.active_service == "podcasts":
                    self.player.stop()
                    self.active_service = "system"
            return {"deleted": deleted}
        elif action == "podcast_move":
            subscription_id = request.get("subscription_id")
            direction = request.get("direction")
            self._podcast_subscription(subscription_id)
            if isinstance(direction, bool) or not isinstance(direction, int):
                raise ValueError("podcast_move requires an integer direction")
            return {"moved": self.store.move_channel(int(subscription_id), direction)}
        elif action == "mediathek_search":
            provider = request.get("provider")
            query = request.get("query", "")
            if not isinstance(provider, str) or provider not in self._mediathek_results:
                raise ValueError("mediathek_search requires a known provider")
            if not isinstance(query, str):
                raise ValueError("mediathek_search requires a text query")
            service_id = MediathekCatalog.provider(provider).service_id
            self._require_enabled(service_id)
            results = self.mediathek_catalog.search(provider, query)
            self._mediathek_results[provider] = results
            self._mediathek_queries[provider] = query.strip()[:120]
            self._mediathek_selected[provider] = (
                results[0].item_id if results else None
            )
            return {
                "provider": provider,
                "result_count": len(results),
                "selected_item_id": self._mediathek_selected[provider],
            }
        elif action == "mediathek_select":
            provider = request.get("provider")
            item_id = request.get("item_id")
            if not isinstance(provider, str) or provider not in self._mediathek_results:
                raise ValueError("mediathek_select requires a known provider")
            if not isinstance(item_id, str):
                raise ValueError("mediathek_select requires an item id")
            if not any(
                item.item_id == item_id for item in self._mediathek_results[provider]
            ):
                raise ValueError("Mediathek item was not found")
            self._mediathek_selected[provider] = item_id
            return {"provider": provider, "selected_item_id": item_id}
        elif action == "mediathek_play":
            provider = request.get("provider")
            item_id = request.get("item_id")
            if not isinstance(provider, str) or provider not in self._mediathek_results:
                raise ValueError("mediathek_play requires a known provider")
            if not isinstance(item_id, str):
                raise ValueError("mediathek_play requires an item id")
            item = next(
                (
                    candidate
                    for candidate in self._mediathek_results[provider]
                    if candidate.item_id == item_id
                ),
                None,
            )
            if item is None:
                raise ValueError("Mediathek item was not found; search again")
            self._play_mediathek_item(
                provider,
                item,
                result_set=self._mediathek_results[provider],
            )
            return {
                "provider": provider,
                "item_id": item_id,
                "playback": self.player.state.as_dict(),
            }
        elif action == "mediathek_step":
            steps = request.get("steps")
            if (
                isinstance(steps, bool)
                or not isinstance(steps, int)
                or steps == 0
                or abs(steps) > 10
            ):
                raise ValueError(
                    "Mediathek steps must be between -10 and 10, excluding zero"
                )
            provider = self._active_mediathek_provider
            active_item = self._active_mediathek_item
            if (
                self.active_service not in MEDIATHEK_SERVICE_IDS
                or provider not in self._mediathek_results
                or active_item is None
            ):
                raise ValueError("no active Mediathek result list")
            results = self._active_mediathek_results
            if not results:
                raise ValueError("the active Mediathek result list is empty")
            active_item_id = str(active_item.get("item_id") or "")
            current = next(
                (
                    index
                    for index, candidate in enumerate(results)
                    if candidate.item_id == active_item_id
                ),
                0,
            )
            item = results[(current + steps) % len(results)]
            self._play_mediathek_item(provider, item)
            return {
                "provider": provider,
                "item_id": item.item_id,
                "playback": self.player.state.as_dict(),
            }
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
        elif action == "camera_add":
            self._require_enabled("webcam")
            name = request.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("camera name is required")
            url, kind = self._camera_source(request.get("url"), request.get("kind"))
            enabled = request.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ValueError("camera enabled state must be boolean")
            if len(self.store.channels("webcam")) >= 100:
                raise ValueError("at most 100 cameras can be saved")
            camera_id = self.store.add_channel(
                "webcam",
                uuid.uuid4().hex,
                name.strip()[:160],
                {"source_url": url, "kind": kind, "enabled": enabled},
            )
            self.selected_camera_id = camera_id
            return {"camera_id": camera_id}
        elif action == "camera_update":
            self._require_enabled("webcam")
            channel = self._camera_channel(request.get("camera_id"))
            name = request.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("camera name is required")
            url, kind = self._camera_source(request.get("url"), request.get("kind"))
            enabled = request.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ValueError("camera enabled state must be boolean")
            self.store.update_channel(
                int(channel["id"]),
                name.strip()[:160],
                {"source_url": url, "kind": kind, "enabled": enabled},
            )
            self.selected_camera_id = int(channel["id"])
            return {"camera_id": int(channel["id"])}
        elif action == "camera_delete":
            self._require_enabled("webcam")
            channel = self._camera_channel(request.get("camera_id"))
            camera_id = int(channel["id"])
            deleted = self.store.delete_channel(camera_id)
            (self.camera.cache_root / f"camera-{camera_id}.jpg").unlink(missing_ok=True)
            cameras = self.content_state.get("cameras")
            if isinstance(cameras, dict):
                cameras.pop(str(camera_id), None)
            remaining = self.store.channels("webcam")
            remaining_ids = [int(item["id"]) for item in remaining]
            if self.selected_camera_id == camera_id:
                self.selected_camera_id = remaining_ids[0] if remaining_ids else None
            return {"deleted": deleted}
        elif action == "camera_move":
            self._require_enabled("webcam")
            channel = self._camera_channel(request.get("camera_id"))
            direction = request.get("direction")
            if isinstance(direction, bool) or direction not in {-1, 1}:
                raise ValueError("camera direction must be -1 or 1")
            return {"moved": self.store.move_channel(int(channel["id"]), int(direction))}
        elif action == "camera_refresh":
            self._require_enabled("webcam")
            channel = self._camera_channel(request.get("camera_id"))
            metadata = channel.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            url, kind = self._camera_source(
                metadata.get("source_url"), metadata.get("kind", "snapshot")
            )
            camera_id = int(channel["id"])
            camera = self.camera.fetch(url, camera_id, kind=kind)
            cameras = self.content_state["cameras"]
            assert isinstance(cameras, dict)
            cameras[str(camera_id)] = camera
            self.selected_camera_id = camera_id
            return {"camera_id": camera_id, "camera": camera}
        elif action == "camera_snapshot":
            self._require_enabled("webcam")
            url = request.get("url")
            slot = request.get("slot", 1)
            if not isinstance(url, str):
                raise ValueError("camera_snapshot requires a URL")
            if isinstance(slot, bool) or not isinstance(slot, int):
                raise ValueError("camera slot must be an integer")
            camera = self.camera.fetch(url, slot, kind="snapshot")
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
            "brandmeister": self.brandmeister.snapshot(),
            "recording": self.recorder.state.as_dict(),
            "radio_buffer": (
                self.radio_buffer.snapshot() if self.radio_buffer is not None else None
            ),
            "selected_preset": self._selected_preset(),
        }

    def _ambient_scene(self, scene_id: object) -> dict[str, object]:
        if isinstance(scene_id, bool) or not isinstance(scene_id, int):
            raise ValueError("ambient scene id must be an integer")
        scene = self.store.channel(scene_id)
        if scene is None or scene["service_id"] != "ambient":
            raise ValueError("ambient scene was not found")
        return scene

    def _ambient_display_text(self, scene: dict[str, object]) -> tuple[str, str]:
        metadata = scene.get("metadata")
        description = (
            str(metadata.get("description") or "Ambient soundscape")
            if isinstance(metadata, dict)
            else "Ambient soundscape"
        )
        translated = ambient_text(str(scene.get("external_id") or ""), self.display_language())
        return translated or (str(scene["name"]), description)

    def _play_ambient_scene(self, scene: dict[str, object]) -> None:
        metadata = scene.get("metadata")
        if not isinstance(metadata, dict) or not isinstance(metadata.get("source_url"), str):
            raise ValueError("ambient scene has no media source")
        source = validate_media_source(str(metadata["source_url"]), (self.media_root,))
        source_preset_id = str(
            metadata.get("source_preset_id") or scene.get("external_id") or ""
        )
        preset = AMBIENT_BY_ID.get(source_preset_id)
        if (
            preset is not None
            and preset.sha256 is not None
            and source == preset.audio_url
        ):
            cached = self.ambient_audio.cached(preset.preset_id, preset.sha256)
            if cached is not None:
                source = validate_media_source(str(cached), (self.media_root,))
        mix_layers = metadata.get("mix_layers")
        if isinstance(mix_layers, dict):
            enabled_count = 0
            restored: dict[str, dict[str, object]] = {}
            for layer_id in AMBIENT_LAYER_IDS:
                item = mix_layers.get(layer_id)
                item = item if isinstance(item, dict) else {}
                enabled = item.get("enabled") is True and enabled_count < 2
                if enabled:
                    enabled_count += 1
                volume = item.get("volume", AMBIENT_LAYER_DEFAULTS[layer_id])
                if isinstance(volume, bool) or not isinstance(volume, int):
                    volume = AMBIENT_LAYER_DEFAULTS[layer_id]
                restored[layer_id] = {
                    "enabled": enabled,
                    "volume": max(0, min(100, volume)),
                }
            self._ambient_layer_state = restored
            self._persist_ambient_layer_state()
        if self.radio_buffer is not None:
            self.radio_buffer.stop(flush=True)
        self._stop_brandmeister_for_audio_owner()
        self.player.load_playlist([source], loop=True)
        scene_id = int(scene["id"])
        self.active_service = "ambient"
        self.selected_ambient_scene_id = scene_id
        self.active_ambient_scene_id = scene_id
        self.active_preset_id = None
        self.active_station_id = None
        self._active_podcast_episode = None
        self._sync_ambient_layers(restart=True)

    def _play_mediathek_item(
        self,
        provider: str,
        item: MediathekEntry,
        *,
        result_set: list[MediathekEntry] | None = None,
    ) -> None:
        """Load one cached Mediathek result through the sole audio owner."""

        self._require_enabled(item.service_id)
        source = validate_media_source(item.source_url, (self.media_root,))
        if self.radio_buffer is not None:
            self.radio_buffer.stop(flush=True)
        self._stop_brandmeister_for_audio_owner()
        self._stop_ambient_layers()
        self.player.load(source)
        self.active_service = item.service_id
        self.active_preset_id = None
        self.active_station_id = None
        self.active_ambient_scene_id = None
        self._active_podcast_episode = None
        self._mediathek_selected[provider] = item.item_id
        self._active_mediathek_provider = provider
        if result_set is not None:
            self._active_mediathek_results = tuple(result_set)
        self._active_mediathek_item = item.public()

    def _active_mediathek_position(self) -> int | None:
        provider = self._active_mediathek_provider
        active_item = self._active_mediathek_item
        if provider not in self._mediathek_results or active_item is None:
            return None
        active_item_id = str(active_item.get("item_id") or "")
        return next(
            (
                index
                for index, item in enumerate(
                    self._active_mediathek_results, start=1
                )
                if item.item_id == active_item_id
            ),
            None,
        )

    def _cache_builtin_ambient_audio(self) -> None:
        for preset in AMBIENT_PRESETS:
            if preset.sha256 is None:
                LOG.warning(
                    "Ambient preset %s has no checksum; skipping cache",
                    preset.preset_id,
                )
                continue
            try:
                self.ambient_audio.ensure(
                    preset.preset_id,
                    preset.audio_url,
                    preset.sha256,
                )
            except (ContentError, OSError, ValueError) as exc:
                LOG.warning(
                    "Ambient offline audio unavailable for %s: %s",
                    preset.preset_id,
                    exc,
                )

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
        self._stop_brandmeister_for_audio_owner()
        self.player.load(str(station["stream_url"]))
        if self.radio_buffer is not None:
            self.radio_buffer.tune(
                str(station["stream_url"]),
                str(station["name"]),
            )
        self.active_service = "webradio"
        self.active_station_id = int(station["id"])
        self._active_podcast_episode = None
        self.active_ambient_scene_id = None
        preset = self._preset_for_station(station)
        self.active_preset_id = preset.preset_id if preset is not None else None
        if preset is not None:
            self._cache_preset_artwork(preset.preset_id)

    @staticmethod
    def _radio_track_line(buffered: dict[str, object]) -> str | None:
        artist = buffered.get("artist")
        title = buffered.get("title")
        stream_title = buffered.get("stream_title")
        if isinstance(artist, str) and isinstance(title, str):
            return f"{artist} – {title}"
        if isinstance(stream_title, str) and stream_title.strip():
            return stream_title.strip()[:500]
        return None

    def _preview_radio_metadata(self, station: dict[str, object]) -> str:
        """Use the existing silent ring buffer to expose ICY metadata before Play."""
        if self.radio_buffer is None:
            return "No title information"
        buffered = self.radio_buffer.snapshot()
        station_name = str(station["name"])
        if buffered.get("station") != station_name:
            try:
                self.radio_buffer.tune(str(station["stream_url"]), station_name)
            except (OSError, RuntimeError, ValueError) as exc:
                LOG.info("Radio metadata unavailable for %s: %s", station_name, exc)
                return "No title information"
            buffered = self.radio_buffer.snapshot()
        track_line = self._radio_track_line(buffered)
        if track_line is not None:
            return track_line
        if buffered.get("state") == "connecting":
            return "Loading title information"
        return "No title information"

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

    @staticmethod
    def _podcast_episode_id(episode: dict[str, object]) -> str:
        identity = str(episode.get("guid") or episode.get("enclosure_url") or "")
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]

    @classmethod
    def _public_podcast_episodes(
        cls, feed: dict[str, object]
    ) -> list[dict[str, object]]:
        episodes = feed.get("episodes")
        if not isinstance(episodes, list):
            return []
        public: list[dict[str, object]] = []
        for item in episodes:
            if not isinstance(item, dict):
                continue
            public.append(
                {
                    "episode_id": cls._podcast_episode_id(item),
                    "title": str(item.get("title") or "Untitled episode"),
                    "summary": str(item.get("summary") or ""),
                    "published": str(item.get("published") or ""),
                    "duration": str(item.get("duration") or ""),
                }
            )
        return public

    def _podcast_subscription(self, subscription_id: object) -> dict[str, object]:
        if isinstance(subscription_id, bool) or not isinstance(subscription_id, int):
            raise ValueError("podcast subscription id must be an integer")
        channel = self.store.channel(subscription_id)
        if channel is None or channel["service_id"] != "podcasts":
            raise ValueError("podcast subscription was not found")
        return channel

    def _refresh_podcast(self, subscription_id: int) -> dict[str, object]:
        channel = self._podcast_subscription(subscription_id)
        metadata = channel.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        feed_url = metadata.get("feed_url")
        if not isinstance(feed_url, str):
            raise ValueError("podcast subscription has no feed URL")
        feed = self.podcast_reader.fetch(feed_url)
        self._podcast_cache[subscription_id] = feed
        self._active_podcast_subscription_id = subscription_id
        if str(feed.get("title") or "").strip() and str(channel["name"]) != str(feed["title"]):
            self.store.update_channel(
                subscription_id,
                str(feed["title"]),
                {
                    **metadata,
                    "description": str(feed.get("description") or ""),
                    "homepage": str(feed.get("homepage") or ""),
                },
            )
        return feed

    @staticmethod
    def _camera_source(url: object, kind: object) -> tuple[str, str]:
        if not isinstance(kind, str) or kind not in {"snapshot", "mjpeg", "rtsp"}:
            raise ValueError("camera kind must be snapshot, mjpeg or rtsp")
        if not isinstance(url, str):
            raise ValueError("camera URL is required")
        if kind in {"snapshot", "mjpeg"}:
            approved = validate_content_url(url)
        else:
            parsed = urlsplit(url)
            if (
                len(url) > 4096
                or parsed.scheme not in {"rtsp", "rtsps"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError("RTSP URL must be credential-free and use rtsp or rtsps")
            approved = url
        if urlsplit(approved).query:
            raise ValueError("persistent camera URLs must not contain a query string")
        return approved, kind

    def _camera_channel(self, camera_id: object) -> dict[str, object]:
        if isinstance(camera_id, bool) or not isinstance(camera_id, int):
            raise ValueError("camera id must be an integer")
        channel = self.store.channel(camera_id)
        if channel is None or channel.get("service_id") != "webcam":
            raise ValueError("camera was not found")
        return channel

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
            relative = resolved.relative_to(root)
            source_kind = (
                "voice"
                if len(relative.parts) >= 3
                and relative.parts[0] == "VoiceRecorder"
                and re.fullmatch(r"\d{6}", relative.parts[1]) is not None
                and re.fullmatch(
                    r"\d{6}_\d{6}_VoiceRecorder\.mp3",
                    relative.name,
                ) is not None
                else "radio"
                if len(relative.parts) >= 3
                and relative.parts[0] == "Music"
                else "local"
            )
            self.store.upsert_media(
                "local_media", resolved, size, source_kind=source_kind
            )
            present.add(str(resolved))
            count += 1
        self.store.remove_missing_media("local_media", present)
        return count

    def _migrate_legacy_recorded_music(self) -> None:
        """Move only the former managed recording tree into ``Media/Music``."""
        legacy_root = self.media_root / "recorded"
        if not legacy_root.is_dir():
            return
        self.music_root.mkdir(parents=True, exist_ok=True, mode=0o750)
        music_root = self.music_root.resolve()
        for source in sorted(legacy_root.rglob("*")):
            if not source.is_file() or source.suffix.lower() not in MEDIA_EXTENSIONS:
                continue
            relative = source.relative_to(legacy_root)
            target = (self.music_root / relative).resolve()
            if not target.is_relative_to(music_root):
                continue
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
            if target.exists():
                digest = hashlib.sha256(source.read_bytes()).hexdigest()[:8]
                target = target.with_name(f"{target.stem} - {digest}{target.suffix}")
            os.replace(source, target)
            self.store.relocate_media_path(source.resolve(), target, target.stat().st_size)
        for directory in sorted(
            (item for item in legacy_root.rglob("*") if item.is_dir()),
            key=lambda item: len(item.parts),
            reverse=True,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass
        try:
            legacy_root.rmdir()
        except OSError:
            pass

    def content_asset(self, path: str) -> tuple[str, bytes] | None:
        if path == "brandmeister-talkgroups.json":
            try:
                return "application/json; charset=utf-8", self.brandmeister_catalog.payload()
            except OSError as exc:
                LOG.warning("BrandMeister talkgroup catalog unavailable: %s", exc)
                return None
        if re.fullmatch(r"camera-\d{1,7}\.jpg", path):
            target = self.camera.cache_root / path
        elif path.startswith("ambient-art/"):
            preset_id = path.removeprefix("ambient-art/")
            if preset_id not in AMBIENT_BY_ID:
                return None
            target = self.ambient_artwork_root / f"{preset_id}.jpg"
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

    def content_redirect(self, path: str) -> str | None:
        """Resolve one opaque, process-local content id to a reviewed public URL."""

        match = re.fullmatch(r"mediathek-video/([a-f0-9]{24})", path)
        if match is None:
            return None
        item_id = match.group(1)
        for results in self._mediathek_results.values():
            for item in results:
                if item.item_id == item_id:
                    return item.browser_url or item.source_url
        return None

    def receiver_overlay(self, view_service: str | None = None) -> dict[str, object]:
        """Return metadata for the selected view without changing audio ownership."""
        requested = str(view_service or "").upper()
        playback = self.player.state
        brandmeister_state = self.brandmeister.snapshot()
        audio_active = (
            getattr(playback, "state", "stopped") == "playing"
            and not bool(getattr(playback, "paused", False))
        ) or str(brandmeister_state.get("status") or "stopped") in {
            "connecting", "listening", "call", "reconnecting",
        }
        valid_views = {"SYSTEM", "RADIO", "WEATHER", "AMBIENT", "DMR", "PLAYER", "REC"}
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
                    "audio_active": audio_active,
                    "channel": ids.index(self.active_weather_channel_id) + 1 if self.active_weather_channel_id in ids else 1,
                    "image_file": str(frame["file"]) if frame is not None else None,
                }
        if requested == "AMBIENT":
            scenes = self.store.channels("ambient")
            scene = (
                self.store.channel(self.selected_ambient_scene_id)
                if self.selected_ambient_scene_id is not None
                else (scenes[0] if scenes else None)
            )
            scene_name, description = (
                self._ambient_display_text(scene)
                if scene is not None
                else ("AmbientR4D10", "Choose a soundscape and press play")
            )
            ids = [int(item["id"]) for item in scenes]
            scene_id = int(scene["id"]) if scene is not None else None
            preset_id = str(scene["external_id"]) if scene is not None else ""
            scene_metadata = scene.get("metadata") if scene is not None else None
            artwork_preset_id = (
                str(scene_metadata.get("source_preset_id") or preset_id)
                if isinstance(scene_metadata, dict)
                else preset_id
            )
            selected_is_playing = (
                scene_id is not None
                and self.active_service == "ambient"
                and self.active_ambient_scene_id == scene_id
                and playback.state in {"playing", "paused"}
                and not playback.paused
            )
            return {
                "service": "AMBIENT",
                "station": scene_name,
                "title": "AmbientR4D10",
                "subtitle": description,
                "playing": selected_is_playing,
                "audio_active": audio_active,
                "volume": playback.volume,
                "preset_id": artwork_preset_id if artwork_preset_id in AMBIENT_BY_ID else None,
                "layer_rows": self._ambient_layer_rows(),
                "layer_position": next(
                    (
                        index
                        for index, item in enumerate(self._ambient_layer_rows(), start=1)
                        if item["selected"] is True
                    ),
                    1,
                ),
                "layer_count": len(AMBIENT_LAYER_IDS) + 1,
                "channel": (
                    ids.index(scene_id) + 1
                    if scene_id is not None and scene_id in ids
                    else None
                ),
            }
        if requested == "DMR":
            selected = self._selected_brandmeister_entry()
            selected_talkgroup = self.selected_brandmeister_talkgroup
            saved_selected = self._saved_brandmeister_channel_for_talkgroup(selected_talkgroup)
            saved_metadata = saved_selected.get("metadata") if saved_selected is not None else None
            selected_enabled = (
                isinstance(saved_metadata, dict) and saved_metadata.get("enabled") is True
            )
            selected_name = str(selected.get("name") or "BrandMeister") if selected else "BrandMeister"
            state = brandmeister_state
            destination = state.get("destination")
            active_talkgroup = (
                destination
                if isinstance(destination, int) and not isinstance(destination, bool)
                else selected_talkgroup
            )
            source = state.get("source")
            alias = state.get("alias")
            status = str(state.get("status") or "stopped")
            catalog_entries = self._brandmeister_device_entries(allow_network=False)
            activity_rows = self._brandmeister_activity_rows(state)
            activity_by_talkgroup = {
                int(item["talkgroup"]): item for item in activity_rows
            }
            for item in catalog_entries:
                talkgroup = item.get("talkgroup")
                heard = (
                    activity_by_talkgroup.get(talkgroup, {})
                    if isinstance(talkgroup, int) and not isinstance(talkgroup, bool)
                    else {}
                )
                source = heard.get("source")
                item.update(
                    {
                        "active": heard.get("active") is True,
                        "source": (
                            source
                            if isinstance(source, int) and not isinstance(source, bool)
                            else None
                        ),
                        "alias": str(heard.get("alias") or "")[:80],
                    }
                )
            catalog_talkgroups = [int(item["talkgroup"]) for item in catalog_entries]
            listening = status in {"connecting", "listening", "call", "reconnecting"}
            catalog_rows, catalog_position, catalog_count = self._brandmeister_device_window(
                catalog_entries
            )
            country_rows, country_position, country_count = self._bounded_selection_window(
                self._brandmeister_country_entries(allow_network=False)
            )
            replacement_entries = self._brandmeister_replacement_rows()
            replacement_rows, replacement_position, replacement_count = (
                self._bounded_selection_window(replacement_entries)
            )
            return {
                "service": "DMR",
                "station": f"TG {active_talkgroup}" if isinstance(active_talkgroup, int) else "BrandMeister",
                "title": str(alias)[:80] if isinstance(alias, str) and alias else selected_name,
                "subtitle": (
                    f"DMR ID {source}"
                    if isinstance(source, int) and not isinstance(source, bool)
                    else "HoseLine receive-only"
                    if listening
                    else "Select talkgroups and press play"
                ),
                "playing": listening,
                "audio_active": audio_active,
                "volume": playback.volume,
                "channel": (
                    catalog_talkgroups.index(selected_talkgroup) + 1
                    if selected_talkgroup is not None and selected_talkgroup in catalog_talkgroups
                    else 1
                ),
                "channel_label": str(selected_talkgroup) if selected_talkgroup is not None else "--",
                "flag_code": country_code(active_talkgroup) if isinstance(active_talkgroup, int) else None,
                "activity_rows": activity_rows,
                "catalog_rows": catalog_rows,
                "catalog_position": catalog_position,
                "catalog_count": catalog_count,
                "selected_enabled": selected_enabled,
                "country_rows": country_rows,
                "country_position": country_position,
                "country_count": country_count,
                "country_filter": self.brandmeister_country_filter,
                "replacement_required": self._pending_brandmeister_talkgroup is not None,
                "pending_talkgroup": self._pending_brandmeister_talkgroup,
                "replacement_rows": replacement_rows,
                "replacement_position": replacement_position,
                "replacement_count": replacement_count,
            }
        service_label = {
            "webradio": "RADIO",
            "local_media": "PLAYER",
            "youtube_audio": "PLAYER",
            "spotify": "PLAYER",
            "ard_mediathek": "PLAYER",
            "zdf_mediathek": "PLAYER",
            "public_mediatheken": "PLAYER",
            "international_media": "PLAYER",
            "podcasts": "PLAYER",
            "ambient": "AMBIENT",
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
                track_line = (
                    self._preview_radio_metadata(station)
                    if station is not None
                    else "No title information"
                )
                return {
                    "service": "RADIO",
                    "station": str(station["name"]) if station is not None else "Radio",
                    "title": str(station["name"]) if station is not None else "Radio",
                    "subtitle": track_line,
                    "playing": False,
                    "audio_active": audio_active,
                    "volume": playback.volume,
                    "preset_id": preset.preset_id if preset is not None else None,
                    "channel": 1 if station is not None else None,
                }
            defaults = {
                "SYSTEM": ("OPENR4D10", "System online", "Receiver ready"),
                "PLAYER": ("LOCAL MEDIA", "Local media", "Select media and press play"),
                "DMR": ("DMR", "Digital radio", "Select a channel and press play"),
                "REC": ("Voice Recorder", "Voice Recorder", "Hold PTT to record"),
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
                "audio_active": audio_active,
                "volume": playback.volume,
            }
        if requested == "REC" or self.active_service == "recorder":
            self._sync_voice_playback_position()
            snapshot = getattr(self.recorder, "voice_snapshot", None)
            voice = (
                snapshot()
                if callable(snapshot)
                else self.recorder.state.as_dict()
            )
            state = str(voice.get("state") or "stopped")
            continuous = voice.get("continuous") is True
            voice_playing = (
                self._voice_playback_active and self.player.state.state == "playing"
            )
            title = (
                "Continuous recording"
                if state == "recording" and continuous
                else "Recording"
                if state == "recording"
                else "Recording paused"
                if voice.get("session_active") is True
                else "Hold PTT to record"
            )
            return {
                "service": "REC",
                "station": "Voice Recorder",
                "title": title,
                "subtitle": "Right microphone above · left microphone below",
                "playing": voice_playing,
                "audio_active": voice_playing,
                "recording": state == "recording",
                "continuous": continuous,
                "timeline": voice.get("timeline") or [],
                "output": voice.get("output"),
                "position_ms": voice.get("position_ms") or 0,
                "duration_ms": voice.get("duration_ms") or 0,
                "channel_label": f"{int(voice.get('position_ms') or 0) / 1000:.1f}",
                "volume": playback.volume,
            }
        if playback.state not in {"playing", "paused"}:
            return {
                "service": requested or "SYSTEM",
                "playing": False,
                "audio_active": audio_active,
                "volume": playback.volume,
            }
        selected = self._selected_preset() if self.active_service == "webradio" else None
        active_ambient_scene = (
            self.store.channel(self.active_ambient_scene_id)
            if self.active_service == "ambient" and self.active_ambient_scene_id is not None
            else None
        )
        station = (
            str(selected["name"])
            if selected is not None
            else self._ambient_display_text(active_ambient_scene)[0]
            if active_ambient_scene is not None
            else str(self._active_podcast_episode["podcast"])
            if self.active_service == "podcasts" and self._active_podcast_episode is not None
            else str(self._active_mediathek_item["channel"])
            if self.active_service in MEDIATHEK_SERVICE_IDS
            and self._active_mediathek_item is not None
            else playback.source or self.active_service
        )
        track_line = "No title information"
        buffered_recording = False
        buffered_continuous = False
        if self.active_service == "webradio" and self.radio_buffer is not None:
            buffered = self.radio_buffer.snapshot()
            buffered_continuous = buffered.get("continuous") is True
            buffered_recording = (
                buffered.get("keep_current") is True
                or buffered_continuous
            )
            track_line = self._radio_track_line(buffered) or track_line
        elif self.active_service == "podcasts" and self._active_podcast_episode is not None:
            track_line = str(self._active_podcast_episode["title"])
        elif (
            self.active_service in MEDIATHEK_SERVICE_IDS
            and self._active_mediathek_item is not None
        ):
            track_line = str(self._active_mediathek_item["title"])
        elif self.active_service == "ambient" and self.active_ambient_scene_id is not None:
            if active_ambient_scene is not None:
                track_line = self._ambient_display_text(active_ambient_scene)[1]
        ambient_preset_id = (
            str(
                (
                    active_ambient_scene.get("metadata") or {}
                ).get("source_preset_id")
                or active_ambient_scene["external_id"]
            )
            if active_ambient_scene is not None
            and str(
                (
                    active_ambient_scene.get("metadata") or {}
                ).get("source_preset_id")
                or active_ambient_scene["external_id"]
            ) in AMBIENT_BY_ID
            else None
        )
        return {
            "service": service_label,
            "station": station,
            "title": track_line,
            "subtitle": track_line,
            "playing": not playback.paused,
            "audio_active": audio_active,
            "recording": (
                self.recorder.state.state == "recording" or buffered_recording
            ),
            "continuous": buffered_continuous,
            "volume": playback.volume,
            "preset_id": (
                selected["preset_id"] if selected is not None else ambient_preset_id
            ),
            "channel": (
                selected["channel"]
                if selected is not None
                else next(
                    (
                        index
                        for index, item in enumerate(
                            self.store.channels("ambient"), start=1
                        )
                        if self.active_ambient_scene_id == int(item["id"])
                    ),
                    None,
                )
                if self.active_service == "ambient"
                else self._active_mediathek_position()
                if self.active_service in MEDIATHEK_SERVICE_IDS
                else None
            ),
            "layer_rows": self._ambient_layer_rows() if service_label == "AMBIENT" else [],
            "layer_position": next(
                (
                    index
                    for index, item in enumerate(self._ambient_layer_rows(), start=1)
                    if item["selected"] is True
                ),
                1,
            ) if service_label == "AMBIENT" else 0,
            "layer_count": len(AMBIENT_LAYER_IDS) + 1 if service_label == "AMBIENT" else 0,
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
        self.scan_media()
        self.brandmeister.close()
        self._stop_ambient_layers()
        if self.radio_buffer is not None:
            self.radio_buffer.close()
        self.player.close()
        self.store.close()
