from __future__ import annotations

import os
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

from openr4d10.services import BUILTIN_SERVICES, ServiceCatalog
from openr4d10.presets import FEED_BY_ID, RADIO_BY_ID
from openr4d10.storage import SCHEMA_VERSION, StateStore


class StateStoreTests(unittest.TestCase):
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

    def test_curated_presets_are_public_without_remote_content_urls(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            catalog = ServiceCatalog(Path(raw).resolve())
            try:
                presets = catalog.snapshot()["presets"]
            finally:
                catalog.close()
        station_ids = {item["preset_id"] for item in presets["stations"]}
        self.assertEqual(station_ids, set(RADIO_BY_ID))
        self.assertTrue({"swr3", "sunshine_live", "deutschlandfunk", "rmf_fm", "radio_zet", "bbc_world"}.issubset(station_ids))
        for item in presets["stations"]:
            self.assertNotIn("stream_url", item)
            self.assertNotIn("artwork_url", item)
            self.assertTrue(item["artwork"].startswith("/api/radio-art/"))
        for item in presets["feeds"]:
            self.assertNotIn("feed_url", item)
        for item in RADIO_BY_ID.values():
            parsed = urlsplit(item.stream_url)
            self.assertEqual(parsed.scheme, "https")
            self.assertIsNone(parsed.username)
            self.assertFalse(parsed.query)
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
        self.assertEqual(len(stations), len(RADIO_BY_ID))

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

    def test_catalog_covers_documented_services_without_claiming_credentials(self) -> None:
        available = {"mpv": "/usr/bin/mpv", "ffmpeg": "/usr/bin/ffmpeg"}
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
            "speech", "codex_remote",
        }
        self.assertTrue(expected.issubset(items))
        self.assertEqual(len(items), len(BUILTIN_SERVICES))
        self.assertEqual(items["webradio"]["readiness"], "ready")
        self.assertEqual(items["brandmeister"]["readiness"], "disabled")
        self.assertNotIn("credential", items["brandmeister"])

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
                    state="stopped", source=None, paused=False, volume=36
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
        self.assertEqual(volume["playback"]["volume"], 76)
        self.assertFalse(paused_overlay["playing"])

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
        self.assertEqual(len(persisted), len(RADIO_BY_ID) - 1)

    def test_media_scan_indexes_only_approved_files_and_removes_stale_rows(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            catalog = ServiceCatalog(root)
            media_root = root / "media"
            media_root.mkdir()
            audio = media_root / "song.mp3"
            ignored = media_root / "notes.txt"
            audio.write_bytes(b"audio")
            ignored.write_text("not media", encoding="utf-8")
            try:
                self.assertEqual(catalog.scan_media(), 1)
                snapshot = catalog.snapshot()
                self.assertEqual(snapshot["media"][0]["title"], "song")
                self.assertNotIn("path", snapshot["media"][0])
                audio.unlink()
                self.assertEqual(catalog.scan_media(), 0)
                self.assertEqual(catalog.snapshot()["media"], [])
            finally:
                catalog.close()
