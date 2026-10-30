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
press controls are already modeled and tested. No GPIO number appears in the UI
or navigation logic; the GPIO input source is added after the delivered
encoders have been identified and measured.

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

`MpvEngine` starts lazily and controls mpv through an inherited Unix socket
using the documented JSON IPC. It disables user configuration and terminal
input. `StreamRecorder` invokes ffmpeg through an argument array with
`shell=False` semantics and writes 64-kbit/s Opus below the state directory.
Network URLs are limited to HTTP(S), reject embedded credentials and are
redacted before appearing in status. Local media must resolve below the
approved media directory.

For a fresh machine, `bootstrap.sh` downloads a GitHub-generated source archive
over HTTPS into a private temporary directory. It checks paths and archive
integrity before extraction, then invokes the same local `install.sh`. Git is
not an installation dependency.

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
still has no access to I2C, homes or unrelated hardware. This generic ALSA
boundary does not select or configure a Whisplay codec revision.
