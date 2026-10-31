from pathlib import Path
import tempfile
import unittest

from openr4d10.radio_capture import (
    IcyRadioBuffer,
    parse_icy_metadata,
    split_stream_title,
)
from openr4d10.storage import StateStore


class RadioCaptureTests(unittest.TestCase):
    def test_icy_metadata_is_bounded_and_split_without_guessing(self) -> None:
        self.assertEqual(
            parse_icy_metadata(b"StreamTitle='The Artist - The Song';\0\0"),
            "The Artist - The Song",
        )
        self.assertEqual(
            split_stream_title("The Artist - The Song"),
            ("The Artist", "The Song"),
        )
        self.assertEqual(split_stream_title("Station announcement"), (None, None))

    def test_ptt_keeps_the_buffered_beginning_at_the_next_title_boundary(self) -> None:
        saved = []
        buffer = IcyRadioBuffer(lambda track: saved.append(track) is None, max_track_bytes=64 * 1024)
        buffer.state.state = "buffering"
        buffer._metadata("Artist - First")
        beginning = b"a" * (64 * 1024)
        buffer._append_audio(beginning)
        buffer.keep_current()
        buffer._metadata("Artist - Second")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].payload, beginning)
        self.assertEqual(saved[0].artist, "Artist")
        self.assertEqual(saved[0].title, "First")
        self.assertEqual(buffer.snapshot()["title"], "Second")

    def test_continuous_mode_splits_tracks_and_bounds_memory(self) -> None:
        saved = []
        buffer = IcyRadioBuffer(lambda track: saved.append(track) is None, max_track_bytes=64 * 1024)
        buffer.state.state = "buffering"
        buffer.set_continuous(True)
        buffer._metadata("Artist - First")
        buffer._append_audio(b"x" * (80 * 1024))
        self.assertEqual(buffer.snapshot()["buffered_bytes"], 64 * 1024)
        buffer._metadata("Artist - Second")
        self.assertEqual(len(saved), 1)
        self.assertTrue(saved[0].truncated)


class RecordedMediaStorageTests(unittest.TestCase):
    def test_recorded_media_is_sorted_favorited_deduplicated_and_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            store = StateStore(root / "state.sqlite3")
            first = root / "Artist" / "Artist – Song.mp3"
            first.parent.mkdir()
            first.write_bytes(b"audio")
            media_id = store.add_recorded_media(
                first,
                artist="Artist",
                title="Song",
                size_bytes=5,
                checksum="checksum",
                normalized_key="artistsong",
                fingerprint="fingerprint",
                review_required=False,
            )
            self.assertEqual(store.media_duplicate("artistsong", None, None)["id"], media_id)
            self.assertTrue(store.set_media_favorite(media_id, True))
            self.assertTrue(store.media_item(media_id)["favorite"])
            deleted = store.delete_media(media_id)
            self.assertEqual(deleted["path"], str(first))
            self.assertIsNone(store.media_item(media_id))
            store.close()
