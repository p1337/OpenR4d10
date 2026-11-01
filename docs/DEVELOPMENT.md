# Development and diagnostics

## Local checks

Python 3.11 or newer is sufficient for the core. The physical renderer requires
Pillow; the target installer uses Debian's `python3-pil`, `python3-libgpiod` and
`python3-spidev` packages rather than downloading code with pip.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash -n bootstrap.sh
bash -n install.sh
bash -n boot/install.sh
bash -n vendor/pisugar-whisplay/audio/scripts/install.sh
bash install.sh --check --allow-unsupported
```

The last command is read-only. It validates the source tree and tests without
creating users, installing packages or changing systemd. `bootstrap.sh` is the
Git-free online entry point; `install.sh` remains the sole system installer.

## Test one rendered frame

Copy both example TOML files to a temporary directory, change the display
backend to `file`, and select a writable absolute output path. Then run:

```bash
PYTHONPATH=src python3 -m openr4d10 \
  --config /tmp/openr4d10.toml \
  --hardware-config /tmp/hardware.toml render-once
```

The resulting JSON is the complete boundary between core UI and a future
display helper. To render the actual 240 x 280 layout without hardware:

```bash
PYTHONPATH=src python3 -m openr4d10 \
  --config config/openr4d10.toml \
  --hardware-config config/hardware.toml \
  preview-ui --output /tmp/openr4d10-ui.png
