from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from openr4d10.ambient import AMBIENT_PRESETS, ambient_text
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
                self.assertTrue(item.source_page.startswith("https://commons.wikimedia.org/"))
                self.assertTrue(item.license_url.startswith("https://"))
                self.assertNotIn("audio_url", item.public())

    def test_device_text_is_localized_without_renaming_custom_scenes(self) -> None:
        self.assertEqual(ambient_text("forest", "de"), ("Wald", "Wald, Wind, Vögel und ferne Insekten"))
        self.assertIsNone(ambient_text("custom-example", "de"))


class AmbientServiceTests(unittest.TestCase):
    def test_scenes_are_persistent_and_play_only_on_explicit_action(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            player = Player()
            catalog = ServiceCatalog(root, player=player, recorder=Recorder())
            try:
                snapshot = catalog.snapshot()["ambient"]
                self.assertEqual(len(snapshot["scenes"]), 6)
                self.assertNotIn("source_url", snapshot["scenes"][0])
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
