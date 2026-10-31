# AmbientR4D10

AmbientR4D10 is a separate audio service for continuously looping natural and
room soundscapes. Selecting the service or browsing scenes never replaces
currently playing radio. Only an explicit Play command gives AmbientR4D10
audio ownership. Weather and other visual services do not interrupt it.

The first catalog uses stable, query-free Wikimedia Commons original-file
addresses. Audio is streamed by the existing isolated `mpv` process and looped
indefinitely; the binary recordings are not copied into this repository. mpv
identifies the project with
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

| Scene | Recording | Credit | License |
|---|---|---|---|
| Café | [Cafe ambiance.ogg](https://commons.wikimedia.org/wiki/File:Cafe_ambiance.ogg) | Marble Toast | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Forest | [20090610 0 ambience.ogg](https://commons.wikimedia.org/wiki/File:20090610_0_ambience.ogg) | nille | Public domain |
| Sea & beach | [On a pebble beach.ogg](https://commons.wikimedia.org/wiki/File:On_a_pebble_beach.ogg) | earthcalling | Public domain |
| Forest brook | [Brook.ogg](https://commons.wikimedia.org/wiki/File:Brook.ogg) | Onegoodtune | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| Gentle rain | [Sound of light rainfall.ogg](https://commons.wikimedia.org/wiki/File:Sound_of_light_rainfall.ogg) | Mijesty | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| Night field & crickets | [Crickets choir.ogg](https://commons.wikimedia.org/wiki/File:Crickets_choir.ogg) | Serg Childed | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |

Public status includes scene name, description, credit, source page and
license, but never the internal media URL. Persistent custom scene URLs must
use HTTP(S), contain no embedded credentials and contain no query string, so a
signed token cannot leak into SQLite or backups.
