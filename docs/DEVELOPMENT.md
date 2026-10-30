# Development and diagnostics

## Local checks

Python 3.11 or newer is sufficient for the core. The physical renderer requires
Pillow; the target installer uses Debian's `python3-pil`, `python3-libgpiod` and
`python3-spidev` packages rather than downloading code with pip.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash -n bootstrap.sh
bash -n install.sh
bash -n boot/install.sh
bash -n vendor/pisugar-whisplay/audio/scripts/install.sh
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
display helper. To render the actual 240 x 280 layout without hardware:

```bash
PYTHONPATH=src python3 -m openr4d10 \
  --config config/openr4d10.toml \
  --hardware-config config/hardware.toml \
  preview-ui --output /tmp/openr4d10-ui.png
```

The normal `run` command also creates a migrated non-secret state database in
the configured state directory. Tests must always point this at a temporary
absolute directory. Never add tokens, passwords or keys to this database; its
setting API rejects secret-like keys by design.

Test the portable metadata backup against a temporary state directory. Restore
must be tested only while the service is stopped and requires `--replace` when
the database already exists. The archive intentionally excludes configuration
secrets, WLAN data, media and recordings.

## Web dashboard

The installed service listens on port 80 by default. It serves only the tracked
files in `web/` plus the following endpoints:

- `/api/status` — current semantic frame and adapter state as JSON
- `/healthz` — simple service health response
- `POST /api/control` — bounded same-origin JSON media controls
- `/api/camera/1` and `/api/camera/2` — locally re-encoded camera snapshots
- `/api/radio-art/<preset-id>` — bounded, locally re-encoded preset artwork

The control endpoint accepts only JSON up to 4096 bytes, rejects mismatched
browser origins and never accepts or stores credentials. It supports explicit
playback, pause, stop, volume and stream-recording actions plus bounded feed and
camera retrieval, saved station management and local media rescans. Saved
station URLs containing query strings are rejected; temporary direct playback
is not persisted. `service_set_enabled` persists module activation; `system`
cannot be disabled and external modules still require their own adapter. Port,
bind address and static directory live in `[web]` in `openr4d10.toml`.

The `device_input` action is the hardware-free input source for the native
display. It accepts only the checked-in logical control names, rotary steps
from -10 through 10 excluding zero, press hold durations from 0 through 5
seconds, and an explicit boolean `active` state for `ptt`. The application
passes the resulting `InputEvent` through its semantic action router and then
to the Whisplay adapter; the normal render loop and browser inputs share its
display lock. A short `right_press`/Enter must be verified to change both the
public playback state and the actual `mpv` pause state, not merely the display
icon. A held right press opens the quick menu without touching playback. No
GPIO number is accepted by this endpoint. Browser PTT must release on key-up,
focus loss and tab hiding. It remains an input indication, not an audio claim,
until a real authorized service adapter consumes it.

Volume and radio-channel regression tests must make the same distinction:
`left_outer` changes `MpvEngine.state.volume` by ten percentage points per
logical step through its IPC command, and
`right_outer` loads the selected curated stream rather than only incrementing a
display counter. Radio frames expose the preset ID, channel and display name,
but no remote artwork URL, stream URL or local cache path. The physical
renderer may read only `radio-<preset-id>.jpg` below the configured cache root.

`system_update` requires the exact boolean field `confirmed: true`. It creates
the fixed runtime request only; it accepts no URL, branch, version, command or
arguments. Test the application boundary with temporary runtime/state
directories and test the installed privilege boundary by asserting root
ownership/modes, the exact systemd path, the helper's fixed HTTPS source and
absence of `sudo`/shell interpolation in the web process. Update progress is
reported in `/api/status` under `update` and the browser disables its button
for `queued`, `running` and `rebooting` states.

Curated controls are `preset_play`, `preset_save` and `feed_fetch_preset`.
They accept only a checked-in preset ID and never a client-supplied internal
stream or feed URL. Update presets and their evidence together in
[`PRESETS.md`](PRESETS.md), then test the current addresses without adding
cookies, tokens or signed URLs.

External account-based modules are never loaded into the web process. Their
non-secret manifests live in `/etc/openr4d10/services.d`; see
[`SERVICE_ADAPTERS.md`](SERVICE_ADAPTERS.md) for the Unix-socket protocol and
per-service credential isolation requirements.

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

For Whisplay audio, `doctor` has three explicit states: missing driver,
installed overlay awaiting reboot, and active ALSA card `whisplaysound`. The
normal 0.10.7 installer reboots automatically after all checks succeed. Use
`--no-reboot` only for an intentional maintenance run; reboot before judging
playback, then verify:

```bash
aplay -l | grep -i whisplay
amixer -c whisplaysound cget name='speaker'
sudo openr4d10 doctor
```

The vendored source provenance and upstream archive checksum live in
`vendor/pisugar-whisplay/UPSTREAM.md`. Updates must replace that reviewed
unmodified subset and retain its own Apache-2.0 `LICENSE`; do not edit vendor
files to implement OpenR4d10 behavior.

`--check` always exits before privileged changes and never reboots. A normal
successful installation requests `systemctl reboot --no-block` only after the
service healthcheck and final diagnostics. Any earlier package, build, service
or healthcheck failure exits without rebooting.

Immediately after an in-session installation, `openr4d10-boot.service` has not
run yet. `openr4d10.service` must nevertheless create the shared
`/run/openr4d10-boot` directory through `RuntimeDirectory=` so the physical UI
can claim the display directly. Repeated `Boot display runtime is absent`
messages indicate a stale application unit; reinstall the current release and
verify the unit's two runtime-directory names before rebooting.

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
