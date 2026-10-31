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
- `/api/camera/1` and `/api/camera/2` — locally re-encoded camera snapshots
- `/api/radio-art/<preset-id>` — bounded, locally re-encoded preset artwork
- `/api/device-screen.png` — exact current native 240 × 280 renderer output
- `/api/weather-frame/<validated-cache-name>` — locally decoded and re-encoded
  DWD satellite frame; remote WMS URLs are never browser image URLs

The control endpoint accepts only JSON up to 4096 bytes and rejects mismatched
browser origins. With the sole exception of the transient `wifi_repair`
handoff described below, it never accepts credentials; no credential is stored
in SQLite, status, backups or logs. It supports explicit
playback, pause, stop, volume and stream-recording actions plus bounded feed and
camera retrieval, saved station management and local media rescans. Saved
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
storage and must not write device or server settings.

`display_brightness` accepts exactly one integer `brightness_percent` from 0
through 100. The application applies it through the configured display adapter
and then persists it under `display.brightness_percent` in the existing SQLite
state. Status exposes the value only as
`services.settings.display_brightness_percent`. Tests must cover the default,
both bounds, invalid booleans/non-integers, restart persistence and delivery to
the Whisplay adapter. Do not add a second configuration file or a direct web
GPIO path. The early native boot player intentionally has no SQLite dependency;
brightness restoration begins at application display handoff.
The target implementation keeps BCM22 active-low but delegates intermediate
PWM timing to the installed `python3-lgpio` C runtime. Do not implement pulse
timing with `threading`, `sleep`, or `Event.wait`: that earlier path visibly
flickered on the real Pi Zero 2 W. Unit tests must cover the active-low mapping,
steady 0/100-percent endpoints and the `lgpio.tx_pwm` call for intermediate
values.
`lgpio` also requires a writable current directory for its private notification
pipe. Keep `WorkingDirectory=/run/openr4d10` in the application unit and test
that the unit still retains `ProtectSystem=strict`; do not solve this by making
`/` writable or broadening `ReadWritePaths`.
Do not call `lgpio.tx_pwm(..., 0, 0)` unless the adapter has successfully
started PWM on that claimed output. Raspberry Pi OS package 0.2.2 returns
`bad PWM micros` for an idle stop. Tests must cover a steady endpoint before
the first intermediate PWM value and cleanup in both active and idle states.

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
While the device menu is open, browser Up/Down must follow the visible list
direction without changing the physical `right_outer` semantics. It remains an input indication, not an audio claim,
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

Compatibility controls `preset_play` and `preset_save` and the feed control
`feed_fetch_preset` accept only a checked-in preset ID and never a client-supplied
internal stream or feed URL. Normal radio UI control uses `station_play`,
`station_move`, `station_delete` and `radio_toggle` against the persistent list.
Update source definitions and their evidence together in
[`PRESETS.md`](PRESETS.md), then test the current addresses without adding
cookies, tokens or signed URLs.
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

Keep configuration ownership, adapter contracts, storage paths, service
permissions and recurring diagnostic traps documented in `docs/`. Update tests
with every contract change. Never add a second installation path or direct GPIO
implementation until the existing adapter boundary has been evaluated first.
