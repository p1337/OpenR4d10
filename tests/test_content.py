from __future__ import annotations

from email.message import Message
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from openr4d10.content import (
    BoundedFetcher,
    CameraSnapshot,
    ContentError,
    FeedReader,
    PresetArtwork,
    validate_content_url,
)


class FakeResponse:
    def __init__(self, payload: bytes, content_type: str) -> None:
        self.payload = payload
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["Content-Length"] = str(len(payload))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, amount: int) -> bytes:
        return self.payload[:amount]


class ContentTests(unittest.TestCase):
    def test_feed_parser_supports_rss_and_removes_markup(self) -> None:
        payload = b"""<?xml version='1.0'?>
        <rss><channel><title>Open Feed</title><item>
        <title>News</title><link>https://example.test/news</link>
        <description>&lt;b&gt;Safe&lt;/b&gt; summary</description>
        <pubDate>today</pubDate></item></channel></rss>"""
        feed = FeedReader.parse(payload)
        self.assertEqual(feed["title"], "Open Feed")
        self.assertEqual(feed["item_count"], 1)
        self.assertEqual(feed["items"][0]["summary"], "Safe summary")

    def test_bounded_fetcher_rejects_credentials_type_and_size(self) -> None:
        with self.assertRaises(ValueError):
            validate_content_url("https://user:pass@example.test/feed")
        fetcher = BoundedFetcher(
            lambda *_args, **_kwargs: FakeResponse(b"not xml", "text/html")
        )
        with self.assertRaises(ContentError):
            fetcher.fetch(
                "https://example.test/feed",
                max_bytes=100,
                accepted_types=("application/xml",),
            )

    def test_camera_image_is_decoded_and_reencoded_inside_cache(self) -> None:
        raw = BytesIO()
        Image.new("RGB", (800, 600), (10, 20, 30)).save(raw, format="PNG")
        fetcher = BoundedFetcher(
            lambda *_args, **_kwargs: FakeResponse(raw.getvalue(), "image/png")
        )
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory).resolve()
            result = CameraSnapshot(cache, fetcher).fetch(
                "https://camera.example/snapshot.png",
                slot=2,
            )
            output = cache / result["file"]
            self.assertTrue(output.is_file())
            with Image.open(output) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertLessEqual(image.width, 640)
                self.assertLessEqual(image.height, 480)

    def test_preset_artwork_is_bounded_reencoded_and_cached(self) -> None:
        raw = BytesIO()
        Image.new("RGBA", (500, 300), (20, 120, 180, 180)).save(raw, format="PNG")
        calls = []

        def opener(*args, **kwargs):
            calls.append((args, kwargs))
            return FakeResponse(raw.getvalue(), "image/png")

        fetcher = BoundedFetcher(opener)
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory).resolve()
            artwork = PresetArtwork(cache, fetcher)
            first = artwork.ensure("test_radio", "https://radio.example/logo.png")
            second = artwork.ensure("test_radio", "https://radio.example/logo.png")
            self.assertEqual(first, second)
            self.assertEqual(len(calls), 1)
            with Image.open(first) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertLessEqual(image.width, 256)
                self.assertLessEqual(image.height, 256)
