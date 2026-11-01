from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

from openr4d10.services import BUILTIN_SERVICES, ServiceCatalog
from openr4d10.content import DWD_RADAR_GIF_URL
from openr4d10.presets import FEED_BY_ID, RADIO_BY_ID
from openr4d10.radio_capture import BufferedTrack
from openr4d10.storage import MIGRATION_1, SCHEMA_VERSION, StateStore


class StateStoreTests(unittest.TestCase):
    def test_v2_service_rows_receive_stable_manifest_positions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw).resolve() / "state.sqlite3"
            connection = sqlite3.connect(path)
            connection.executescript(MIGRATION_1)
            connection.executemany(
                "INSERT INTO service_state(service_id, enabled, updated_at) VALUES (?, 1, 'now')",
                ((item,) for item in ("system", "webradio", "rss")),
            )
            connection.execute("PRAGMA user_version = 2")
            connection.commit()
            connection.close()
            store = StateStore(path)
            try:
                store.ensure_services(("system", "webradio", "weather", "rss"), {"weather"})
                ordered = list(store.service_states())
            finally:
                store.close()
        self.assertEqual(ordered, ["system", "webradio", "weather", "rss"])

    def test_migrates_persists_and_rejects_secret_settings(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw).resolve() / "state.sqlite3"
            store = StateStore(path)
            try:
                version = store.connection.execute("PRAGMA user_version").fetchone()[0]
                self.assertEqual(version, SCHEMA_VERSION)
                store.set_setting("ui.accent", {"r": 73, "g": 222, "b": 204})
                self.assertEqual(store.get_setting("ui.accent")["g"], 222)
                for forbidden in ("spotify.token", "mumble-password", "api_key"):
                    with self.subTest(forbidden=forbidden):
                        with self.assertRaises(ValueError):
                            store.set_setting(forbidden, "never")
            finally:
                store.close()
            if os.name != "nt":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)


