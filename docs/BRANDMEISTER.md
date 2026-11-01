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

On the physical device, the right outer channel axis browses the complete
official catalog one entry at a time. Because Squelch has no meaning for this
IP-based DMR receiver, the left inner axis jumps 25 catalog entries per detent.
The device renders a bounded scrolling window over that complete catalog, with
enabled entries first and inactive entries below them. The selected row, its
on/off state and its position in the full catalog stay visible. A currently
speaking subscribed talkgroup is pinned above the scrolling rows and shows its
destination, source ID and available alias. The device no longer renders a
single decorative TG or country tile.

The short right press while the BrandMeister view is open starts reception of
the already enabled talkgroups. This is an explicit Play action and takes audio
ownership from a running radio or another audio service. A short PTT press adds
and enables the selected talkgroup in the persistent quick list or disables an
already saved entry when the button is released. Holding PTT for at least two
seconds opens a country list derived from the bounded cached official catalog.
The right outer axis selects a country and the right press applies that browse
filter. The filter never changes the five current subscriptions. Inside a menu
PTT keeps its normal back/cancel role. A long right press remains the service
quick menu. The header changes with the service and shows the real DMR
assignments instead of `SQL` and a generic channel label. Up to five checked
talkgroups are subscribed at once. None of these controls transmits audio or a
BrandMeister PTT message.

When five talkgroups are active and a sixth is selected, OpenR4d10 does not
silently remove one and does not merely reject the action. The device opens a
five-row replacement list: right outer selects the old TG, right press confirms
the swap and PTT cancels it. The browser presents the same explicit choice.

The native receiver keeps one bounded current/last-heard row for each of the
up to five subscribed talkgroups. A row contains only data actually observed
in HoseLine packets: destination talkgroup, source DMR ID, optional talker
alias, active state and update time. Active rows sort first. The browser and
physical display render these rows as a compact icon list; the device no longer
uses its BrandMeister content area for a large decorative country image. The
list does not claim to enumerate silent members of a talkgroup. Geographic or
callsign enrichment through third-party subscriber databases is deliberately
not performed without a separately reviewed data-use contract.

The selected row exposes `ON`/localized `AN` or `OFF`/localized `AUS`; PTT
changes that state. The right-button edge label remains `PLAY` (or the localized
equivalent) because that button starts reception. Browser rows combine the
normal checkbox with the same translated written state. A list change updates
an already running receiver but leaves a different audio service untouched;
the right Play action remains the only takeover. No separate save step is
required.

Display volume has one authoritative value: the central audio-owner volume in
`MpvEngine.state.volume`. A dormant BrandMeister receiver snapshot must not
overwrite that value during a DMR-view refresh while radio is still the active
audio owner. Starting BrandMeister copies the same value into its ALSA receiver,
so the header and audible output remain synchronized across service changes.

On 2026-10-31 the user heard a real subscribed HoseLine call through the fitted
Whisplay speaker. This confirms the complete native WebSocket, MessagePack,
G.711 µ-law, PCM and `whisplaysound` ALSA path on the target hardware.
