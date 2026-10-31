# OpenR4d10

The versioned project truth and complete accumulated product requirements live
in [`CODEX_TO_CODEX_MASTER.md`](CODEX_TO_CODEX_MASTER.md). It must be read
before changing architecture, hardware assumptions or product scope.

OpenR4d10 is a small Python service for a Raspberry Pi Zero 2 W
running Debian 13 (Trixie). It provides a safe foundation for a receiver UI,
boot sequence, display output, status data and power telemetry without guessing
the Whisplay pinout, display controller or PiSugar protocol.

The repository is intentionally usable before the final hardware details are
known: the service starts in a visible `unconfigured` mode, while `doctor` and
the installer report exactly which adapters still need configuration.

## Current status

- Raspberry Pi Zero 2 W / Debian 13 / `aarch64` platform checks
- idempotent one-command online installer with no Git dependency
- hardened `systemd` autostart service
- responsive local web dashboard on `http://<raspberry-pi-ip>/`
- persistent browser language switch for English, Deutsch, Polski, Français
  and Español with an English fallback
- explicitly confirmed system updates directly from the web dashboard
- automatic recovery of stale web-update state after a reboot
- confirmed NetworkManager WLAN repair without persistent web-side credentials
- native Whisplay ST7789 boot animation installed and enabled automatically
- safe display handoff both at boot and during an in-session installation
- real-device-confirmed Whisplay SPI transport, colour order and orientation
- persistent 0–100% Whisplay brightness control in the web settings
- native 240 x 280 physical UI with the agreed four-axis encoder layout
- browser controls for all four virtual encoder axes and both press actions
- semantic UI frame model and configurable text boot sequence
- safe `unconfigured`, JSON-file and external-command display adapters
- built-in Linux system status and optional external-command status/power adapters
- persistent configuration in `/etc/openr4d10`
- runtime data in `/run/openr4d10` and state in `/var/lib/openr4d10`
- versioned SQLite state for non-secret settings, services, stations, channels,
  media and recordings
- native DWD rain-radar loop plus retained METEOSAT satellite loops for Germany
  and Europe, with bounded local frame caching and persistent channel/service
  priority
- central catalog covering all specified service modules with honest dependency,
  adapter and local-login readiness
- persistent enable/disable lifecycle for native and external service modules
- checksummed, secret-free SQLite backup and guarded offline restore
- direct web-radio/local-media playback through private mpv JSON IPC and
  stream recording through shell-free ffmpeg/Opus
- bounded RSS/Atom reader and two-slot camera snapshots with image validation
  and safe JPEG re-encoding
- persistent, ordered web-radio library and bounded local-media library scanning
- curated one-click radio and news-feed presets with locally re-encoded artwork
- standard-library-only test suite and GitHub Actions CI

Hardware-specific integration still pending:

- PiSugar API details
- acoustic verification of actual Whisplay speaker output
- encoder GPIO input
- credentials, WLAN settings, tokens or secrets

Those values must come from the exact hardware documentation. See
[`docs/HARDWARE.md`](docs/HARDWARE.md).

The verified DWD product, request limits, attribution and cache contract are
documented in [`docs/WEATHER.md`](docs/WEATHER.md).

## Install

On a fresh Debian installation with `curl`, use this one command. Git is not
needed; `bootstrap.sh` performs the complete download and installation.

```bash
curl -fsSL https://raw.githubusercontent.com/p1337/OpenR4d10/main/bootstrap.sh | sudo bash
```

If the image has `wget` instead of `curl`, the equivalent command is:

```bash
wget -qO- https://raw.githubusercontent.com/p1337/OpenR4d10/main/bootstrap.sh | sudo bash
```

The bootstrap downloads a complete GitHub source archive without root access,
validates the archive before extraction, prints its SHA-256, and only then
starts the local installer, which requests root access when required.
The installer verifies the operating system, CPU architecture and Raspberry Pi
model, installs files below `/opt/openr4d10`, preserves existing configuration,
compiles the Whisplay boot player locally for the Pi, installs the Debian
Pillow/libgpiod/spidev/mpv/ffmpeg packages, enables SPI, builds the pinned
official unified Whisplay sound-card driver for the running kernel, enables
I²C/I²S, installs its overlay and ALSA configuration, installs and enables
the systemd services, and runs a final diagnostic. The official driver supports
both WM8960 and ES8389 without guessing the fitted revision. The installer
requests the exact `linux-headers-$(uname -r)` package and validates its kernel
build tools before compilation. Neither script collects or writes credentials.

