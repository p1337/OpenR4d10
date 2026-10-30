# Hardware integration status

## Known, verified deployment target

- Raspberry Pi Zero 2 W Rev 1.0
- Debian GNU/Linux 13 (Trixie)
- `aarch64`

## Deliberately unknown

This repository currently has no trustworthy source for the exact Whisplay
board revision, display controller, resolution, colour format, SPI bus/chip
select, GPIO assignments, backlight control, input buttons or PiSugar model/API.
None of these values may be inferred from a product name alone.

Until those facts are documented, keep `display.backend` and `power.backend` as
`unconfigured`. This is a supported diagnostic mode, not an implementation gap
hidden by fake values.

## Generic adapter contract

### Display command

Configure an absolute executable and arguments:

```toml
[display]
backend = "command"
command = ["/opt/vendor/bin/verified-display-helper", "render"]
timeout_seconds = 2.0
```

For every frame, OpenR4d10 writes one JSON object to the helper's standard
input. The object contains:

```json
{
  "screen": "dashboard",
  "title": "OpenR4d10",
  "body": "Receiver ready",
  "fields": {},
  "severity": "info",
  "timestamp": "2026-10-30T12:00:00+00:00"
}
```

Exit status `0` means the frame was accepted. Standard output is ignored;
non-zero status and timeout are logged. The helper owns rasterisation, driver
initialisation and verified pin selection.

For integration testing without hardware, use the file adapter:

```toml
[display]
backend = "file"
output_path = "/run/openr4d10/display.json"
```

### Telemetry commands

Power and receiver command helpers receive no standard input and must print one
JSON object to standard output. Example shape (not a PiSugar protocol):

```json
{"state": "online", "battery_percent": 87}
```

The object is passed through as semantic UI data. OpenR4d10 does not assume
field names beyond the optional `state` value.

## Checklist before adding a vendor adapter

1. Record exact board and display model/revision.
2. Link the manufacturer's pinout and driver documentation.
3. Verify the bus and device nodes on the target Pi.
4. Confirm voltage and logic-level requirements before wiring.
5. Implement the helper without root privileges where possible.
6. Add only required groups/device permissions via a systemd drop-in. The
   default unit intentionally sets `PrivateDevices=true` and an empty capability
   set, so a verified hardware adapter must document its narrow override.
7. Test boot, shutdown, helper timeout and disconnected-hardware behaviour.
8. Update this document with the source and verified target revision.

Do not place WLAN passwords, API tokens or device secrets in either TOML file.
If a future adapter requires a secret, use a separate root-owned credential
mechanism and document it without committing the value.