```

Physical-renderer regressions must inspect the native 240 × 280 pixels, not a
browser approximation. Tests verify the compact header boundary, language
mapping, absence of date/footer/player-status text, enlarged artwork bounds,
the play button position and that main-menu rendering contains neither artwork
nor player title. They also verify the vertical ten-entry main-menu list,
selection scrolling, Enter selection without media side effects, PTT back
navigation, the framed filled back icon, player-only accent glow, label clearance
below the rounded top corners and the red/white edge-aligned PTT indicator only
for an explicit ready PTT context. The five curated languages
use the same renderer and fall back to English for unknown language codes.
Header tests additionally compare the visible bounding-box top of every
localized control label with its associated value; a fixed origin offset is
insufficient because the two font sizes have different metrics. They also
require the mirrored right-side order and one common right label edge. The
VoiceRecorder additionally uses `MIN/MAX` for its boundary axis and one fixed
x=90 value column for both yellow left-axis values; tests measure a minimum
six-pixel clearance from each label.
DMR country and replacement menu tests compare the central x=198..239,
y=70..93 back-badge crop with the generic menu badge. This pixel comparison
must remain identical even when a list position such as `1/5` is visible;
checking only that the counter text was emitted cannot detect an overlap.

Recorder performance regressions must prove that a PTT press/release does not
call the normal display snapshot, `apply_input()` redraw or `render_once()`
path. The edge may queue only the priority glow update. Tests also require the
ST7789 region coordinates and y-offset, a white two-pixel playhead rendered
after dense waveform bars, live elapsed position, file-probed segment duration
and the verified four-core split: background `{0,1}`, UI `{2}`, input `{3}`.
Do not move telemetry or remote artwork lookup back into the 10 Hz recorder
frame path.

Recorder seek, boundary and play/pause controls have a separate latency
regression: one resolved input may cause exactly one recorder repaint and must
not call the display adapter's presentation-only `apply_input()` first. The
10 Hz loop is deadline-based, not `render time + 100 ms`. RGB565 tests must keep
the exact big-endian wire bytes while the implementation stays free of a
Python per-pixel loop. `/api/device-screen.png` reads the adapter's last drawn
image; a recorder browser preview may poll that bounded endpoint at 10 Hz but
must never overlap its own image requests or raise the full `/api/status` rate.
Voice playback regression tests must also prove that the initial cursor is part
of the single mpv `loadfile` command and that consecutive 10 Hz mpv positions
advance the white playhead. Never reintroduce a separate seek immediately after
an asynchronous load, and never persist every live 100 ms position sample to
`edit.json`; only pause, stop and explicit navigation are persistence points.
They must additionally prove that Play at a non-empty recording's exact end
persists cursor zero and loads from zero, while a cursor before the end remains
unchanged. This is an explicit replay action, never an automatic loop.

The real-device performance gate measures semantic control, renderer/RGB565,
SPI presentation and browser preview separately. Normal full-frame starts are
capped at 10 FPS, and the intended input-to-visible-response target is 100 ms;
300 ms or more is a release blocker. Regression tests must preserve shared font
and quantized glow caches plus ordered browser detent coalescing. Never solve
backpressure by dropping the resulting rotary distance: combine adjacent steps
within the API's bounded `-10..10` range and send any remainder next.
The real-device stress check must include at least fifteen consecutive recorder
detents. Periodic timeline rendering must yield during the interaction and
resume after 200 ms of quiet; a late-series rise to 300 ms or more is a failed
release even when isolated first-step latency is acceptable.
Service navigation has an additional one-frame regression: the optimized
Whisplay path may call `apply_input_state()` once and render the resolved target
once, but must not call the presentation-producing `apply_input()` first.
Measure service entry and exit separately on the Pi; a result at or above the
same 300 ms gate blocks release. Input debouncing may combine pressure only
when it retains ordering and the complete logical movement.
Web-control latency tests must use one persistent connection after one warm-up
request and also report cold connection setup separately. The HTTP handler must
remain HTTP/1.1 with a valid `Content-Length`; returning to per-request HTTP/1.0
connections is a performance regression.

The verified 0.10.77 Pi gate measured 50 warm persistent-LAN recorder controls
at 86.8–178.4 ms (110 ms mean, none at or above 200 ms), ten full service
transitions at 101.8–232.8 ms (none at or above 300 ms), and 30 loopback
controls at 79–89 ms. Keep these as comparison baselines, not simulated timing.

## Release gate and device provenance

Local tests are necessary but never sufficient for a Pi release. After every
push, the GitHub Actions run for that exact commit SHA must finish successfully
for every configured Python version before the web updater or bootstrap is run
on the device. A failed, cancelled, skipped or still-running workflow blocks
deployment. Do not infer portability from a green Windows run: the physical
renderer deliberately uses Linux DejaVu font metrics, which can change fitted
text compared with Pillow's Windows fallback.

A red workflow is priority one, not a hand-off item. The active development
task remains unfinished: inspect the failing job and its logs immediately,
repair the repository, push the correction and repeat until the newest exact
commit is fully green. Never leave a known red `main` for a later session and
never report completion while it remains red.

The device receives source only through the fixed GitHub `main` bootstrap and
the archive it downloads. Never edit files below `/opt/openr4d10/current`, a
release directory, `/usr/local/bin`, `/usr/local/sbin` or the installed systemd
units to repair an application defect. Fix, test, commit and push the source;
wait for the exact GitHub commit to turn green; only then deploy it. Runtime
configuration under `/etc/openr4d10` and persistent state below
`/var/lib/openr4d10` remain device-owned and are not source patches.

The normal `run` command also creates a migrated non-secret state database in
the configured state directory. Tests must always point this at a temporary
absolute directory. Never add tokens, passwords or keys to this database; its
setting API rejects secret-like keys by design.

Test the portable metadata backup against a temporary state directory. Restore
must be tested only while the service is stopped and requires `--replace` when
the database already exists. The archive intentionally excludes configuration
secrets, WLAN data, media and recordings.

## Web dashboard

The installed service listens on port 80 by default. It serves only the tracked
files in `web/` plus the following endpoints:

- `/i18n.json` — fixed same-origin catalog for the five curated browser locales
- `/api/status` — current semantic frame and adapter state as JSON
- `/healthz` — simple service health response
- `POST /api/control` — bounded same-origin JSON media controls
- `/api/camera/<camera-id>` — locally re-encoded frame from a persistent
  Snapshot, MJPEG or RTSP camera entry
- `/api/radio-art/<preset-id>` — bounded, locally re-encoded preset artwork
- `/api/mediathek-video/<opaque-item-id>` — no-store redirect to the preferred
  already validated public broadcaster video; never accepts a URL
- `/api/device-screen.png` — exact current native 240 × 280 renderer output
- `/api/weather-frame/<validated-cache-name>` — locally decoded and re-encoded
  DWD satellite frame; remote WMS URLs are never browser image URLs

The control endpoint accepts only JSON up to 4096 bytes and rejects mismatched
browser origins. With the sole exception of the transient `wifi_repair`
handoff described below, it never accepts credentials; no credential is stored
in SQLite, status, backups or logs. It supports explicit
playback, pause, stop, volume and stream-recording actions plus bounded feed and
camera retrieval, persistent camera add/update/delete/reorder/refresh actions,
saved station management and local media rescans. Saved
station URLs containing query strings are rejected; temporary direct playback
is not persisted. `service_set_enabled` persists module activation; `system`
cannot be disabled and external modules still require their own adapter. Port,
bind address and static directory live in `[web]` in `openr4d10.toml`.

`wifi_repair` accepts exactly `ssid`, `passphrase`, `replace_existing` and
`confirmed`, with both booleans required to be true for the destructive
replacement mode. SSID is limited to 1–32 encoded bytes and passphrase to the
WPA-PSK contract. The application may create only the fixed 0600 runtime
request; it never calls `nmcli`. Tests must assert that neither status nor
responses contain SSID/passphrase, that a second queued request is rejected,
and that the installed helper uses the fixed `wlan0`/NetworkManager path with a
root-only keyfile and creates the new connection before deleting old profiles.

The automatic fallback is a separate fixed root boundary. Tests must require
the argument-free `openr4d10-hotspot` helper, its timer, the fixed `wlan0`
interface, NetworkManager AP mode, WPA-PSK, `ipv4.method=shared`, a disconnect
grace period and a non-autoconnecting setup profile. They must reject any
parallel `hostapd`/`wpa_supplicant` implementation and prove that the generated
passphrase is absent from hotspot status and `DeviceUiState.public_state()`.
The physical setup renderer may receive it only from the local 0600 secret
file. Unit tests use temporary status/secret files; they never use a real
credential.

Receiver telemetry tests mock the two fixed `nmcli` calls: active connection
UUID followed by that profile's `802-11-wireless.ssid` and mode. The displayed
label must be the actual SSID, not the connection ID and not the old literal
`WLAN`; failures and disconnected state become `OFFLINE`.

Browser localization tests extract every static `data-i18n*` reference and
every literal runtime `t()` key, require it in the checked-in catalog, require
all five non-empty translations, and compare placeholder sets. A new visible
browser message therefore requires translations for English, German, Polish,
French and Spanish in the same change. Locale switching persists in browser
storage as an early-load cache and must also call the bounded
`display_language` action. That action validates `en`, `de`, `pl`, `fr` or `es`,
redraws the physical display, persists `ui.language` in SQLite and publishes it
under `services.settings.language`. Tests must cover restart persistence,
delivery to `WhisplayDisplay`, invalid codes and browser control wiring.
Fixed renderer-owned help, readiness, menu-description and loading strings must
also use the same device catalog. Station names, programme titles and other
real content metadata remain verbatim.

`display_brightness` accepts exactly one integer `brightness_percent` from 0
through 100. The application applies it through the configured display adapter
and then persists it under `display.brightness_percent` in the existing SQLite
state. Status exposes the value only as
`services.settings.display_brightness_percent`. Tests must cover the default,
both bounds, invalid booleans/non-integers, restart persistence and delivery to
the Whisplay adapter. Do not add a second configuration file or a direct web
GPIO path. The early native boot player intentionally has no SQLite dependency;
brightness restoration begins at application display handoff.
The target implementation keeps BCM22 active-low but delegates every pulse
edge to the in-tree `pwm-gpio` kernel driver at a 1 ms period. Do not
reintroduce `threading`, `sleep`, `Event.wait` or `lgpio.tx_pwm`: normal
userspace scheduling caused load-correlated brighter and darker jumps on the
real battery-powered Pi. Unit tests must require the exact
`dtoverlay=pwm-gpio,gpio=22`, the fixed root helper/path boundary, active-low
polarity, and the real device-tree unit-address spelling `pwm_gpio@16` (hex for
BCM22). The helper may retain `pwm_gpio@22` only as a compatibility spelling.
Tests also require the duty mapping and an atomic, deduplicated 0–100 request. The application must
not receive sysfs write access.

The early initializer owns BCM22 before the native animation and sets 0
percent. The native player owns only reset/DC and queues 100 percent after its
first full frame. The normal display later restores the persisted value through
the same request. Tests must reject a GPIO22 request in the native player. Keep
the application's `ProtectSystem=strict`; its only added writable path is the
dedicated `/run/openr4d10-backlight` request directory.
The separately sandboxed early-boot unit also needs that exact runtime path in
`ReadWritePaths`, because its native player atomically publishes the first
brightness request there; it receives no other writable system path.

`display_appearance` accepts and persists only one `#RRGGBB` accent string.
The Whisplay renderer used for the physical panel and PNG preview centrally
draws the edge glow for every registered normal service view before dispatching
to service-specific content. Recorder, system and future plugin views must not
depend on their own glow call; only menus and WLAN setup bypass it.
`screen_border_enabled` is no longer a public or active setting. Tests cover
persistence, malformed colors, every registered service, the straight top glow
below the status row, the R5 curve, a clearly visible minimum glow intensity
and the absence of any pixel in the glow samples that exactly equals the accent color.
The permanent glow strength is explicitly `1.3`; do not replace it with an
unmeasured color or line-width change.
That last assertion prevents a crisp line from returning. Device media use the
shared asymmetric mask: 12-pixel top corners, 43-pixel panel-matched lower
corners and equal minimal side/bottom margins. New device text must use at
least the SSID font size; tests enforce this for the battery percentage.

