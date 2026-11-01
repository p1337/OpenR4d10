# Architecture

## Design boundary

OpenR4d10 has a hardware-independent core and small adapters at the boundary:

```text
Linux/systemd
    |
    v
CLI -> configuration -> application loop -> semantic UI Frame
              |                       |             |
              |                       |             +-> display adapter
              |                       +-> receiver/power telemetry adapters
              +-> local HTTP dashboard (port 80)
```

A `Frame` describes intent (`screen`, `title`, `body`, fields and severity), not
pixels. `WhisplayDisplay` maps it onto the agreed 240 x 280 device layout with
Pillow and streams big-endian RGB565 to the verified ST7789 transport. The
native early-boot player is a separate, deliberately narrow path: it initializes
the same panel and streams the checked-in animation until the application has
its first complete dashboard frame and claims display ownership.

The physical renderer owns the permanent rounded service-view glow as a
central composition layer. It is applied after the shared header/status area
and before any service-specific content branch, so recorder, system and future
registered plugin views cannot accidentally omit it. Individual services must
not draw a parallel frame. Only device menus and the WLAN setup screen bypass
that layer because they use their own navigation treatment.
The same compositor owns its state colors: idle uses the saved accent, any
globally active audio owner uses green, and radio/voice recording overrides
both with red. Continuous recording modulates only red glow strength. Play
actions use the same green cue, while Pause and Stop use the saved accent.

Encoder hardware is isolated behind logical `InputEvent` values. Four rotary
controls (`left_outer`, `left_inner`, `right_outer`, `right_inner`) and two
press controls are already modeled and tested. A seventh held `ptt` control has
an explicit boolean state so release cannot be confused with a second click.
It is only an input indication until an authorized PTT service adapter consumes
it. No GPIO number appears in the UI or navigation logic; the GPIO input source
is added after the delivered encoders have been identified and measured.

The local web dashboard can submit those same bounded `InputEvent` values to
the configured Whisplay adapter. The adapter serializes browser input and the
normal render loop with one display lock, updates its existing `DeviceUiState`
and repaints the physical panel immediately. This is the temporary hardware-
free input source and remains useful for remote operation after GPIO input is
added; it is not a second navigation model. Browser keyboard bindings translate
WASD, arrow keys, Space, Enter and held Backspace into this same contract and
are disabled while the user edits a form field. In an open device menu only,
the browser reverses its arrow-to-step mapping so visible Up and Down follow the
list; the logical input path and physical encoder semantics do not change.

The dashboard navigation is a client-side tab switch over the existing local
application sections, not a set of new routes or a second application state.
The checked-in `web/i18n.json` catalog contains the same complete browser
message-key set for English, German, Polish, French and Spanish. Language is a
shared device setting, not a browser-only preference: `ui.language` is stored
by `ServiceCatalog` in SQLite, restored into `DeviceUiState.language` during
application construction and changed through the bounded `display_language`
control. The display is redrawn before the successful response; if persistence
fails, the previous device language is restored. Browser-local storage caches
the same value only for the early load phase. Every status snapshot makes the
saved device value authoritative again, and unknown values fall back to
English. The static server exposes the catalog as a fixed same-origin asset.
Its fixed desktop device preview requests `/api/device-screen.png`; that image
is encoded from the same `render_device_ui()` call and locked `DeviceUiState`
used for SPI output. It therefore cannot drift into a separately maintained
CSS approximation. The endpoint is same-origin, non-cacheable and unavailable
when the configured display adapter has no native renderer.
The preview card deliberately has only the localized `LIVE DISPLAY` eyebrow;
there is no redundant device-view heading above the exact native image.

Semantic actions are resolved by the application before the display reflects
them. In particular, a short `right_press` routes through `ServiceCatalog` to
the same `MpvEngine.toggle_pause()` operation as the HTTP media control; only a
successfully active or paused stream may be toggled. A held `right_press`
remains display navigation for the quick menu. This prevents keyboard or future
GPIO input from changing a presentation-only `playing` flag while audio keeps
running.

The selected `DeviceUiState.service` is navigation state, while
`ServiceCatalog.active_service` identifies only the owner of the currently
loaded audio source. Periodic rendering requests a view-specific overlay and
must never copy the audio owner back into the service selector. Weather open,
step and refresh operations update only weather selection/cache state. A new
audio source replaces the old one only through an explicit play operation.
The explicit Mediathek `Audio on device` and `Video on device` commands are
also deliberate device-focus requests: after the central player accepts the
lowest available source, the application renders one resolved `PLAYER` frame.
Audio mode keeps the metadata view. Video mode queues software screenshots from
that same mpv process and composites the completed JPEG into the native frame
at no more than 25 FPS while video is actually playing. Only the edge-to-edge
240 x 175 lower video region uses that partial-transfer path; normal full UI
frames remain capped at
10 FPS. The one transient file lives under `/run/openr4d10`, is
bounded and removed after consumption; no video frame enters persistent state.
Because mpv remains the sole decoder and clock, pause, resume and channel
changes cannot drift between sound and picture. Search, selection and
browser-only video remain presentation-neutral. While that Mediathek source
owns the player, `right_outer` cycles and immediately loads entries from the
same cached result set without changing the selected audio/video mode, and
`right_press` uses the existing real pause path.
Audio device playback explicitly sets mpv's `vid` property to `no`; video
device playback sets it to `auto`. All other audio-source loads default to
`vid=no`, so hiding the device picture can never leave an unused video decoder
running.

