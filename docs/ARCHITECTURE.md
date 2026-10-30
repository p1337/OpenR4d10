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
WASD, arrow keys, Space, Enter and held Q into this same contract and are
disabled while the user edits a form field.

Semantic actions are resolved by the application before the display reflects
them. In particular, a short `right_press` routes through `ServiceCatalog` to
the same `MpvEngine.toggle_pause()` operation as the HTTP media control; only a
successfully active or paused stream may be toggled. A held `right_press`
remains display navigation for the quick menu. This prevents keyboard or future
GPIO input from changing a presentation-only `playing` flag while audio keeps
running.

The same router maps each `left_outer` detent to a bounded ten-percentage-point
change of the real mpv volume and `right_outer` to cyclic preset selection
while the radio service is active.
`ServiceCatalog` owns the active preset identity, human-readable station name,
channel number and reviewed artwork ID. The public semantic frame contains only
that safe metadata; the Whisplay adapter resolves an artwork ID against its
configured private cache root and otherwise draws a local initials tile. It
never receives a remote image URL or exposes the private cache path.
Selecting a curated preset starts its existing bounded decode/re-encode cache
operation in a daemon worker after audio loading succeeds. Artwork latency or
failure therefore cannot delay or fail stream switching; a later normal frame
refresh picks up the completed local JPEG.
The application serializes the semantic media action, device-state update and
immediate repaint as one device-input transaction so keyboard repeat and future
GPIO events cannot lose volume or channel steps through concurrent requests.

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

The web dashboard persists named radio stations without query strings and can
rescan the private media directory for a bounded set of supported extensions.
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

Curated radio and news entries are immutable data in `presets.py`, separate
from playback and parser logic. Public status includes display metadata and a
local artwork route, but omits the underlying stream, feed and remote artwork
addresses. Selecting a radio resolves the reviewed stream only inside the
core. Preset artwork uses the same bounded-download boundary as camera images,
is decoded and re-encoded to a maximum 256 x 256 JPEG in the private cache, and
falls back to a browser-generated initials tile when retrieval fails. Current
sources and their review references are recorded in `PRESETS.md`.

For a fresh machine, `bootstrap.sh` downloads a GitHub-generated source archive
over HTTPS into a private temporary directory. It checks paths and archive
integrity before extraction, then invokes the same local `install.sh`. Git is
not an installation dependency. The reviewed official Whisplay sound-card
source is pinned and vendored with its Apache-2.0 license, so audio installation
also requires neither Git nor a second source download. The installer builds it
in a private temporary directory for the running kernel, installs the unified
WM8960/ES8389 module and overlay, and leaves activation to the required reboot.

## Startup sequence

1. `openr4d10-boot.service` opens SPI0/CS0 plus only the verified LCD GPIO
   lines and plays the native animation; its final second loops.
2. `systemd` creates application runtime and state directories as the
   `openr4d10` user.
3. The CLI parses and validates both TOML files.
4. Adapters are created from explicit backend names.
5. The service catalog migrates the non-secret state database and evaluates
   local dependencies.
6. The read-only web dashboard binds to the configured local address and port.
7. The semantic text boot manifest is rendered when enabled.
8. The semantic dashboard state is refreshed at the configured interval and
   exposed through `/api/status`.
9. The Whisplay UI calls `claim_display()`, waits for the boot player to close
   SPI/GPIO and keeps the ownership lock for its entire lifetime.
10. `SIGTERM` or `SIGINT` stops the loop, database and HTTP server cleanly.

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
application runs as `openr4d10`, receives only the `gpio`, `spi` and standard
`audio` supplementary groups. Its closed policy permits the same LCD devices
plus the standard `char-alsa` device class for media playback/recording; it
still has no direct access to I2C, homes or unrelated hardware. Codec control
and detection stay inside the kernel/ALSA driver installed by the privileged
installer; the application itself never selects or guesses a codec revision.
