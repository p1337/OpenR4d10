# Development and diagnostics

## Local checks

Python 3.11 or newer is sufficient; the application has no runtime packages
outside the standard library.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash -n bootstrap.sh
bash -n install.sh
bash -n boot/install.sh
bash install.sh --check --allow-unsupported
```

The last command is read-only. It validates the source tree and tests without
creating users, installing packages or changing systemd. `bootstrap.sh` is the
Git-free online entry point; `install.sh` remains the sole system installer.

## Test one rendered frame

Copy both example TOML files to a temporary directory, change the display
backend to `file`, and select a writable absolute output path. Then run:

```bash
PYTHONPATH=src python3 -m openr4d10 \
  --config /tmp/openr4d10.toml \
  --hardware-config /tmp/hardware.toml render-once
```

The resulting JSON is the complete boundary between core UI and a future
display helper.

## Web dashboard

The installed service listens on port 80 by default. It serves only the tracked
files in `web/` plus two read-only endpoints:

- `/api/status` — current semantic frame and adapter state as JSON
- `/healthz` — simple service health response

No credentials or configuration writes are exposed over HTTP. Port, bind
address and static directory live in `[web]` in `openr4d10.toml`.

## Installed diagnostics

```bash
sudo openr4d10 doctor
systemctl status openr4d10 --no-pager
journalctl -u openr4d10 -b --no-pager
systemctl cat openr4d10
```

`doctor` exit status `2` means the checked-in placeholder hardware configuration
is still active. It does not mean the installer failed. Exit status `1` means a
file, helper, manifest or platform check failed.

The native boot player has an additional hardware-independent integrity mode:

```bash
gcc -O2 -std=c11 -Wall -Wextra -Werror \
  boot/native/openr4d10_boot.c -lz -o /tmp/openr4d10-boot-check
/tmp/openr4d10-boot-check --verify boot/assets/boot.opb
```

## Making lasting architecture changes

Keep configuration ownership, adapter contracts, storage paths, service
permissions and recurring diagnostic traps documented in `docs/`. Update tests
with every contract change. Never add a second installation path or direct GPIO
implementation until the existing adapter boundary has been evaluated first.
