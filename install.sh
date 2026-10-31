#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALL_ROOT=/opt/openr4d10
readonly CONFIG_ROOT=/etc/openr4d10
readonly STATE_ROOT=/var/lib/openr4d10
readonly SERVICE_FILE=/etc/systemd/system/openr4d10.service
readonly WRAPPER_FILE=/usr/local/bin/openr4d10
readonly UPDATE_SERVICE_FILE=/etc/systemd/system/openr4d10-update.service
readonly UPDATE_PATH_FILE=/etc/systemd/system/openr4d10-update.path
readonly UPDATE_HELPER_FILE=/usr/local/sbin/openr4d10-update
readonly UPDATE_RECOVER_SERVICE_FILE=/etc/systemd/system/openr4d10-update-recover.service
readonly UPDATE_RECOVER_HELPER_FILE=/usr/local/sbin/openr4d10-update-recover
readonly WIFI_REPAIR_SERVICE_FILE=/etc/systemd/system/openr4d10-wifi-repair.service
readonly WIFI_REPAIR_PATH_FILE=/etc/systemd/system/openr4d10-wifi-repair.path
readonly WIFI_REPAIR_HELPER_FILE=/usr/local/sbin/openr4d10-wifi-repair
readonly HOTSPOT_SERVICE_FILE=/etc/systemd/system/openr4d10-hotspot.service
readonly HOTSPOT_TIMER_FILE=/etc/systemd/system/openr4d10-hotspot.timer
readonly HOTSPOT_HELPER_FILE=/usr/local/sbin/openr4d10-hotspot

CHECK_ONLY=false
ALLOW_UNSUPPORTED=false
AUTO_REBOOT=true

usage() {
    echo "Usage: sudo ./install.sh [--check] [--allow-unsupported] [--no-reboot]"
}

die() {
    echo "ERROR: $*" >&2
    exit 1
}

note() {
    echo "==> $*"
}

for argument in "$@"; do
    case "$argument" in
        --check) CHECK_ONLY=true ;;
        --allow-unsupported) ALLOW_UNSUPPORTED=true ;;
        --no-reboot) AUTO_REBOOT=false ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; die "Unknown argument: $argument" ;;
    esac
done

SOURCE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SOURCE_ROOT

required=(
    VERSION README.md
    src/openr4d10/__main__.py src/openr4d10/radio_capture.py
    config/openr4d10.toml config/hardware.toml config/openr4d10-i2c.conf
    assets/boot/text-sequence.toml
    web/index.html web/app.css web/app.js web/i18n.json
    systemd/openr4d10.service systemd/openr4d10-update.service
    systemd/openr4d10-update.path systemd/openr4d10-update-recover.service
    systemd/openr4d10-wifi-repair.service systemd/openr4d10-wifi-repair.path
    systemd/openr4d10-hotspot.service systemd/openr4d10-hotspot.timer
    bin/openr4d10 bin/openr4d10-update bin/openr4d10-update-recover
    bin/openr4d10-wifi-repair
    bin/openr4d10-hotspot
    boot/install.sh boot/openr4d10-boot.service
    boot/openr4d10-backlight boot/openr4d10-backlight-init.service
    boot/openr4d10-backlight.path boot/openr4d10-backlight.service
    boot/native/openr4d10_boot.c boot/native/LICENSE.PiSugar
    boot/native/NOTICE.PiSugar boot/assets/boot.opb boot/assets/first.opb
    boot/assets/manifest.json
    vendor/pisugar-whisplay/LICENSE vendor/pisugar-whisplay/UPSTREAM.md
    vendor/pisugar-whisplay/audio/scripts/install.sh
    vendor/pisugar-whisplay/audio/configs/asound.conf
    vendor/pisugar-whisplay/audio/src/Makefile
    vendor/pisugar-whisplay/audio/src/whisplay-core.c
    vendor/pisugar-whisplay/audio/src/es8389.c
    vendor/pisugar-whisplay/audio/src/dts/whisplay-soundcard.dts
)
for relative in "${required[@]}"; do
    [[ -f "$SOURCE_ROOT/$relative" ]] || die "Required project file missing: $relative"
done

if [[ "$CHECK_ONLY" == true ]]; then
    note "Checking source tree without changing the system"
    PYTHONPATH="$SOURCE_ROOT/src" python3 -m unittest discover -s "$SOURCE_ROOT/tests" -v
    # The repository config points to the installed boot path. Validate its
    # checked-in source equivalent separately through the tests.
    note "Source tree and tests are valid"
    exit 0
