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
pixels. This is deliberate: the verified Whisplay controller and header pinout
are documented in `docs/HARDWARE.md`, but the display adapter has not yet been
implemented and verified on this Debian 13 target. A future Whisplay adapter is
responsible for mapping a frame onto that hardware.

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

1. `systemd` creates runtime and state directories as the `openr4d10` user.
2. The CLI parses and validates both TOML files.
3. Adapters are created from explicit backend names.
4. The read-only web dashboard binds to the configured local address and port.
5. The text boot manifest is rendered when enabled.
6. The semantic dashboard state is refreshed at the configured interval and
   exposed through `/api/status`.
7. `SIGTERM` or `SIGINT` stops the loop and HTTP server cleanly.

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

Hardware device and group permissions are intentionally not granted globally.
They must be added narrowly after the real adapter and device nodes are known.
