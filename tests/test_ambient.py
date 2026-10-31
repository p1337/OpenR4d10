from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from openr4d10.ambient import (
    AMBIENT_ARTWORK_ROOT,
    AMBIENT_BY_ID,
    AMBIENT_PRESETS,
    ambient_text,
)
from openr4d10.media import PlaybackState
from openr4d10.services import ServiceCatalog


class Player:
    def __init__(self) -> None:
        self.state = PlaybackState()
        self.playlists: list[tuple[list[str], bool, bool]] = []

    def load_playlist(self, sources, *, shuffle=False, loop=False) -> None:
        self.playlists.append((list(sources), shuffle, loop))
        self.state = PlaybackState("playing", str(sources[0]), self.state.volume)

    def toggle_pause(self) -> None:
        self.state.paused = not self.state.paused
        self.state.state = "paused" if self.state.paused else "playing"

    def stop(self) -> None:
        self.state = PlaybackState(volume=self.state.volume)

    def close(self) -> None:
        pass


class Recorder:
    def __init__(self) -> None:
        self.state = PlaybackState()

    def stop(self) -> None:
        self.state = PlaybackState()

    def close(self) -> None:
        pass


class AmbientPresetTests(unittest.TestCase):
    def test_presets_have_public_https_sources_and_documented_licenses(self) -> None:
        self.assertEqual(
            {item.preset_id for item in AMBIENT_PRESETS},
            {"cafe", "forest", "beach", "brook", "rain", "night_crickets"},
        )
        for item in AMBIENT_PRESETS:
            with self.subTest(item.preset_id):
                self.assertTrue(item.audio_url.startswith("https://"))
                self.assertTrue(
                    item.audio_url.startswith("https://upload.wikimedia.org/")
                    or item.audio_url.startswith("https://cdn.freesound.org/")
                )
                self.assertNotIn("?", item.audio_url)
                self.assertTrue(
                    item.source_page.startswith("https://commons.wikimedia.org/")
                    or item.source_page.startswith("https://freesound.org/")
                )
                self.assertTrue(item.license_url.startswith("https://"))
                self.assertNotIn("audio_url", item.public())
                self.assertEqual(
                    item.public()["artwork"], f"/api/ambient-art/{item.preset_id}"
                )

    def test_each_preset_has_a_readable_bundled_square_artwork(self) -> None:
        for item in AMBIENT_PRESETS:
            with self.subTest(item.preset_id):
                path = AMBIENT_ARTWORK_ROOT / f"{item.preset_id}.jpg"
                with Image.open(path) as artwork:
                    self.assertEqual(artwork.format, "JPEG")
                    self.assertEqual(artwork.size, (768, 768))

    def test_device_text_is_localized_without_renaming_custom_scenes(self) -> None:
        self.assertEqual(ambient_text("forest", "de"), ("Wald", "Wald, Wind, Vögel und ferne Insekten"))
        self.assertIsNone(ambient_text("custom-example", "de"))

    def test_cafe_uses_the_quiet_cc0_coffeehouse_recording(self) -> None:
        cafe = AMBIENT_BY_ID["cafe"]
        self.assertEqual(
            cafe.audio_url,
            "https://cdn.freesound.org/previews/46/46310_43834-lq.ogg",
        )
        self.assertEqual(cafe.credit, "moxobna")
        self.assertEqual(cafe.license_name, "CC0 1.0")
        self.assertEqual(
            cafe.sha256,
            "86c51e4fa5001c4fbf597c8725b50e36a347c31fbc0c499cad0a1bc27e9bb072",
        )