The `pisugar3` backend must verify registers `0x00 == 3` and `0x01 == 0x0F`
before accepting register `0x2A` as a percentage. Tests mock the I2C boundary
and require exactly those three SMBus byte-data reads; separate raw
register-selection writes are not allowed because they failed on the real
controller. No write-capable control register may appear. The installed unit
may access only `/dev/i2c-1`, and the installer must load `i2c-dev` without
installing a PiSugar web account.

The `device_input` action is the hardware-free input source for the native
display. It accepts only the checked-in logical control names, rotary steps
from -10 through 10 excluding zero, press hold durations from 0 through 5
seconds, and an explicit boolean `active` state for `ptt`. The application
passes the resulting `InputEvent` through its semantic action router and then
to the Whisplay adapter; the normal render loop and browser inputs share its
display lock. A short `right_press`/Enter must be verified to change both the
public playback state and the actual `mpv` pause state, not merely the display
icon. If radio is selected while the player is stopped, the same event starts
the first persistent station. A held right press opens the quick menu without
touching playback. No
GPIO number is accepted by this endpoint. Browser PTT uses held Backspace only
outside editable fields and must release on key-up, focus loss and tab hiding.
In the normal BrandMeister view the application measures those same physical
or browser edges: a release before two seconds toggles the marked TG and one
cancellable timer opens the country filter at the two-second threshold while
PTT remains held. Releasing after that threshold is consumed and must neither
toggle a TG nor close the country menu. Tests must drive the timer without a
wall-clock sleep and prove both the pre-threshold cancellation and post-threshold
release behavior. A seventh activation must be
tested as an explicit six-choice replacement transaction, including cancellation;
it must never evict a TG implicitly.
Device-catalog tests must also disable a selected enabled TG and prove that the
cursor returns to catalog position one on the first remaining enabled row,
while the disabled TG remains off. Re-enable it explicitly before subsequent
receiver-subscription assertions; selection movement must never masquerade as
an enable action.
While the device menu is open, browser Up/Down must follow the visible list
direction without changing the physical `right_outer` semantics. An open device
menu owns those two arrow keys even if a dashboard search/input field still has
browser focus; all other keys retain the editable-field protection. It remains an input indication, not an audio claim,
until a real authorized service adapter consumes it.

