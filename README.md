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
- persistent accent color plus one centrally composited permanent strong, soft
  service-view glow following the rounded display contour and closing below
  the status row; recorder and future plugins inherit it automatically
- read-only PiSugar 3 battery percentage over the manufacturer-documented I2C
  identity and capacity registers; no separate PiSugar web service or default
  account is installed
- read-only PiSugar 3 power-button input: one complete short press opens the
  main menu, while a press held beyond 0.6 seconds is discarded by OpenR4d10
  and remains exclusively under the PiSugar power controller
- native 240 x 280 physical UI with the agreed four-axis encoder layout
- real Whisplay button on physical pin 11 / BCM17 routed to the logical PTT and
  menu-back path with active-high debouncing
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
- boot-persistent maximum clean Whisplay speaker gain: the bounded ALSA
  `speaker` control is set to 100 after codec warm-up while digital source gain
  remains capped at 100 to avoid fabricated overdrive; the warm-up/application
  order is regression-tested against systemd boot cycles
- bounded RSS/Atom reader and a persistent sortable camera library for
  credential-free Snapshot, MJPEG and RTSP sources with frame limits, image
  validation and safe local JPEG re-encoding
- persistent, ordered web-radio library and bounded local-media library scanning
- ICY-aware radio pre-buffer: PTT retains the current song including its
  buffered beginning; optional continuous capture splits on title metadata,
  suppresses duplicates and stores `Media/Music/Artist/Artist - Song.mp3`;
  microphone recordings remain separate below `Media/VoiceRecorder/JJMMTT`
- editable current voice take with exclusive audio ownership: opening
  VoiceRecorder immediately stops radio, podcasts/local media, Ambient layers
  and BrandMeister; the two left axes provide 0.1-second fine seek and
  start/end jumps, the upper right axis seeks by one second, and the right
  press plays or pauses from the cursor; pressing Play at the exact end rewinds
  once to zero and starts from the beginning without enabling a loop;
  recording from an earlier cursor replaces only the covered interval and
  preserves the untouched tail;
  recorder playback is fixed at 100% and restores the prior service volume on exit
- collision-free VoiceRecorder header: the start/end axis is labelled
  `MIN/MAX`, while its yellow `↔` value and the 0.1-second `±` value share a
  separate right-aligned column instead of touching their labels
- restored VoiceRecorder startup uses that same exclusive entry lifecycle
  before the web server, boot wait or first recorder frame; rebooting into the
  last `REC` view can therefore never leave BrandMeister or another stream audible
- latency-prioritized VoiceRecorder input: physical PTT starts capture on its
  press edge and stops it on release without waiting for telemetry or a full
  display transfer; the white two-pixel playhead is drawn above the waveform
  and the red/idle glow changes through a small ST7789 region update
- near-live VoiceRecorder cursor and playback display: encoder/browser seek
  performs one cached-telemetry repaint, RGB565 conversion is vectorized, the
  native timeline keeps a deadline-based 10 Hz ceiling and the browser preview
  reads the last drawn native frame without blocking SPI with a rerender
- shared interaction-performance contract: normal panel presentation is capped
  at 10 FPS, fonts and quantized glow layers are cached, adjacent browser rotary
  repeats are coalesced in order, and 300 ms user-input latency blocks release
- device input owns display slots while controls are active; expendable
  periodic recorder frames resume after 200 ms of input quiet instead of
  competing with or delaying the requested cursor frame
- service navigation mutates the ordered UI state without drawing a stale
  intermediate screen, resolves entry/exit work, and then presents exactly one
  final frame from cached telemetry
- browser controls reuse persistent HTTP/1.1 connections with delayed small
  packet buffering disabled, avoiding connection setup for every key repeat
- verified Pi Zero 2 W CPU placement uses all four cores by role: two for
  background/audio/web work, one for the fluid native UI and waveform, and one
  for BCM17 plus future measured encoder input; other platforms keep their
  normal operating-system scheduling
- silent ICY title lookup in the radio view before audible Play, with localized
  non-technical fallback text when a station supplies no title