fi

if [[ $EUID -ne 0 ]]; then
    command -v sudo >/dev/null 2>&1 || die "Run this installer as root"
    exec sudo -- "$SOURCE_ROOT/install.sh" "$@"
fi

[[ -r /etc/os-release ]] || die "Cannot identify operating system"
# shellcheck disable=SC1091
source /etc/os-release
machine="$(uname -m)"
model=""
if [[ -r /proc/device-tree/model ]]; then
    model="$(tr -d '\0' </proc/device-tree/model)"
fi

platform_ok=true
[[ "${ID:-}" == debian && "${VERSION_ID:-}" == 13 ]] || platform_ok=false
[[ "$machine" == aarch64 || "$machine" == arm64 ]] || platform_ok=false
[[ "$model" == *"Raspberry Pi Zero 2 W"* ]] || platform_ok=false
if [[ "$platform_ok" != true && "$ALLOW_UNSUPPORTED" != true ]]; then
    die "Expected Debian 13/aarch64 on Raspberry Pi Zero 2 W; found ${PRETTY_NAME:-unknown}, $machine, ${model:-unknown}. Use --allow-unsupported only for deliberate development installs."
fi

version="$(tr -d '[:space:]' <"$SOURCE_ROOT/VERSION")"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9.-]+)?$ ]] \
    || die "VERSION has an unsafe format"

state_database="$STATE_ROOT/openr4d10.sqlite3"
if [[ -f "$state_database" ]]; then
    command -v python3 >/dev/null 2>&1 \
        || die "Cannot back up the existing OpenR4d10 state because python3 is unavailable"
    backup_root="$STATE_ROOT/backups"
    install -d -m 0750 -o root -g root "$backup_root"
    backup_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    backup_file="$backup_root/pre-update-${backup_stamp}-v${version}.openr4d10.zip"
    note "Backing up persistent OpenR4d10 state before the update"
    PYTHONPATH="$SOURCE_ROOT/src" python3 - "$state_database" "$backup_file" <<'PY'
from pathlib import Path
import sys

from openr4d10.backup import create_backup

manifest = create_backup(Path(sys.argv[1]), Path(sys.argv[2]))
print(
    "Pre-update backup created: "
    f"{sys.argv[2]} (schema {manifest['schema_version']})"
)
PY
    if getent group openr4d10 >/dev/null 2>&1; then
        chown root:openr4d10 "$backup_root" "$backup_file"
    fi
    chmod 0750 "$backup_root"
    chmod 0600 "$backup_file"
fi

note "Installing required operating-system package"
export DEBIAN_FRONTEND=noninteractive
kernel_release="$(uname -r)"
apt-get update
apt-get install -y --no-install-recommends \
    python3 python3-pil python3-libgpiod python3-spidev python3-websockets python3-msgpack fonts-dejavu-core \
    mpv ffmpeg libchromaprint-tools ca-certificates gcc make kmod libc6-dev zlib1g-dev \
    "linux-headers-$kernel_release" device-tree-compiler alsa-utils \
    libasound2-plugins sox network-manager dnsmasq-base

kernel_build_root="/lib/modules/$kernel_release/build"
[[ -f "$kernel_build_root/Makefile" ]] \
    || die "Matching kernel headers are incomplete: $kernel_build_root/Makefile is missing"
[[ -x "$kernel_build_root/scripts/basic/fixdep" ]] \
    || die "Matching kernel headers are incomplete: $kernel_build_root/scripts/basic/fixdep is missing"

for system_group in openr4d10 gpio spi audio i2c; do
    if ! getent group "$system_group" >/dev/null; then
        groupadd --system "$system_group"
    fi
done
if ! id -u openr4d10 >/dev/null 2>&1; then
    useradd --system --gid openr4d10 --home-dir /var/lib/openr4d10 \
        --shell /usr/sbin/nologin openr4d10
fi
usermod --append --groups gpio,spi,audio,i2c openr4d10

