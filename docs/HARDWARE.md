# Hardware integration status

## Known, verified deployment target

- Raspberry Pi Zero 2 W Rev 1.0
- Debian GNU/Linux 13 (Trixie)
- `aarch64`

## Physical assembly reported on 2026-10-30

- complete 2 x 20 header soldered at all 40 Pi contacts
- Whisplay HAT fitted on the front
- PiSugar 3 battery pack fitted on the rear
- Raspberry Pi and `openr4d10.service` boot successfully
- Whisplay RGB LED illuminates
- the original native boot animation has since been recorded visibly on the
  LCD with correct colour order and orientation

The earlier LED observation alone did not confirm the LCD SPI path. The later
device recording now confirms initialisation, SPI image transfer, colour order
and orientation. Sustained frame rate, boot latency, revised animation seam,
audio coexistence and long-term electrical stability remain target-unverified.

## Verified Whisplay HAT facts

The official [PiSugar Whisplay documentation](https://docs.pisugar.com/docs/product-wiki/whisplay/overview)
and [manufacturer product page](https://www.pisugar.com/products/whisplay-hat-for-pi-zero-2w-audio-display)
document the following:

- interface: full Raspberry Pi 40-pin GPIO header
- supply voltage: 5 V; logic voltage: 3.3 V
- display: 1.69 inch, 240 x 280 RGB, ST7789, 4-wire SPI
- audio codec revision: WM8960 or ES8389
- physical orientation: Whisplay button side faces the Pi USB-port side

The [Raspberry Pi Zero 2 W documentation](https://www.raspberrypi.com/documentation/computers/zero.html)
specifies one complete `2 x 20`, 2.54 mm male GPIO header soldered into all 40
through-holes for boards without a factory header. Do not
solder only the signal pins listed below: the complete header provides correct
alignment, mechanical support, ground/power contacts and the HAT connection.
The Whisplay plugs onto that header; it is not soldered directly to the Pi.

### Manufacturer pin assignment (physical pin numbers)

| Function | Physical pin(s) | Function | Physical pin(s) |
| --- | --- | --- | --- |
| 5 V | 2, 4 | Button | 11 |
| I2C data | 3 | LED 1 | 22 |
| I2C clock | 5 | LED 2 | 18 |
| SPI reset | 7 | LED 3 | 16 |
| SPI data/command | 13 | LCD control | 15 |
| SPI MOSI | 19 | SPI clock | 23 |
| SPI chip select | 24 | I2S word select | 35 |
| I2S data in | 38 | I2S data out | 40 |

The official driver additionally describes the audio bus as using I2S header
pins `12/35/38/40`. Ground is taken from the standard header ground contacts.

### Safe assembly

1. Shut the Pi down and disconnect USB power and any battery/UPS.
2. Fit the complete straight 2 x 20 male header; keep it square to the PCB.
3. Solder all 40 joints on the Pi. Do not solder with the Whisplay attached.
4. Inspect for bridges, especially around 5 V, 3.3 V and adjacent ground pins.
5. With power still disconnected, seat the Whisplay fully and without a
   one-row/one-column offset; button side points toward the Pi USB ports.
6. Hold the Whisplay PCB edges, not the glass, while seating it.

If the Whisplay board itself has no fitted female socket, stop and identify the
exact board/revision from clear photos before soldering; that is a different
assembly case.

### Physical access for additional controls

The Whisplay's female 2 x 20 socket covers the Pi's complete male header. A pin
can therefore be electrically unused by Whisplay while still being physically
inaccessible from above. Soldering only selected header pins does not solve
this and would make the HAT mechanically unreliable.

Bare mechanical rotary encoders are not SPI devices. A conventional encoder
with a push switch needs three GPIO inputs (`A`, `B`, and `SW`) plus a shared
ground. Its bare contacts may be wired directly; it does not need its own PCB.
Use 3.3 V GPIO pull-ups and never feed 5 V into a GPIO.

Without an additional breakout PCB, the only direct wiring option is to solder
thin insulated wires to the corresponding GPIO and ground solder pads on the
underside of the Pi after fitting the full header. Add strain relief and route
the wires so they cannot be pinched or short against the Whisplay or enclosure.
Do not do this if a PiSugar board, battery, case, or other hardware covers those
pads; use a suitable 40-pin header splitter/breakout instead.

Do not attach encoder contacts to the Whisplay's LCD SPI signals. Sharing an SPI
bus is relevant only for an actual SPI peripheral with its own chip-select and
does not provide inputs for a bare encoder.

No final encoder GPIO assignment is committed yet. The exact encoder type must
first be identified:

- two conventional rotary encoders with push switches require six GPIO inputs
  in total;
- two dual-concentric encoders with push switches commonly require ten GPIO
  inputs in total and may need a GPIO expander or small controller.

The planned underside wiring also has to be checked against the exact PiSugar
model and the enclosure before soldering.

As of 2026-10-30 the ordered dual-concentric encoders are still in transit from
China to Waiblingen. Physical measurement, continuity testing and soldering are
therefore not possible yet. UI development proceeds through the hardware-free
input-event interface; the future GPIO implementation must plug into that
interface without changing screen or navigation logic.

## Native boot display

The normal installer compiles `boot/native/openr4d10_boot.c` on the target,
verifies every compressed animation frame before installation, enables SPI and
enables `openr4d10-boot.service` for the next reboot. The implementation uses
the manufacturer-verified profile: SPI0/CS0, BCM4 reset, BCM27 data/command,
BCM22 active-low backlight, RGB565, MADCTL `0xC0` and vertical offset 20. It
starts conservatively at 32 MHz rather than copying the vendor runtime's
100 MHz request.

The service has access only to `/dev/spidev0.0` and `/dev/gpiochip0`. It does
not configure audio, I2C, PiSugar or encoder GPIOs. See `boot/README.md` for the
ownership handoff and exact validation status.

## Physical application UI

Release 0.4 adds the real physical renderer and selects
`display.backend = "whisplay"` by default. It uses Debian 13's packaged
`python3-pil`, `python3-libgpiod` and `python3-spidev` modules. The service waits
for the early player to release the display lock, keeps that lock, requests
only BCM4 reset, BCM27 data/command and BCM22 active-low backlight, and writes
240 x 280 big-endian RGB565 frames through SPI0/CS0 at a conservative 32 MHz.

The UI implements the documented four control fields, vertical `MENU`/`PLAY`
click labels, WLAN/IP, date/time and battery status row, and the
service-dependent media area. Logical encoder events are implemented and can be
tested without hardware; no encoder GPIO assignment is active.

## Still deliberately unknown

The installed Whisplay audio codec revision and PiSugar model/API have not yet
been identified on the physical device. Keep `power.backend` as `unconfigured`
until the PiSugar integration is implemented and verified. The Whisplay display
backend is implemented but remains physically unverified until the updated
installer has run and the real panel result has been reported.

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
6. Add only required groups/device permissions. The current unit uses
   `DevicePolicy=closed` and permits only the verified SPI and GPIO character
   devices; future audio, PiSugar or encoder access needs its own documented
   review.
7. Test boot, shutdown, helper timeout and disconnected-hardware behaviour.
8. Update this document with the source and verified target revision.

Do not place WLAN passwords, API tokens or device secrets in either TOML file.
If a future adapter requires a secret, use a separate root-owned credential
mechanism and document it without committing the value.