The same router maps each `left_outer` detent to a bounded ten-percentage-point
change of the real mpv volume and `right_outer` to cyclic selection in the
persistent personal station order while the radio service is active. A short
right press toggles actual playback; if the selected service is radio and the
player is stopped, it loads position one.
`ServiceCatalog` owns the active station identity, human-readable station name,
channel number and optional reviewed artwork ID. The public semantic frame contains
only that safe metadata; the Whisplay adapter resolves an artwork ID against its
configured private cache root and otherwise draws a local initials tile. It
never receives a remote image URL or exposes the private cache path.
Selecting a curated preset starts its existing bounded decode/re-encode cache
operation in a daemon worker after audio loading succeeds. Artwork latency or
failure therefore cannot delay or fail stream switching; a later normal frame
refresh picks up the completed local JPEG.
The application serializes the semantic media action, device-state update and
immediate repaint as one device-input transaction so keyboard repeat and future
GPIO events cannot lose volume or channel steps through concurrent requests.

The physical renderer owns one compact layout contract. Its normal header uses
four localized three-character labels (`VOL`, `SQL`, `CH`, `SRV` in the English
fallback), larger values and a larger time without a date. The radio body does
not repeat the selected service or a written playback state; playback remains
visible through the button icon and actual media state. The old bottom status/
brand strip is removed and its space belongs to the larger station artwork.
The shared `_font()` boundary clamps every requested native-display font to the
battery percentage reference of 9 TrueType pixels. Service renderers and future
plugins cannot opt into smaller text to solve a layout problem; important
instructions must use a larger size and layouts must instead trim or reflow.
Each localized control label and its larger value are positioned from their
actual font bounding boxes so their visible glyph tops align exactly in both
header rows. The two halves are mirrored: labels precede values on the left,
while values precede right-aligned labels on the right. This keeps all values
toward the center divider and all control names toward the physical controls.
When `DeviceUiState.menu_open` identifies the main menu, the renderer exits the
player branch entirely and paints the localized heading plus the documented
ten-item settings list. The right outer encoder moves only the bounded menu
selection, and a short right press opens the selected page instead of reaching
media controls. Logical `HOME`, produced by a released short PiSugar power-
button press or Browser Space, opens the main menu from every service. The left
encoder press has no global action and remains available for later service use.
Menu history stays inside `DeviceUiState`; an active PTT press
returns one level unless the current semantic frame explicitly declares a
ready PTT-owning context. The back/PTT affordance is one edge-aligned silhouette
with a left-rounded, right-open frame and a filled mini arrow. The normal player
always adds a pronounced two-stage, line-free soft glow around its physical rounded contour, with a
straight upper glow immediately below the status row. A soft attenuation mask
reduces only the two lower corner pools while leaving the straight edge glow
strong. Vertical header labels
are offset down and inward from the rounded top corners and the right label is
rotated for reading from the right/bottom edge. This remains one Pillow renderer
and one logical input path, not a second menu surface or a fabricated PTT adapter.

## Configuration and storage

Mediathek-Suchläufe werden in der Anwendungsebene entprellt und anschließend als
ein relativer Befehl an denselben zentralen mpv-Prozess übergeben. Die
Anwendungsebene erzeugt weder einen zweiten Player noch einen eigenen A/V-Takt.
Abspielposition, Dauer und Vorpuffer stammen aus mpv; der Verlauf speichert nur
stabile Inhaltsmetadaten und niemals eine Rohmedienadresse.

- repository defaults: `config/*.toml`
- installed live configuration: `/etc/openr4d10/*.toml`
- current default copies for comparison: `/etc/openr4d10/*.toml.dist`
- immutable application release: `/opt/openr4d10/releases/<version>`
- active release symlink: `/opt/openr4d10/current`
- ephemeral runtime output: `/run/openr4d10`
- bounded brightness handoff: `/run/openr4d10-backlight/brightness.request`
- persistent application state: `/var/lib/openr4d10`
- non-secret SQLite state: `/var/lib/openr4d10/openr4d10.sqlite3`
- service logs: system journal, unit `openr4d10.service`
- transient WLAN repair request: `/run/openr4d10/wifi-repair.request`
- non-secret WLAN repair status: `/var/lib/openr4d10/wifi-repair-status.json`
- non-secret hotspot state: `/var/lib/openr4d10/hotspot-status.json`
- local hotspot secret: `/var/lib/openr4d10/hotspot-passphrase` (0600,
  never part of status, SQLite or backup)

