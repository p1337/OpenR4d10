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
- persistent device-language switch for English, Deutsch, Polski, Français
  and Español; browser and physical Whisplay use the same saved selection
- explicitly confirmed system updates directly from the web dashboard
- automatic recovery of stale web-update state after a reboot
- confirmed NetworkManager WLAN repair without persistent web-side credentials
- automatic WPA2 setup hotspot when saved WLANs remain unavailable
- actual connected SSID beside the physical Wi-Fi symbol instead of `WLAN`
- native Whisplay ST7789 boot animation installed and enabled automatically
- safe display handoff both at boot and during an in-session installation
- real-device-confirmed Whisplay SPI transport, colour order and orientation
- persistent, kernel-timed 0–100% Whisplay brightness control in the web settings
- persistent accent color plus a permanent strong, soft player-edge glow following
  the rounded display contour and closing below the status row
- read-only PiSugar 3 battery percentage over the manufacturer-documented I2C
  identity and capacity registers; no separate PiSugar web service or default
  account is installed
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
- disabled-by-default Anker SOLIX service contract for bounded PV, house, grid
  and battery telemetry; supported local Modbus devices are preferred and any
  community cloud login remains isolated outside the core
- researched service roadmap with 88 concrete energy, PTT, camera, VPN,
  location, sensor, media and operations integrations
- persistent enable/disable lifecycle for native and external service modules
- checksummed, secret-free SQLite backup and guarded offline restore
- direct web-radio/local-media playback through private mpv JSON IPC and
  stream recording through shell-free ffmpeg/Opus
- bounded RSS/Atom reader and two-slot camera snapshots with image validation
  and safe JPEG re-encoding
- persistent, ordered web-radio library and bounded local-media library scanning
- ICY-aware radio pre-buffer: PTT retains the current song including its
  buffered beginning; optional continuous capture splits on title metadata,
  suppresses duplicates and stores `Artist – Song` by artist
- silent ICY title lookup in the radio view before audible Play, with localized
  non-technical fallback text when a station supplies no title
- simple recorded-music player with favorites, `My Soundmix`, shuffle,
  previous/next, optional cover cache and confirmed deletion
- curated 41-station radio catalog across eight languages with local artwork,
  persistent active/disabled selection, search and language/category filters
- persistent podcast subscriptions with bounded RSS/Atom episode loading,
  search and playback through the existing audio owner
- separate AmbientR4D10 audio service with six license-documented café,
  forest, beach, brook, rain and night soundscapes, endless looping and a
  persistent sortable scene library with one consistent bundled artwork per
  built-in scene in both the browser and physical display
- direct receive-only BrandMeister HoseLine browser audio with a persistent
  multi-talkgroup checkbox quick list, country flags and active-call display;
  no account password, user token, PTT or claimed Whisplay-speaker routing
- standard-library-only test suite and GitHub Actions CI

Hardware-specific integration still pending:

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
Pillow/libgpiod/spidev/mpv/ffmpeg packages, enables SPI, installs the kernel
`pwm-gpio` backlight overlay, builds the pinned
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

If no saved WLAN can be activated after the boot/disconnect grace period,
OpenR4d10 automatically starts a device-specific WPA2 setup hotspot through the
same NetworkManager owner. The Whisplay shows its complete SSID, locally
generated password and `http://10.42.0.1/`; connect the phone to that hotspot,
open the shown address and use **Device → WLAN repair**. A successful repair
replaces the hotspot with the new client connection. The hotspot password is
generated only on the device and is excluded from Git, status JSON, SQLite,
logs and backups. A merely selected or repeatedly authenticating infrastructure
profile is not treated as connected: only NetworkManager's fully activated
device state cancels the fallback. After the grace period the helper stops a
stalled WPA/SAE attempt, forces the Wi-Fi software radio on and retries the
local WPA2 hotspot three times. Its runtime directory is created by systemd
before sandbox setup, so the fallback also works before the main application
has started. The 30-second timer keeps retrying after missing hardware,
NetworkManager startup delay or a failed AP activation.

The dashboard shows live service, system and adapter status. The real Whisplay
display and sound card are verified. The PiSugar 3 adapter uses the same SMBus
byte-data transaction as the manufacturer driver, checks the official device
identity and application mode at I2C address `0x57`, then reads only the
calculated 0–100% capacity register. The percentage appears immediately left
of the physical battery icon and in the web energy card. It never changes
charging, RTC, shutdown or controller configuration.

