# Native Whisplay boot display

Read [../CODEX_TO_CODEX_MASTER.md](../CODEX_TO_CODEX_MASTER.md) first.

Prepared for Raspberry Pi Zero 2 W and the PiSugar Whisplay ST7789 panel.
**This implementation has passed development-host checks. It has not been
installed or measured on the physical Pi/Whisplay.**

The approved source is
`assets/boot/OpenR4d10_APPROVED_ORIGINAL.mp4` in the project root, SHA256
`b15de122f95d0fd0281ab81e989cba5d715456a701eed686bf14fcdcb24d6c19`.
Its animation is preserved. Conversion changes only resolution, placement and
pixel encoding; no generated replacement animation is used.

## What the hardware can do

Whisplay is an SPI-controlled LCD with volatile display RAM. It has no exposed
standalone boot-animation firmware or file player to flash. At cold power-on,
the existing Pi must initialize SPI and the LCD before a custom image can
appear. An image precisely at power application is not possible through this
software path.

The prepared stages are:

1. Optional initramfs: paint the first skull frame once, before mounting the
   root filesystem, as soon as the GPIO/SPI devices exist.
2. Early systemd service: play the approved animation once, then repeat its
   final second while Linux and the application continue starting.
3. Actual physical UI: acquire the display-owner lock and take over. A working
   web API alone does not stop the boot animation.

The initramfs stage is a still image; the animated stage starts with the root
filesystem. Neither stage depends on Wi-Fi, audio, a browser or Python. The
vendor reset/sleep sequence alone takes approximately 440 ms **after** device
availability; this is not a measured power-to-image time.

Keeping the Pi running and waking its display could hide a cold boot, but
consumes standby power. A separate display controller would be a hardware
redesign, not firmware for the present HAT. Neither alternative is implemented.

## Native files

| File | Purpose | Size / timing |
| --- | --- | --- |
| `assets/boot.opb` | Actual native boot animation | 1,589,895 bytes; 240 × 280; 24 fps; 73 frames |
| `assets/first.opb` | Tiny first-frame pack for initramfs | 12,551 bytes |
| `assets/first.rgb565` | Uncompressed first frame | 134,400 bytes |
| `assets/preview_240x280.mp4` | Browser/phone preview only | 235,268 bytes; 3.042 s |
| `assets/manifest.json` | Source hash, timing and validation status | JSON |

The square source is fitted without stretching or cutting the wordmark. Its
22-pixel near-black footer at native scale is removed (maximum discarded RGB
value 13/255 in the approved source). The content is placed 22 pixels lower,
so the real fire base reaches physical row 279. The unused space is above.
The converter refuses this framing if a different source has visible content
in that footer. RGB565 uses
the panel's big-endian wire order; per-frame zlib compression is lossless after
the necessary 24-bit-to-16-bit conversion. At boot the player expands only one
134.4 KB pixel frame at a time. It does not decode MP4/H.264.

The last 24 original frames repeat in forward order. The loop join must still
be reviewed on hardware; it is not a newly generated seamless extension. If a
new longer version is approved, rebuild from that separately named source and
retain the original unchanged.

## Installation on the target Pi

The main OpenR4d10 installer now installs this normal boot stage automatically.
From the project root it can also be installed separately:

```bash
sudo bash boot/install.sh
```

Optional earlier still image, with a boot-configuration backup:

```bash
sudo bash boot/install.sh --initramfs
```

The installer compiles on the Pi for its installed architecture, enables SPI
through `raspi-config` when available and otherwise adds the standard
`dtparam=spi=on` setting with a timestamped configuration backup,
installs the native player and enables its service for the next boot. It does
not reboot or start the player over an active display session. It refuses an
active/enabled `whisplay-daemon`, because two independent owners must not write
the LCD. If the application uses that daemon, implement the handoff in the
daemon first instead of bypassing it.

The optional initramfs route requires Raspberry Pi OS kernel hooks to copy the
matching image into the firmware partition. **Check that image before
rebooting**; this path is prepared, not target-validated. Do not enable it on an
unattended Pi without a way to recover the SD card. No SSH settings or secrets
are changed by this installer.

The standalone boot installer does not install the rest of OpenR4d10 or the
Whisplay audio driver. Those remain separate from the LCD boot path.

## Physical UI handoff

The web prototype currently has no physical UI renderer. Integrate the supplied
helper into that renderer when it exists:

```python
from openr4d10.boot_display import claim_display

# Finish other UI preparation first. Do not call from web API startup.
with claim_display():
    # Initialize WhisplayBoard here and draw the actual first UI frame.
    # Keep this context for the physical UI's entire lifetime.
    run_physical_ui()
```

The helper creates `/run/openr4d10-boot/release`, waits for the boot player to
close SPI/GPIO and holds `display.lock`. The UI process must belong to
`openr4d10` and have its own required GPIO/SPI permissions. The helper is
neither a renderer nor a substitute for the hardware driver. A vendor renderer
may reset the panel during initialization; measure and address any visible
handoff flash on the actual hardware.

## Verification and performance

Host checks:

```bash
gcc -static -O2 -std=c11 -Wall -Wextra -Werror \
  boot/native/openr4d10_boot.c -lz -o /tmp/openr4d10-boot-check
/tmp/openr4d10-boot-check --verify boot/assets/boot.opb
python3 -m unittest discover -s tests -v
```

`--verify` does not open GPIO/SPI. Invalid dimensions, truncation, corrupt
compressed records and CRC mismatches cause failure before hardware access.
`--benchmark N` measures host decompression only, **not Pi/display performance**.

SPI starts conservatively at 32 MHz; 24 full frames/s require 25.8048 Mbit/s of
pixel payload before overhead. The vendor driver requests 100 MHz, but this is
not a guarantee for every assembled unit. After installation, measure the
journal's first-frame kernel-monotonic timestamp and dropped-frame counter,
check colours/orientation, warm restart, cold start, loop join and UI handoff.
Do not claim a frame rate or boot latency until measured on the actual Pi.

## Disable / recovery

To disable only the normal animated stage:

```bash
sudo systemctl disable --now openr4d10-boot.service
```

For an installed early stage, remove these two installer-owned files and then
rebuild the current kernel's initramfs:

```bash
sudo rm /etc/initramfs-tools/hooks/openr4d10-boot
sudo rm /etc/initramfs-tools/scripts/init-top/openr4d10-boot
sudo update-initramfs -u -k "$(uname -r)"
```

Remove the three-line OpenR4d10 block from `config.txt` only if the system does
not otherwise need automatic initramfs. The timestamped backup is beside the
original config. Restore it only after comparing subsequent user changes.
The early display script exits successfully if its display attempt fails, so
an unavailable LCD should not itself block normal boot.

## Sources and license

- [PiSugar hardware overview and physical pins](https://docs.pisugar.com/docs/product-wiki/whisplay/overview).
- [PiSugar Whisplay driver](https://github.com/PiSugar/Whisplay), inspected at
  commit `b2ccecab528caf939f0e3a900547cd094029f13e`.
- [Raspberry Pi boot configuration](https://www.raspberrypi.com/documentation/computers/config_txt.html).
- [Linux GPIO character interface](https://www.kernel.org/doc/html/latest/userspace-api/gpio/chardev.html).
- [Linux spidev interface](https://www.kernel.org/doc/html/latest/spi/spidev.html).

Vendor-derived initialization retains Apache-2.0 attribution in
`native/NOTICE.PiSugar` and `native/LICENSE.PiSugar`. A repository-wide public
license has not yet been added; do not infer one from the vendor attribution.