Portable core backups contain a SQLite online-backup snapshot plus a public
manifest and SHA-256. Restore accepts exactly those two archive members,
validates integrity and schema compatibility, requires the runtime directory to
be absent (service stopped), and requires explicit replacement of an existing
database. Credentials and bulk media are outside this format.

The installer never overwrites live configuration. It refreshes only the
`.dist` files. `StateStore` applies explicit SQLite migrations and stores only
non-secret state: settings, service readiness, stations, channels, media and
recording metadata. Secret-like setting keys are rejected. No credential store
exists in the application; future credentials require a separate protected
mechanism.

Display brightness is the non-secret integer setting
`display.brightness_percent` with an accepted range of 0 through 100. The
`ServiceCatalog` remains its single persistence owner. At application
construction the saved value is passed to the configured display adapter; a
web change is first accepted by the existing `WhisplayDisplay` owner and then
committed to SQLite. A failed database write attempts to restore the previous
hardware value. BCM22 is not a native PWM output on the verified Zero 2 W
mapping. The installed `pwm-gpio,gpio=22` overlay therefore owns it and uses
the kernel's high-resolution timer rather than an application-scheduled pulse
thread. Reset and data/command remain ordinary `libgpiod` lines.

The unprivileged application never writes PWM sysfs. `_KernelPwmBacklight`
atomically publishes only one 0600 integer request below
`/run/openr4d10-backlight`. A fixed root-owned systemd path/service validates
the owner, mode, exact 0–100 range and the `pwm_gpio@22` device before applying
the active-low duty. The helper is the sole sysfs writer; neither a URL nor an
arbitrary path crosses this boundary. The native player no longer claims
BCM22. An early initializer holds it off until the first decoded boot frame,
after which the player queues 100 percent through the same fixed request.
Application handoff then restores SQLite brightness without changing the PWM
owner.

The non-secret setting `ui.accent_color` (`#RRGGBB`) is restored into the one
`WhisplayDisplay` renderer. The browser may change it only through the bounded
`display_appearance` action; there is no CSS-only device preview or second
appearance store. The closed player edge glow is a permanent part of that
renderer, not a stored option. A stale `ui.screen_border_enabled` row from
0.10.26 through 0.10.28 is ignored.

The built-in `pisugar3` power backend is a narrow read-only I2C boundary. It
opens `/dev/i2c-1`, selects the documented `0x57` controller, verifies version
`3` and application mode `0x0F`, and then reads calculated capacity register
`0x2A` through the manufacturer's SMBus byte-data transaction. Split raw
write/read transactions are forbidden because the real controller returns the
version byte again after their STOP condition. The adapter exposes only model,
ready state and bounded percentage. Controller writes and an additional
PiSugar network service are intentionally absent.

## Service catalog

`ServiceCatalog` is the single inventory for device and web UI. It currently
covers system, web radio, AmbientR4D10, podcasts, local media, recorder, BrandMeister, remote SDR,
private PTT, Mumble, Discord, Telegram, feeds, webcams, YouTube audio, Spotify,
ARD/ZDF/international media, speech, Bluetooth, remote Codex and TeamSpeak.
Each entry declares capabilities, implementation boundary, external executable
requirements and whether an individual local login is required. Status output
never contains a credential value and does not describe an external adapter as
ready merely because its menu entry exists.

Account-bearing integrations use the protocol in
[`SERVICE_ADAPTERS.md`](SERVICE_ADAPTERS.md). Their code and credentials stay
in separate system services; the core connects only to a service-named Unix
socket and exchanges bounded JSON. A successful status handshake is required
before an external catalog entry becomes ready.

Service activation is persistent. Core modules (`system`, web radio, local
media, recorder, feeds and the camera library) start enabled; external modules
start disabled. Disabled modules are not probed or reported as ready. Enabling
an external module still requires its manifest and successful handshake, and
disabling an active media module stops its current playback or recording.

`MpvEngine` starts lazily and controls mpv through an inherited Unix socket
using the documented JSON IPC. It disables user configuration and terminal
input. Video decoding uses the headless `vo=null` output with audio-clock
synchronization. The physical renderer asks for a software JPEG screenshot
asynchronously; this reuses mpv's actual current frame instead of introducing a
second decoder or synthetic clock. `StreamRecorder` invokes ffmpeg through an argument array with
`shell=False` semantics and writes 64-kbit/s Opus below the state directory.
The engine associates asynchronous `start-file` and `end-file` events by mpv's
`playlist_entry_id`; an end event from a replaced entry cannot overwrite the
state of the newer entry that is already playing. The successful `loadfile`
response publishes the new entry ID before those asynchronous events on mpv
0.40, so it becomes authoritative immediately; `start-file` then confirms the
playing state.
Network URLs are limited to HTTP(S), reject embedded credentials and are
redacted before appearing in status. Local media must resolve below the
approved media directory.

