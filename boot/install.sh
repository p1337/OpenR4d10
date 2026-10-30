#!/usr/bin/env bash
set -Eeuo pipefail
BOOT_SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EARLY=0
case "${1:-}" in
  --initramfs) EARLY=1;;
  --help|-h)
    echo 'Usage: sudo bash boot/install.sh [--initramfs]'
    echo 'Installs the Pi Zero 2 W / Whisplay boot display. Optional --initramfs modifies the early boot image.'
    exit 0;;
  '') ;;
  *) echo 'Unknown option' >&2; exit 2;;
esac
[[ $# -le 1 ]] || exit 2
[[ $EUID -eq 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
[[ -r /proc/device-tree/model ]] || { echo 'No Pi detected; nothing changed.' >&2; exit 1; }
MODEL="$(tr -d '\0' </proc/device-tree/model)"
[[ "$MODEL" == *'Raspberry Pi Zero 2'* ]] || { echo "Unverified model: $MODEL; nothing changed." >&2; exit 1; }
[[ -r "$BOOT_SOURCE/assets/boot.opb" ]] || { echo 'Build boot assets first.' >&2; exit 1; }
if systemctl is-enabled --quiet whisplay-daemon.service 2>/dev/null ||
   systemctl is-active --quiet whisplay-daemon.service 2>/dev/null; then
  echo 'whisplay-daemon already owns the LCD. Plan its handoff before enabling this direct-SPI player.' >&2
  exit 1
fi
BOOT_CONFIG=/boot/firmware/config.txt
[[ -f "$BOOT_CONFIG" ]] || BOOT_CONFIG=/boot/config.txt
[[ -f "$BOOT_CONFIG" ]] || { echo 'Raspberry Pi boot config not found.' >&2; exit 1; }
if [[ "${OPENR4D10_SKIP_APT:-0}" != 1 ]]; then
  apt-get update
  apt-get install -y --no-install-recommends gcc libc6-dev zlib1g-dev
  if [[ $EARLY -eq 1 ]]; then
    apt-get install -y --no-install-recommends initramfs-tools
  fi
fi
getent group openr4d10 >/dev/null || groupadd --system openr4d10
BUILD_DIR="$(mktemp -d -t openr4d10-boot-build.XXXXXX)"
trap 'rmdir "$BUILD_DIR" 2>/dev/null || true' EXIT
# Build locally for the installed 32/64-bit Pi OS. No wrong-architecture binary
# is copied from the development host. Static build supports the initramfs path.
gcc -static -O2 -std=c11 -Wall -Wextra -Werror \
  "$BOOT_SOURCE/native/openr4d10_boot.c" -lz -o "$BUILD_DIR/openr4d10-boot"
"$BUILD_DIR/openr4d10-boot" --verify "$BOOT_SOURCE/assets/boot.opb"
install -d -m 0755 /usr/libexec /usr/share/openr4d10/boot /etc/openr4d10
install -m 0755 "$BUILD_DIR/openr4d10-boot" /usr/libexec/openr4d10-boot
install -m 0644 "$BOOT_SOURCE/assets/boot.opb" "$BOOT_SOURCE/assets/first.opb" \
  "$BOOT_SOURCE/assets/manifest.json" /usr/share/openr4d10/boot/
install -m 0644 "$BOOT_SOURCE/native/LICENSE.PiSugar" "$BOOT_SOURCE/native/NOTICE.PiSugar" \
  /usr/share/openr4d10/boot/
install -m 0644 "$BOOT_SOURCE/openr4d10-boot.service" /etc/systemd/system/openr4d10-boot.service
if [[ ! -f /etc/openr4d10/boot.env ]]; then
  printf 'OPENR4D10_SPI_HZ=32000000\n' >/etc/openr4d10/boot.env
  chmod 0644 /etc/openr4d10/boot.env
fi
# The initializer enables only SPI and does not touch I2S, audio or button pins.
if command -v raspi-config >/dev/null 2>&1; then
  raspi-config nonint do_spi 0
else
  CURRENT_SPI="$(sed -n 's/^[[:space:]]*dtparam=spi=\(on\|off\).*/\1/p' "$BOOT_CONFIG" | tail -n 1)"
  if [[ "$CURRENT_SPI" != on ]]; then
    BACKUP="${BOOT_CONFIG}.openr4d10.$(date -u +%Y%m%dT%H%M%SZ).bak"
    cp --preserve=mode,timestamps "$BOOT_CONFIG" "$BACKUP"
    printf '\n[all]\n# OpenR4d10 Whisplay SPI\ndtparam=spi=on\n' >>"$BOOT_CONFIG"
    echo "Boot configuration backup: $BACKUP"
  fi
fi
if [[ $EARLY -eq 1 ]]; then
  install -m 0755 "$BOOT_SOURCE/initramfs/hooks/openr4d10-boot" \
    /etc/initramfs-tools/hooks/openr4d10-boot
  install -d -m 0755 /etc/initramfs-tools/scripts/init-top
  install -m 0755 "$BOOT_SOURCE/initramfs/scripts/init-top/openr4d10-boot" \
    /etc/initramfs-tools/scripts/init-top/openr4d10-boot
  BACKUP="${BOOT_CONFIG}.openr4d10.$(date -u +%Y%m%dT%H%M%SZ).bak"
  cp --preserve=mode,timestamps "$BOOT_CONFIG" "$BACKUP"
  # Put the setting under [all] so a preceding board filter cannot hide it.
  if ! grep -q '^# OpenR4d10 early display$' "$BOOT_CONFIG"; then
    printf '\n[all]\n# OpenR4d10 early display\nauto_initramfs=1\n' >>"$BOOT_CONFIG"
  fi
  if [[ -f "/boot/initrd.img-$(uname -r)" ]]; then
    update-initramfs -u -k "$(uname -r)"
  else
    update-initramfs -c -k "$(uname -r)"
  fi
  echo "Boot configuration backup: $BACKUP"
  echo 'Check that the Pi OS kernel hooks copied the matching initramfs to the firmware partition before reboot.'
fi
systemctl daemon-reload
systemctl enable openr4d10-boot.service
# Do not start mid-session or reboot without permission. New boot state applies
# at the next user-controlled reboot; no active UI is interrupted here.
rm -- "$BUILD_DIR/openr4d10-boot"
echo 'Boot display installed and enabled for the next boot. Hardware timing and colour verification still required.'