- simple recorded-music player with favorites, `My Soundmix`, shuffle,
  previous/next, optional cover cache and confirmed deletion
- curated 46-station radio catalog across eight languages with local artwork,
  persistent active/disabled selection, search and language/category filters
- persistent podcast subscriptions with bounded RSS/Atom episode loading,
  search and playback through the existing audio owner
- one bounded German public Mediathek catalog covering ARD, ZDF, ZDFinfo,
  ZDFneo, 3sat, ARTE, phoenix, ARD alpha, tagesschau24, ONE, Deutsche Welle
  and the regional ARD broadcasters; current news, Tatort, documentary, science, Terra X and
  Harald-Lesch selections can be watched in the browser or explicitly played
  as audio-only or low-resolution synchronized video through the sole device
  player; while video is actually running, only its edge-to-edge 240 x 175
  lower video region may update at up to 25 FPS, whereas every normal full UI
  frame remains capped at
  10 FPS; device playback focuses `PLAYER`, where the channel control cycles
  the same result set without changing mode and the right press pauses/resumes
- generation-safe mpv event handling: a delayed `end-file` from a replaced
  Mediathek item cannot mark the newer, already running item as stopped
- separate AmbientR4D10 audio service with ten license-documented café,
  nature, water, traffic, rain and night soundscapes, endless looping, up to
  two subtle additive sound layers, persistent favorite mixes and a sortable
  scene library with one consistent bundled artwork per built-in scene in both
  the browser and physical display
- native receive-only BrandMeister HoseLine audio through the Whisplay ALSA
  speaker plus optional browser audio, with a persistent multi-talkgroup
  checkbox quick list, complete searchable official catalog, country flags and
  compact per-talkgroup current/last-heard participant rows on web and device;
  the physical view highlights the speaking TG with a green glow directly in
  its six-row scrollable enabled-first catalog window; a short right click
  starts reception of the enabled TGs,
  short PTT toggles the marked TG and a two-second PTT hold opens the country
  filter immediately at the threshold while the button is still held, without
  transmitting; the following release is consumed, and activating a seventh TG
  explicitly asks which of the six active TGs to replace; disabling a marked
  TG returns the device cursor to the first remaining active TG instead of
  following the disabled row into the inactive catalog;
  no account password or user token
- standard-library-only test suite and GitHub Actions CI
- strict release gate: the exact commit must pass GitHub Actions before a Pi
  update is considered releasable; the device is never patched in place

Project terminology is strict: **PTT always means the separate physical
Whisplay hardware button on BCM17**. Held Backspace is only its browser
simulation. Encoder presses and drawn display controls are never PTT.

The long-term module contract requires every service, including current
built-ins, to live in its own Git-visible module directory with its own
manifest, entry point, tests and complete service README. This is a staged
extraction of the existing implementation behind the same core broker, not a
parallel rewrite; the current monolithic service catalog remains the migration
source of truth until each extraction is regression-tested.

Hardware-specific integration still pending:

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

Saved BrandMeister talkgroups remain configured across restarts, but DMR audio
never starts automatically after boot. The receiver starts only after an
explicit PLAY/ENTER action and the same action stops its real HoseLine/ALSA
owner again.

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
identity and application mode at I2C address `0x57`, and reads the
calculated 0–100% capacity register. The percentage appears immediately left
of the physical battery icon and in the web energy card. It never changes
charging, RTC, shutdown or controller configuration.

A separate read-only 20-ms monitor reads only the documented power-button bit
in status register `0x02`. It emits Home after a released press of at most
0.6 seconds; longer holds produce no application event and therefore retain
the PiSugar's normal power-off behavior. It never changes watchdog or
controller configuration.

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
The same settings area stores the selected accent color. Every normal service
view receives one centrally composited, clearly visible strong, soft edge glow
along the physical rounded contour, including a straight upper
glow immediately below the status row. Recorder, system and future plugin
views inherit it without service-specific drawing code. Menus and the WLAN
setup screen deliberately retain their separate navigation treatment. The glow
uses the accent color while idle, green during actual audio playback and red
during radio or microphone recording; continuous recording pulses red. Real
Play actions are green, while Pause and Stop remain in the accent color. It has
no crisp border line and no disable switch. Media, weather and camera
images use the same 43-pixel corner radius as the panel. Device text is never
introduced below the battery percentage's exact 9-pixel TrueType reference
size; the shared font loader clamps every native-display font to at least 9
pixels, and important actions use larger type. Battery percentage remains bold.
Menu selection and PTT indicators remain independent functional cues.

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
service explicitly owns PTT. A short PiSugar power-button press opens this
menu globally; the left encoder push is deliberately unassigned for future
service use. Browser Space simulates the PiSugar short press. The default
interface accent is `#FDB813`.