`IcyRadioBuffer` opens a second bounded, credential-free HTTP(S) read of the
selected radio stream and requests ICY metadata. Opening the radio view tunes
this already existing silent buffer even before audible playback, so the UI can
show `Artist – Title` and retain the beginning without adding a separate
metadata adapter. If ICY metadata is absent, the device shows a localized
end-user fallback rather than player, ALSA or backend diagnostics. At most 32 MiB of the current
track is retained in memory. A radio-context PTT press marks that buffer for
storage; the next metadata title boundary atomically writes the complete
available track beginning. Continuous mode marks every delimited track. Missing
or malformed metadata is never guessed: the bounded material remains a review
item. The library normalizes `Artist - Song.mp3` and stores it below the fixed
`Media/Music/<Artist>/` tree. Whisplay microphone captures use the separate
`Media/VoiceRecorder/JJMMTT/` tree. The library checks metadata, checksum and
Chromaprint fingerprint duplicates and never exposes local paths. Startup moves
only the former managed `Media/recorded` tree into `Media/Music`; arbitrary user
folders are never reclassified.
The real SWR3 ICY format `Title / Artist` is the one verified reverse-order
case and is normalized to `Artist – Title`; unknown formats remain verbatim.
Optional covers use rate-limited MusicBrainz search and Cover Art Archive data,
then pass through the existing bounded decode/re-encode boundary.

Recorded-media playback reuses the one private mpv instance. `My Soundmix`
loads favorite recordings in random order with an endless playlist; the all-
recordings action shuffles once. Previous, next, favorite and confirmed-delete
operations use stable database IDs. Start volume is always 30 percent.

The microphone VoiceRecorder is an explicit exclusive audio owner. Entering
its view first stops BrandMeister, every Ambient layer, the common mpv source
and the ICY radio buffer. Its pending directory contains an atomically updated
edit manifest plus one working MP3. The logical cursor is moved in one-second
steps by `right_outer`, in 0.1-second fine steps by `left_outer`, or directly
to start/end by `left_inner`; `right_press` uses exact absolute mpv seek and
toggles playback from that cursor. If the cursor is exactly at or beyond the
non-empty working file's end, that explicit Play action first persists cursor
zero and starts from the beginning; it does not enable looping. A later PTT
capture uses ffmpeg through an argument-only boundary to splice the new stereo
segment over the covered interval while preserving the prefix and any
unreached suffix. The manifest
and captured segment remain recoverable until the working MP3 is replaced.
Leaving the service finalizes that working file in the fixed
`Media/VoiceRecorder/JJMMTT` tree. Recorder playback temporarily owns a fixed
100-percent player level; its entry remembers and its exit restores the prior
global service volume. The recorder header names the boundary axis `MIN/MAX`.
Its yellow `↔` value and the fine-seek `±` value share a recorder-only fixed
column at x=90, leaving at least six pixels after the corresponding label.
Normal service headers retain their existing compact value column.

VoiceRecorder PTT edges are a separate latency-critical path inside that same
recorder. The physical input callback reads only the display's lock-free routing
context, starts or stops capture before any renderer call and never performs a
synchronous full-frame transfer. The display queues a four-region ST7789 glow
update, while the normal recorder frame loop renders the waveform at up to 10 Hz from
cached telemetry. Network, SSID and power reads are excluded from those fast
frames. The playhead is a white two-pixel overlay drawn after every stereo bar,
so it remains visible at the live end and at a paused seek position. Segment
duration is probed from the closed audio file instead of trusting wall time.
During recorder playback the 10 Hz overlay reads mpv's actual absolute position,
moves that same playhead and uses the central green audio-active glow; pausing
leaves the cursor at the last reported position.
Playback is opened with one JSON-IPC `loadfile` command whose per-file `start`
option contains the visible cursor position. Do not restore the former
`loadfile`-then-`seek` sequence: loading is asynchronous and mpv can reject the
early seek while already emitting audio, leaving the application unaware of
the active playback. The 10 Hz following updates are deliberately not written
to the recovery manifest; pause, stop and explicit seek boundaries persist the
final cursor instead.

Recorder seek, boundary and play/pause inputs use one semantic update and one
native repaint. They do not first repaint the presentation-only encoder state
and then repaint the resolved recorder state, and they reuse cached receiver
and power telemetry. RGB565 conversion is performed by Pillow channel
operations rather than a Python per-pixel loop. The recorder loop schedules a
fixed 10 Hz ceiling by subtracting render time from the next wait. The display
adapter also caches the last image it actually presented; the browser preview
encodes that cached frame without rerendering or holding the SPI lock through a
second complete composition.

