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
    DWD_RADAR_GIF_URL,
    DwdSatelliteFrames,
    FeedReader,
    PodcastReader,
    PresetArtwork,
    TrackArtwork,
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
    def test_track_artwork_uses_high_score_release_and_reencodes_cover(self) -> None:
        raw = BytesIO()
        Image.new("RGB", (600, 600), (80, 20, 120)).save(raw, format="PNG")
        calls = []

        class Fetcher:
            def fetch(self, url, **_kwargs):
                calls.append(url)
                if "musicbrainz.org" in url:
                    return (
                        b'{"recordings":[{"score":98,"releases":[{"id":"12345678-1234-1234-1234-123456789abc"}]}]}',
                        "application/json",
                    )
                if "coverartarchive.org/release" in url:
                    return (
                        b'{"images":[{"front":true,"approved":true,"thumbnails":{"250":"https://images.example/cover.png"}}]}',
                        "application/json",
                    )
                return raw.getvalue(), "image/png"

        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory).resolve()
            artwork = TrackArtwork(cache, Fetcher())
            artwork._last_request = -100
            result = artwork.ensure(7, "Artist", "Song")
            self.assertEqual(result.name, "track-7.jpg")
            with Image.open(result) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertLessEqual(image.width, 512)
            self.assertEqual(len(calls), 3)

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

    def test_podcast_parser_keeps_only_safe_audio_enclosures(self) -> None:
        payload = b"""<?xml version='1.0'?>
        <rss><channel><title>Open Podcast</title><description>Science show</description>
        <link>https://example.test/show</link><item><title>Episode 1</title>
        <guid>episode-one</guid><pubDate>today</pubDate><itunes:duration xmlns:itunes='urn:itunes'>12:34</itunes:duration>
        <description>&lt;b&gt;Safe&lt;/b&gt; episode</description>
        <enclosure url='https://media.example.test/one.mp3' type='audio/mpeg'/></item>
        <item><title>Video</title><enclosure url='https://media.example.test/video.mp4' type='video/mp4'/></item>
        </channel></rss>"""
        podcast = PodcastReader.parse(payload)
        self.assertEqual(podcast["title"], "Open Podcast")
        self.assertEqual(podcast["episode_count"], 1)
        self.assertEqual(podcast["episodes"][0]["summary"], "Safe episode")
        self.assertEqual(
            podcast["episodes"][0]["enclosure_url"],
            "https://media.example.test/one.mp3",
        )

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

    def test_mjpeg_and_rtsp_camera_frames_are_bounded_and_reencoded(self) -> None:
        raw = BytesIO()
        Image.new("RGB", (320, 240), (30, 50, 70)).save(raw, format="JPEG")
        jpeg = raw.getvalue()
        mjpeg = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
        fetcher = BoundedFetcher(
            lambda *_args, **_kwargs: FakeResponse(
                mjpeg, "multipart/x-mixed-replace; boundary=frame"
            )
        )

        class Result:
            returncode = 0
            stdout = jpeg
            stderr = b""

        commands = []

        def runner(command, **_kwargs):
            commands.append(command)
            return Result()

        with tempfile.TemporaryDirectory() as directory:
            camera = CameraSnapshot(Path(directory).resolve(), fetcher, runner)
            mjpeg_result = camera.fetch(
                "https://camera.example/live.mjpg", 7, kind="mjpeg"
            )
            rtsp_result = camera.fetch(
                "rtsp://camera.example/live", 8, kind="rtsp"
            )
            self.assertEqual(mjpeg_result["kind"], "mjpeg")
            self.assertEqual(rtsp_result["kind"], "rtsp")
            self.assertEqual(commands[0][0], "/usr/bin/ffmpeg")
            self.assertNotIn("shell", commands[0])
            self.assertTrue((Path(directory) / "camera-7.jpg").is_file())
            self.assertTrue((Path(directory) / "camera-8.jpg").is_file())
            with self.assertRaises(ValueError):
                camera.fetch("rtsp://user:secret@camera.example/live", 9, kind="rtsp")

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

    def test_dwd_satellite_frames_are_bounded_reencoded_and_rate_limited(self) -> None:
        capabilities = b"""<?xml version='1.0'?>
        <WMS_Capabilities><Capability><Layer><Layer>
          <Name>Satellite_meteosat_1km_euat_rgb_day_hrv_and_night_ir108_3h</Name>
          <Dimension name='time'>2026-10-30T09:00:00.000Z/2026-10-31T06:00:00.000Z/PT3H</Dimension>
        </Layer></Layer></Capability></WMS_Capabilities>"""
        raw = BytesIO()
        Image.new("RGB", (480, 360), (45, 80, 120)).save(raw, format="PNG")
        calls = []

        def opener(request, **_kwargs):
            calls.append(request.full_url)
            if "GetCapabilities" in request.full_url:
                return FakeResponse(capabilities, "text/xml")
            self.assertIn("request=GetMap", request.full_url)
            self.assertIn("bbox=47%2C5%2C55.5%2C16", request.full_url)
            return FakeResponse(raw.getvalue(), "image/png")

        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory).resolve()
            weather = DwdSatelliteFrames(cache, BoundedFetcher(opener))
            first = weather.refresh("dwd-deutschland", (47, 5, 55.5, 16))
            second = weather.refresh("dwd-deutschland", (47, 5, 55.5, 16))
            self.assertEqual(first, second)
            self.assertEqual(len(first), 8)
            self.assertEqual(len(calls), 9)
            with Image.open(cache / str(first[0]["file"])) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertLessEqual(image.width, 480)

    def test_dwd_radar_gif_is_bounded_reencoded_and_rate_limited(self) -> None:
        raw = BytesIO()
        frames = [
            Image.new("RGB", (680, 680), (index * 15, 40, 120))
            for index in range(10)
        ]
        frames[0].save(
            raw,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=500,
            loop=0,
        )
        calls = []

        def opener(request, **_kwargs):
            calls.append(request.full_url)
            self.assertEqual(request.full_url, DWD_RADAR_GIF_URL)
            return FakeResponse(raw.getvalue(), "image/gif")

        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory).resolve()
            weather = DwdSatelliteFrames(cache, BoundedFetcher(opener))
            first = weather.refresh_radar("dwd-deutschland")
            second = weather.refresh_radar("dwd-deutschland")
            self.assertEqual(first, second)
            self.assertEqual(len(first), 8)
            self.assertEqual(len(calls), 1)
            with Image.open(cache / str(first[0]["file"])) as image:
                self.assertEqual(image.format, "JPEG")
                self.assertLessEqual(image.width, 480)
                self.assertLessEqual(image.height, 480)