Volume and radio-channel regression tests must make the same distinction:
`left_outer` changes `MpvEngine.state.volume` by ten percentage points per
logical step through its IPC command, and
`right_outer` loads the selected entry from the persistent station order rather
than only incrementing a display counter. Deleting and reordering default
stations must survive a new `ServiceCatalog` instance. Radio frames expose the
optional preset ID, channel and display name,
but no remote artwork URL, stream URL or local cache path. The physical
renderer may read only `radio-<preset-id>.jpg` below the configured cache root.
Tests must also keep view selection and audio ownership separate: switching to
weather followed by normal frame refresh may not jump back to the audio service;
weather open/step/refresh must leave mpv state and its audio-service owner
unchanged. Only explicit Play in another audio service may replace the source.

`system_update` requires the exact boolean field `confirmed: true`. It creates
the fixed runtime request only; it accepts no URL, branch, version, command or
arguments. Test the application boundary with temporary runtime/state
directories and test the installed privilege boundary by asserting root
ownership/modes, the exact systemd path, the helper's fixed HTTPS source and
absence of `sudo`/shell interpolation in the web process. Update progress is
reported in `/api/status` under `update` and the browser disables its button
for `queued`, `running` and `rebooting` states.
The root helper contract test must require `bash "$bootstrap" --no-reboot`, a
`rebooting` status write before `systemctl reboot --no-block`, and no
client-controlled argument forwarding. Status tests must also cover an older
`running` record whose boot ID differs from the current boot; it is reported as
failed so an earlier helper cannot wedge the update control forever or claim an
unconfirmed success.
The boot recovery helper must additionally persist this transition before the
application starts, including `rebooting` to `completed`, while refusing to
modify a same-boot active status. The browser button is disabled only for a
current-boot `queued`, `running` or `rebooting` state.
`install.sh` must create a portable state backup before `apt-get update` whenever
the live SQLite database exists. A failed backup is a hard stop; do not move this
protection behind package installation or release-symlink replacement.
Before restarting the service, the installer repairs only the fixed SQLite DB,
WAL and SHM ownership without following symlinks or recursing into media. The
bounded health loop allows 60 attempts so one automatic systemd retry can still
become ready without producing a false failed update.

