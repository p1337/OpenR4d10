# Hardware integration status

## Known, verified deployment target

- Raspberry Pi Zero 2 W Rev 1.0
- Debian GNU/Linux 13 (Trixie)
- `aarch64`

## Physical assembly reported on 2026-10-30

- complete 2 x 20 header soldered at all 40 Pi contacts
- Whisplay HAT fitted on the front
- PiSugar 3 battery pack fitted on the rear
- the PiSugar supplies the running Pi successfully from its battery; the
  software now has a bounded, read-only PiSugar 3 percentage adapter
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
- exact panel in the
  [official Whisplay display package](https://cdn.pisugar.com/pisugar-docs/documents/whisplay/1.69LCD.zip):
  `ZJY169TP-IF95`,
  27.972 x 32.634 mm active area and 0.11655 mm square pixel pitch
- audio codec revision: WM8960 or ES8389
- physical orientation: Whisplay button side faces the Pi USB-port side

The panel has four visibly rounded corners. The
[R5-mm geometry documented for this matching 1.69-inch panel family](https://www.waveshare.com/wiki/1.69inch_LCD_Module)
corresponds to
approximately 43 pixels at the documented pitch. UI decoration must therefore
follow that contour. The permanent player effect is a blurred, line-free glow
whose source follows the outer R5 boundary and closes with a straight light
source immediately below the status row. The physical panel, the content mask
and the matching browser mask clip its outside half, leaving only a soft inward
glow without a corner line that can disappear below the glass.

### User-facing peripherals

The manufacturer documents these user-facing resources on the Whisplay HAT:

- two onboard microphones;
- one onboard 8 ohm / 1 W speaker;
- one PH2.0 connector for a single-channel external mono speaker;
- one three-channel RGB LED;
- one programmable physical button;
- the LCD and its controllable backlight listed above.

### Can the RGB LED be used as an ambient-light sensor?

An LED junction can physically act as a wavelength-selective photodiode. A
common all-digital measurement first reverse-biases the junction capacitance,
then changes the circuit to a high-impedance input and times how quickly the
photocurrent discharges it. This is not a resistance measurement. The method is
described in the MERL paper
[`Very Low-Cost Sensing and Communication Using Bidirectional LEDs`](https://people.ece.cornell.edu/land/courses/ece4760/ideas/LEDsensor.pdf)
and in the peer-reviewed paired-LED study
[`A low-cost optical sensing device based on paired emitter-detector LEDs`](https://doi.org/10.1016/j.aca.2005.10.046).

That general principle does **not** establish a safe sensing path on the fitted
Whisplay. The manufacturer exposes only one Raspberry Pi line for each colour
(physical P22/P18/P16, BCM25/24/23), and its official runtime claims all three
as active-low outputs. No official Whisplay schematic currently documents the
RGB LED common terminal, individual series resistors, reverse-voltage limit or
an analogue sensing node. The Pi Zero 2 W header provides digital GPIO but no
ADC. The published active-low drive makes a common-supply topology plausible,
but that remains an inference and is insufficient authority to reverse-bias a
board-mounted LED through unknown circuitry.

Consequently OpenR4d10 does not repurpose or reverse-drive the onboard RGB LED
as a light sensor. Automatic brightness requires either a manufacturer
schematic plus bench measurements proving a safe two-terminal timing circuit,
or a separate verified ambient-light sensor/ADC. Leaving the RGB LED unused
does not create the missing electrical measurement path.

The real OpenR4d10 stack reports `whisplaysound` as a WM8960 sound card for
both ALSA capture and playback, with stable `mic` and `speaker` mixer controls.
The manufacturer also ships ES8389 variants, so application code continues to
use the stable ALSA card name rather than assuming a codec revision. No
manufacturer documentation currently establishes a touchscreen, camera, IMU,
rotary encoder, or additional physical buttons on this HAT; none of those may
be exposed as present without later hardware evidence.

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

The UI implements the documented four compact control fields, inward-offset
vertical `MENU`/`PLAY` click labels, actual Wi-Fi SSID/IP, a larger time without
a date, readable battery percentage and the service-dependent media area. The
control header is shorter and uses larger labels/values. No device information
text may be smaller than the SSID text. In radio mode the service caption,
written player state and lower status/brand strip are omitted; station,
weather and camera artwork use the full media width and the panel's 43-pixel
corner radius. The play/pause icon sits at the upper right below the battery.
The main-menu body contains its large localized heading followed immediately by
the documented vertical settings list and no player. The right outer encoder
scrolls that list, the right press selects, and PTT returns one menu level unless
a ready service explicitly owns PTT.
Logical encoder events are implemented and can be tested without hardware; no
encoder GPIO assignment is active. The local web dashboard exposes all four
rotations and both short/long press actions through the same input-event path
and repaints the physical LCD immediately.

When NetworkManager enters the automatic setup-hotspot mode, the physical
display temporarily replaces the normal content area with the complete
device-specific setup SSID, locally generated WPA2 passphrase and
`http://10.42.0.1/`. This is intentionally a physical provisioning screen: the
passphrase is never added to semantic frames, public status, SQLite, backups or
logs. After the phone submits a working client WLAN through the existing web
repair form, the normal device UI returns and the status row shows that WLAN's
actual SSID. If no profile is active it shows `OFFLINE`, never the fabricated
generic label `WLAN`.

The official PiSugar Whisplay
[`runtime/whisplay.py`](https://github.com/PiSugar/Whisplay/blob/bb4cdcc5371838009804940559e828d6a7a7ba04/runtime/whisplay.py)
for Raspberry Pi Zero 2 W implements `set_backlight(0..100)` as 1000 Hz
software PWM on the same physical pin 15 / BCM22 output. Because the backlight
is active-low, its GPIO duty is
`100 - brightness`. The real stack has now disproved the Python thread as a
usable timing implementation: 100 percent is steady, while every intermediate
setting visibly alternates between bright and dark. OpenR4d10 must retain the
verified BCM22 mapping and active-low polarity but move the timing out of
Python to a target-available stable PWM implementation. The real target
used Raspberry Pi OS package `python3-lgpio` 0.2.2 as an intermediate repair.
That removed Python scheduling and redundant waveform restarts, but the real
battery-powered stack still produced occasional brighter and darker jumps
under CPU load. A controlled four-worker CPU test kept `get_throttled=0x0`,
1 GHz CPU frequency and normal temperature, so no firmware-level under-voltage
or thermal throttle event was recorded. This does not measure small 5 V rail
movement below the Pi threshold, but the bidirectional jumps match delayed PWM
on/off edges.

Source inspection established that `lgpio.tx_pwm` is still a normal userspace
software-timing thread using absolute sleeps. OpenR4d10 therefore installs the
Raspberry Pi kernel's `pwm-gpio,gpio=22` overlay and drives its 1 kHz PWM through
the kernel high-resolution-timer path. BCM22 mapping and active-low duty remain
unchanged; this is kernel-timed software PWM, not native PWM hardware. A fixed
root helper is the only sysfs writer. The application queues a validated 0–100
integer below `/run/openr4d10-backlight` and never owns BCM22.

The boot ownership conflict is explicitly resolved: an early initializer holds
the backlight off, the native C player owns only reset and data/command, and it
queues 100 percent only after the first complete frame is in display RAM. The
application later restores the persistent SQLite value through the same bounded
request. The overlay becomes active only after the installer's reboot.

The proposed RGB-LED light experiment cannot be a direct resistance read: the
Pi header exposes digital GPIO and no ADC. A later supervised test may look for
light-dependent junction discharge timing only after the LED common terminal,
series resistors, GPIO directions and safe voltage/reverse-bias limits have
been verified on the actual board. Until then all three active-low LED GPIOs
remain ordinary outputs and must not be driven against the Whisplay circuit.

The application media boundary uses generic ALSA through Debian's mpv and
ffmpeg packages. Its systemd unit allows the standard `char-alsa` device class
and the `audio` group. Release 0.10.5 adds the official unified PiSugar
Whisplay driver, which detects WM8960 or ES8389 rather than requiring the
physical revision to be guessed.

On the real freshly installed Pi on 2026-10-30, `/proc/asound/cards` and
`aplay -l` expose only `vc4-hdmi`; no Whisplay speaker device is present yet.
Independent `ffprobe` checks successfully identify the curated SWR3, sunshine
live and Deutschlandfunk endpoints as MP3 streams. A playback timeout on this
stack must therefore not be described as a WLAN or station-source failure;
the missing Whisplay ALSA integration remains the open hardware boundary.

A later live check with OpenR4d10 0.10.4 confirms that SWR3 is in `playing`
state and the private mpv process is running, while ALSA still exposes only
`vc4-hdmi`. There is no `/dev/i2c-*`, no `whisplaysound` card and no active
Whisplay sound overlay. The physical HAT also exposes no readable HAT EEPROM
node on this boot, so automatic EEPROM overlay loading cannot be assumed.

The current official PiSugar Whisplay repository provides one unified
`whisplay-soundcard` driver for both WM8960 and ES8389 variants. OpenR4d10 pins
the unmodified sound-card source to manufacturer commit
`736975188ebbe146d319e450aad19c218a310611`; its complete upstream archive has
SHA-256
`1fac1045fb763de52eed5aa23704d7752ff5e024c9ce64692cf9832261cfb88a`.
Source, Apache-2.0 license and provenance are retained below
`vendor/pisugar-whisplay`.

The main installer enables I2C and I2S, builds the module for the running
kernel, installs the device-tree overlay, makes ALSA card `whisplaysound` the
default and enables the manufacturer's warm-up service. A reboot is mandatory.
The normal installer performs that reboot automatically after every preceding
step and diagnostic succeeds; `--no-reboot` is the explicit maintenance opt-out.
On Raspberry Pi OS Debian 13 it installs the exact
`linux-headers-$(uname -r)` package; the obsolete package name
`raspberrypi-kernel-headers` is not available on the verified target.
Before reboot, `doctor` reports the installed-but-inactive state; afterwards it
requires the card to appear in `/proc/asound/cards`. Actual speaker operation
still needs a real listening test and is not claimed merely from the card name.

The real target has now completed that reboot with OpenR4d10 0.10.6. ALSA
reports card `whisplaysound`, device `Whisplay HiFi wm8960-hifi-0`; the unified
driver therefore detected this physical HAT as WM8960. Mixer control `speaker`
exists with range 0 through 100 and was initialized to 80. These checks confirm
driver, overlay and mixer activation, but not yet audible output from the
speaker; the listening test remains separate.

## PiSugar 3 percentage telemetry

The physically reported pack is the 1200-mAh PiSugar 3 for the Pi Zero family.
The official
[PiSugar 3 documentation](https://docs.pisugar.com/docs/product-wiki/battery/pisugar3/pisugar-3-series)
identifies controller address `0x57`, register `0x00` value `3`,
application-mode register `0x01` value `0x0F` and the calculated battery
percentage in register `0x2A`. The manufacturer's
[reference battery module](https://github.com/PiSugar/pisugar-power-manager-rs/blob/master/pisugar-module/pisugar-3/pisugar_3_battery.c)
uses the same identity checks and register mapping.

`PiSugar3Telemetry` opens only `/dev/i2c-1`, selects address `0x57`, verifies
the identity and application mode, and reads the single percentage byte using
the manufacturer's `I2C_SMBUS_BYTE_DATA` transaction. A value outside 0
through 100 or an identity mismatch becomes an adapter error; it is never
drawn as a plausible battery level. The adapter does not write
charging, RTC, watchdog, shutdown or configuration registers. The installer
loads `i2c-dev`, grants the service only its existing I2C group plus
`/dev/i2c-1`, and does not install the optional PiSugar HTTP server or create
an account.

The first real-target implementation used separate register-selection and
read system calls. On this physical PiSugar that starts a new transaction and
returns the version byte `0x03` for every requested register. A target probe on
2026-10-31 confirmed the required SMBus byte-data path as `0x03` for register
`0x00`, `0x0F` for `0x01`, and `0x5A` (90%) for `0x2A`. Do not replace the
combined SMBus transaction with split raw I2C calls.

## Still deliberately unknown

The Whisplay audio driver has identified the installed HAT as WM8960, and
capture/playback devices plus `mic`/`speaker` controls are present; an actual
microphone recording and audible speaker test remain separate physical checks.
PiSugar charging control, RTC, watchdog and shutdown integration remain outside
the percentage adapter until individually requested and verified. The Whisplay
display backend is implemented and physically verified on the real stack.

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
