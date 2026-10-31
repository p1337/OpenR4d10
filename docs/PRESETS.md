# Curated radio and feed presets

The preset catalog is intentionally small and reviewable. It contains no
credentials, cookies, signed download URLs or user-specific parameters. The
runtime reads it from `src/openr4d10/presets.py`; playback and feed parsing do
not contain station-specific branches. On a new database the radio catalog is
copied once into the ordered personal station library. Its seed marker is then
permanent, so user reordering and deletion survive restarts and updates; this
source catalog remains evidence for artwork and intentional re-adding only.

The addresses below were reviewed on 2026-10-30. Broadcasters may change
public endpoints, formats or availability. A preset update must be checked
against the broadcaster or clearly responsible delivery domain, exercised with
the actual player/parser, and committed together with this document.

## Radio

| Preset | Public stream | Review reference |
|---|---|---|
| SWR3 | `https://dispatcher.rndfnk.com/swr/swr3/live/mp3/128/stream.mp3` | [SWR3: Empfang über das Internet](https://www.swr3.de/musik/webradio/swr3-ueber-das-internet-empfangen-100.html) |
| sunshine live | `https://stream.sunshine-live.de/live/mp3-128/stream.sunshine-live.de/` | [sunshine live stream directory](https://stream.sunshine-live.de/live) |
| Deutschlandfunk | `https://st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3` | [Deutschlandradio streaming services](https://www.deutschlandradio.de/streamingdienste-100.html) |
| RMF FM | `https://rs9-krk2.rmfstream.pl/rmf_fm` | [RMF FM radio page](https://www.rmf.fm/radio/) and RMF-owned stream host |
| Radio ZET | `https://zt01.cdn.eurozet.pl/zet-old.mp3` | [Official Radio ZET player](https://player.radiozet.pl/) and Eurozet-owned delivery host |
| BBC World Service | `https://stream.live.vc.bbcmedia.co.uk/bbc_world_service` | [BBC Sounds: World Service](https://www.bbc.co.uk/sounds/play/live:bbc_world_service) |
| DIE NEUE 107.7 | `https://addrad.io/4454xcp` | [Offizielle Livestream-Seite](https://dieneue1077.de/radio/bester-rock-und-pop); die Adresse wird vom offiziellen Stream-Service des Senders geliefert |
| AFN The Eagle (Kaiserslautern) | `https://playerservices.streamtheworld.com/api/livestream-redirect/AFNE_KTN.mp3` | [AFN Go Kaiserslautern](https://afngo.net/afneurope/Kaiserslautern/radio/Kaiserslautern); AFN richtet das Angebot an seine berechtigte Zielgruppe außerhalb der USA |
| ROCK ANTENNE | `https://stream.rockantenne.de/rockantenne/stream/mp3` | [Offizielle Streamlinks](https://www.rockantenne.de/rockhoeren/empfang/streamlinks) |
| ROCK FM | `https://stream.regenbogen2.de/dab/mp3-128/private` | [Offizielle Empfangsseite](https://www.rockfm.de/service/empfang) |

The artwork sources are also explicit catalog data. The browser never receives
their remote URLs. The service downloads at most 2 MiB, rejects non-images and
excessive dimensions, decodes the file, and stores a new local JPEG. Artwork
failure does not block radio playback.

## News feeds

| Preset | Feed | Review reference and credit |
|---|---|---|
| tagesschau – alle Meldungen | `https://www.tagesschau.de/infoservices/alle-meldungen-100~rss2.xml` | [tagesschau RSS service](https://www.tagesschau.de/infoservices/rssfeeds), credit `Quelle: tagesschau.de` |
| Deutschlandfunk Nachrichten | `https://www.deutschlandfunk.de/nachrichten-100.rss` | [Deutschlandfunk RSS offer](https://www.deutschlandfunk.de/rss-angebot-102.html), credit `Quelle: Deutschlandfunk` |
| RMF24 | `https://www.rmf24.pl/feed` | [RMF24 RSS channels](https://www.rmf24.pl/kanaly/rss), credit `Źródło: RMF24.pl` |
| BBC News – World | `https://feeds.bbci.co.uk/news/world/rss.xml` | [BBC News feeds](https://www.bbc.co.uk/news/10628494), credit `Source: BBC News` |

The dashboard shows source credit for curated feeds and links individual items
to their publisher. It parses no more than 50 entries from a response of at
most 2 MiB and renders only text extracted by the core.

## Update checklist

1. Use an HTTPS endpoint controlled by or explicitly documented for the
   broadcaster. Never copy a temporary URL containing tokens or signatures.
2. Confirm the radio response is playable audio or the feed is valid RSS/Atom.
3. Confirm the public preset representation exposes no internal stream, feed
   or artwork URL.
4. Run the complete unit suite and the installer check.
5. Record the review date and evidence here.