The **Einstellungen → Display** panel changes the physical Whisplay backlight
immediately from 0 through 100 percent. The value is stored in the existing
non-secret SQLite state, included in the normal pre-update backup and restored
automatically when the application starts. The early native boot animation
runs before that database is available; the saved value takes effect when the
normal OpenR4d10 device UI takes over the panel. Intermediate values use
Raspberry Pi OS's in-tree `pwm-gpio` driver on the manufacturer-verified
active-low BCM22 backlight line. Its high-resolution kernel timer continues to
generate pulse edges when the application process is delayed by CPU load. The
application publishes only a bounded 0–100 request below
`/run/openr4d10-backlight`; a fixed root-owned helper validates it and changes
the kernel PWM interface. The native boot player no longer claims BCM22, keeps
the backlight dark until its first complete frame and then uses the same
bounded handoff. This transition needs the installer's automatic reboot.
The same settings area stores the selected accent color. The normal player
always receives a clearly visible strong, soft edge glow in that color along the physical rounded
contour, including a straight upper glow immediately below the status row. It
has no crisp border line and no disable switch. Media, weather and camera
images use the same 43-pixel corner radius as the panel. Device text is never
introduced below the SSID text size; battery percentage is at least that size
and bold. Menu selection and PTT indicators remain independent functional cues.

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

The browser arrow direction matches the visible direction everywhere: Up
selects the previous/upper channel or menu item and Down selects the
next/lower one. There is no separate menu-only inversion.

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
radio view reserves the freed space for a 151 × 151 station image and a larger
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
Saved radio stations can be managed in the same dashboard. On first use the ten
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
The language selector in the header changes the physical device language first,
stores that non-secret value in SQLite and keeps the browser synchronized with
the same selection. Browser-local storage is only the early-load cache before
the device status arrives. The live-display card uses only its compact section
label and has no redundant `Device view` heading.
Local files copied below
`/var/lib/openr4d10/media` appear after selecting **Neu einlesen**; their full
paths never appear in the public status response.

The navigation tree is maintained only as an internal debugging overview in
[`docs/MENU_TREE.md`](docs/MENU_TREE.md). It is not a product page or a visible
menu entry.

The personal list initially includes SWR3, sunshine live, Deutschlandfunk,
RMF FM, Radio ZET, BBC World Service, DIE NEUE 107.7, AFN The Eagle,
ROCK ANTENNE and ROCK FM. A separate inactive catalog expands this to 41
reviewed stations with at least five each in German, English, Polish, French,
Spanish, Italian, Dutch and Portuguese. Activating a catalog row moves it into
the persistent personal list; updates do not activate new stations or restore
ones the user removed. News presets include
tagesschau, Deutschlandfunk Nachrichten, RMF24 and BBC News World. The source
addresses and their review references are documented in
[`docs/PRESETS.md`](docs/PRESETS.md). Station artwork is fetched only from the
reviewed list, size-limited, decoded and locally re-encoded as JPEG. If a logo
is unavailable, the dashboard keeps working and displays a text tile instead.

The **Podcasts** tab accepts a public RSS/Atom podcast-feed address, stores the
subscription in the same non-secret SQLite state, loads at most 50 playable
audio episodes on demand and can search or play those episodes. Raw feed and
enclosure URLs are not returned by the status API. Feeds with embedded
credentials or persistent query strings are refused so signed/private feed
tokens cannot accidentally enter backups or public state.

The **AmbientR4D10** tab is an independent audio service, not a radio-station
group or a third-party branded clone. Its six initial soundscapes are fetched
once from reviewed public CC sources, checksum-verified into the protected
local media cache and looped offline by the existing private mpv owner;
the café uses a quieter CC0 coffeehouse recording with a small group instead
of dense crowd noise. Opening the service does not disturb other audio. Once
its channel control is turned, the newly selected scene starts immediately and
replaces the previous audio source. Scene order, deletion and custom
credential-free HTTP(S) additions persist across updates. Sources, attribution
and licenses are recorded in [`docs/AMBIENT.md`](docs/AMBIENT.md). The six
matching scene artworks are bundled locally, so no external image service is
needed at runtime. The Ambient tab loads those local thumbnails immediately
through the bounded OpenR4d10 content endpoint rather than deferring them as
off-screen browser images.

If the repository files are already present, the local command remains:

```bash
sudo ./install.sh
```

For an inspect-first installation, download `bootstrap.sh`, review it, and run
it with `sudo bash bootstrap.sh`. Regardless of how the bootstrap is started,
it downloads and validates the complete project archive before installation.

PiSugar 3 percentage telemetry, the Whisplay display backend and the unified
audio driver are installed automatically. With `--no-reboot`, the
diagnostic deliberately reports the audio driver as installed but not yet
active until the administrator reboots manually. The early-boot display log is available with
`journalctl -u openr4d10-boot -b --no-pager`.

## Configure hardware

The installer creates these files only if they do not already exist:

- `/etc/openr4d10/openr4d10.toml`
- `/etc/openr4d10/hardware.toml`

It also refreshes `.dist` copies on every install so local changes can be
compared with the current defaults. Exact existing `unconfigured` placeholders
are migrated to `display.backend = "whisplay"` and
`power.backend = "pisugar3"`; command/file adapters and their local arguments
remain untouched. Edit
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
Potential future integrations are ranked in
[`docs/SERVICE_CANDIDATES.md`](docs/SERVICE_CANDIDATES.md); this is research,
not an installed service catalog.
The verified receive-only browser transport and its explicit limits are in
[`docs/BRANDMEISTER.md`](docs/BRANDMEISTER.md).
