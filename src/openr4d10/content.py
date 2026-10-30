"""Bounded RSS/Atom and camera content retrieval for local service modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html import unescape
from io import BytesIO
import os
from pathlib import Path
import re
import threading
from typing import Any, Callable
from urllib.parse import urlsplit
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