class ServiceCatalogTests(unittest.TestCase):
    def test_recorded_song_uses_media_music_artist_layout(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            catalog = ServiceCatalog(root, executable_lookup=lambda _name: None)
            try:
                stored = catalog._store_buffered_track(
                    BufferedTrack(
                        payload=b"mpeg-audio",
                        content_type="audio/mpeg",
                        stream_title="Gorillaz - Feel Good Inc",
                        artist="Gorillaz",
                        title="Feel Good Inc",
                        started_at="2026-11-01T08:21:59+00:00",
                        truncated=False,
                    )
                )
                expected = (
                    root
                    / "media"
                    / "Music"
                    / "Gorillaz"
                    / "Gorillaz - Feel Good Inc.mp3"
                )
                self.assertTrue(stored)
                self.assertTrue(expected.is_file())
                item = next(
                    entry for entry in catalog.snapshot()["media"]
                    if entry["source_kind"] == "radio"
                )
                self.assertEqual(item["folder"], "Music/Gorillaz")
            finally:
                catalog.close()

    def test_legacy_recorded_tree_moves_to_music_without_losing_favorite(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            old = root / "media" / "recorded" / "Artist" / "Artist - Song.mp3"
            old.parent.mkdir(parents=True)
            old.write_bytes(b"audio")
            store = StateStore(root / "openr4d10.sqlite3")
            media_id = store.add_recorded_media(
                old,
                artist="Artist",
                title="Song",
                size_bytes=5,
                checksum="legacy-checksum",
                normalized_key="artistsong",
                fingerprint=None,
                review_required=False,
            )
            store.set_media_favorite(media_id, True)
            store.close()

            catalog = ServiceCatalog(root)
            try:
                target = root / "media" / "Music" / "Artist" / "Artist - Song.mp3"
                self.assertFalse(old.exists())
                self.assertTrue(target.is_file())
                item = catalog.store.media_item(media_id)
                self.assertEqual(item["path"], str(target))
                self.assertTrue(item["favorite"])
                self.assertEqual(item["source_kind"], "radio")
            finally:
                catalog.close()

    def test_weather_radar_upgrade_preserves_customization_and_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            store = StateStore(root / "openr4d10.sqlite3")
            try:
                store.ensure_services(tuple(item.service_id for item in BUILTIN_SERVICES))
                store.seed_channels_once(
                    "weather",
                    (("dwd-deutschland", "Mein Wetter", {"bbox": [48.0, 6.0, 54.0, 15.0]}),),
                    marker="weather.defaults_seeded_v1",
                )
            finally:
                store.close()

            catalog = ServiceCatalog(root, executable_lookup=lambda _name: "/bin/true")
            try:
                channels = catalog.snapshot()["weather"]["channels"]
                channel = channels[0]
                satellite = next(
                    item
                    for item in channels
                    if item["external_id"] == "dwd-deutschland-satellit"
                )
                stored = catalog.store.channel(channel["id"])
                self.assertEqual(channel["name"], "Mein Wetter")
                self.assertEqual(channel["kind"], "radar_gif")
                self.assertEqual(stored["metadata"]["bbox"], [48.0, 6.0, 54.0, 15.0])
                self.assertEqual(stored["metadata"]["source_url"], DWD_RADAR_GIF_URL)
                self.assertEqual(satellite["kind"], "satellite_wms")
                self.assertEqual(satellite["provider"], "DWD / EUMETSAT")
                catalog.store.delete_channel(channel["id"])
                catalog.store.delete_channel(satellite["id"])
            finally:
                catalog.close()

            reopened = ServiceCatalog(root, executable_lookup=lambda _name: "/bin/true")
            try:
                ids = {
                    item["external_id"]
                    for item in reopened.snapshot()["weather"]["channels"]
                }
                self.assertNotIn("dwd-deutschland", ids)
                self.assertNotIn("dwd-deutschland-satellit", ids)
            finally:
                reopened.close()

    def test_weather_defaults_channel_loop_and_service_priority_persist(self) -> None:
        class Weather:
            def __init__(self, root):
                self.cache_root = root / "cache"
                self.refreshed = threading.Event()

            def frames(self, key):
                return [
                    {
                        "file": f"weather-{key}-20261031T060000Z.jpg",
                        "timestamp": "2026-10-31T06:00Z",
                    }
                ] if self.refreshed.is_set() else []

            def refresh(self, key, bbox):
                self.last = (key, bbox)
                self.refreshed.set()
                return self.frames(key)

            def refresh_radar(self, key, source_url):
                self.last = (key, source_url)
                self.refreshed.set()
                return self.frames(key)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            weather = Weather(root)
            catalog = ServiceCatalog(root, weather=weather)
            try:
                snapshot = catalog.snapshot()
                channels = snapshot["weather"]["channels"]
                self.assertEqual(
                    [item["name"] for item in channels],
                    ["Regenradar Deutschland", "Satellit Deutschland", "Europa"],
                )
                self.assertEqual(channels[0]["provider"], "DWD")
                self.assertEqual(channels[0]["kind"], "radar_gif")
                self.assertEqual(channels[1]["provider"], "DWD / EUMETSAT")
                self.assertEqual(channels[1]["kind"], "satellite_wms")
                with self.assertRaisesRegex(ValueError, "layer coverage"):
                    catalog.control(
                        {
                            "action": "weather_channel_save",
                            "name": "Ungültig",
                            "bbox": [-90, -180, 90, 180],
                        }
                    )
                catalog.active_service = "webradio"
                playback_before = catalog.player.state.as_dict()
                catalog.control({"action": "weather_open", "channel_id": channels[0]["id"]})
                self.assertTrue(weather.refreshed.wait(1))
                self.assertEqual(catalog.active_service, "webradio")
                self.assertEqual(catalog.player.state.as_dict(), playback_before)
                overlay = catalog.receiver_overlay("WEATHER")
                self.assertEqual(overlay["service"], "WEATHER")
                self.assertTrue(str(overlay["image_file"]).startswith("weather-dwd-deutschland-"))
                stepped = catalog.control({"action": "weather_step", "steps": 1})
                self.assertEqual(stepped["channel_id"], channels[1]["id"])
                self.assertEqual(catalog.active_service, "webradio")
                catalog.control({"action": "weather_channel_move", "channel_id": channels[1]["id"], "direction": -1})
                catalog.control({"action": "service_move", "service_id": "weather", "direction": -1})
            finally:
                catalog.close()

            reopened = ServiceCatalog(root, weather=Weather(root))
            try:
                persisted = reopened.snapshot()
                self.assertEqual(
                    persisted["weather"]["channels"][0]["name"],
                    "Satellit Deutschland",
                )
                service_ids = [item["service_id"] for item in persisted["items"]]
                self.assertLess(service_ids.index("weather"), service_ids.index("webradio"))
            finally:
                reopened.close()

    def test_display_brightness_is_persistent_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state_root = Path(raw).resolve()
            catalog = ServiceCatalog(state_root)
            try:
                self.assertEqual(catalog.display_brightness(), 100)
                self.assertEqual(catalog.set_display_brightness(35), 35)
                self.assertEqual(
                    catalog.snapshot()["settings"]["display_brightness_percent"],
                    35,
                )
                for invalid in (-1, 101, True, 50.0):
                    with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                        catalog.set_display_brightness(invalid)  # type: ignore[arg-type]
            finally:
                catalog.close()
            reopened = ServiceCatalog(state_root)
            try:
                self.assertEqual(reopened.display_brightness(), 35)
            finally:
                reopened.close()

    def test_display_language_is_persistent_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state_root = Path(raw).resolve()
            catalog = ServiceCatalog(state_root)
            try:
                self.assertEqual(catalog.display_language(), "en")
                self.assertEqual(catalog.set_display_language("de-DE"), "de")
                self.assertEqual(catalog.snapshot()["settings"]["language"], "de")
                for invalid in ("it", "", True, None):
                    with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                        catalog.set_display_language(invalid)  # type: ignore[arg-type]
            finally:
                catalog.close()
            reopened = ServiceCatalog(state_root)
            try:
                self.assertEqual(reopened.display_language(), "de")
            finally:
                reopened.close()

    def test_display_appearance_is_persistent_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state_root = Path(raw).resolve()
            catalog = ServiceCatalog(state_root)
            try:
                self.assertEqual(
                    catalog.display_appearance(),
                    {"accent_color": "#FDB813"},
                )
                self.assertEqual(
                    catalog.set_display_appearance("#12abef"),
                    {"accent_color": "#12ABEF"},
                )
                with self.assertRaises(ValueError):
                    catalog.set_display_appearance("orange")
            finally:
                catalog.close()
            reopened = ServiceCatalog(state_root)
            try:
                self.assertEqual(
                    reopened.display_appearance(),
                    {"accent_color": "#12ABEF"},
                )
            finally:
                reopened.close()

    def test_last_sensible_view_is_restored_without_changing_audio(self) -> None:
        class State:
            state = "stopped"
            source = None
            paused = False
            volume = 30

            def as_dict(self):
                return {
                    "state": self.state,
                    "source": self.source,
                    "paused": self.paused,
                    "volume": self.volume,
                }

        class Player:
            def __init__(self):
                self.state = State()

            def close(self):
                pass

        class Recorder:
            def __init__(self):
                self.state = State()

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            catalog = ServiceCatalog(root, player=Player(), recorder=Recorder())
            try:
                self.assertEqual(catalog.receiver_overlay()["service"], "RADIO")
                self.assertEqual(catalog.receiver_overlay("WEATHER")["service"], "WEATHER")
            finally:
                catalog.close()
            reopened = ServiceCatalog(root, player=Player(), recorder=Recorder())
            try:
                self.assertEqual(reopened.receiver_overlay()["service"], "WEATHER")
            finally:
                reopened.close()

    def test_curated_presets_are_public_without_remote_content_urls(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            catalog = ServiceCatalog(Path(raw).resolve())
            try:
                presets = catalog.snapshot()["presets"]
            finally:
                catalog.close()
        station_ids = {item["preset_id"] for item in presets["stations"]}
        self.assertEqual(station_ids, set(RADIO_BY_ID))
        self.assertEqual(len(station_ids), 46)
        self.assertTrue({"swr3", "sunshine_live", "deutschlandfunk", "rmf_fm", "radio_zet", "bbc_world"}.issubset(station_ids))
        self.assertTrue(
            {
                "radio_gra_torun",
                "polskie_radio_2",
                "polskie_radio_3",
                "radio_357",
                "radio_nowy_swiat",
            }.issubset(station_ids)
        )
        self.assertFalse(any("maryja" in item.casefold() for item in station_ids))
        for item in presets["stations"]:
            self.assertNotIn("stream_url", item)
            self.assertNotIn("artwork_url", item)
            self.assertTrue(item["artwork"].startswith("/api/radio-art/"))
        for item in presets["feeds"]:
            self.assertNotIn("feed_url", item)
        for item in RADIO_BY_ID.values():
            parsed = urlsplit(item.stream_url)
            self.assertIn(parsed.scheme, {"http", "https"})
            self.assertIsNone(parsed.username)
            self.assertFalse(parsed.query)
            self.assertTrue(item.language)
            self.assertTrue(item.categories)
        language_counts = {}
        for item in RADIO_BY_ID.values():
            language_counts[item.language] = language_counts.get(item.language, 0) + 1
        self.assertEqual(set(language_counts), {"de", "en", "pl", "fr", "es", "it", "nl", "pt"})
        self.assertTrue(all(count >= 5 for count in language_counts.values()))
        self.assertEqual(sum(item.default_enabled for item in RADIO_BY_ID.values()), 10)
        for preset_id in (
            "radio_gra_torun",
            "polskie_radio_2",
            "polskie_radio_3",
            "radio_357",
            "radio_nowy_swiat",
        ):
            self.assertFalse(RADIO_BY_ID[preset_id].default_enabled)
        for item in FEED_BY_ID.values():
            parsed = urlsplit(item.feed_url)
            self.assertEqual(parsed.scheme, "https")
            self.assertIsNone(parsed.username)

    def test_radio_preset_plays_and_saves_idempotently(self) -> None:
        class State:
            state = "stopped"
            source = None
            paused = False
            volume = 36

            def as_dict(self):
                return {"state": self.state, "source": self.source, "paused": self.paused}

        class Player:
            def __init__(self):
                self.state = State()
                self.loaded = None

            def load(self, source):
                self.loaded = source

            def close(self):
                pass

        class Recorder:
            def __init__(self):
                self.state = State()

            def close(self):
                pass

        class Artwork:
            def __init__(self):
                self.loaded = []
                self.ready = threading.Event()

            def ensure(self, preset_id, _url):
                self.loaded.append(preset_id)
                self.ready.set()
                return Path(f"/{preset_id}.jpg")

        with tempfile.TemporaryDirectory() as raw:
            player = Player()
            artwork = Artwork()
            catalog = ServiceCatalog(
                Path(raw).resolve(),
                player=player,
                recorder=Recorder(),
                artwork=artwork,
            )
            try:
                catalog.control({"action": "preset_play", "preset_id": "swr3"})
                selected = catalog.snapshot()["selected_preset"]
                swr3_source = player.loaded
                stepped = catalog.control({"action": "preset_step", "steps": 1})
                first = catalog.control({"action": "preset_save", "preset_id": "swr3"})
                second = catalog.control({"action": "preset_save", "preset_id": "swr3"})
                stations = catalog.snapshot()["stations"]
                self.assertTrue(artwork.ready.wait(1))
            finally:
                catalog.close()
        self.assertEqual(swr3_source, RADIO_BY_ID["swr3"].stream_url)
        self.assertEqual(selected["name"], "SWR3")
        self.assertEqual(player.loaded, RADIO_BY_ID["sunshine_live"].stream_url)
        self.assertEqual(stepped["selected_preset"]["name"], "sunshine live")
        self.assertIn("swr3", artwork.loaded)
        self.assertEqual(first["station_id"], second["station_id"])
        self.assertEqual(len(stations), 10)

    def test_feed_preset_uses_curated_address_and_returns_credit(self) -> None:
        class Reader:
            def __init__(self):
                self.loaded = None

            def fetch(self, url):
                self.loaded = url
                return {"title": "World", "item_count": 1, "items": []}

        reader = Reader()
        with tempfile.TemporaryDirectory() as raw:
            catalog = ServiceCatalog(Path(raw).resolve(), feed_reader=reader)
            try:
                result = catalog.control(
                    {"action": "feed_fetch_preset", "preset_id": "bbc_world"}
                )
            finally:
                catalog.close()
        self.assertEqual(reader.loaded, FEED_BY_ID["bbc_world"].feed_url)
        self.assertEqual(result["credit"], "Source: BBC News")
        self.assertNotIn("feed_url", result)

    def test_podcast_subscriptions_persist_and_episodes_play_without_exposing_urls(self) -> None:
        class State:
            state = "stopped"
            volume = 30

            def as_dict(self):
                return {"state": self.state, "volume": self.volume}

        class Player:
            def __init__(self):
                self.state = State()
                self.loaded = None

            def load(self, source):
                self.loaded = source
                self.state.state = "playing"

            def stop(self):
                self.state.state = "stopped"

            def close(self):
                pass

        class Recorder:
            state = State()

            def close(self):
                pass

        class Reader:
            def fetch(self, url):
                self.loaded = url
                return {
                    "title": "Science Weekly",
                    "description": "Research and technology",
                    "homepage": "https://example.test/show",
                    "episode_count": 1,
                    "episodes": [{
                        "title": "New discovery",
                        "summary": "A safe summary",
                        "published": "today",
                        "duration": "10:00",
                        "guid": "episode-1",
                        "enclosure_url": "https://media.example.test/episode-1.mp3",
                        "enclosure_type": "audio/mpeg",
                    }],
                }

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            player = Player()
            catalog = ServiceCatalog(
                root, player=player, recorder=Recorder(), podcast_reader=Reader()
            )
            try:
                subscribed = catalog.control({
                    "action": "podcast_subscribe",
                    "url": "https://example.test/feed.xml",
                })
                snapshot = catalog.snapshot()["podcasts"]
                episode = snapshot["episodes"][0]
                catalog.control({
                    "action": "podcast_play",
                    "subscription_id": subscribed["subscription_id"],
                    "episode_id": episode["episode_id"],
                })
                public_snapshot = catalog.snapshot()["podcasts"]
            finally:
                catalog.close()
            reopened = ServiceCatalog(root, player=Player(), recorder=Recorder(), podcast_reader=Reader())
            try:
                persisted = reopened.snapshot()["podcasts"]["subscriptions"]
            finally:
                reopened.close()

        self.assertEqual(player.loaded, "https://media.example.test/episode-1.mp3")
        self.assertEqual(public_snapshot["active_episode"]["title"], "New discovery")
        self.assertNotIn("enclosure_url", public_snapshot["episodes"][0])
        self.assertNotIn("feed_url", public_snapshot["subscriptions"][0])
        self.assertEqual(persisted[0]["name"], "Science Weekly")

    def test_catalog_covers_documented_services_without_claiming_credentials(self) -> None:
        available = {
            "mpv": "/usr/bin/mpv",
            "ffmpeg": "/usr/bin/ffmpeg",
            "aplay": "/usr/bin/aplay",
        }
        with tempfile.TemporaryDirectory() as raw:
            catalog = ServiceCatalog(
                Path(raw).resolve(),
                executable_lookup=available.get,
            )
            try:
                snapshot = catalog.snapshot()
            finally:
                catalog.close()
        items = {item["service_id"]: item for item in snapshot["items"]}
        expected = {
            "brandmeister", "webradio", "local_media", "recorder", "mumble",
            "discord", "telegram", "webcam", "rss", "youtube_audio",
            "spotify", "ard_mediathek", "zdf_mediathek", "remote_sdr",
            "speech", "codex_remote", "anker_solix",
        }
        self.assertTrue(expected.issubset(items))
        self.assertEqual(len(items), len(BUILTIN_SERVICES))
        self.assertEqual(items["webradio"]["readiness"], "ready")
        self.assertEqual(items["brandmeister"]["readiness"], "ready")
        self.assertNotIn("credential", items["brandmeister"])

    def test_brandmeister_talkgroups_are_device_persistent_and_drive_receiver(self) -> None:
        class Receiver:
            def __init__(self):
                self.state = {
                    "status": "stopped",
                    "talkgroups": [],
                    "destination": None,
                    "source": None,
                    "alias": "",
                    "volume": 30,
                    "error": None,
                    "country_code": None,
                }

            def snapshot(self):
                return dict(self.state)

            def set_volume(self, volume):
                self.state["volume"] = volume
                return self.snapshot()

            def listen(self, talkgroups):
                self.state["status"] = "listening"
                self.state["talkgroups"] = list(talkgroups)
                return self.snapshot()

            def stop(self):
                self.state["status"] = "stopped"
                self.state["talkgroups"] = []
                return self.snapshot()

            def close(self):
                self.stop()

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            receiver = Receiver()
            catalog = ServiceCatalog(
                root,
                brandmeister=receiver,  # type: ignore[arg-type]
                executable_lookup=lambda _name: "/bin/true",
            )
            try:
                initial = catalog.snapshot()["brandmeister"]
                self.assertEqual(initial["channels"][0]["talkgroup"], 91)
                self.assertTrue(initial["channels"][0]["enabled"])
                added = catalog.control(
                    {
                        "action": "brandmeister_talkgroup_add",
                        "talkgroup": 262,
                        "name": "Germany",
                        "enabled": True,
                    }
                )
                self.assertIsInstance(added["channel_id"], int)
                self.assertEqual(receiver.state["talkgroups"], [])
                catalog.active_service = "webradio"
                started = catalog.control({"action": "brandmeister_toggle"})
                self.assertEqual(receiver.state["talkgroups"], [91, 262])
                self.assertEqual(started["brandmeister"]["status"], "listening")
                self.assertEqual(catalog.active_service, "brandmeister")
            finally:
                catalog.close()
            reopened = ServiceCatalog(
                root,
                brandmeister=Receiver(),  # type: ignore[arg-type]
                executable_lookup=lambda _name: "/bin/true",
            )
            try:
                persisted = reopened.snapshot()["brandmeister"]["channels"]
                self.assertEqual(
                    [item["talkgroup"] for item in persisted],
                    [91, 262],
                )
            finally:
                reopened.close()

    def test_brandmeister_device_browses_full_catalog_and_toggles_unsaved_group(self) -> None:
        class Receiver:
            def __init__(self):
                self.state = {
                    "status": "stopped", "talkgroups": [], "destination": None,
                    "source": None, "alias": "", "volume": 30, "error": None,
                    "country_code": None,
                }

            def snapshot(self):
                return dict(self.state)

            def set_volume(self, volume):
                self.state["volume"] = volume
                return self.snapshot()

            def listen(self, talkgroups):
                self.state["status"] = "listening"
                self.state["talkgroups"] = list(talkgroups)
                return self.snapshot()

            def stop(self):
                self.state["status"] = "stopped"
                self.state["talkgroups"] = []
                return self.snapshot()

            def close(self):
                self.stop()

        class Talkgroups:
            def entries(self):
                return [
                    {"talkgroup": number, "name": f"TG {number}", "country_code": None}
                    for number in range(91, 151)
                ]

        with tempfile.TemporaryDirectory() as raw:
            catalog = ServiceCatalog(
                Path(raw).resolve(),
                brandmeister=Receiver(),  # type: ignore[arg-type]
                brandmeister_catalog=Talkgroups(),  # type: ignore[arg-type]
                executable_lookup=lambda _name: "/bin/true",
            )
            try:
                catalog._load_brandmeister_catalog()
                one = catalog.control({"action": "brandmeister_step", "steps": 1})
                self.assertEqual(one["talkgroup"], 92)
                fast = catalog.control({"action": "brandmeister_step", "steps": 25})
                self.assertEqual(fast["talkgroup"], 117)
                toggled = catalog.control({"action": "brandmeister_toggle_selected"})
                self.assertTrue(toggled["enabled"])
                self.assertEqual(toggled["talkgroup"], 117)
                snapshot = catalog.snapshot()["brandmeister"]
                self.assertEqual(snapshot["selected_talkgroup"], 117)
                self.assertEqual(snapshot["talkgroups"], [])
                catalog.player.state.volume = 40
                frame = catalog.receiver_overlay("DMR")
                self.assertEqual(frame["volume"], 40)
                self.assertEqual(frame["catalog_position"], 2)
                self.assertEqual(frame["catalog_count"], 60)
                self.assertEqual(
                    [item["talkgroup"] for item in frame["catalog_rows"][:2]],
                    [91, 117],
                )
                self.assertTrue(frame["catalog_rows"][1]["selected"])
                self.assertTrue(frame["catalog_rows"][1]["enabled"])
                self.assertTrue(
                    all(
                        item["enabled"] is False
                        for item in catalog._brandmeister_device_entries(allow_network=False)[2:]
                    )
                )
                started = catalog.control({"action": "brandmeister_toggle"})
                self.assertEqual(started["brandmeister"]["talkgroups"], [91, 117])
                self.assertEqual(started["brandmeister"]["volume"], 40)
                self.assertEqual(catalog.active_service, "brandmeister")
                stopped = catalog.control({"action": "brandmeister_toggle"})
                self.assertEqual(stopped["brandmeister"]["status"], "stopped")
                self.assertEqual(catalog.active_service, "system")
                jumped = catalog.control({"action": "brandmeister_jump_first"})
                self.assertEqual(jumped["talkgroup"], 91)
                jumped_snapshot = catalog.snapshot()["brandmeister"]
                self.assertEqual(jumped_snapshot["selected_talkgroup"], 91)
                jumped_frame = catalog.receiver_overlay("DMR")
                self.assertEqual(jumped_frame["catalog_position"], 1)
                self.assertTrue(jumped_frame["catalog_rows"][0]["selected"])
            finally:
                catalog.close()

    def test_brandmeister_country_filter_and_sixth_talkgroup_replacement(self) -> None:
        class Receiver:
            def __init__(self):
                self.state = {
                    "status": "stopped", "talkgroups": [], "destination": None,
                    "source": None, "alias": "", "volume": 30, "error": None,
                    "country_code": None,
                }

            def snapshot(self):
                return dict(self.state)

            def set_volume(self, volume):
                self.state["volume"] = volume
                return self.snapshot()

            def listen(self, talkgroups):
                self.state["status"] = "listening"
                self.state["talkgroups"] = list(talkgroups)
                return self.snapshot()

            def stop(self):
                self.state["status"] = "stopped"
                self.state["talkgroups"] = []
                return self.snapshot()

            def close(self):
                self.stop()

        class Talkgroups:
            def entries(self):
                return [
                    {"talkgroup": 91, "name": "Worldwide", "country_code": None},
                    {"talkgroup": 262, "name": "Germany", "country_code": "DE"},
                    {"talkgroup": 3100, "name": "USA", "country_code": "US"},
                    {"talkgroup": 234, "name": "United Kingdom", "country_code": "GB"},
                    {"talkgroup": 204, "name": "Netherlands", "country_code": "NL"},
                    {"talkgroup": 505, "name": "Australia", "country_code": "AU"},
                ]

        with tempfile.TemporaryDirectory() as raw:
            catalog = ServiceCatalog(
                Path(raw).resolve(),
                brandmeister=Receiver(),  # type: ignore[arg-type]
                brandmeister_catalog=Talkgroups(),  # type: ignore[arg-type]
                executable_lookup=lambda _name: "/bin/true",
            )
            try:
                catalog._load_brandmeister_catalog()
                catalog.control({"action": "brandmeister_country_menu_open"})
                catalog.selected_brandmeister_country = "DE"
                selected = catalog.control({"action": "brandmeister_country_select"})
                self.assertEqual(selected["country_code"], "DE")
                country_frame = catalog.receiver_overlay("DMR")
                self.assertEqual(country_frame["country_filter"], "DE")
                self.assertTrue(
                    all(row["country_code"] == "DE" for row in country_frame["catalog_rows"])
                )

                catalog.brandmeister_country_filter = None
                for talkgroup, name in (
                    (262, "Germany"),
                    (3100, "USA"),
                    (234, "United Kingdom"),
                    (204, "Netherlands"),
                ):
                    catalog.control(
                        {
                            "action": "brandmeister_talkgroup_add",
                            "talkgroup": talkgroup,
                            "name": name,
                            "enabled": True,
                        }
                    )
                catalog.selected_brandmeister_talkgroup = 505
                pending = catalog.control({"action": "brandmeister_toggle_selected"})
                self.assertTrue(pending["replacement_required"])
                replacement_frame = catalog.receiver_overlay("DMR")
                self.assertTrue(replacement_frame["replacement_required"])
                self.assertEqual(len(replacement_frame["replacement_rows"]), 5)

                catalog.control({"action": "brandmeister_replacement_step", "steps": 1})
                replaced = catalog.control({"action": "brandmeister_replacement_confirm"})
                enabled = catalog._enabled_brandmeister_talkgroups()
                self.assertEqual(len(enabled), 5)
                self.assertIn(505, enabled)
                self.assertNotIn(replaced["replaced_talkgroup"], enabled)
            finally:
                catalog.close()

    def test_solix_adapter_exposes_only_bounded_public_energy_metrics(self) -> None:
        class Registry:
            def configured(self, service_id):
                return service_id == "anker_solix"

            def status(self, service_id):
                return {
                    "ok": True,
                    "ready": True,
                    "status": "connected",
                    "metrics": {
                        "solar_w": 612,
                        "home_w": 281,
                        "grid_w": -144,
                        "battery_w": 187,
                        "battery_percent": 73,
                        "energy_today_kwh": 2.8,
                        "serial_number": "must-not-leak",
                        "impossible_w": 999_999,
                    },
                }

            def call(self, service_id, operation, parameters=None):
                return {"ok": True}

        with tempfile.TemporaryDirectory() as raw:
            catalog = ServiceCatalog(Path(raw).resolve(), adapter_registry=Registry())
            try:
                catalog.control(
                    {
                        "action": "service_set_enabled",
                        "service_id": "anker_solix",
                        "enabled": True,
                    }
                )
                solix = {
                    item["service_id"]: item for item in catalog.snapshot()["items"]
                }["anker_solix"]
            finally:
                catalog.close()

        self.assertEqual(solix["readiness"], "ready")
        self.assertEqual(
            solix["adapter"]["metrics"],
            {
                "solar_w": 612,
                "home_w": 281,
                "grid_w": -144,
                "battery_w": 187,
                "battery_percent": 73,
                "energy_today_kwh": 2.8,
            },
        )

    def test_camera_library_persists_orders_and_refreshes_multiple_protocols(self) -> None:
        class Camera:
            def __init__(self, root):
                self.cache_root = root
                self.calls = []

            def fetch(self, url, slot, *, kind="snapshot"):
                self.calls.append((url, slot, kind))
                self.cache_root.mkdir(parents=True, exist_ok=True)
                self.cache_root.joinpath(f"camera-{slot}.jpg").write_bytes(b"jpeg")
                return {
                    "slot": slot, "file": f"camera-{slot}.jpg", "kind": kind,
                    "width": 320, "height": 240,
                }

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            camera = Camera(root / "cache")
            catalog = ServiceCatalog(root, camera=camera)  # type: ignore[arg-type]
            try:
                first = catalog.control(
                    {
                        "action": "camera_add", "name": "Town square",
                        "kind": "snapshot", "url": "https://cam.example/image.jpg",
                    }
                )
                second = catalog.control(
                    {
                        "action": "camera_add", "name": "Harbour",
                        "kind": "rtsp", "url": "rtsp://cam.example/live",
                    }
                )
                refreshed = catalog.control(
                    {"action": "camera_refresh", "camera_id": second["camera_id"]}
                )
                self.assertEqual(refreshed["camera"]["kind"], "rtsp")
                self.assertEqual(camera.calls[-1][2], "rtsp")
                self.assertTrue(
                    catalog.control(
                        {
                            "action": "camera_move",
                            "camera_id": second["camera_id"],
                            "direction": -1,
                        }
                    )["moved"]
                )
                public = catalog.snapshot()["webcams"]["channels"]
                self.assertEqual([item["name"] for item in public], ["Harbour", "Town square"])
                self.assertNotIn("source_url", public[0])
                with self.assertRaises(ValueError):
                    catalog.control(
                        {
                            "action": "camera_add", "name": "Secret",
                            "kind": "snapshot",
                            "url": "https://cam.example/image.jpg?token=secret",
                        }
                    )
            finally:
                catalog.close()

            reopened = ServiceCatalog(root, camera=Camera(root / "cache"))  # type: ignore[arg-type]
            try:
                persisted = reopened.snapshot()["webcams"]["channels"]
                self.assertEqual([item["name"] for item in persisted], ["Harbour", "Town square"])
                self.assertEqual(reopened.selected_camera_id, second["camera_id"])
            finally:
                reopened.close()

    def test_missing_process_dependency_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            catalog = ServiceCatalog(
                Path(raw).resolve(),
                executable_lookup=lambda _name: None,
            )
            try:
                items = {item["service_id"]: item for item in catalog.snapshot()["items"]}
            finally:
                catalog.close()
        self.assertEqual(items["recorder"]["readiness"], "missing_dependency")
        self.assertEqual(items["recorder"]["missing_executables"], ["ffmpeg"])

    def test_external_service_is_ready_only_after_adapter_handshake(self) -> None:
        class Registry:
            def configured(self, service_id):
                return service_id == "mumble"

            def status(self, service_id):
                return {"ok": True, "ready": True, "status": "connected"}

            def call(self, service_id, operation, parameters=None):
                return {"ok": True, "operation": operation}

        with tempfile.TemporaryDirectory() as raw:
            catalog = ServiceCatalog(
                Path(raw).resolve(), adapter_registry=Registry()
            )
            try:
                with self.assertRaisesRegex(ValueError, "no active media"):
                    catalog.control({"action": "pause"})
                catalog.control(
                    {
                        "action": "service_set_enabled",
                        "service_id": "mumble",
                        "enabled": True,
                    }
                )
                items = {item["service_id"]: item for item in catalog.snapshot()["items"]}
                result = catalog.control(
                    {
                        "action": "adapter_call",
                        "service_id": "mumble",
                        "operation": "list_channels",
                    }
                )
            finally:
                catalog.close()
        self.assertEqual(items["mumble"]["readiness"], "ready")
        self.assertEqual(items["discord"]["readiness"], "disabled")
        self.assertEqual(result["adapter"]["operation"], "list_channels")

    def test_service_lifecycle_persists_and_system_cannot_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            catalog = ServiceCatalog(root)
            try:
                first = {item["service_id"]: item for item in catalog.snapshot()["items"]}
                self.assertTrue(first["webradio"]["enabled"])
                self.assertFalse(first["spotify"]["enabled"])
                catalog.control(
                    {
                        "action": "service_set_enabled",
                        "service_id": "spotify",
                        "enabled": True,
                    }
                )
                with self.assertRaisesRegex(ValueError, "cannot be disabled"):
                    catalog.control(
                        {
                            "action": "service_set_enabled",
                            "service_id": "system",
                            "enabled": False,
                        }
                    )
            finally:
                catalog.close()
            reopened = ServiceCatalog(root)
            try:
                state = {item["service_id"]: item for item in reopened.snapshot()["items"]}
            finally:
                reopened.close()
        self.assertTrue(state["spotify"]["enabled"])
        self.assertEqual(state["spotify"]["readiness"], "configuration_required")

    def test_media_control_updates_public_receiver_overlay(self) -> None:
        class State:
            def __init__(self, **values):
                self.values = values
                for key, value in values.items():
                    setattr(self, key, value)

            def as_dict(self):
                return dict(self.values)

        class Player:
            def __init__(self):
                self.state = State(
                    state="stopped", source=None, paused=False, volume=30
                )

            def load(self, source):
                self.state = State(
                    state="playing", source="https://radio.example/live",
                    paused=False, volume=self.state.volume,
                )

            def toggle_pause(self):
                self.state.paused = True
                self.state.values["paused"] = True

            def set_volume(self, value):
                self.state.volume = value
                self.state.values["volume"] = value

            def stop(self):
                self.state = State(state="stopped", source=None, paused=False)

            def close(self):
                pass

        class Recorder:
            def __init__(self):
                self.state = State(state="stopped")

            def start(self, source):
                self.state = State(state="recording")

            def stop(self):
                self.state = State(state="stopped")

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as raw:
            catalog = ServiceCatalog(
                Path(raw).resolve(),
                executable_lookup=lambda name: f"/usr/bin/{name}",
                player=Player(),
                recorder=Recorder(),
            )
            try:
                catalog.control(
                    {
                        "action": "play",
                        "service_id": "webradio",
                        "source": "https://radio.example/live?private=value",
                    }
                )
                overlay = catalog.receiver_overlay()
                volume = catalog.control({"action": "volume_step", "steps": 4})
                catalog.control({"action": "pause"})
                paused_overlay = catalog.receiver_overlay()
            finally:
                catalog.close()
        self.assertEqual(overlay["service"], "RADIO")
        self.assertEqual(overlay["station"], "https://radio.example/live")
        self.assertTrue(overlay["playing"])
        self.assertEqual(volume["playback"]["volume"], 70)
        self.assertFalse(paused_overlay["playing"])

    def test_radio_view_fetches_icy_title_before_audible_playback(self) -> None:
        class State:
            state = "stopped"
            source = None
            paused = False
            volume = 30

            def as_dict(self):
                return {
                    "state": self.state,
                    "source": self.source,
                    "paused": self.paused,
                    "volume": self.volume,
                }

        class Passive:
            def __init__(self):
                self.state = State()

            def close(self):
                pass

        class Buffer:
            def __init__(self):
                self.value = {"state": "stopped", "station": None}
                self.tuned = None

            def tune(self, source, station):
                self.tuned = (source, station)
                self.value = {"state": "connecting", "station": station}
                return dict(self.value)

            def set_continuous(self, enabled):
                self.value["continuous"] = enabled
                return dict(self.value)

            def snapshot(self):
                return dict(self.value)

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as raw:
            buffer = Buffer()
            catalog = ServiceCatalog(
                Path(raw).resolve(),
                player=Passive(),
                recorder=Passive(),
                radio_buffer=buffer,  # type: ignore[arg-type]
            )
            try:
                loading = catalog.receiver_overlay("RADIO")
                buffer.value.update(
                    {
                        "state": "buffering",
                        "artist": "The Artist",
                        "title": "The Song",
                    }
                )
                titled = catalog.receiver_overlay("RADIO")
            finally:
                catalog.close()
        self.assertIsNotNone(buffer.tuned)
        self.assertEqual(loading["subtitle"], "Loading title information")
        self.assertEqual(titled["subtitle"], "The Artist – The Song")
        self.assertFalse(titled["playing"])
        self.assertNotIn("aplay", str(titled).casefold())

    def test_station_library_is_persistent_and_never_exposes_query_values(self) -> None:
        class State:
            def __init__(self, **values):
                self.values = values
                for key, value in values.items():
                    setattr(self, key, value)

            def as_dict(self):
                return dict(self.values)

        class Player:
            def __init__(self):
                self.state = State(state="stopped", source=None, paused=False)
                self.loaded = None

            def load(self, source):
                self.loaded = source
                self.state = State(state="playing", source=source, paused=False)

            def close(self):
                pass

        class Recorder:
            def __init__(self):
                self.state = State(state="stopped")

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as raw:
            player = Player()
            catalog = ServiceCatalog(
                Path(raw).resolve(), player=player, recorder=Recorder()
            )
            try:
                result = catalog.control(
                    {
                        "action": "station_add",
                        "name": "Open Radio",
                        "source": "https://radio.example/live",
                    }
                )
                catalog.control(
                    {"action": "station_play", "station_id": result["station_id"]}
                )
                snapshot = catalog.snapshot()
                with self.assertRaisesRegex(ValueError, "cannot contain a query"):
                    catalog.control(
                        {
                            "action": "station_add",
                            "name": "Secret",
                            "source": "https://radio.example/live?token=never-store",
                        }
                    )
            finally:
                catalog.close()
        self.assertEqual(player.loaded, "https://radio.example/live")
        saved = next(item for item in snapshot["stations"] if item["name"] == "Open Radio")
        self.assertNotIn("stream_url", saved)

    def test_personal_radio_order_drives_enter_and_survives_restart(self) -> None:
        class State:
            def __init__(self, state="stopped", source=None, paused=False):
                self.state = state
                self.source = source
                self.paused = paused
                self.volume = 36

            def as_dict(self):
                return {
                    "state": self.state,
                    "source": self.source,
                    "paused": self.paused,
                    "volume": self.volume,
                }

        class Player:
            def __init__(self):
                self.state = State()
                self.loaded = None

            def load(self, source):
                self.loaded = source
                self.state = State("playing", source, False)

            def toggle_pause(self):
                self.state.paused = not self.state.paused
                self.state.state = "paused" if self.state.paused else "playing"

            def stop(self):
                self.state = State()

            def close(self):
                pass

        class Recorder:
            def __init__(self):
                self.state = State()

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            player = Player()
            catalog = ServiceCatalog(root, player=player, recorder=Recorder())
            stations = catalog.snapshot()["stations"]
            swr3 = next(item for item in stations if item["preset_id"] == "swr3")
            sunshine = next(
                item for item in stations if item["preset_id"] == "sunshine_live"
            )
            catalog.control(
                {
                    "action": "station_move",
                    "station_id": sunshine["id"],
                    "direction": -1,
                }
            )
            catalog.control({"action": "radio_toggle"})
            self.assertEqual(player.loaded, RADIO_BY_ID["sunshine_live"].stream_url)
            catalog.control({"action": "station_delete", "station_id": swr3["id"]})
            catalog.close()

            reopened = ServiceCatalog(root, player=Player(), recorder=Recorder())
            try:
                persisted = reopened.snapshot()["stations"]
            finally:
                reopened.close()

        self.assertEqual(persisted[0]["preset_id"], "sunshine_live")
        self.assertNotIn("swr3", {item["preset_id"] for item in persisted})
        self.assertEqual(len(persisted), 9)

    def test_media_scan_indexes_only_approved_files_and_removes_stale_rows(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            catalog = ServiceCatalog(root)
            media_root = root / "media"
            media_root.mkdir(exist_ok=True)
            audio = media_root / "song.mp3"
            voice = (
                media_root
                / "VoiceRecorder"
                / "261101"
                / "261101_082159_VoiceRecorder.mp3"
            )
            ignored = media_root / "notes.txt"
            audio.write_bytes(b"audio")
            voice.parent.mkdir(parents=True)
            voice.write_bytes(b"voice")
            ignored.write_text("not media", encoding="utf-8")
            try:
                self.assertEqual(catalog.scan_media(), 2)
                snapshot = catalog.snapshot()
                song = next(item for item in snapshot["media"] if item["title"] == "song")
                recorded = next(
                    item for item in snapshot["media"] if item["source_kind"] == "voice"
                )
                self.assertNotIn("path", song)
                self.assertEqual(recorded["folder"], "VoiceRecorder/261101")
                self.assertEqual(
                    recorded["title"], "261101_082159_VoiceRecorder"
                )
                audio.unlink()
                voice.unlink()
                self.assertEqual(catalog.scan_media(), 0)
                self.assertEqual(catalog.snapshot()["media"], [])
            finally:
                catalog.close()

    def test_voice_playback_sync_moves_the_recorder_playhead(self) -> None:
        class Player:
            def __init__(self) -> None:
                self.positions = iter((0.125, 0.275, 0.4))

            def position_seconds(self):
                return next(self.positions)

        class Recorder:
            def __init__(self) -> None:
                self.followed_positions = []
                self.persisted_positions = []

            def voice_follow_playback(self, position_ms):
                self.followed_positions.append(position_ms)

            def voice_set_position(self, position_ms):
                self.persisted_positions.append(position_ms)

        catalog = object.__new__(ServiceCatalog)
        catalog.player = Player()  # type: ignore[assignment]
        catalog.recorder = Recorder()  # type: ignore[assignment]
        catalog._voice_playback_active = True

        catalog._sync_voice_playback_position()
        catalog._sync_voice_playback_position()
        catalog._sync_voice_playback_position(persist=True)

        self.assertEqual(  # type: ignore[attr-defined]
            catalog.recorder.followed_positions,
            [125, 275],
        )
        self.assertEqual(  # type: ignore[attr-defined]
            catalog.recorder.persisted_positions,
            [400],
        )

    def test_voice_recorder_open_stops_playback_and_uses_one_resumable_session(self) -> None:
        class State:
            volume = 30
            state = "stopped"

            def as_dict(self):
                return {"state": self.state, "volume": self.volume}

        class Brandmeister:
            def __init__(self) -> None:
                self.stops = 0

            def stop(self):
                self.stops += 1
                return {"status": "stopped", "volume": 30}

            def snapshot(self):
                return {"status": "stopped", "volume": 30}

            def close(self):
                pass

        class Buffer:
            def __init__(self) -> None:
                self.stops = []

            def stop(self, *, flush=False):
                self.stops.append(flush)

            def snapshot(self):
                return {"state": "stopped"}

            def set_continuous(self, _enabled):
                return self.snapshot()

            def close(self):
                pass

        class AmbientLayer:
            def __init__(self) -> None:
                self.closed = False

            def close(self):
                self.closed = True

        class Player:
            def __init__(self) -> None:
                self.state = State()
                self.stops = 0

            def stop(self):
                self.stops += 1
                self.state.state = "stopped"

            def close(self):
                pass

        class Recorder:
            def __init__(self) -> None:
                self.state = State()
                self.calls = []
                self.snapshot = {
                    "state": "stopped",
                    "continuous": False,
                    "session_active": False,
                    "timeline": [],
                }

            def voice_snapshot(self):
                return dict(self.snapshot)

            def voice_start(self, *, continuous=False):
                self.calls.append(("start", continuous))
                self.snapshot.update(
                    state="recording",
                    continuous=continuous,
                    session_active=True,
                )
                return self.voice_snapshot()

            def voice_pause(self):
                self.calls.append(("pause", False))
                self.snapshot.update(state="paused", continuous=False)
                return self.voice_snapshot()

            def voice_finalize(self):
                self.calls.append(("finalize", False))
                self.snapshot.update(
                    state="stopped", continuous=False, session_active=False
                )
                return self.voice_snapshot()

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as raw:
            player = Player()
            recorder = Recorder()
            brandmeister = Brandmeister()
            buffer = Buffer()
            layer = AmbientLayer()
            catalog = ServiceCatalog(
                Path(raw).resolve(),
                player=player,
                recorder=recorder,
                brandmeister=brandmeister,  # type: ignore[arg-type]
                radio_buffer=buffer,  # type: ignore[arg-type]
            )
            catalog._ambient_layer_players["test"] = layer  # type: ignore[assignment]
            try:
                catalog.control({"action": "voice_recorder_open"})
                open_volume = player.state.volume
                catalog.control({"action": "voice_recorder_hold"})
                catalog.control({"action": "voice_recorder_pause"})
                catalog.control({"action": "voice_recorder_continuous"})
                overlay = catalog.receiver_overlay("REC")
                catalog.control({"action": "voice_recorder_close"})
                restored_volume = player.state.volume
            finally:
                catalog.close()

        self.assertEqual(player.stops, 1)
        self.assertEqual(brandmeister.stops, 1)
        self.assertEqual(buffer.stops, [True])
        self.assertTrue(layer.closed)
        self.assertEqual(open_volume, 100)
        self.assertEqual(restored_volume, 30)
        self.assertEqual(overlay["service"], "REC")
        self.assertTrue(overlay["recording"])
        self.assertTrue(overlay["continuous"])
        self.assertEqual(
            recorder.calls,
            [
                ("start", False),
                ("pause", False),
                ("start", True),
                ("finalize", False),
            ],
        )
