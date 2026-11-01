# AmbientR4D10

AmbientR4D10 is a separate audio service for continuously looping natural and
room soundscapes. Merely selecting the service never replaces currently
playing radio. Turning the channel control inside Ambient immediately starts
the selected scene and gives AmbientR4D10 audio ownership. Weather and other
visual services do not interrupt it.

The catalog uses stable, query-free public audio addresses: five Wikimedia
Commons originals and five Freesound CC0 previews. The additional Freesound
recordings provide a quiet orchard meadow, distant road noise with birds, sea
heard from a cliff and distant thunder.
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
`assets/ambient/`. The ten images deliberately share one visual language:
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
| Orchard meadow & birds | [Meadow.wav](https://freesound.org/people/PuzzleAudio/sounds/440807/) | PuzzleAudio | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | `64efe6c695a26333528592674fd23652cb712ebd359bb159e253f882099dca2f` |
| Distant road & birds | [Distant Road w/ Birds](https://freesound.org/people/myrinvp/sounds/188402/) | myrinvp | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | `caa3be417ae45f0298c2dba9fe6eca2ec852180e3ceb5980c6bec15894030ef4` |
| Sea from a cliff | [sea from cliff.wav](https://freesound.org/people/bruno.auzet/sounds/525029/) | bruno.auzet | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | `6f5e589d412feeee5d8c01defff9092bf169c8f9b64a01451e8d9d8636e64a58` |
| Distant thunder | [Distant Thunder](https://freesound.org/people/Beetlemuse/sounds/530133/) | Beetlemuse | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | `97b3411cd2b2ba2036b4cb8e45ef245a7350a39cbcb47bc7463900fa1edadb6d` |

The café preset uses Freesound's public query-free Ogg preview of the
6:20-minute quiet-coffeehouse recording. The remaining five built-ins continue
to use Wikimedia Commons originals.

Changing the Ambient channel immediately starts the newly selected scene. Merely
opening the Ambient service still does not interrupt another audio service.

## Sound layers and favorite mixes

The four new recordings can also run as low-level sound layers over any active
Ambient scene. Layer enablement and a relative volume from 0 to 100 percent are
stored in the existing SQLite settings. The main volume remains the master;
each layer's effective ALSA volume is the saved relative percentage of that
master. Layers stop whenever another audio service takes ownership.
At most two layers may be enabled at once on the Pi Zero 2 W; a third request is
rejected instead of silently adding decoder and battery load.

On the physical device, hold the right control for two seconds while Ambient is
visible. The sound-layer list then uses the outer right control for selection,
a short right press for on/off, the inner left control for ten-percent volume
steps, and PTT for back. The final list row saves the current base scene and
layer settings as an ordinary Ambient favorite mix. The browser exposes the
same list and permits a custom favorite name. Favorite mixes are ordinary
persistent Ambient channels and therefore retain order and settings across
updates.

Public status includes scene name, description, credit, source page and
license, but never the internal media URL. Persistent custom scene URLs must
use HTTP(S), contain no embedded credentials and contain no query string, so a
signed token cannot leak into SQLite or backups.