The complete user-facing control contract, hardware legend and honest mapping
of every currently implemented service are maintained in
[`docs/USER_GUIDE_CONTROLS.md`](docs/USER_GUIDE_CONTROLS.md). Its two scalable
SVG quick-reference sheets are suitable for the browser, repository and print.
The hardware sheet is a source-grounded component map of the real Whisplay
front/back and Whisplay → Pi Zero 2 W → PiSugar 3 stack. It must never invent
an enclosure or button position; planned encoders remain visibly separate from
already fitted hardware until they have been measured. The separate white
service-comparison sheet covers every currently enabled service in one repeated
layout: real captured Whisplay view on the left and that service's exact
controls on the right. Ready, browser-only and configuration-required services
remain visibly distinct instead of receiving a fabricated native screen.

BrandMeister replaces the otherwise meaningless Squelch assignment in its
device view. The right outer axis browses the complete official talkgroup
catalog one entry at a time, while the left inner axis jumps 25 entries per
detent. The device renders six bounded catalog rows with enabled entries first
and all inactive entries below them. A speaking TG keeps its normal row and
glows green; its technical position remains visible and the real HoseLine
talker alias is appended behind it in the accent colour when supplied. The
leading green point pulses at 2 Hz. The short right press starts BrandMeister
reception for the enabled TGs and therefore explicitly takes over audio from
radio or another audio service. A short PTT press toggles the selected TG when
the button is released. Holding PTT for at least two seconds instead opens the
country filter; the right outer axis chooses a country and the right press
applies it. Neither action transmits audio. A long right press remains the
service quick menu. The localized header shows these real assignments
(`JMP`/`TG` in English) instead of the normal `SQL`/`CH` labels. On 2026-10-31
a real subscribed HoseLine call was heard through the fitted Whisplay speaker,
confirming the native ALSA path. Ended calls remain visibly marked as last
heard until a new receiver session begins. This is observed HoseLine activity,
not a claim that every member of a talkgroup is online.
The vertical right-button label shows `PLAY` or its localized equivalent
because the right press owns reception start. The selected catalog row still
shows its translated On/Off state, and PTT changes that state. In the browser
every saved row has a normal checkbox plus a written On/Off state. A change
reconfigures an already running receiver immediately, but never steals audio
  from radio while BrandMeister is stopped. If six TGs are already active, the
  seventh opens an explicit replacement choice on both device and browser;
  cancel leaves all six unchanged.

The service section accepts an explicit `http` or `https` audio URL for local
playback and recording. It rejects credentials embedded in URLs and does not
persist URL query strings in public status. Actual sound requires an ALSA
device. Local sound uses the official Whisplay ALSA card `whisplaysound`; the
installer builds the unified driver for either supported codec revision and
the real speaker is verified after reboot.
RSS/Atom URLs and camera snapshot URLs can be loaded in the same local panel.
Feed downloads are size-limited; camera responses are decoded, dimension-
checked, resized and re-encoded before the browser can retrieve them.
The camera library stores up to 100 non-secret sources and preserves user
order and deletion across updates. MJPEG reads only the first complete bounded
JPEG frame instead of proxying an endless foreign stream. RTSP uses one
argument-only `ffmpeg` frame extraction with a hard timeout. Persistent URLs
may not contain credentials or query strings. Authenticated private RTSP and
ONVIF discovery therefore remain an isolated-adapter task; no camera password
is written to Git, SQLite, public status, logs or backups. See
[`docs/CAMERAS.md`](docs/CAMERAS.md).
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
ROCK ANTENNE and ROCK FM. A separate inactive catalog expands this to 46
reviewed stations with at least five each in German, English, Polish, French,
Spanish, Italian, Dutch and Portuguese. Activating a catalog row moves it into
the persistent personal list; updates do not activate new stations or restore
ones the user removed. News presets include
tagesschau, Deutschlandfunk Nachrichten, RMF24 and BBC News World. The source
addresses and their review references are documented in
[`docs/PRESETS.md`](docs/PRESETS.md). Station artwork is fetched only from the
reviewed list, size-limited, decoded and locally re-encoded as JPEG. If a logo
is unavailable, the dashboard keeps working and displays a text tile instead.

