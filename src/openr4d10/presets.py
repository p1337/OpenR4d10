"""Curated, reviewable radio and feed presets with no credentials."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class RadioPreset:
    preset_id: str
    name: str
    country: str
    genre: str
    stream_url: str
    homepage: str
    artwork_url: str
    source_url: str

    def public(self) -> dict[str, str]:
        value = asdict(self)
        value.pop("stream_url")
        value.pop("artwork_url")
        value["artwork"] = f"/api/radio-art/{self.preset_id}"
        return value


@dataclass(frozen=True, slots=True)
class FeedPreset:
    preset_id: str
    name: str
    language: str
    feed_url: str
    homepage: str
    credit: str

    def public(self) -> dict[str, str]:
        value = asdict(self)
        value.pop("feed_url")
        return value


RADIO_PRESETS = (
    RadioPreset(
        "swr3", "SWR3", "Deutschland", "Pop & Nachrichten",
        "https://dispatcher.rndfnk.com/swr/swr3/live/mp3/128/stream.mp3",
        "https://www.swr3.de/",
        "https://www.swr3.de/assets/swr3/icons/logo.jpg",
        "https://www.swr3.de/musik/webradio/swr3-ueber-das-internet-empfangen-100.html",
    ),
    RadioPreset(
        "sunshine_live", "sunshine live", "Deutschland", "Electronic Music",
        "https://stream.sunshine-live.de/live/mp3-128/stream.sunshine-live.de/",
        "https://www.sunshine-live.de/",
        "https://upload.sunshine-live.de/production/static/1792483605187/icons/icon_512.fmRwc30M41g.png",
        "https://stream.sunshine-live.de/live",
    ),
    RadioPreset(
        "deutschlandfunk", "Deutschlandfunk", "Deutschland", "Nachrichten & Kultur",
        "https://st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3",
        "https://www.deutschlandfunk.de/",
        "https://www.deutschlandfunk.de/static/img/deutschlandfunk/icons/apple-touch-icon-180x180.png",
        "https://www.deutschlandradio.de/streamingdienste-100.html",
    ),
    RadioPreset(
        "rmf_fm", "RMF FM", "Polska", "Muzyka & wiadomości",
        "https://rs9-krk2.rmfstream.pl/rmf_fm",
        "https://www.rmf.fm/",
        "https://www.rmfon.pl/assets/images/favicon/android-chrome-192x192.png",
        "https://www.rmf.fm/radio/",
    ),
    RadioPreset(
        "radio_zet", "Radio ZET", "Polska", "Muzyka & wiadomości",
        "https://zt01.cdn.eurozet.pl/zet-old.mp3",
        "https://player.radiozet.pl/",
        "https://gfx-player.radiozet.pl/design/player_radiozet/images/logo_share.jpg",
        "https://player.radiozet.pl/",
    ),
    RadioPreset(
        "bbc_world", "BBC World Service", "United Kingdom", "World News",
        "https://stream.live.vc.bbcmedia.co.uk/bbc_world_service",
        "https://www.bbc.co.uk/sounds/play/live:bbc_world_service",
        "https://static.files.bbci.co.uk/bbcdotcom/web/20261027-121803-88dfe2b2c8-web-3.26.0-4/apple-touch-icon.png",
        "https://www.bbc.co.uk/sounds/play/live:bbc_world_service",
    ),
)

FEED_PRESETS = (
    FeedPreset(
        "tagesschau", "tagesschau – alle Meldungen", "de",
        "https://www.tagesschau.de/infoservices/alle-meldungen-100~rss2.xml",
        "https://www.tagesschau.de/", "Quelle: tagesschau.de",
    ),
    FeedPreset(
        "dlf_nachrichten", "Deutschlandfunk Nachrichten", "de",
        "https://www.deutschlandfunk.de/nachrichten-100.rss",
        "https://www.deutschlandfunk.de/", "Quelle: Deutschlandfunk",
    ),
    FeedPreset(
        "rmf24", "RMF24 – najważniejsze informacje", "pl",
        "https://www.rmf24.pl/feed",
        "https://www.rmf24.pl/", "Źródło: RMF24.pl",
    ),
    FeedPreset(
        "bbc_world", "BBC News – World", "en",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.bbc.com/news/world", "Source: BBC News",
    ),
)

RADIO_BY_ID = {item.preset_id: item for item in RADIO_PRESETS}
FEED_BY_ID = {item.preset_id: item for item in FEED_PRESETS}
