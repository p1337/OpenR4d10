# BrandMeister HoseLine reception

OpenR4d10 provides receive-only BrandMeister audio on the Raspberry Pi and as
an additional browser-dashboard output.
The implementation follows the transport used by the official HoseLine web
application at `https://hose.brandmeister.network/`:

- WebSocket endpoint `wss://hose.brandmeister.network/spotter/`
- WebSocket subprotocol `spotter`
- MessagePack group subscription messages
- 8 kHz G.711 µ-law call audio decoded through the browser Web Audio API

The quick list stores up to 30 numeric talkgroup choices in the device SQLite
state and subscribes to at most five checked entries at once. A country flag
is derived only for known DMR country prefixes; unknown and worldwide groups
use the globe symbol. When a subscribed group becomes active, its destination,
source and available talker alias take visual priority while the other checked
groups remain subscribed.

No BrandMeister password, account credential or user API token is requested or
stored. This adapter never sends voice or PTT. The official HoseLine page stays
linked as a compatibility fallback if its public browser protocol changes.

The native receiver uses the packaged `websockets` and MessagePack libraries,
decodes the same bounded 8 kHz G.711 µ-law packets and writes signed 16-bit PCM
only to ALSA device `whisplaysound` through an argument-only `aplay` process.
The browser Web Audio receiver remains an optional second output.

The complete searchable name catalog is fetched only from the fixed public
BrandMeister endpoint `https://api.brandmeister.network/v2/talkgroup`, bounded
to 256 KiB, validated and cached for one day. It doesn't use a SelfCare API key
and doesn't manage repeaters, hotspots or static account subscriptions.

On the physical device, channel rotation selects a saved talkgroup and the
right short press activates or deactivates it. Up to five checked talkgroups
are subscribed at once. The active call takes display priority and shows its
destination, source ID, available alias and a conservative country flag cue.
No transmit or PTT message exists in this adapter. Native speaker operation is
claimed only after a real Pi receive and audio test.