Compatibility controls `preset_play` and `preset_save` and the feed control
`feed_fetch_preset` accept only a checked-in preset ID and never a client-supplied
internal stream or feed URL. Normal radio UI control uses `station_play`,
`station_move`, `station_delete` and `radio_toggle` against the persistent list.
Update source definitions and their evidence together in
[`PRESETS.md`](PRESETS.md), then test the current addresses without adding
cookies, tokens or signed URLs.
The default seed is deliberately limited to the ten entries whose
`default_enabled` flag is true. Tests must count at least five catalog entries
for each supported catalog language, prove that a new database activates only
those ten, and prove that deleting one does not recreate it. Browser tests must
require one active list, one inactive catalog list behind two accessible
sub-tabs whose two selectors remain visible while the selected one alone is
accent-highlighted, shared add/search/language/category controls, and the `preset_save`
activation path. Successful custom creation and preset activation must select
the active tab without resetting the shared filters. The radio page does not
render the generic direct-source URL input; its Play/Pause, Stop, current-song
retention and continuous-capture controls remain available.

Podcast regressions use bounded local XML fixtures. They must cover RSS/Atom
audio-enclosure parsing, the 50-episode limit, persistent `podcasts` channels,
stable public episode IDs, playback through the existing `MpvEngine`, and the
absence of raw feed/enclosure URLs in snapshots. Network tests are diagnostic
only. Never check in a private podcast URL, a feed query token or a signed
enclosure URL.
AmbientR4D10 regressions must verify the ten reviewed built-ins, HTTPS source
and license metadata, absence of playable URLs from public snapshots, and real
`loop=True` playback only after an explicit play action. They must also prove
that selection alone leaves the audio owner untouched and that custom scenes,
ordering and deletion survive a new `ServiceCatalog` without restoring removed
defaults. Query-bearing custom URLs are rejected because they may contain
persistent access tokens.
Radio recording regressions must cover ICY parsing, title-boundary splitting,
PTT retention of already buffered bytes, the production memory bound,
continuous mode, storage deduplication and explicit deletion. `fpcalc` comes
from Debian's `libchromaprint-tools`; a missing fingerprint tool may reduce
duplicate detection quality but must never destroy a valid buffered recording.
Cover tests use fake MusicBrainz/Cover Art Archive responses and may not depend
on the public network.
The stopped radio view must tune the same silent `IcyRadioBuffer`, surface its
metadata before audible Play and use only localized end-user fallback text when
metadata is unavailable. Tests must reject technical player/backend wording.
The radio tab must expose the persistent station rows only once through the
compact sortable station list. Browser regression tests reject the removed
`radio-preset-grid` and require the retained list's primary play-button class.
Service-module regressions require semantic list markup and a type-search input,
reject the removed card grid and verify that filtering includes the serialized
public service metadata as well as translated visible labels. Do not add an
unverified network logo URL to make a row look branded.

Weather controls use `weather_open`, `weather_step`, `weather_refresh`,
`weather_channel_save`, `weather_channel_move` and `weather_channel_delete`.
The three defaults are Germany radar, Germany satellite and Europe satellite;
tests must prove that their user order and edits survive a new `ServiceCatalog`.
An upgrade from the earlier two-channel state must append Germany satellite
once and must not recreate it after deletion. `service_move`
similarly persists every service priority. The DWD WMS integration must keep
the five-minute capability refresh floor, tolerate missing timestamps and
retain the last safe cache. The official radar GIF uses the same refresh floor,
bounded fetch, frame-count/pixel limits and local JPEG re-encoding. Live network
checks are diagnostic only; unit tests use bounded fake WMS/GIF responses.