All normal full-panel presentations share a 10 FPS ceiling. The adapter spaces frame
starts by at least 100 ms while the recorder's normal timeline uses up to 10 Hz;
only the small priority PTT glow regions bypass the full-frame cadence. Cached
TrueType fonts and quantized compositor glow layers remove repeated filesystem
and Gaussian-blur work. Browser key-repeat detents are coalesced in order before
they enter the bounded device-input API, so the resulting rotation is preserved
without creating an HTTP or display backlog.
Running Mediathek video is the other explicit partial-update exception: only its
240 x 175 rectangle from `(0, 105)` through the physical bottom edge may run at
up to 25 FPS. Pausing or leaving video mode
stops that cadence immediately and never raises the full-panel limit. Each such
frame bypasses both the complete UI renderer and complete 240 x 280 RGB565
conversion; scaling, conversion and SPI transfer are region-only.
While a logical hardware or browser control is active, periodic recorder
timeline frames yield their display slot. The resolved interaction frame still
renders immediately; only the redundant periodic frame is skipped. After 200 ms
without another input edge/detent, deadline-based timeline rendering resumes.
Service-axis navigation follows the same one-frame rule: the native adapter
changes its ordered state under the display lock without transferring an
intermediate panel image, application entry/exit lifecycle work is resolved,
and one final cached-telemetry frame is presented. Debouncing or coalescing may
bound event pressure, but it must preserve the resulting rotary distance.
Resolved media actions use that same rule: Play/Pause, channel and volume
mutate ordered display state without presenting a stale preliminary full frame,
then publish exactly one authoritative result frame from cached receiver,
network, power and system telemetry. They never wait for synchronous telemetry
collection; periodic refresh owns that work.
Periodic frames also carry the interaction generation captured before their
overlay work. If an input transaction starts or finishes before publication,
that stale periodic frame is discarded. The resolved interaction frame itself
does not use this discard guard. This prevents a precomputed 10 Hz DMR frame
from restoring DMR after the service axis has already presented another view.

The local control server uses persistent HTTP/1.1 connections and disables
Nagle buffering on accepted LAN sockets. Browser key repeats therefore reuse a
warm transport instead of paying a TCP setup and small-packet delay for each
detent; the bounded ordered input queue remains the backpressure boundary.

On the verified four-core Pi Zero 2 W, CPU affinity gives background work
(including ffmpeg/mpv and the level parser) cores 0–1, native UI/SPI core 2 and
the physical input poller core 3. Processes spawned from the input callback are
immediately moved back to cores 0–1 so inherited affinity cannot starve input.
The mapping is best-effort and disabled unless `/proc/device-tree/model`
identifies a Pi Zero 2 with at least four CPUs.

The entry lifecycle is required for both navigation and process startup. On
startup the application resolves the persisted view before starting the web
server or waiting through the semantic boot sequence. If that restored view is
`REC`, it synchronously invokes the existing `voice_recorder_open` action and
then rebuilds the first overlay from the silenced state. The resolved overlay
is cached only until the first frame, so normal refreshes do not repeatedly
reset recorder playback or volume. Treating restored view state as a
presentation-only value previously allowed `service=REC` and
`active_service=brandmeister` to coexist after reboot.

Physical media surfaces use one shared asymmetric mask: 12-pixel upper corners,
43-pixel lower corners matching the panel, and equal minimal side/bottom
margins. This applies to station artwork and visual service media rather than
one-off sender layouts.

The web dashboard persists named radio stations without query strings and can
rescan the private media directory for a bounded set of supported extensions.
It renders the compact sortable personal list first and a separate inactive
catalog list below it. The immutable catalog is not a second active-player
copy: a station exists in exactly one of those two regions. Activating copies
the reviewed entry into the personal SQLite list; deactivating removes only
that personal row, so the catalog entry becomes available again. The initial
seed contains exactly the original ten stations. Later catalog additions never
activate themselves on a new release. Search, language and category filters are
client-side operations over already-public metadata and do not change personal
order. The active list's play action uses the normal yellow interface accent.
The service catalog is likewise rendered as one compact list. Client-side
search compares a normalized query with the complete already-public service
object plus its localized visible labels; it neither sends queries nor exposes
new server data. Service logos are optional checked-in presentation metadata,
never guessed remote URLs.
The scanner resolves every candidate, rejects paths outside the media root and
removes stale database rows. Status output exposes stable IDs, display names
and sizes, never local filesystem paths or raw stored stream URLs. SQLite
access is serialized because the application loop and threaded HTTP server
share one `StateStore` connection.

`BoundedFetcher` supplies the native feed, podcast and HTTP camera modules. It
accepts only HTTP(S) URLs without embedded credentials and enforces response-
type, size and timeout limits. The feed reader parses at most 50 RSS/Atom
entries and converts markup to bounded text. The persistent camera library
stores at most 100 ordered Snapshot, MJPEG or RTSP sources as `webcam` channels.
MJPEG consumes only the first complete JPEG frame; RTSP invokes the fixed
`/usr/bin/ffmpeg` binary with an argument array, TCP transport, one-frame output
and a hard timeout. Every path accepts at most 5 MiB, rejects excessive pixel
dimensions and always decodes, resizes and atomically re-encodes JPEG rather
than serving untrusted remote bytes. Persistent camera URLs reject credentials
and query strings. Authenticated cameras and ONVIF therefore belong in a
separate secret-bearing adapter and are not falsely reported as native support.

