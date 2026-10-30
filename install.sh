#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALL_ROOT=/opt/openr4d10
readonly CONFIG_ROOT=/etc/openr4d10
readonly SERVICE_FILE=/etc/systemd/system/openr4d10.service
readonly WRAPPER_FILE=/usr/local/bin/openr4d10

CHECK_ONLY=false
ALLOW_UNSUPPORTED=false

usage() {
    echo "Usage: sudo ./install.sh [--check] [--allow-unsupported]"
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
        -h|--help) usage; exit 0 ;;
        *) usage >&2; die "Unknown argument: $argument" ;;
    esac
done

SOURCE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SOURCE_ROOT

required=(
    VERSION README.md
    src/openr4d10/__main__.py
    config/openr4d10.toml config/hardware.toml
    assets/boot/text-sequence.toml
    web/index.html web/app.css web/app.js
    systemd/openr4d10.service bin/openr4d10
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

note "Installing required operating-system package"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3 ca-certificates

if ! getent group openr4d10 >/dev/null; then
    groupadd --system openr4d10
fi
if ! id -u openr4d10 >/dev/null 2>&1; then
    useradd --system --gid openr4d10 --home-dir /var/lib/openr4d10 \
        --shell /usr/sbin/nologin openr4d10
fi

version="$(tr -d '[:space:]' <"$SOURCE_ROOT/VERSION")"
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9.-]+)?$ ]] \
    || die "VERSION has an unsafe format"
release_root="$INSTALL_ROOT/releases/$version"

note "Installing OpenR4d10 $version"
install -d -m 0755 -o root -g root "$release_root"
for directory in src assets web; do
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

install -m 0755 -o root -g root "$SOURCE_ROOT/bin/openr4d10" "$WRAPPER_FILE"
install -m 0644 -o root -g root "$SOURCE_ROOT/systemd/openr4d10.service" "$SERVICE_FILE"

note "Enabling systemd autostart"
systemctl daemon-reload
systemctl enable openr4d10.service
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
    echo "HARDWARE CONFIGURATION REQUIRED: edit $CONFIG_ROOT/hardware.toml"
    echo "No Whisplay pins, display driver or PiSugar protocol was guessed."
fi
echo "Status: systemctl status openr4d10"
echo "Logs:   journalctl -u openr4d10 -f"
echo "Web UI: http://<raspberry-pi-ip>/"
