# OpenR4d10

OpenR4d10 is a small Python service for a Raspberry Pi Zero 2 W
running Debian 13 (Trixie). It provides a safe foundation for a receiver UI,
boot sequence, display output, status data and power telemetry without guessing
the Whisplay pinout, display controller or PiSugar protocol.

The repository is intentionally usable before the final hardware details are
known: the service starts in a visible `unconfigured` mode, while `doctor` and
the installer report exactly which adapters still need configuration.

## Current status

- Raspberry Pi Zero 2 W / Debian 13 / `aarch64` platform checks
- idempotent one-command online installer with no Git dependency
- hardened `systemd` autostart service
- responsive local web dashboard on `http://<raspberry-pi-ip>/`
- native Whisplay ST7789 boot animation installed and enabled automatically
- real-device-confirmed Whisplay SPI transport, colour order and orientation
- native 240 x 280 physical UI with the agreed four-axis encoder layout
- semantic UI frame model and configurable text boot sequence
- safe `unconfigured`, JSON-file and external-command display adapters
- built-in Linux system status and optional external-command status/power adapters
- persistent configuration in `/etc/openr4d10`
- runtime data in `/run/openr4d10` and state in `/var/lib/openr4d10`
- versioned SQLite state for non-secret settings, services, stations, channels,
  media and recordings
- central catalog covering all specified service modules with honest dependency,
  adapter and local-login readiness
- direct web-radio/local-media playback through private mpv JSON IPC and
  stream recording through shell-free ffmpeg/Opus
- standard-library-only test suite and GitHub Actions CI

Hardware-specific integration still pending:

- the Whisplay audio adapter
- PiSugar API details
- physical Whisplay audio codec setup and encoder GPIO input
- credentials, WLAN settings, tokens or secrets

Those values must come from the exact hardware documentation. See
[`docs/HARDWARE.md`](docs/HARDWARE.md).

## Install

On a fresh Debian installation with `curl`, use this one command. Git is not
needed; `bootstrap.sh` performs the complete download and installation.

```bash
curl -fsSL https://raw.githubusercontent.com/p1337/OpenR4d10/main/bootstrap.sh | sudo bash
```

If the image has `wget` instead of `curl`, the equivalent command is:

```bash
wget -qO- https://raw.githubusercontent.com/p1337/OpenR4d10/main/bootstrap.sh | sudo bash
```

The bootstrap downloads a complete GitHub source archive without root access,
validates the archive before extraction, prints its SHA-256, and only then
starts the local installer, which requests root access when required.
The installer verifies the operating system, CPU architecture and Raspberry Pi
model, installs files below `/opt/openr4d10`, preserves existing configuration,
compiles the Whisplay boot player locally for the Pi, installs the Debian
Pillow/libgpiod/spidev/mpv/ffmpeg packages, enables SPI, installs and enables
both systemd services, and runs a final diagnostic. Neither script collects or
writes credentials.

Reboot after the first installation. The native Whisplay animation starts on
the next boot, keeps the moving skull visible 1.5 seconds longer and then keeps
its reviewed final-logo loop visible until the physical
application UI is ready and takes over the panel. The web dashboard remains
available independently.

After installation, open the Pi address directly in a browser, for example:

```text
http://192.168.1.64/
```

The dashboard shows live service, system and adapter status. Until verified
Whisplay and PiSugar adapters are configured, it labels those components as
open instead of displaying invented measurements.

The service section accepts an explicit `http` or `https` audio URL for local
playback and recording. It rejects credentials embedded in URLs and does not
persist URL query strings in public status. Actual sound requires an ALSA
device; the Whisplay codec driver is still hardware-revision-dependent.

If the repository files are already present, the local command remains:

```bash
sudo ./install.sh
```

For an inspect-first installation, download `bootstrap.sh`, review it, and run
it with `sudo bash bootstrap.sh`. Regardless of how the bootstrap is started,
it downloads and validates the complete project archive before installation.

PiSugar telemetry and hardware audio are still reported as
configuration-required. The Whisplay
display backend is installed and selected automatically. Its early-boot log is
available with `journalctl -u openr4d10-boot -b --no-pager`.

## Configure hardware

The installer creates these files only if they do not already exist:

- `/etc/openr4d10/openr4d10.toml`
- `/etc/openr4d10/hardware.toml`

It also refreshes `.dist` copies on every install so local changes can be
compared with the current defaults. An existing display placeholder is migrated
to `backend = "whisplay"`; all other local settings are preserved. Edit
`hardware.toml`, then run:

```bash
sudo openr4d10 doctor
sudo systemctl restart openr4d10
sudo journalctl -u openr4d10 -f
```

The generic `command` adapter sends one JSON document to an executable through
standard input. This keeps vendor code outside the privileged installer and
allows the exact, documented Whisplay or PiSugar helper to be connected later.
No shell is involved and the command must be an absolute path.

## Useful commands

```bash
sudo openr4d10 doctor
openr4d10 render-once
openr4d10 preview-ui --output /tmp/openr4d10-ui.png
systemctl status openr4d10
journalctl -u openr4d10 --since today
journalctl -u openr4d10-boot -b --no-pager
curl http://127.0.0.1/healthz
```

For development:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m openr4d10 --config config/openr4d10.toml \
  --hardware-config config/hardware.toml doctor
```

More detail is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md),
[`docs/HARDWARE.md`](docs/HARDWARE.md) and
[`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).
