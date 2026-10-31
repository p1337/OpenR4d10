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
Each localized control label and its larger value are positioned from their
actual font bounding boxes so their visible glyph tops align exactly in both
header rows. The two halves are mirrored: labels precede values on the left,
while values precede right-aligned labels on the right. This keeps all values
toward the center divider and all control names toward the physical controls.
When `DeviceUiState.menu_open` identifies the main menu, the renderer exits the
player branch entirely and paints the localized heading plus the documented
ten-item settings list. The right outer encoder moves only the bounded menu
selection, and a short right press opens the selected page instead of reaching
media controls. Menu history stays inside `DeviceUiState`; an active PTT press
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

- repository defaults: `config/*.toml`
- installed live configuration: `/etc/openr4d10/*.toml`
- current default copies for comparison: `/etc/openr4d10/*.toml.dist`
- immutable application release: `/opt/openr4d10/releases/<version>`
- active release symlink: `/opt/openr4d10/current`
- ephemeral runtime output: `/run/openr4d10`
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
hardware value. No parallel settings file, daemon or GPIO owner exists.
BCM22 is not a native PWM output on the verified Zero 2 W mapping. The same
`WhisplayPanel` process therefore owns that line through the Raspberry Pi OS
`python3-lgpio` binding and uses `lgpio.tx_pwm`, whose timing loop is in the
packaged C library. Reset and data/command remain ordinary `libgpiod` lines.
The replaced Python PWM thread must not be reintroduced; its scheduler jitter
was visibly confirmed as brightness flicker on the real panel.
The `lgpio` module creates its private `.lgd-nfy*` notification pipe in the
process working directory during import. The hardened application unit therefore
uses its existing `RuntimeDirectory=/run/openr4d10` as `WorkingDirectory`.
That path was already the unit's private writable runtime boundary;
`ProtectSystem=strict` and the existing `ReadWritePaths` remain unchanged.
The packaged 0.2.2 binding rejects an idle `tx_pwm(..., 0, 0)` stop request
with `bad PWM micros` despite its API text. `_LgpioPwm` therefore tracks
whether it has successfully started PWM and sends the stop request only in
that state. Steady endpoint writes never issue a speculative stop. The real
panel still showed a rarer bright/dark jump below 100 percent because the
periodic renderer called the brightness path after every frame and re-armed an
unchanged PWM waveform. `_LgpioPwm` now caches its current duty cycle and does
not call `tx_pwm` unless the requested duty actually changes.

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
covers system, web radio, local media, recorder, BrandMeister, remote SDR,
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
media, recorder, feeds and camera snapshots) start enabled; external modules
start disabled. Disabled modules are not probed or reported as ready. Enabling
an external module still requires its manifest and successful handshake, and
disabling an active media module stops its current playback or recording.

`MpvEngine` starts lazily and controls mpv through an inherited Unix socket
using the documented JSON IPC. It disables user configuration and terminal
input. `StreamRecorder` invokes ffmpeg through an argument array with
`shell=False` semantics and writes 64-kbit/s Opus below the state directory.
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
item. The library normalizes `Artist – Song`, stores by artist, checks metadata,
checksum and Chromaprint fingerprint duplicates, and never exposes local paths.
The real SWR3 ICY format `Title / Artist` is the one verified reverse-order
case and is normalized to `Artist – Title`; unknown formats remain verbatim.
Optional covers use rate-limited MusicBrainz search and Cover Art Archive data,
then pass through the existing bounded decode/re-encode boundary.

Recorded-media playback reuses the one private mpv instance. `My Soundmix`
loads favorite recordings in random order with an endless playlist; the all-
recordings action shuffles once. Previous, next, favorite and confirmed-delete
operations use stable database IDs. Start volume is always 30 percent.

Physical media surfaces use one shared asymmetric mask: 12-pixel upper corners,
43-pixel lower corners matching the panel, and equal minimal side/bottom
margins. This applies to station artwork and visual service media rather than
one-off sender layouts.

The web dashboard persists named radio stations without query strings and can
rescan the private media directory for a bounded set of supported extensions.
It renders that persistent station collection once, in the compact sortable
editor/list; there is no second preset-card copy of the same rows. The list's
play action uses the normal yellow interface accent.
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

`BoundedFetcher` supplies the native feed and camera modules. It accepts only
HTTP(S) URLs without embedded credentials and enforces response-type, size and
timeout limits. The feed reader parses at most 50 RSS/Atom entries and converts
markup to bounded text. Camera slots accept at most 5 MiB, reject excessive
pixel dimensions and always decode, resize and atomically re-encode JPEG rather
than serving untrusted remote bytes.

Curated radio and news source definitions remain reviewable data in `presets.py`,
separate from playback and parser logic. Radio definitions are seeded exactly
once into the ordered SQLite station library; the seed marker prevents deleted
defaults from returning. Channel stepping, Enter-at-stop and the web editor all
use this persistent list. Public status includes display metadata and a
local artwork route, but omits the underlying stream, feed and remote artwork
addresses. Selecting a radio resolves the reviewed stream only inside the
core. Preset artwork uses the same bounded-download boundary as camera images,
is decoded and re-encoded to a maximum 256 x 256 JPEG in the private cache, and
falls back to a browser-generated initials tile when retrieval fails. Current
sources and their review references are recorded in `PRESETS.md`.

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

1. `openr4d10-boot.service` opens SPI0/CS0 plus only the verified LCD GPIO
   lines and plays the native animation; its final second loops.
2. `systemd` creates application runtime and state directories as the
   `openr4d10` user.
3. The CLI parses and validates both TOML files.
4. Adapters are created from explicit backend names.
5. The service catalog migrates the non-secret state database and evaluates
   local dependencies.
6. The persisted display brightness and device language are loaded into the
   display adapter without opening a second hardware path.
7. The local web dashboard binds to the configured local address and port.
8. The semantic text boot manifest is rendered when enabled.
9. The semantic dashboard state is refreshed at the configured interval and
   exposed through `/api/status`.
10. The Whisplay UI calls `claim_display()`, waits for the boot player to close
   SPI/GPIO and keeps the ownership lock for its entire lifetime.
11. `SIGTERM` or `SIGINT` stops the loop, database and HTTP server cleanly.

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
