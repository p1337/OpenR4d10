# BrandMeister HoseLine reception

OpenR4d10 provides receive-only BrandMeister audio in its browser dashboard.
The implementation follows the transport used by the official HoseLine web
application at `https://hose.brandmeister.network/`:

- WebSocket endpoint `wss://hose.brandmeister.network/spotter/`
- WebSocket subprotocol `spotter`
- MessagePack group subscription messages
- 8 kHz G.711 µ-law call audio decoded through the browser Web Audio API

The quick list stores up to 30 numeric talkgroup choices in browser-local
storage and subscribes to at most five checked entries at once. A country flag
is derived only for known DMR country prefixes; unknown and worldwide groups
use the globe symbol. When a subscribed group becomes active, its destination,
source and available talker alias take visual priority while the other checked
groups remain subscribed.

No BrandMeister password, account credential or user API token is requested or
stored. This adapter never sends voice or PTT. The official HoseLine page stays
linked as a compatibility fallback if its public browser protocol changes.

Audio from this integration is rendered by the browser that opened the local
dashboard. Routing the same receive-only transport to the physical Whisplay
speaker is a separate adapter and must not be claimed until it has passed a
real Pi audio test.
