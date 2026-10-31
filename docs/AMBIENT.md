# AmbientR4D10

AmbientR4D10 is a separate audio service for continuously looping natural and
room soundscapes. Merely selecting the service never replaces currently
playing radio. Turning the channel control inside Ambient immediately starts
the selected scene and gives AmbientR4D10 audio ownership. Weather and other
visual services do not interrupt it.

The first catalog uses stable, query-free public audio addresses: five
Wikimedia Commons originals and one Freesound CC0 preview for the quieter café.
The reviewed recordings are downloaded once in the background into the
protected local media directory, bounded to 64 MiB each, verified against their
curated SHA-256 digests and atomically published for offline playback. Existing
valid cache files survive updates and restarts. Until a particular cache entry
is complete, the same reviewed public URL remains the temporary playback
fallback. The binary recordings are not copied into every repository archive.
The existing isolated `mpv` process loops the local file indefinitely and
identifies network fallback requests with
`OpenR4d10 (+https://github.com/p1337/OpenR4d10)` because Wikimedia rejects the
anonymous ffmpeg default client with HTTP 429. Updates seed the catalog only
once and never recreate a scene that the user deliberately deleted from
persistent state.

Each built-in scene has a bundled, text-free square artwork in
`assets/ambient/`. The six images deliberately share one visual language:
cinematic miniature-diorama realism, deep charcoal/petrol shadows and restrained
`#FDB813` amber light. They are generated project assets rather than remote
downloads, so both the browser and the physical display keep working offline.
The central composition remains readable as a 46-pixel list thumbnail and when
cropped into the native 240 x 280 player. User-created scenes keep the existing
initials fallback; arbitrary filenames are never accepted by the artwork API.

| Scene | Recording | Credit | License | SHA-256 |
|---|---|---|---|---|
| Café | [0105coffeehouse.wav](https://freesound.org/people/moxobna/sounds/46310/) | moxobna | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | `86c51e4fa5001c4fbf597c8725b50e36a347c31fbc0c499cad0a1bc27e9bb072` |
| Forest | [20090610 0 ambience.ogg](https://commons.wikimedia.org/wiki/File:20090610_0_ambience.ogg) | nille | Public domain | `43848c3eda5f42829f1033112c2a91ba3e5c91b79a0532fda264c9f59856d431` |
| Sea & beach | [On a pebble beach.ogg](https://commons.wikimedia.org/wiki/File:On_a_pebble_beach.ogg) | earthcalling | Public domain | `4e506141b9a285d03debdb8e0fbc9c1e30aaa29f82f8b2f368f70d5491a636b6` |
| Forest brook | [Brook.ogg](https://commons.wikimedia.org/wiki/File:Brook.ogg) | Onegoodtune | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) | `9847be31041e84dff3a70a52cfaf9f8a1b3d12bf836033e5a157daef8b036efb` |
| Gentle rain | [Sound of light rainfall.ogg](https://commons.wikimedia.org/wiki/File:Sound_of_light_rainfall.ogg) | Mijesty | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | `e0233652d8173650149adcf3d6e5ddc01b73e8a93ce61b8d7809abfe582251a8` |
| Night field & crickets | [Crickets choir.ogg](https://commons.wikimedia.org/wiki/File:Crickets_choir.ogg) | Serg Childed | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | `f0d82e6b96d110d09615ccca2b2f0b8945f06b0be50c09864c66b9e440b1a7b3` |

The café preset uses Freesound's public query-free Ogg preview of the
6:20-minute quiet-coffeehouse recording. The remaining five built-ins continue
to use Wikimedia Commons originals.

Changing the Ambient channel immediately starts the newly selected scene. Merely
opening the Ambient service still does not interrupt another audio service.

Public status includes scene name, description, credit, source page and
license, but never the internal media URL. Persistent custom scene URLs must
use HTTP(S), contain no embedded credentials and contain no query string, so a
signed token cannot leak into SQLite or backups.