`PodcastReader` accepts at most 3 MiB of RSS/Atom XML and at most 50 entries
with HTTP(S) audio enclosures. A subscription is stored as a `podcasts` channel
whose metadata contains the local feed address; public snapshots expose only
its host, title, description and homepage. Raw feed and enclosure URLs remain
inside the core. The process-local episode cache uses stable hashes for public
episode IDs. `podcast_play` resolves an ID back to the cached enclosure and
hands it to the one `MpvEngine`; therefore explicit podcast playback replaces
the previous audio owner, while browsing subscriptions does not. Persistent
feed URLs with query strings are rejected to prevent signed/private tokens from
entering SQLite and portable backups.

`MediathekCatalog` performs credential-free search across a fixed German public
broadcaster catalog through one bounded MediathekViewWeb JSON request: POST
only, HTTPS only, ten-second timeout, 2 MiB response ceiling and 30 public
results. An all-broadcaster query may inspect at most 120 raw rows before exact
channel filtering. Exact matching prevents short names such as `SR` from also
accepting `SRF`. A bounded 16-entry, five-minute memory cache avoids repeated
network waits for the same current selection. Private-address, local and
credentialed sources are rejected. The private result cache retains a lower-
bandwidth device source, the preferred browser-video source and the broadcaster
website URL; public snapshots expose only an opaque item id, provider, channel,
topic, title, description, duration and timestamp. Explicit device Play resolves
that opaque id into the central `MpvEngine`. The local browser-video route
accepts only the same cached ID and returns a no-store redirect instead of
proxying media through the Pi. Search, provider switching, selection and browser
video do not change device audio ownership or device focus. Explicit device
play stores the originating provider/result identity, focuses `PLAYER` and
exposes the one-based result position so physical/browser channel input can
cycle the same bounded list. See `MEDIATHEK.md`.

AmbientR4D10 stores its ordered scene library in the existing generic
`channels` table under the `ambient` service ID. Built-in definitions in
`ambient.py` bind each public audio URL to a review page, credit and license;
public snapshots expose those attribution fields but never the playable URL.
The seed marker runs once, so user deletion, custom additions and ordering are
not undone by an update. Scene selection changes only navigation state.
`ambient_play` alone resolves the private source and hands a one-item endless
playlist to the single `MpvEngine`, thereby deliberately replacing the prior
audio owner. Device labels and descriptions are localized independently of the
browser while custom user names remain unchanged. See `AMBIENT.md`.

BrandMeister uses the same generic ordered `channels` table for a non-secret
device talkgroup quick list. The native receive-only adapter owns one bounded
HoseLine WebSocket thread and one lazy `aplay` PCM sink for the verified
`whisplaysound` ALSA device. It decodes only the documented MessagePack call,
alias and G.711 µ-law packet shapes. Browser controls and physical encoder
events mutate the same SQLite rows. A separate bounded daily cache of the
official public talkgroup-name endpoint supplies search metadata without
placing thousands of catalog rows into every status snapshot.
The right-docked menu-back badge owns its central interior through the physical
panel edge. DMR country and replacement position counters are aligned to a
separate right edge at x=178, as is the Ambient layer counter, so list metadata
can never be composited over the filled back-arrow glyph.
The application measures the DMR PTT press centrally: release before two
seconds toggles the selected TG, while one cancellable timer opens the country
filter over the cached catalog exactly at the two-second threshold without
waiting for release. That subsequent release is consumed. A pending sixth
activation is an explicit state with a bounded five-row replacement list; only
confirmation performs the atomic disable/enable swap, and cancel preserves the
prior subscriptions.
Because the device catalog is enabled-first, disabling the selected TG also
selects the first remaining enabled row after the same atomic metadata update.
This changes only cursor state; it never enables another TG. With no remaining
enabled row, the just-disabled TG remains the deterministic selection.

Curated radio and news source definitions remain reviewable data in `presets.py`,
separate from playback and parser logic. Radio definitions are seeded exactly
once into the ordered SQLite station library only when `default_enabled` is
true; the seed marker prevents deleted defaults from returning. All other
definitions remain inactive catalog data until selected. Channel stepping,
Enter-at-stop and the web editor all use the persistent personal list. Public status includes display metadata and a
local artwork route, but omits the underlying stream, feed and remote artwork
addresses. Selecting a radio resolves the reviewed stream only inside the
core. Preset artwork uses the same bounded-download boundary as camera images,
is decoded and re-encoded to a maximum 256 x 256 JPEG in the private cache, and
falls back to a browser-generated initials tile when retrieval fails. Current
sources and their review references are recorded in `PRESETS.md`.

The browser presents that one model through two radio sub-tabs rather than two
simultaneously long lists. Shared custom-add, metadata search, language and
category controls sit above both tabs. Creating a custom station or activating
an inactive preset appends it to the persistent personal order and selects the
active tab; both selectors stay visible and only the selected selector receives
the readable accent treatment. No second catalog state exists in JavaScript or SQLite. The generic
direct-URL player is intentionally not exposed on the radio page, while the
core's checked playback path remains available to other service adapters.

