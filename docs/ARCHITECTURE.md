# Architecture

## Design boundary

OpenR4d10 has a hardware-independent core and small adapters at the boundary:

```text
Linux/systemd
    |
    v
CLI -> configuration -> application loop -> semantic UI Frame
                                      |             |
                                      |             +-> display adapter
                                      +-> receiver/power telemetry adapters
```

A `Frame` describes intent (`screen`, `title`, `body`, fields and severity), not
pixels. This is deliberate: display dimensions, colour format, orientation,
controller and pins are not documented in this repository. A future Whisplay
adapter is responsible for mapping a frame onto verified hardware.

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

## Startup sequence

1. `systemd` creates runtime and state directories as the `openr4d10` user.
2. The CLI parses and validates both TOML files.
3. Adapters are created from explicit backend names.
4. The text boot manifest is rendered when enabled.
5. The dashboard is refreshed at the configured interval.
6. `SIGTERM` or `SIGINT` stops the loop cleanly.

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
runtime and state directories. The generic command adapter uses an argument
array and `shell=False`; it never interpolates input into a shell command.

Hardware device and group permissions are intentionally not granted globally.
They must be added narrowly after the real adapter and device nodes are known.