After every successful normal installation the installer announces and starts
the required reboot automatically; the SSH connection therefore closes. The
sound-card kernel module and overlay cannot become active before that reboot.
The native Whisplay animation starts on the next boot, keeps the moving skull
visible 1.5 seconds longer and then keeps its reviewed final-logo loop visible
until the physical application UI is ready and takes over the panel. The web
dashboard remains available independently. After reboot, `openr4d10 doctor`
must report `whisplaysound` before internal speaker output is treated as
available.

For an intentional maintenance run without an automatic reboot, pass the
explicit opt-out through the bootstrap:

```bash
curl -fsSL https://raw.githubusercontent.com/p1337/OpenR4d10/main/bootstrap.sh | sudo bash -s -- --no-reboot
```

After installation, open the Pi address directly in a browser, for example:

```text
http://192.168.1.64/
```

The **Systemupdate** control in the running-service panel can install later
releases without SSH. It requires an explicit browser confirmation, shows
queued/running/failure/reboot status and uses a fixed root-owned systemd helper.
The web service itself receives no sudo or arbitrary command capability. A
successful web update follows the same bootstrap/installer checks and automatic
reboot as the one-command installation. In this path the fixed root helper
suppresses the installer's own reboot, records the installed version and
`rebooting` state first, then requests the reboot itself; a previous-boot
`running` record therefore cannot permanently block another update. Before an
existing installation is changed, the installer must successfully create a
consistent secret-free state backup below `/var/lib/openr4d10/backups`; a
backup failure aborts the update.

On every boot a fixed root-owned recovery unit reconciles an older update
record before the dashboard starts. A previous-boot `queued` or `running` state
becomes retryable failure, while a previous-boot `rebooting` state becomes
completed. The update button is therefore never left permanently disabled by a
reboot. A same-boot installer remains serialized and is not killed during
package writes.

The **Device → WLAN repair** panel can replace the device's Wi-Fi connection
with a user-supplied SSID and passphrase. It uses the already active
NetworkManager owner on `wlan0`: the root helper first creates and activates a
new profile, and only after success removes older Wi-Fi profiles when the user
explicitly selected replacement. The passphrase is carried in a short-lived
0600 runtime handoff and then only in NetworkManager's root-only system profile,
never in Git, SQLite, status JSON, backups, logs or a process argument. Because
the current dashboard is plain local HTTP, enter WLAN
credentials only from a trusted private LAN.

The dashboard shows live service, system and adapter status. Until verified
Whisplay and PiSugar adapters are configured, it labels those components as
open instead of displaying invented measurements.

The **Einstellungen → Display** panel changes the physical Whisplay backlight
immediately from 0 through 100 percent. The value is stored in the existing
non-secret SQLite state, included in the normal pre-update backup and restored
automatically when the application starts. The early native boot animation
runs before that database is available; the saved value takes effect when the
normal OpenR4d10 device UI takes over the panel.

Until the physical encoders are delivered, the **Virtuelle Encoder** panel in
the same dashboard controls the real Whisplay immediately. Its volume, squelch,
channel and service buttons plus short/long press actions use the same logical
input events as the future GPIO adapter; no provisional pin assignment is
required. Keyboard control is available outside form fields: `W`/`S` control
volume, `A`/`D` control squelch, the up/down arrows control the channel, the
left/right arrows control the service, Space is the left click and Enter is the
right click. Holding `Backspace` exposes the logical PTT input outside editable
fields; until a verified PTT
service adapter is configured it deliberately shows input state without
claiming audio transmission.

For the radio service, `W`/`S` changes the actual mpv output volume in
10-percentage-point steps and up/down immediately loads the previous or next
station in the personal order. Enter pauses or resumes the real stream; while
radio is selected and playback is stopped, it starts the first station in that
list. The native radio view uses the station name
and locally cached safe artwork (or an initials fallback), not a raw stream URL
or a decorative fake equalizer.

Service navigation and audio ownership are independent. Moving to weather,
system or another visual service never stops or replaces a playing stream and
periodic status refreshes never force the display back to the audio source.
Only an explicit Play action in another audio-capable service replaces the
current source.

The physical 240 × 280 layout uses the compact, localized control labels
`VOL`, `SQL`, `CH` and `SRV` in its English fallback. Its shorter control head
uses larger type, the status row shows a larger clock without a date, and the
radio view reserves the freed space for a 138 × 138 station image and a larger
station heading. The redundant service caption, written playback state and
bottom `READY`/`OpenR4d10` strip are not rendered. Opening the main menu hides
the complete player and shows the localized heading plus the ten documented
settings areas as a scrollable list. Up/down on the right outer control moves
the selection, Enter opens it and PTT returns one menu level unless a ready
service explicitly owns PTT. The default interface accent is `#FDB813`.