The debug navigation overview is versioned in `MENU_TREE.md`. It is not served
by the web application and is not a visible device-menu item.

The native weather module reuses the bounded-download boundary. The primary
Germany channel uses the official DWD radar-film GIF; its bounded animation
frames are decoded and re-encoded as local JPEGs. Separate Germany and Europe
satellite channels read the official DWD WMS capabilities no more often than
every five minutes and select up to eight recent timestamps from
`Satellite_meteosat_1km_euat_rgb_day_hrv_and_night_ir108_3h`. Missing or invalid
frames are skipped; a DWD or network outage leaves the last valid cache usable.
A one-time guarded metadata upgrade changes only the untouched old Germany
channel to radar. A separate one-time addition appends the retained Germany
satellite channel to existing libraries without recreating it after deletion or
resetting existing order. Browser and physical display read only the local
cache.

For a fresh machine, `bootstrap.sh` downloads a GitHub-generated source archive
over HTTPS into a private temporary directory. It checks paths and archive
integrity before extraction, then invokes the same local `install.sh`. Git is
not an installation dependency. The reviewed official Whisplay sound-card
source is pinned and vendored with its Apache-2.0 license, so audio installation
also requires neither Git nor a second source download. The installer builds it
in a private temporary directory for the running kernel, installs the unified
WM8960/ES8389 module and overlay, and leaves activation to the required reboot.

## Privileged web-requested updates

The HTTP process never runs an installer, invokes a shell or receives sudo
permission. An explicitly confirmed `system_update` control atomically creates
only `/run/openr4d10/update.request`. A root-owned
`openr4d10-update.path` unit watches that exact file and starts the fixed
`/usr/local/sbin/openr4d10-update` helper. The helper accepts no browser
arguments or URL, serializes runs with a private lock, downloads only the
checked-in public `bootstrap.sh` URL over HTTPS and therefore rejoins the sole
existing bootstrap/install path.

The helper publishes bounded, non-secret JSON at
`/var/lib/openr4d10/update-status.json`; the application exposes it with normal
status data. Requests are rejected while state is `queued` or `running` in the
current boot.
Installer failure preserves the normal configuration rules, records a generic
failure pointing to the root helper's journal and attempts to start the current
release so the dashboard can report the failure.
The helper passes only the fixed `--no-reboot` maintenance flag to the existing
bootstrap, then reads the installed version, atomically records `rebooting`,
syncs and requests the reboot itself. This ordering prevents reboot from killing
the helper while its status still says `running`. For compatibility with older
installed helpers, a `running` status carrying a different boot ID is treated as
an interrupted failure rather than blocking all future requests or claiming an
unconfirmed success. No arbitrary command, repository, branch or client-
selected installer option crosses the web/root boundary.

The sole installer detects an existing state database before package or release
changes. It uses the existing SQLite online-backup format to create a dated,
secret-free archive below `/var/lib/openr4d10/backups`. Backup failure is fatal,
so the update never starts without a recoverable copy of station order and all
other non-secret state.

A root-owned `openr4d10-update-recover.service` runs before the application on
every boot. It atomically converts previous-boot `queued`/`running` records to
`failed` and previous-boot `rebooting` to `completed`. It does not kill a live
same-boot package transaction. The application keeps the same defensive
read-time normalization, so both newly installed and older status files leave
the update button retryable after reboot.

## Privileged WLAN repair

The unprivileged HTTP process accepts one strictly bounded repair request with
SSID, passphrase and an explicit replace flag. It writes those values only to a
new 0600 file at `/run/openr4d10/wifi-repair.request`; neither the SQLite store
nor the public status snapshot receives a credential value. A root-owned
systemd path starts the fixed `openr4d10-wifi-repair` helper, which accepts no
arguments and supports only NetworkManager on the fixed `wlan0` interface.

The helper validates SSID and WPA-PSK limits without printing the values and
creates a root-only NetworkManager keyfile with a new UUID. Neither `nmcli` nor
another process receives the passphrase in its argument vector. Only after the
new profile is active may an explicitly confirmed replacement remove the other
Wi-Fi profiles. A failed activation removes only the temporary new profile and
leaves existing profiles available. The web request is removed on every exit;
the bounded public status contains only
queued/running/succeeded/failed plus a generic message. The current dashboard
uses local HTTP, so this operation is documented for trusted private networks
only until a local HTTPS provisioning boundary exists.

## NetworkManager fallback hotspot

The existing NetworkManager instance remains the sole owner of `wlan0`. A
root-owned, argument-free timer helper checks the active NetworkManager profile
without accepting browser input. An active infrastructure profile clears the
fallback timer. If no client profile can be activated, the helper waits through
a disconnect grace period and then loads one fixed AP profile with
`ipv4.method=shared`. NetworkManager supplies the private address, DHCP and DNS;
OpenR4d10 does not start parallel `hostapd`, `dnsmasq`, `wpa_supplicant` or
network configuration services.