# StateDirectory creates the root on first boot, but older/manual media folders
# may have been created by root. Only repair the application-owned directory
# boundaries; never recurse into or replace user media.
install -d -m 0750 -o openr4d10 -g openr4d10 "$STATE_ROOT"
install -d -m 0750 -o openr4d10 -g openr4d10 \
    "$STATE_ROOT/media" \
    "$STATE_ROOT/media/ambient" \
    "$STATE_ROOT/recordings" \
    "$STATE_ROOT/cache"

# PiSugar 3 telemetry uses only the documented read-only I2C register path.
# The character device module is loaded now and again automatically on boot.
install -m 0644 -o root -g root \
    "$SOURCE_ROOT/config/openr4d10-i2c.conf" \
    /etc/modules-load.d/openr4d10-i2c.conf
modprobe i2c-dev || die "Cannot load the i2c-dev module required for PiSugar 3 telemetry"

release_root="$INSTALL_ROOT/releases/$version"

note "Installing OpenR4d10 $version"
install -d -m 0755 -o root -g root "$release_root"
for directory in src assets web vendor; do
    install -d -m 0755 -o root -g root "$release_root/$directory"
    cp -a -- "$SOURCE_ROOT/$directory/." "$release_root/$directory/"
done

install -m 0644 -o root -g root "$SOURCE_ROOT/VERSION" "$release_root/VERSION"
find "$release_root" -type d -exec chmod 0755 {} +
find "$release_root" -type f -exec chmod 0644 {} +

install -d -m 0755 -o root -g root "$INSTALL_ROOT"
ln -sfn -- "$release_root" "$INSTALL_ROOT/current.next"
mv -Tf -- "$INSTALL_ROOT/current.next" "$INSTALL_ROOT/current"

install -d -m 0750 -o root -g openr4d10 "$CONFIG_ROOT"
install -d -m 0750 -o root -g openr4d10 "$CONFIG_ROOT/services.d"
for config_name in openr4d10.toml hardware.toml; do
    source_config="$SOURCE_ROOT/config/$config_name"
    dist_config="$CONFIG_ROOT/$config_name.dist"
    live_config="$CONFIG_ROOT/$config_name"
    install -m 0640 -o root -g openr4d10 "$source_config" "$dist_config"
    if [[ ! -e "$live_config" ]]; then
        install -m 0640 -o root -g openr4d10 "$source_config" "$live_config"
    else
        note "Preserving existing $live_config"
    fi
done

# Earlier releases kept the verified Whisplay and PiSugar 3 target adapters as
# exact unconfigured placeholders. Migrate only those placeholders and leave
# every command/file adapter and all local arguments untouched. On a fresh
# installation the current defaults already make this a no-op.
python3 - "$CONFIG_ROOT/hardware.toml" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
section = ""
changed = False
for index, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        section = stripped[1:-1]
    elif section == "display" and stripped == 'backend = "unconfigured"':
        newline = "\n" if line.endswith("\n") else ""
        lines[index] = 'backend = "whisplay"' + newline
        changed = True
    elif section == "power" and stripped == 'backend = "unconfigured"':
        newline = "\n" if line.endswith("\n") else ""
        lines[index] = 'backend = "pisugar3"' + newline
        changed = True
if changed:
    path.write_text("".join(lines), encoding="utf-8")
PY
chown root:openr4d10 "$CONFIG_ROOT/hardware.toml"
chmod 0640 "$CONFIG_ROOT/hardware.toml"

install -m 0755 -o root -g root "$SOURCE_ROOT/bin/openr4d10" "$WRAPPER_FILE"
install -m 0644 -o root -g root "$SOURCE_ROOT/systemd/openr4d10.service" "$SERVICE_FILE"
install -m 0755 -o root -g root "$SOURCE_ROOT/bin/openr4d10-update" "$UPDATE_HELPER_FILE"
install -m 0644 -o root -g root "$SOURCE_ROOT/systemd/openr4d10-update.service" "$UPDATE_SERVICE_FILE"
install -m 0644 -o root -g root "$SOURCE_ROOT/systemd/openr4d10-update.path" "$UPDATE_PATH_FILE"
install -m 0755 -o root -g root "$SOURCE_ROOT/bin/openr4d10-update-recover" "$UPDATE_RECOVER_HELPER_FILE"
install -m 0644 -o root -g root "$SOURCE_ROOT/systemd/openr4d10-update-recover.service" "$UPDATE_RECOVER_SERVICE_FILE"
install -m 0755 -o root -g root "$SOURCE_ROOT/bin/openr4d10-wifi-repair" "$WIFI_REPAIR_HELPER_FILE"
install -m 0644 -o root -g root "$SOURCE_ROOT/systemd/openr4d10-wifi-repair.service" "$WIFI_REPAIR_SERVICE_FILE"
install -m 0644 -o root -g root "$SOURCE_ROOT/systemd/openr4d10-wifi-repair.path" "$WIFI_REPAIR_PATH_FILE"
install -m 0755 -o root -g root "$SOURCE_ROOT/bin/openr4d10-hotspot" "$HOTSPOT_HELPER_FILE"
install -m 0644 -o root -g root "$SOURCE_ROOT/systemd/openr4d10-hotspot.service" "$HOTSPOT_SERVICE_FILE"
install -m 0644 -o root -g root "$SOURCE_ROOT/systemd/openr4d10-hotspot.timer" "$HOTSPOT_TIMER_FILE"