The service section accepts an explicit `http` or `https` audio URL for local
playback and recording. It rejects credentials embedded in URLs and does not
persist URL query strings in public status. Actual sound requires an ALSA
device. Local sound uses the official Whisplay ALSA card `whisplaysound`; the
installer builds the unified driver for either supported codec revision and
the real speaker is verified after reboot.
RSS/Atom URLs and camera snapshot URLs can be loaded in the same local panel.
Feed downloads are size-limited; camera responses are decoded, dimension-
checked, resized and re-encoded before the browser can retrieve them.
Saved radio stations can be managed in the same dashboard. On first use the six
curated stations are copied once into this persistent library. All entries can
then be reordered, deleted or extended; an intentionally deleted default is not
recreated by a restart or update. Station URLs with a query are intentionally
refused for persistent storage, while direct temporary playback remains possible.
The dashboard separates radio, media/news, device, system and services into
tabs instead of one long page. On desktop it keeps the exact native 240 × 280
renderer output visible at the upper right. The radio tab renders the persistent
station library exactly once as a compact sortable list with safe local artwork;
its primary play controls use the yellow interface accent.
Repeated collections such as services, stations, weather channels and media use
compact lists instead of card grids. The service list has a local search field
covering its full public metadata; only verified local logos may replace the
neutral initials marker.
The language selector in the header translates static and generated browser
controls, keeps its choice in local browser storage and does not silently
change the independent physical-display language. The live-display card uses
only its compact section label and has no redundant `Device view` heading.
Local files copied below
`/var/lib/openr4d10/media` appear after selecting **Neu einlesen**; their full
paths never appear in the public status response.

The built-in selection currently includes SWR3, sunshine live,
Deutschlandfunk, RMF FM, Radio ZET and BBC World Service. News presets include
tagesschau, Deutschlandfunk Nachrichten, RMF24 and BBC News World. The source
addresses and their review references are documented in
[`docs/PRESETS.md`](docs/PRESETS.md). Station artwork is fetched only from the
reviewed list, size-limited, decoded and locally re-encoded as JPEG. If a logo
is unavailable, the dashboard keeps working and displays a text tile instead.

If the repository files are already present, the local command remains:

```bash
sudo ./install.sh
```

For an inspect-first installation, download `bootstrap.sh`, review it, and run
it with `sudo bash bootstrap.sh`. Regardless of how the bootstrap is started,
it downloads and validates the complete project archive before installation.

PiSugar telemetry remains configuration-required. The Whisplay display backend
and unified audio driver are installed automatically. With `--no-reboot`, the
diagnostic deliberately reports the audio driver as installed but not yet
active until the administrator reboots manually. The early-boot display log is available with
`journalctl -u openr4d10-boot -b --no-pager`.

## Configure hardware

The installer creates these files only if they do not already exist:

- `/etc/openr4d10/openr4d10.toml`
- `/etc/openr4d10/hardware.toml`

It also refreshes `.dist` copies on every install so local changes can be
compared with the current defaults. An existing display placeholder is migrated
to `backend = "whisplay"`; all other local settings are preserved. Edit
`hardware.toml`, then run:

```bash
sudo openr4d10 doctor
sudo systemctl restart openr4d10
sudo journalctl -u openr4d10 -f
```

The generic `command` adapter sends one JSON document to an executable through
standard input. This keeps vendor code outside the privileged installer and
allows the exact, documented Whisplay or PiSugar helper to be connected later.
No shell is involved and the command must be an absolute path.

## Useful commands

```bash
sudo openr4d10 doctor
openr4d10 render-once
openr4d10 preview-ui --output /tmp/openr4d10-ui.png
systemctl status openr4d10
journalctl -u openr4d10 --since today
journalctl -u openr4d10-boot -b --no-pager
curl http://127.0.0.1/healthz
sudo openr4d10 backup --output /var/lib/openr4d10/backups/manual.openr4d10.zip
```

A restore is deliberately offline and explicit:

```bash
sudo systemctl stop openr4d10
sudo openr4d10 restore --input /path/to/backup.openr4d10.zip --replace
sudo systemctl start openr4d10
```

The core backup contains the consistent non-secret SQLite state and service
activation plan. It does not contain credentials, WLAN data, SSH keys, media or
recordings.

For development:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m openr4d10 --config config/openr4d10.toml \
  --hardware-config config/hardware.toml doctor
```

More detail is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md),
[`docs/HARDWARE.md`](docs/HARDWARE.md) and
[`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md). The isolated protocol for
account-bearing modules is documented in
[`docs/SERVICE_ADAPTERS.md`](docs/SERVICE_ADAPTERS.md).