The setup SSID contains a non-secret suffix derived from the `wlan0` hardware
address so nearby devices can be distinguished. Its WPA2 passphrase is randomly
generated on the device, stored only in the root-only NetworkManager keyfile and
a 0600 file owned by the display service account. The helper's public status is
bounded to mode, SSID and setup address. The Whisplay adapter reads the secret
only while that public state says the setup hotspot is active and paints SSID,
passphrase and `http://10.42.0.1/` directly on the physical setup screen. The
semantic frame, `/api/status`, SQLite, logs and portable backup never receive
the passphrase.

The timer does not periodically tear down an active setup hotspot to probe for
client networks. This avoids flapping on unstable WLANs. Submitting a confirmed
WLAN repair activates the new infrastructure profile on the same interface;
that successful transition naturally replaces the AP. A reboot starts the
normal saved-profile attempt and grace period again.

`SystemTelemetry` resolves the actual SSID through fixed, bounded `nmcli`
queries using the active connection UUID. It reports the SSID beside the Wi-Fi
symbol, `OFFLINE` when there is no active Wi-Fi profile, and the setup SSID
while the AP profile is active. A NetworkManager connection-profile name is
not substituted for the SSID.

## Startup sequence

1. `openr4d10-backlight-init.service` claims BCM22 through kernel `pwm-gpio`
   and keeps the active-low backlight dark.
2. `openr4d10-boot.service` opens SPI0/CS0 plus reset/DC only, queues full
   brightness after its first complete frame and plays the native animation;
   its final second loops.
3. `systemd` creates application runtime and state directories as the
   `openr4d10` user.
4. The CLI parses and validates both TOML files.
5. Adapters are created from explicit backend names.
6. The service catalog migrates the non-secret state database and evaluates
   local dependencies.
7. The application resolves the persisted device view. A restored `REC` view
   runs the exclusive VoiceRecorder entry action synchronously and silences
   every other audio owner before startup continues.
8. The persisted display brightness and device language are loaded into the
   display adapter without opening a second hardware path.
9. The local web dashboard binds to the configured local address and port.
10. The semantic text boot manifest is rendered when enabled.
11. The semantic dashboard state is refreshed at the configured interval and
   exposed through `/api/status`.
12. The Whisplay UI calls `claim_display()`, waits for the boot player to close
   SPI/GPIO and keeps the ownership lock for its entire lifetime.
13. `SIGTERM` or `SIGINT` stops the loop, database and HTTP server cleanly.

Both display services declare the shared `/run/openr4d10-boot` runtime. This is
also required when the installer starts the application in an already running
system where the early-boot player did not run. In that case the application
creates and locks the handoff file itself and initializes the panel directly;
on a normal reboot the native player creates the same runtime first and the
release handshake remains unchanged.

An unconfigured display consumes semantic frames without touching GPIO. An
unconfigured power adapter returns an explicit state that the UI surfaces as
`Hardware configuration required`.

## Failure behaviour

- invalid TOML or invalid adapter arguments: startup fails with a precise error
- receiver/power helper failure: dashboard remains alive and shows adapter error
- display helper failure: logged; next render retries
- missing boot manifest: boot sequence is skipped, main dashboard still starts
- unconfigured hardware: warning, not a crash or a fabricated fallback driver

The `doctor` command distinguishes errors from configuration-required warnings.
Exit codes are `0` ready, `1` invalid/error, and `2` hardware action required.

## Security model

The service runs as a dedicated unprivileged user with a read-only system view,
private temporary directory, no new privileges and writable access only to its
runtime and state directories. It receives only `CAP_NET_BIND_SERVICE`, which
allows the unprivileged process to bind local HTTP port 80. The generic command
adapter uses an argument array and `shell=False`; it never interpolates input
into a shell command.

Hardware device access is not granted globally. The early boot service's closed
device policy permits only `/dev/spidev0.0` and `/dev/gpiochip0`. The
application runs as `openr4d10`, receives only the `gpio`, `spi`, `audio` and
`i2c` supplementary groups. Its closed policy permits the same LCD devices,
the single `/dev/i2c-1` node for the verified PiSugar 3 address, plus the
standard `char-alsa` device class for media playback/recording; it still has no
access to homes or unrelated hardware. Codec control
and detection stay inside the kernel/ALSA driver installed by the privileged
installer; the application itself never selects or guesses a codec revision.
# Audio boot ownership

BrandMeister talkgroups persist only as configuration. Process startup warms
the public catalog but never calls the HoseLine receiver. A real DMR audio
owner can be created only by explicit PLAY/ENTER input. New media playback also
checks the receiver's actual runtime status, not only `active_service`, before
stopping DMR, so a stale UI/service label cannot leave hidden ALSA audio alive.

Device-side Mediathek group lookup is dispatched to a bounded background
worker. The input/SPI path only changes selection and queues work; it never
waits for the network query. A generation token prevents a superseded or
cancelled lookup from taking playback ownership later.
