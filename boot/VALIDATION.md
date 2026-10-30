# Validation — 2026-10-30

The native files were validated on the development host. A 2026-10-30 device
recording additionally confirms that the original native player produces the
correct visible image, colours and orientation on the assembled Pi Zero 2 W /
Whisplay / PiSugar 3 stack.

- Native player: static GCC build, `-O2 -std=c11 -Wall -Wextra -Werror` passed.
- All 109 generated animation frames and the separate first frame decompressed and passed
  CRC validation through the actual C reader, without GPIO/SPI access.
- Truncated, trailing, wrong-dimension, damaged-compression and CRC-damaged
  files rejected in verification mode.
- Every first-frame RGB565 pixel matches the native conversion and raw file.
- Display lock: UI waits for existing owner, gets exclusive ownership and
  reports timeout / absent runtime explicitly.
- Project test suite: 12 tests passed.
- Installer and initramfs scripts: shell syntax passed.
- systemd-analyze unit validation passed using the host-built executable path
  in a temporary copy of the unit. No service was installed or started.
- First and last native preview images inspected: portrait canvas, full skull,
  full wordmark, original lower-edge fire, no stretched square image.
- Framing correction: removed the 22-row footer with peak RGB value 13/255,
  shifted original content down 22 pixels. All retained pixels in all 73 frames
  compare exactly before RGB565 conversion; no skull or letter was cut off.
  Original blue fire reaches physical row 279 in all 24 end-loop frames.

Still required on the actual target: revised 1.5-second skull extension, new
source-frame-54 loop seam, GPIO retention between boot stages, cold
power-to-image latency, achieved frame rate, audio coexistence and physical UI
handoff. The optional initramfs image and Raspberry Pi OS firmware-copy hooks
have not been tested on the target. Web API readiness is not display readiness.
