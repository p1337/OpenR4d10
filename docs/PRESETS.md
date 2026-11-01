# Curated radio and feed presets

The preset catalog is intentionally finite and reviewable. It contains no
credentials, cookies, signed download URLs or user-specific parameters. The
runtime reads it from `src/openr4d10/presets.py`; playback and feed parsing do
not contain station-specific branches. On a new database only the ten entries
marked `default_enabled` are copied once into the ordered personal station
library. The remaining entries start inactive. Activating one copies it into
that library; removing it makes it available in the catalog again. The seed
marker is permanent, so user reordering and deletion survive restarts and
updates. A later source-catalog addition never activates itself.

The original 41-station set was reviewed on 2026-10-31. Every configured
stream produced a decodable audio stream with ffprobe during that review, and
all 41 artwork locations returned decodable image content (temporary Wikimedia
rate limiting remains a normal cache retry condition). Broadcasters may change
public endpoints, formats or availability. A preset update must be checked
against the broadcaster or clearly responsible delivery domain, exercised with
the actual player/parser, and committed together with this document.

On 2026-11-01 the five additional Polish entries below were tested with the
real Raspberry Pi Zero 2 W `ffprobe`: Radio GRA, Radio 357 and Radio Nowy Świat
decoded as MP3; Dwójka and Trójka decoded as AAC/HLS. Their five artwork URLs
were independently downloaded, decoded and dimension-checked with Pillow.

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

These ten rows are the default-enabled personal list. The following reviewed
catalog rows start inactive; their exact stream, homepage, artwork and review
reference are the adjacent fields of the corresponding `RadioPreset` in
`src/openr4d10/presets.py`.

| Language | Inactive catalog stations | Primary review family |
|---|---|---|
| English (`en`) | BBC Radio 2, BBC Radio 3, BBC Radio 4 | [BBC Sounds live radio](https://www.bbc.co.uk/sounds) and BBC/Akamai delivery |
| Polish (`pl`) | Polskie Radio Jedynka, Polskie Radio Czwórka, Polskie Radio 24, Radio GRA Toruń, Polskie Radio Dwójka, Polskie Radio Trójka, Radio 357, Radio Nowy Świat | [Polskie Radio player](https://player.polskieradio.pl/), [Radio GRA](https://gra.fm/), [Radio 357 stream documentation](https://radio357.pl/faq/ogolne/jak-sluchac-radia-357/) and [Radio Nowy Świat stream documentation](https://nowyswiat.online/jak-nas-sluchac) |
| French (`fr`) | France Inter, franceinfo, France Culture, FIP, France Musique | [Radio France](https://www.radiofrance.fr/) and franceinfo |
| Spanish (`es`) | RNE Radio Nacional, RNE Radio Clásica, RNE Radio 3, RNE Radio 5, RNE Radio Exterior | [RTVE radio live](https://www.rtve.es/play/videos/directo/radio-en-directo/) |
| Italian (`it`) | Rai Radio 1, Rai Radio 2, Rai Radio 3, Rai Isoradio, Radio 24 | [Radio Rai](https://www.radiocorrieretv.rai.it/radio-rai/) and Radio 24 |
| Dutch (`nl`) | NPO Radio 1, NPO Radio 2, NPO 3FM, NPO Klassiek, NPO Radio 5 | [NPO Luister & Radio](https://npo.nl/service/npo-luister-en-radio) |
| Portuguese (`pt`) | RTP Antena 1, RTP Antena 2, RTP Antena 3, TSF Rádio Notícias, Rádio Observador | [RTP live radio](https://www.rtp.pt/), [TSF](https://www.tsf.pt/) and [Observador](https://observador.pt/radio/) |

Together with the defaults this yields German 6, English 5, Polish 10, French
5, Spanish 5, Italian 5, Dutch 5 and Portuguese 5. Category metadata is also
reviewed catalog data. It includes music styles, news, talk, culture, sport and
explicit `science`/`technology` labels where the broadcaster's programme remit
supports them; category labels do not claim that every programme has that topic.

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

1. Prefer an HTTPS endpoint controlled by or explicitly documented for the
   broadcaster. A legacy HTTP-only public broadcaster endpoint is allowed only
   when the actual player test succeeds and the responsible source is recorded.
   Never copy a temporary URL containing tokens or signatures.
2. Confirm the radio response is playable audio or the feed is valid RSS/Atom.
3. Confirm the public preset representation exposes no internal stream, feed
   or artwork URL.
4. Run the complete unit suite and the installer check.
5. Record the review date and evidence here.