note "Installing the verified Whisplay ST7789 boot display"
OPENR4D10_SKIP_APT=1 bash "$SOURCE_ROOT/boot/install.sh"

note "Installing the official unified Whisplay sound-card driver"
# Close any old mpv instance before the vendor installer replaces the default
# ALSA configuration. The service is started again below even though the new
# kernel module and overlay deliberately wait for a controlled reboot.
systemctl stop openr4d10.service >/dev/null 2>&1 || true
driver_build_root="$(mktemp -d)"
trap 'rm -rf -- "$driver_build_root"' EXIT
cp -a -- "$SOURCE_ROOT/vendor/pisugar-whisplay/audio/." "$driver_build_root/"
WHISPLAY_PLATFORM=raspberry_pi \
    bash "$driver_build_root/scripts/install.sh"
rm -rf -- "$driver_build_root"
trap - EXIT

note "Enabling systemd autostart"
systemctl daemon-reload
systemctl enable openr4d10.service
systemctl enable --now openr4d10-update-recover.service
systemctl enable --now openr4d10-update.path openr4d10-wifi-repair.path
systemctl enable --now openr4d10-hotspot.timer
systemctl restart openr4d10.service

note "Checking local web dashboard"
web_ready=false
for _attempt in {1..10}; do
    if python3 -c 'from urllib.request import urlopen; response = urlopen("http://127.0.0.1/healthz", timeout=1); raise SystemExit(0 if response.read() == b"ok\n" else 1)' >/dev/null 2>&1; then
        web_ready=true
        break
    fi
    sleep 0.5
done
if [[ "$web_ready" != true ]]; then
    systemctl status openr4d10.service --no-pager >&2 || true
    die "Web dashboard did not become ready on port 80. Check: journalctl -u openr4d10"
fi

note "Running final diagnostics"
set +e
doctor_output="$("$WRAPPER_FILE" --config "$CONFIG_ROOT/openr4d10.toml" \
    --hardware-config "$CONFIG_ROOT/hardware.toml" doctor 2>&1)"
doctor_status=$?
set -e
echo "$doctor_output"

if [[ $doctor_status -eq 1 ]]; then
    die "Installation completed, but diagnostics found an error. Check: journalctl -u openr4d10"
fi

echo
echo "OpenR4d10 $version is installed and enabled."
if [[ $doctor_status -eq 2 ]]; then
    echo "APPLICATION HARDWARE CONFIGURATION REQUIRED: edit $CONFIG_ROOT/hardware.toml"
    echo "The native Whisplay UI is installed; PiSugar telemetry remains unconfigured."
fi
echo "Status: systemctl status openr4d10"
echo "Logs:   journalctl -u openr4d10 -f"
echo "Web UI: http://<raspberry-pi-ip>/"
echo "Web updates: enabled through the confirmed Systemupdate control"
echo "Whisplay boot animation: enabled for the next reboot"
echo "Whisplay logs: journalctl -u openr4d10-boot -b --no-pager"
echo "Whisplay audio: official unified WM8960/ES8389 driver installed"
echo "After reboot: aplay -l | grep -i whisplay"
if [[ "$AUTO_REBOOT" == true ]]; then
    echo "Installation succeeded. Rebooting automatically in 5 seconds."
    echo "The SSH connection will close; reconnect after about one minute."
    sync
    sleep 5
    systemctl reboot --no-block
else
    echo "Automatic reboot disabled by --no-reboot."
    echo "REBOOT REQUIRED: sudo reboot"
fi