External account-based modules are never loaded into the web process. Their
non-secret manifests live in `/etc/openr4d10/services.d`; see
[`SERVICE_ADAPTERS.md`](SERVICE_ADAPTERS.md) for the Unix-socket protocol and
per-service credential isolation requirements.

## Installed diagnostics

```bash
sudo openr4d10 doctor
systemctl status openr4d10 --no-pager
journalctl -u openr4d10 -b --no-pager
systemctl cat openr4d10
```

`doctor` exit status `2` means the checked-in placeholder hardware configuration
is still active. It does not mean the installer failed. Exit status `1` means a
file, helper, manifest or platform check failed.

For Whisplay audio, `doctor` has three explicit states: missing driver,
installed overlay awaiting reboot, and active ALSA card `whisplaysound`. The
normal 0.10.7 installer reboots automatically after all checks succeed. Use
`--no-reboot` only for an intentional maintenance run; reboot before judging
playback, then verify:

```bash
aplay -l | grep -i whisplay
amixer -c whisplaysound cget name='speaker'
sudo openr4d10 doctor
```

`doctor` also reports whether `pwm_gpio@22` is active. Immediately after an
in-session install it correctly requests a reboot; after reboot it must report
`Whisplay backlight uses kernel-timed PWM on BCM22`.

The vendored source provenance and upstream archive checksum live in
`vendor/pisugar-whisplay/UPSTREAM.md`. Updates must replace that reviewed
unmodified subset and retain its own Apache-2.0 `LICENSE`; do not edit vendor
files to implement OpenR4d10 behavior.

`--check` always exits before privileged changes and never reboots. A normal
successful installation requests `systemctl reboot --no-block` only after the
service healthcheck and final diagnostics. Any earlier package, build, service
or healthcheck failure exits without rebooting.

Immediately after an in-session installation, `openr4d10-boot.service` has not
run yet. `openr4d10.service` must nevertheless create the shared
`/run/openr4d10-boot` directory through `RuntimeDirectory=` so the physical UI
can claim the display directly. Repeated `Boot display runtime is absent`
messages indicate a stale application unit; reinstall the current release and
verify the unit's two runtime-directory names before rebooting.

The native boot player has an additional hardware-independent integrity mode:

```bash
gcc -O2 -std=c11 -Wall -Wextra -Werror \
  boot/native/openr4d10_boot.c -lz -o /tmp/openr4d10-boot-check
/tmp/openr4d10-boot-check --verify boot/assets/boot.opb
```

## Making lasting architecture changes

Bei Mediathek-Änderungen muss zusätzlich nachgewiesen werden, dass
`LEFT_OUTER` nur die Lautstärke ändert, `LEFT_INNER` schnelle Suchrastungen
zusammenfasst und nur einen mpv-Sprung auslöst. Fortschritt und Puffer dürfen
nur aus der zentralen mpv-Zeitquelle stammen. Neue Browsertexte für Verlauf,
Archiv oder Favoriten benötigen Übersetzungen in allen fünf unterstützten
Sprachen.

Keep configuration ownership, adapter contracts, storage paths, service
permissions and recurring diagnostic traps documented in `docs/`. Update tests
with every contract change. Never add a second installation path or direct GPIO
implementation until the existing adapter boundary has been evaluated first.

PiSugar 3 power-button tests must preserve the read-only status-register
contract: an initial level creates no event, a released press up to 0.6 seconds
creates exactly one logical `HOME`, and every longer hold plus its release
creates none. Custom-button tests must preserve the manufacturer's `0x08` tap
codes and map single/double/long to `RIGHT_OUTER +1`, `RIGHT_PRESS`, and
`RIGHT_INNER +1`. Only acknowledgement of those two tap bits may use the
documented temporary write-enable sequence. No test or implementation may
enable watchdog, soft shutdown or change another PiSugar register as a side
effect of input.
# DMR boot and Mediathek device regression rules

Tests must fail if the real `run` path calls
`start_brandmeister_receiver()`: saved talkgroups must not imply playback after
boot. Device input tests must also cover stopping a real background DMR owner
from a mismatched PLAYER presentation.

Mediathek device tests cover the two-second PTT threshold, consumed release,
five-language group labels, non-blocking group lookup, video-first device
playback and randomized next-item selection. Network fetching remains outside
the serialized input path.
