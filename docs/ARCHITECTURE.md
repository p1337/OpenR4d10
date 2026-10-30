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
pixels. The native early-boot player is a separate, deliberately narrow path:
it initializes the verified Whisplay ST7789 panel and streams the checked-in
240 x 280 RGB565 animation before the application is ready. The final physical
application renderer is still responsible for mapping semantic frames onto the
panel and then claiming display ownership from the boot player.

## Configuration and storage

- repository defaults: `config/*.toml`
- installed live configuration: `/etc/openr4d10/*.toml`
- current default copies for comparison: `/etc/openr4d10/*.toml.dist`
- immutable application release: `/opt/openr4d10/releases/<version>`
- active release symlink: `/opt/openr4d10/current`
- ephemeral runtime output: `/run/openr4d10`
- persistent application state: `/var/lib/openr4d10`
- service logs: system journal, unit `openr4d10.service`

The installer never overwrites live configuration. It refreshes only the
`.dist` files. No credential store exists in the application.

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
5. The read-only web dashboard binds to the configured local address and port.
6. The semantic text boot manifest is rendered when enabled.
7. The semantic dashboard state is refreshed at the configured interval and
   exposed through `/api/status`.
8. A future physical UI calls `claim_display()`, waits for the boot player to
   close SPI/GPIO and keeps the ownership lock for its entire lifetime.
9. `SIGTERM` or `SIGINT` stops the loop and HTTP server cleanly.

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

Hardware device access is not granted globally. The early boot unit runs a
small native player with a closed device policy that permits only
`/dev/spidev0.0` and `/dev/gpiochip0`. The application service retains its
stricter private-device policy until the physical UI renderer exists.