class AmbientServiceTests(unittest.TestCase):
    def test_redirect_sources_migrate_without_recreating_deleted_scenes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            catalog = ServiceCatalog(root, player=Player(), recorder=Recorder())
            first = catalog.store.channels("ambient")[0]
            metadata = dict(first["metadata"])
            metadata["source_url"] = (
                "https://commons.wikimedia.org/wiki/Special:Redirect/file/"
                "Cafe_ambiance.ogg"
            )
            catalog.store.update_channel(first["id"], first["name"], metadata)
            catalog.store.set_setting("ambient.direct_sources_v1", False)
            deleted = catalog.store.channels("ambient")[1]
            catalog.store.delete_channel(deleted["id"])
            catalog.close()

            reopened = ServiceCatalog(root, player=Player(), recorder=Recorder())
            try:
                scenes = reopened.store.channels("ambient")
                migrated = next(item for item in scenes if item["id"] == first["id"])
                self.assertEqual(
                    migrated["metadata"]["source_url"],
                    AMBIENT_BY_ID[str(migrated["external_id"])].audio_url,
                )
                self.assertNotIn(deleted["id"], {item["id"] for item in scenes})
            finally:
                reopened.close()

    def test_scenes_are_persistent_and_play_only_on_explicit_action(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            player = Player()
            catalog = ServiceCatalog(root, player=player, recorder=Recorder())
            try:
                snapshot = catalog.snapshot()["ambient"]
                self.assertEqual(len(snapshot["scenes"]), 6)
                self.assertNotIn("source_url", snapshot["scenes"][0])
                self.assertEqual(
                    snapshot["scenes"][0]["artwork"], "/api/ambient-art/cafe"
                )
                first, second = snapshot["scenes"][:2]
                catalog.control({"action": "ambient_step", "steps": 1})
                self.assertEqual(player.playlists, [])
                catalog.control({"action": "ambient_play", "scene_id": second["id"]})
                self.assertEqual(player.playlists[-1][1:], (False, True))
                self.assertEqual(catalog.active_service, "ambient")
                catalog.control({"action": "ambient_toggle"})
                self.assertTrue(player.state.paused)
                custom = catalog.control(
                    {
                        "action": "ambient_scene_save",
                        "name": "My waves",
                        "source": "https://example.org/waves.ogg",
                    }
                )
                catalog.control({"action": "ambient_scene_delete", "scene_id": first["id"]})
                custom_id = custom["scene_id"]
            finally:
                catalog.close()

            reopened = ServiceCatalog(root, player=Player(), recorder=Recorder())
            try:
                scenes = reopened.snapshot()["ambient"]["scenes"]
                self.assertIn(custom_id, {item["id"] for item in scenes})
                self.assertNotIn(first["preset_id"], {item["preset_id"] for item in scenes})
            finally:
                reopened.close()

    def test_channel_browsing_keeps_the_selected_scene_visible(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            player = Player()
            catalog = ServiceCatalog(
                Path(raw).resolve(), player=player, recorder=Recorder()
            )
            try:
                first, second = catalog.snapshot()["ambient"]["scenes"][:2]
                catalog.control({"action": "ambient_play", "scene_id": first["id"]})
                catalog.control({"action": "ambient_step", "steps": 1})

                selected = catalog.receiver_overlay("AMBIENT")
                self.assertEqual(selected["channel"], 2)
                self.assertEqual(selected["preset_id"], second["preset_id"])
                self.assertFalse(selected["playing"])
                self.assertEqual(catalog.active_ambient_scene_id, first["id"])
                self.assertEqual(len(player.playlists), 1)

                catalog.control({"action": "ambient_toggle"})
                active = catalog.receiver_overlay("AMBIENT")
                self.assertEqual(active["channel"], 2)
                self.assertTrue(active["playing"])
                self.assertEqual(catalog.active_ambient_scene_id, second["id"])
                self.assertEqual(len(player.playlists), 2)
            finally:
                catalog.close()

    def test_old_cafe_source_is_migrated_without_overwriting_custom_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            catalog = ServiceCatalog(root, player=Player(), recorder=Recorder())
            cafe = next(
                item
                for item in catalog.store.channels("ambient")
                if item["external_id"] == "cafe"
            )
            old_metadata = dict(cafe["metadata"])
            old_metadata.update(
                {
                    "source_url": (
                        "https://upload.wikimedia.org/wikipedia/commons/5/54/"
                        "Cafe_ambiance.ogg"
                    ),
                    "source_page": (
                        "https://commons.wikimedia.org/wiki/File:Cafe_ambiance.ogg"
                    ),
                    "credit": "Marble Toast",
                }
            )
            catalog.store.update_channel(cafe["id"], cafe["name"], old_metadata)
            catalog.store.set_setting("ambient.quiet_cafe_v1", False)
            catalog.close()

            reopened = ServiceCatalog(root, player=Player(), recorder=Recorder())
            try:
                migrated = next(
                    item
                    for item in reopened.store.channels("ambient")
                    if item["external_id"] == "cafe"
                )
                self.assertEqual(
                    migrated["metadata"]["source_url"],
                    AMBIENT_BY_ID["cafe"].audio_url,
                )
                self.assertEqual(migrated["metadata"]["credit"], "moxobna")
                self.assertEqual(
                    migrated["metadata"]["sha256"], AMBIENT_BY_ID["cafe"].sha256
                )
            finally:
                reopened.close()

            custom_source = "https://example.org/my-quiet-cafe.ogg"
            third = ServiceCatalog(root, player=Player(), recorder=Recorder())
            cafe = next(
                item
                for item in third.store.channels("ambient")
                if item["external_id"] == "cafe"
            )
            custom_metadata = dict(cafe["metadata"])
            custom_metadata["source_url"] = custom_source
            third.store.update_channel(cafe["id"], cafe["name"], custom_metadata)
            third.store.set_setting("ambient.quiet_cafe_v1", False)
            third.close()

            final = ServiceCatalog(root, player=Player(), recorder=Recorder())
            try:
                preserved = next(
                    item
                    for item in final.store.channels("ambient")
                    if item["external_id"] == "cafe"
                )
                self.assertEqual(preserved["metadata"]["source_url"], custom_source)
            finally:
                final.close()

    def test_bundled_artwork_is_served_only_for_known_presets(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            artwork_root = root / "artwork"
            artwork_root.mkdir()
            artwork_root.joinpath("cafe.jpg").write_bytes(b"cafe-art")
            catalog = ServiceCatalog(
                root,
                player=Player(),
                recorder=Recorder(),
                ambient_artwork_root=artwork_root,
            )
            try:
                self.assertEqual(
                    catalog.content_asset("ambient-art/cafe"),
                    ("image/jpeg", b"cafe-art"),
                )
                self.assertIsNone(catalog.content_asset("ambient-art/custom-example"))
            finally:
                catalog.close()

    def test_custom_scene_rejects_query_bearing_urls(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            catalog = ServiceCatalog(Path(raw).resolve(), player=Player(), recorder=Recorder())
            try:
                with self.assertRaisesRegex(ValueError, "query"):
                    catalog.control(
                        {
                            "action": "ambient_scene_save",
                            "name": "Unsafe tokenized link",
                            "source": "https://example.org/sound.ogg?token=secret",
                        }
                    )
            finally:
                catalog.close()


if __name__ == "__main__":
    unittest.main()