The browser radio manager keeps the existing add form, shared full-metadata
search and language/category filters above two compact sub-tabs. **Active
stations** contains the persistent personal order; **Add stations** contains
only inactive reviewed presets. A newly entered custom station and an activated
catalog station are appended to the personal order and immediately open the
active tab. Both tab selectors remain visible at all times; the selected one is
shown with a readable accent highlight rather than being hidden. The Polish
inactive catalog additionally contains Radio GRA Toruń,
Polskie Radio Dwójka, Polskie Radio Trójka, Radio 357 and Radio Nowy Świat;
religious stations are intentionally not included.

The **Podcasts** tab accepts a public RSS/Atom podcast-feed address, stores the
subscription in the same non-secret SQLite state, loads at most 50 playable
audio episodes on demand and can search or play those episodes. Raw feed and
enclosure URLs are not returned by the status API. Feeds with embedded
credentials or persistent query strings are refused so signed/private feed
tokens cannot accidentally enter backups or public state.

The **Mediatheques** tab provides credential-free catalog search for ARD, ZDF
and the German public documentary, information and regional broadcasters
through the bounded MediathekViewWeb index. Compact current selections cover
news, Tatort/crime, documentaries, science, Terra X, Harald Lesch, history and
nature. Browser video follows one opaque, process-local redirect without proxying the
large media through the Pi. Every result separately offers device audio and
device video; both always choose the smallest available broadcaster
representation. Device video takes its audio-synchronized frame from the same
central mpv process and uses only one transient JPEG below `/run/openr4d10`.
Only the moving media region may update at up to 25 FPS while video is playing;
pause immediately returns to the normal 10-FPS full-UI ceiling. Browsing and
searching never interrupt current audio. Raw
stream and website URLs stay process-local and are not exposed by
the status API. This integration does not bypass DRM, age gates, login or
geoblocking. The exact catalog and limits are documented in
[`docs/MEDIATHEK.md`](docs/MEDIATHEK.md).
Device audio explicitly disables mpv video decoding; device video enables it
only for that selected load. Radio, podcasts and other audio sources keep video
decoding off.

The **AmbientR4D10** tab is an independent audio service, not a radio-station
group or a third-party branded clone. Its ten built-in soundscapes are fetched
once from reviewed public CC sources, checksum-verified into the protected
local media cache and looped offline by the existing private mpv owner;
the café uses a quieter CC0 coffeehouse recording with a small group instead
of dense crowd noise. Opening the service does not disturb other audio. Once
its channel control is turned, the newly selected scene starts immediately and
replaces the previous audio source. Scene order, deletion and custom
credential-free HTTP(S) additions persist across updates. Sources, attribution
and licenses are recorded in [`docs/AMBIENT.md`](docs/AMBIENT.md). The ten
matching scene artworks are bundled locally, so no external image service is
needed at runtime. The Ambient tab loads those local thumbnails immediately
through the bounded OpenR4d10 content endpoint rather than deferring them as
off-screen browser images.

Hold the right control for two seconds in the Ambient view to open the sound
layer list. The outer right control selects, a short right press toggles, the
inner left control changes the selected relative level in ten-percent steps,
and PTT returns. At most two layers run together. The last list row and the
browser can save the current base scene plus layer levels as an update-safe
favorite mix.

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
