# Validation — 2026-10-30

Development host only. No attached Pi Zero 2 W or Whisplay was used.

- Native player: static GCC build, `-O2 -std=c11 -Wall -Wextra -Werror` passed.
- All 73 animation frames and the separate first frame decompressed and passed
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

Still required on actual target: kernel/device-node compatibility, colour
order and orientation, GPIO retention between boot stages, cold power-to-image
latency, achieved frame rate, loop seam, audio coexistence and physical UI
handoff. The optional initramfs image and Raspberry Pi OS firmware-copy hooks
have not been tested on the target. Web API readiness is not display readiness.
