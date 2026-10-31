"""Bounded RSS/Atom and camera content retrieval for local service modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import hashlib
from html import unescape
from io import BytesIO
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from PIL import Image, ImageOps, UnidentifiedImageError


class ContentError(RuntimeError):
    pass


def validate_content_url(url: str) -> str:
    if not isinstance(url, str) or not url or len(url) > 4096:
        raise ValueError("content URL must be a non-empty string")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("content URL must use http or https")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("credentials must not be embedded in a content URL")
    return url


ResponseOpener = Callable[..., Any]


class BoundedFetcher:
    def __init__(self, opener: ResponseOpener = urlopen) -> None:
        self.opener = opener

    def fetch(
        self,
        url: str,
        *,
        max_bytes: int,
        accepted_types: tuple[str, ...],
        timeout: float = 8.0,
    ) -> tuple[bytes, str]:
        approved = validate_content_url(url)
        request = Request(
            approved,
            headers={
                "User-Agent": "OpenR4d10 (+https://github.com/p1337/OpenR4d10)",
                "Accept": ", ".join(accepted_types),
            },
        )
        try:
            with self.opener(request, timeout=timeout) as response:
                content_type = response.headers.get_content_type().lower()
                if not any(
                    content_type == item or (item.endswith("/*") and content_type.startswith(item[:-1]))
                    for item in accepted_types
                ):
                    raise ContentError(f"unexpected content type: {content_type}")
                declared = response.headers.get("Content-Length")
                if declared is not None and int(declared) > max_bytes:
                    raise ContentError("remote content exceeds the size limit")
                payload = response.read(max_bytes + 1)
        except ContentError:
            raise
        except (OSError, ValueError) as exc:
            raise ContentError(f"content request failed: {exc}") from exc
        if len(payload) > max_bytes:
            raise ContentError("remote content exceeds the size limit")
        return payload, content_type


class AmbientAudioCache:
    """Checksum-verified local cache for reviewed AmbientR4D10 recordings."""

    MAX_BYTES = 64 * 1024 * 1024

    def __init__(self, cache_root: Path, fetcher: BoundedFetcher | None = None) -> None:
        if not cache_root.is_absolute():
            raise ValueError("ambient audio cache path must be absolute")
        self.cache_root = cache_root
        self.fetcher = fetcher or BoundedFetcher()
        self._lock = threading.Lock()
        self._verified: dict[Path, tuple[int, int]] = {}

    @staticmethod
    def _identity(preset_id: str, checksum: str) -> tuple[str, str]:
        if re.fullmatch(r"[a-z][a-z0-9_]{1,63}", preset_id) is None:
            raise ValueError("ambient preset id is invalid")
        normalized = checksum.casefold()
        if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
            raise ValueError("ambient audio checksum must be SHA-256")
        return preset_id, normalized

    def path(self, preset_id: str, checksum: str) -> Path:
        preset_id, checksum = self._identity(preset_id, checksum)
        return self.cache_root / f"{preset_id}-{checksum[:12]}.ogg"

    def cached(self, preset_id: str, checksum: str) -> Path | None:
        target = self.path(preset_id, checksum)
        with self._lock:
            try:
                stat = target.stat()
                signature = (stat.st_size, stat.st_mtime_ns)
                if stat.st_size <= 0 or not target.is_file():
                    return None
                if self._verified.get(target) == signature:
                    return target
                if self._file_sha256(target) == checksum.casefold():
                    self._verified[target] = signature
                    return target
                self._verified.pop(target, None)
                target.unlink(missing_ok=True)
            except OSError:
                return None
        return None

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def ensure(self, preset_id: str, url: str, checksum: str) -> Path:
        preset_id, checksum = self._identity(preset_id, checksum)
        target = self.path(preset_id, checksum)
        with self._lock:
            if target.is_file():
                digest = self._file_sha256(target)
                if digest == checksum:
                    stat = target.stat()
                    self._verified[target] = (stat.st_size, stat.st_mtime_ns)
                    return target
                target.unlink(missing_ok=True)
            payload, _content_type = self.fetcher.fetch(
                url,
                max_bytes=self.MAX_BYTES,
                accepted_types=("audio/ogg", "application/ogg", "audio/*"),
                timeout=600.0,
            )
            if hashlib.sha256(payload).hexdigest() != checksum:
                raise ContentError("ambient audio checksum does not match")
            self.cache_root.mkdir(parents=True, exist_ok=True, mode=0o750)
            temporary = target.with_name(
                f".{target.name}.{os.getpid()}.{threading.get_ident()}.part"
            )
            try:
                with temporary.open("xb") as output:
                    output.write(payload)
                    output.flush()
                    os.fsync(output.fileno())
                temporary.chmod(0o640)
                os.replace(temporary, target)
                stat = target.stat()
                self._verified[target] = (stat.st_size, stat.st_mtime_ns)
            finally:
                temporary.unlink(missing_ok=True)
            for stale in self.cache_root.glob(f"{preset_id}-*.ogg"):
                if stale != target:
                    stale.unlink(missing_ok=True)
            return target


_TAGS = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def _plain_text(value: str | None, limit: int) -> str:
    text = unescape(_TAGS.sub(" ", value or ""))
    return _SPACE.sub(" ", text).strip()[:limit]


def _child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in node:
        local_name = child.tag.rsplit("}", 1)[-1].lower()
        if local_name in names and child.text:
            return child.text
    return ""


@dataclass(frozen=True, slots=True)
class FeedItem:
    title: str
    link: str
    summary: str
    published: str


class FeedReader:
    def __init__(self, fetcher: BoundedFetcher | None = None) -> None:
        self.fetcher = fetcher or BoundedFetcher()

    @staticmethod
    def parse(payload: bytes) -> dict[str, object]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise ContentError(f"invalid feed XML: {exc}") from exc
        channel = next(
            (node for node in root.iter() if node.tag.rsplit("}", 1)[-1].lower() == "channel"),
            root,
        )
        feed_title = _plain_text(_child_text(channel, ("title",)), 160)
        items: list[FeedItem] = []
        for node in root.iter():
            kind = node.tag.rsplit("}", 1)[-1].lower()
            if kind not in {"item", "entry"}:
                continue
            link = _child_text(node, ("link",))
            if not link:
                link_node = next(
                    (child for child in node if child.tag.rsplit("}", 1)[-1].lower() == "link"),
                    None,
                )
                if link_node is not None:
                    link = link_node.attrib.get("href", "")
            items.append(
                FeedItem(
                    title=_plain_text(_child_text(node, ("title",)), 240),
                    link=link[:2048],
                    summary=_plain_text(_child_text(node, ("description", "summary", "content")), 500),
                    published=_plain_text(_child_text(node, ("pubdate", "published", "updated")), 80),
                )
            )
            if len(items) >= 50:
                break
        return {
            "title": feed_title or "Feed",
            "item_count": len(items),
            "items": [asdict(item) for item in items],
        }

    def fetch(self, url: str) -> dict[str, object]:
        payload, _content_type = self.fetcher.fetch(
            url,
            max_bytes=2 * 1024 * 1024,
            accepted_types=(
                "application/rss+xml",
                "application/atom+xml",
                "application/xml",
                "text/xml",
            ),
        )
        return self.parse(payload)


@dataclass(frozen=True, slots=True)
class PodcastEpisode:
    title: str
    summary: str
    published: str
    duration: str
    guid: str
    enclosure_url: str
    enclosure_type: str


class PodcastReader:
    """Read bounded public podcast feeds and retain only playable enclosures."""

    def __init__(self, fetcher: BoundedFetcher | None = None) -> None:
        self.fetcher = fetcher or BoundedFetcher()

    @staticmethod
    def _link(node: ET.Element, *, enclosure: bool = False) -> tuple[str, str]:
        for child in node:
            local_name = child.tag.rsplit("}", 1)[-1].lower()
            if enclosure and local_name in {"enclosure", "content"}:
                url = child.attrib.get("url", "")
                media_type = child.attrib.get("type", "")
                if url and (not media_type or media_type.startswith("audio/")):
                    return url, media_type
            if local_name == "link":
                relation = child.attrib.get("rel", "alternate").lower()
                href = child.attrib.get("href", "")
                if enclosure and relation == "enclosure":
                    media_type = child.attrib.get("type", "")
                    if href and (not media_type or media_type.startswith("audio/")):
                        return href, media_type
                if not enclosure and relation in {"", "alternate"}:
                    return href or (child.text or ""), child.attrib.get("type", "")
        return "", ""

    @staticmethod
    def parse(payload: bytes) -> dict[str, object]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise ContentError(f"invalid podcast XML: {exc}") from exc
        channel = next(
            (node for node in root.iter() if node.tag.rsplit("}", 1)[-1].lower() == "channel"),
            root,
        )
        title = _plain_text(_child_text(channel, ("title",)), 160) or "Podcast"
        description = _plain_text(
            _child_text(channel, ("description", "subtitle", "summary")), 500
        )
        homepage, _homepage_type = PodcastReader._link(channel)
        episodes: list[PodcastEpisode] = []
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1].lower() not in {"item", "entry"}:
                continue
            enclosure_url, enclosure_type = PodcastReader._link(node, enclosure=True)
            if not enclosure_url:
                continue
            try:
                enclosure_url = validate_content_url(enclosure_url)
            except ValueError:
                continue
            guid = _plain_text(_child_text(node, ("guid", "id")), 512)
            episodes.append(
                PodcastEpisode(
                    title=_plain_text(_child_text(node, ("title",)), 240) or "Untitled episode",
                    summary=_plain_text(
                        _child_text(node, ("description", "summary", "content", "subtitle")),
                        800,
                    ),
                    published=_plain_text(
                        _child_text(node, ("pubdate", "published", "updated")), 80
                    ),
                    duration=_plain_text(_child_text(node, ("duration",)), 32),
                    guid=guid or enclosure_url,
                    enclosure_url=enclosure_url,
                    enclosure_type=enclosure_type[:80],
                )
            )
            if len(episodes) >= 50:
                break
        if not episodes:
            raise ContentError("podcast feed contains no playable audio episodes")
        if homepage:
            try:
                homepage = validate_content_url(homepage)
            except ValueError:
                homepage = ""
        return {
            "title": title,
            "description": description,
            "homepage": homepage,
            "episode_count": len(episodes),
            "episodes": [asdict(item) for item in episodes],
        }

    def fetch(self, url: str) -> dict[str, object]:
        payload, _content_type = self.fetcher.fetch(
            url,
            max_bytes=3 * 1024 * 1024,
            accepted_types=(
                "application/rss+xml",
                "application/atom+xml",
                "application/xml",
                "text/xml",
            ),
            timeout=10,
        )
        return self.parse(payload)


class CameraSnapshot:
    def __init__(self, cache_root: Path, fetcher: BoundedFetcher | None = None) -> None:
        if not cache_root.is_absolute():
            raise ValueError("camera cache path must be absolute")
        self.cache_root = cache_root
        self.fetcher = fetcher or BoundedFetcher()

    def fetch(self, url: str, slot: int = 1) -> dict[str, object]:
        if slot not in {1, 2}:
            raise ValueError("camera slot must be 1 or 2")
        payload, content_type = self.fetcher.fetch(
            url,
            max_bytes=5 * 1024 * 1024,
            accepted_types=("image/*",),
        )
        try:
            with Image.open(BytesIO(payload)) as source:
                if source.width * source.height > 40_000_000:
                    raise ContentError("camera image dimensions exceed the safety limit")
                source.verify()
            with Image.open(BytesIO(payload)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((640, 480), Image.Resampling.LANCZOS)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ContentError(f"invalid camera image: {exc}") from exc
        self.cache_root.mkdir(parents=True, exist_ok=True, mode=0o750)
        output = self.cache_root / f"camera-{slot}.jpg"
        encoded = BytesIO()
        image.save(encoded, format="JPEG", quality=88, optimize=True)
        temporary = output.with_suffix(".jpg.tmp")
        temporary.write_bytes(encoded.getvalue())
        os.replace(temporary, output)
        return {
            "slot": slot,
            "file": output.name,
            "width": image.width,
            "height": image.height,
            "source_type": content_type,
            "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }


class PresetArtwork:
    """Fetch only curated preset artwork and re-encode it into a local JPEG."""

    def __init__(self, cache_root: Path, fetcher: BoundedFetcher | None = None) -> None:
        if not cache_root.is_absolute():
            raise ValueError("artwork cache path must be absolute")
        self.cache_root = cache_root
        self.fetcher = fetcher or BoundedFetcher()
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _preset_lock(self, preset_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(preset_id, threading.Lock())

    def ensure(self, preset_id: str, url: str) -> Path:
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", preset_id):
            raise ValueError("invalid radio preset id")
        output = self.cache_root / f"radio-{preset_id}.jpg"
        with self._preset_lock(preset_id):
            if output.is_file():
                return output
            payload, _content_type = self.fetcher.fetch(
                url, max_bytes=2 * 1024 * 1024, accepted_types=("image/*",)
            )
            try:
                with Image.open(BytesIO(payload)) as source:
                    if source.width * source.height > 20_000_000:
                        raise ContentError("station artwork dimensions exceed the safety limit")
                    source.verify()
                with Image.open(BytesIO(payload)) as source:
                    image = ImageOps.exif_transpose(source).convert("RGB")
                    image.thumbnail((256, 256), Image.Resampling.LANCZOS)
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
                raise ContentError(f"invalid station artwork: {exc}") from exc
            self.cache_root.mkdir(parents=True, exist_ok=True, mode=0o750)
            encoded = BytesIO()
            image.save(encoded, format="JPEG", quality=88, optimize=True)
            temporary = output.with_suffix(".jpg.tmp")
            temporary.write_bytes(encoded.getvalue())
            os.replace(temporary, output)
            return output


class TrackArtwork:
    """Resolve optional track covers through MusicBrainz and Cover Art Archive."""

    def __init__(self, cache_root: Path, fetcher: BoundedFetcher | None = None) -> None:
        if not cache_root.is_absolute():
            raise ValueError("track artwork cache path must be absolute")
        self.cache_root = cache_root
        self.fetcher = fetcher or BoundedFetcher()
        self._request_guard = threading.Lock()
        self._last_request = 0.0

    def _json(self, url: str) -> dict[str, object]:
        with self._request_guard:
            remaining = 1.05 - (time.monotonic() - self._last_request)
            if remaining > 0:
                time.sleep(remaining)
            payload, _content_type = self.fetcher.fetch(
                url,
                max_bytes=1024 * 1024,
                accepted_types=("application/json",),
                timeout=10,
            )
            self._last_request = time.monotonic()
        try:
            value = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContentError(f"invalid cover metadata: {exc}") from exc
        if not isinstance(value, dict):
            raise ContentError("cover metadata response is not an object")
        return value

    def ensure(self, media_id: int, artist: str, title: str) -> Path:
        if (
            isinstance(media_id, bool)
            or not isinstance(media_id, int)
            or media_id < 1
            or not artist.strip()
            or not title.strip()
        ):
            raise ValueError("track cover requires media id, artist and title")
        output = self.cache_root / f"track-{media_id}.jpg"
        if output.is_file():
            return output
        query = urlencode(
            {
                "query": f'recording:"{title[:200]}" AND artist:"{artist[:160]}"',
                "fmt": "json",
                "limit": "5",
            }
        )
        search = self._json(f"https://musicbrainz.org/ws/2/recording?{query}")
        releases: list[object] = []
        recordings = search.get("recordings")
        if isinstance(recordings, list):
            for recording in recordings:
                if not isinstance(recording, dict):
                    continue
                score = recording.get("score", 0)
                if not isinstance(score, int) or score < 85:
                    continue
                candidate = recording.get("releases")
                if isinstance(candidate, list):
                    releases.extend(candidate)
        image_url: str | None = None
        for release in releases[:5]:
            if not isinstance(release, dict):
                continue
            release_id = release.get("id")
            if not isinstance(release_id, str) or not re.fullmatch(
                r"[0-9a-fA-F-]{36}", release_id
            ):
                continue
            try:
                listing = self._json(
                    f"https://coverartarchive.org/release/{release_id}/"
                )
            except ContentError:
                continue
            images = listing.get("images")
            if not isinstance(images, list):
                continue
            front = next(
                (
                    item
                    for item in images
                    if isinstance(item, dict)
                    and item.get("front") is True
                    and item.get("approved", True) is True
                ),
                None,
            )
            if isinstance(front, dict):
                thumbnails = front.get("thumbnails")
                if isinstance(thumbnails, dict):
                    candidate = thumbnails.get("250") or thumbnails.get("small")
                    if isinstance(candidate, str):
                        image_url = candidate.replace("http://", "https://", 1)
                        break
        if image_url is None:
            raise ContentError("no verified front cover was found")
        payload, _content_type = self.fetcher.fetch(
            image_url,
            max_bytes=2 * 1024 * 1024,
            accepted_types=("image/*",),
            timeout=10,
        )
        try:
            with Image.open(BytesIO(payload)) as source:
                if source.width * source.height > 20_000_000:
                    raise ContentError("track cover dimensions exceed the safety limit")
                source.verify()
            with Image.open(BytesIO(payload)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((512, 512), Image.Resampling.LANCZOS)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ContentError(f"invalid track cover: {exc}") from exc
        self.cache_root.mkdir(parents=True, exist_ok=True, mode=0o750)
        encoded = BytesIO()
        image.save(encoded, format="JPEG", quality=88, optimize=True)
        temporary = output.with_suffix(".jpg.tmp")
        temporary.write_bytes(encoded.getvalue())
        os.replace(temporary, output)
        return output


DWD_WMS_URL = "https://maps.dwd.de/geoserver/dwd/wms"
DWD_SATELLITE_LAYER = "Satellite_meteosat_1km_euat_rgb_day_hrv_and_night_ir108_3h"
DWD_RADAR_GIF_URL = "https://www.wettergefahren.de/DWD/wetter/radar/Radarfilm_WEB_DL.gif"
WEATHER_REFRESH_SECONDS = 300
WEATHER_FRAME_COUNT = 8


class DwdSatelliteFrames:
    """Bounded local JPEG cache for the official DWD WMS and radar-film sources."""

    def __init__(self, cache_root: Path, fetcher: BoundedFetcher | None = None) -> None:
        if not cache_root.is_absolute():
            raise ValueError("weather cache path must be absolute")
        self.cache_root = cache_root
        self.fetcher = fetcher or BoundedFetcher()
        self._lock = threading.RLock()
        self._last_refresh: dict[str, float] = {}
        self._capability_times: tuple[datetime, ...] = ()
        self._capabilities_checked = 0.0

    @staticmethod
    def _slug(value: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9_-]{1,63}", value):
            raise ValueError("invalid weather channel id")
        return value

    @staticmethod
    def _parse_instant(value: str) -> datetime:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).astimezone(UTC)

    @classmethod
    def parse_capability_times(cls, payload: bytes) -> tuple[datetime, ...]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise ContentError(f"invalid DWD capabilities XML: {exc}") from exc
        for layer in root.iter():
            if layer.tag.rsplit("}", 1)[-1] != "Layer":
                continue
            name = next(
                (
                    child.text.strip()
                    for child in layer
                    if child.tag.rsplit("}", 1)[-1] == "Name" and child.text
                ),
                "",
            )
            if name != DWD_SATELLITE_LAYER:
                continue
            dimension = next(
                (
                    child
                    for child in layer
                    if child.tag.rsplit("}", 1)[-1] == "Dimension"
                    and child.attrib.get("name") == "time"
                    and child.text
                ),
                None,
            )
            if dimension is None or not dimension.text:
                break
            value = dimension.text.strip()
            if "/" in value:
                parts = value.split("/")
                if len(parts) != 3 or parts[2] != "PT3H":
                    raise ContentError("unsupported DWD satellite time interval")
                start, end = cls._parse_instant(parts[0]), cls._parse_instant(parts[1])
                values: list[datetime] = []
                current = start
                while current <= end and len(values) < 1000:
                    values.append(current)
                    current += timedelta(hours=3)
                return tuple(values)
            return tuple(cls._parse_instant(item) for item in value.split(",") if item.strip())
        raise ContentError("DWD satellite layer has no time dimension")

    def _available_times(self) -> tuple[datetime, ...]:
        now = time.monotonic()
        if self._capability_times and now - self._capabilities_checked < WEATHER_REFRESH_SECONDS:
            return self._capability_times
        query = urlencode(
            {
                "service": "WMS",
                "request": "GetCapabilities",
                "version": "1.3.0",
            }
        )
        payload, _content_type = self.fetcher.fetch(
            f"{DWD_WMS_URL}?{query}",
            max_bytes=2 * 1024 * 1024,
            accepted_types=("text/xml", "application/xml"),
            timeout=12.0,
        )
        values = self.parse_capability_times(payload)
        if not values:
            raise ContentError("DWD satellite time list is empty")
        self._capability_times = values
        self._capabilities_checked = now
        return values

    @staticmethod
    def _timestamp_name(value: datetime) -> str:
        return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")

    def frames(self, channel_key: str) -> list[dict[str, object]]:
        slug = self._slug(channel_key)
        frames: list[dict[str, object]] = []
        for path in sorted(self.cache_root.glob(f"weather-{slug}-*.jpg")):
            match = re.fullmatch(
                rf"weather-{re.escape(slug)}-(\d{{8}}T\d{{6}}Z)\.jpg",
                path.name,
            )
            if match is None:
                continue
            try:
                timestamp = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            except ValueError:
                continue
            frames.append(
                {
                    "file": path.name,
                    "timestamp": timestamp.isoformat(timespec="minutes").replace("+00:00", "Z"),
                }
            )
        return frames[-WEATHER_FRAME_COUNT:]

    def invalidate(self, channel_key: str) -> None:
        """Remove frames after a channel crop changes or is deleted."""
        slug = self._slug(channel_key)
        with self._lock:
            for path in self.cache_root.glob(f"weather-{slug}-*.jpg"):
                try:
                    path.unlink()
                except OSError:
                    pass
            self._last_refresh.pop(slug, None)

    def _fetch_frame(
        self,
        channel_key: str,
        bbox: tuple[float, float, float, float],
        timestamp: datetime,
    ) -> Path:
        slug = self._slug(channel_key)
        output = self.cache_root / f"weather-{slug}-{self._timestamp_name(timestamp)}.jpg"
        if output.is_file():
            return output
        query = urlencode(
            {
                "service": "WMS",
                "version": "1.3.0",
                "request": "GetMap",
                "layers": DWD_SATELLITE_LAYER,
                "styles": "raster",
                "crs": "EPSG:4326",
                "format": "image/png",
                "transparent": "false",
                "width": "480",
                "height": "360",
                # WMS 1.3 uses latitude,longitude axis order for EPSG:4326.
                "bbox": ",".join(f"{item:g}" for item in bbox),
                "time": timestamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
            }
        )
        payload, _content_type = self.fetcher.fetch(
            f"{DWD_WMS_URL}?{query}",
            max_bytes=2 * 1024 * 1024,
            accepted_types=("image/*",),
            timeout=12.0,
        )
        try:
            with Image.open(BytesIO(payload)) as source:
                if source.width * source.height > 4_000_000:
                    raise ContentError("DWD satellite image dimensions exceed the safety limit")
                source.verify()
            with Image.open(BytesIO(payload)) as source:
                image = source.convert("RGB")
                image.thumbnail((480, 360), Image.Resampling.LANCZOS)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ContentError(f"invalid DWD satellite image: {exc}") from exc
        self.cache_root.mkdir(parents=True, exist_ok=True, mode=0o750)
        encoded = BytesIO()
        image.save(encoded, format="JPEG", quality=88, optimize=True)
        temporary = output.with_suffix(".jpg.tmp")
        temporary.write_bytes(encoded.getvalue())
        os.replace(temporary, output)
        return output

    def refresh(
        self,
        channel_key: str,
        bbox: tuple[float, float, float, float],
    ) -> list[dict[str, object]]:
        slug = self._slug(channel_key)
        with self._lock:
            cached = self.frames(slug)
            now = time.monotonic()
            if cached:
                newest_mtime = max(
                    (
                        (self.cache_root / str(item["file"])).stat().st_mtime
                        for item in cached
                    ),
                    default=0.0,
                )
                if (
                    now - self._last_refresh.get(slug, 0.0) < WEATHER_REFRESH_SECONDS
                    or time.time() - newest_mtime < WEATHER_REFRESH_SECONDS
                ):
                    return cached
            try:
                selected: list[datetime] = []
                last_error: Exception | None = None
                for timestamp in reversed(self._available_times()):
                    try:
                        self._fetch_frame(slug, bbox, timestamp)
                    except (ContentError, OSError, ValueError) as exc:
                        last_error = exc
                        continue
                    selected.append(timestamp)
                    if len(selected) >= WEATHER_FRAME_COUNT:
                        break
                selected.sort()
                if not selected:
                    if last_error is not None:
                        raise last_error
                    raise ContentError("DWD returned no usable satellite frames")
                keep = {
                    f"weather-{slug}-{self._timestamp_name(timestamp)}.jpg"
                    for timestamp in selected
                }
                for path in self.cache_root.glob(f"weather-{slug}-*.jpg"):
                    if path.name not in keep:
                        try:
                            path.unlink()
                        except OSError:
                            pass
                self._last_refresh[slug] = now
            except (ContentError, OSError, ValueError):
                if not cached:
                    raise
            return self.frames(slug)

    def refresh_radar(
        self,
        channel_key: str,
        source_url: str = DWD_RADAR_GIF_URL,
    ) -> list[dict[str, object]]:
        """Fetch the fixed reviewed DWD radar GIF and re-encode bounded frames."""
        if source_url != DWD_RADAR_GIF_URL:
            raise ValueError("unsupported DWD radar source")
        slug = self._slug(channel_key)
        with self._lock:
            cached = self.frames(slug)
            now = time.monotonic()
            if cached:
                newest_mtime = max(
                    (
                        (self.cache_root / str(item["file"])).stat().st_mtime
                        for item in cached
                    ),
                    default=0.0,
                )
                if (
                    now - self._last_refresh.get(slug, 0.0) < WEATHER_REFRESH_SECONDS
                    or time.time() - newest_mtime < WEATHER_REFRESH_SECONDS
                ):
                    return cached
            try:
                payload, _content_type = self.fetcher.fetch(
                    source_url,
                    max_bytes=8 * 1024 * 1024,
                    accepted_types=("image/gif",),
                    timeout=12.0,
                )
                encoded_frames: list[bytes] = []
                try:
                    with Image.open(BytesIO(payload)) as source:
                        frame_count = int(getattr(source, "n_frames", 1))
                        if frame_count < 2 or frame_count > 60:
                            raise ContentError("DWD radar animation has an invalid frame count")
                        if source.width * source.height > 4_000_000:
                            raise ContentError("DWD radar dimensions exceed the safety limit")
                        first = max(0, frame_count - WEATHER_FRAME_COUNT)
                        for index in range(first, frame_count):
                            source.seek(index)
                            frame = source.convert("RGB")
                            frame.thumbnail((480, 480), Image.Resampling.LANCZOS)
                            output = BytesIO()
                            frame.save(output, format="JPEG", quality=88, optimize=True)
                            encoded_frames.append(output.getvalue())
                except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
                    raise ContentError(f"invalid DWD radar animation: {exc}") from exc

                self.cache_root.mkdir(parents=True, exist_ok=True, mode=0o750)
                newest = datetime.now(UTC).replace(microsecond=0)
                keep: set[str] = set()
                for index, encoded in enumerate(encoded_frames):
                    timestamp = newest - timedelta(seconds=len(encoded_frames) - index - 1)
                    name = f"weather-{slug}-{self._timestamp_name(timestamp)}.jpg"
                    target = self.cache_root / name
                    temporary = target.with_suffix(".jpg.tmp")
                    temporary.write_bytes(encoded)
                    os.replace(temporary, target)
                    keep.add(name)
                for path in self.cache_root.glob(f"weather-{slug}-*.jpg"):
                    if path.name not in keep:
                        try:
                            path.unlink()
                        except OSError:
                            pass
                self._last_refresh[slug] = now
            except (ContentError, OSError, ValueError):
                if not cached:
                    raise
            return self.frames(slug)
