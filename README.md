# OpenR4d10

OpenR4d10 is a small, dependency-free Python service for a Raspberry Pi Zero 2 W
running Debian 13 (Trixie). It provides a safe foundation for a receiver UI,
boot sequence, display output, status data and power telemetry without guessing
the Whisplay pinout, display controller or PiSugar protocol.

The repository is intentionally usable before the final hardware details are
known: the service starts in a visible `unconfigured` mode, while `doctor` and
the installer report exactly which adapters still need configuration.

## Current status

- Raspberry Pi Zero 2 W / Debian 13 / `aarch64` platform checks
- idempotent one-command installer from a reviewed checkout
- hardened `systemd` autostart service
- semantic UI frame model and configurable text boot sequence
- safe `unconfigured`, JSON-file and external-command display adapters
- built-in Linux system status and optional external-command status/power adapters
- persistent configuration in `/etc/openr4d10`
- runtime data in `/run/openr4d10` and state in `/var/lib/openr4d10`
- standard-library-only test suite and GitHub Actions CI

Not included on purpose:

- Whisplay GPIO/SPI pins, dimensions, controller name or Python driver
- PiSugar API details
- binary boot-animation assets
- credentials, WLAN settings, tokens or secrets

Those values must come from the exact hardware documentation. See
[`docs/HARDWARE.md`](docs/HARDWARE.md).

## Install

Review the checkout, then run exactly one command from its root:

```bash
sudo ./install.sh
```

The installer verifies the operating system, CPU architecture and Raspberry Pi
model, installs files below `/opt/openr4d10`, preserves existing configuration,
installs and enables `openr4d10.service`, and runs a final diagnostic. It does
not collect or write credentials.

For a fresh Pi, one shell line can clone and run the reviewed installer:

```bash
git clone --depth 1 https://github.com/p1337/OpenR4d10.git && cd OpenR4d10 && sudo ./install.sh
```

The project deliberately does not recommend `curl | sudo bash`: cloning first
makes the code reviewable and avoids executing a partially downloaded script.

If the final hardware adapter is not configured yet, installation still
succeeds and the service runs headless. The final output clearly says
`HARDWARE CONFIGURATION REQUIRED`. This is expected and safer than inventing
pins or silently attempting GPIO access.

## Configure hardware

The installer creates these files only if they do not already exist:

- `/etc/openr4d10/openr4d10.toml`
- `/etc/openr4d10/hardware.toml`

It also refreshes `.dist` copies on every install so local changes can be
compared with the current defaults. Edit `hardware.toml`, then run:

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
systemctl status openr4d10
journalctl -u openr4d10 --since today
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
