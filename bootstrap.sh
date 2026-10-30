#!/usr/bin/env bash
set -Eeuo pipefail

readonly ARCHIVE_URL="https://github.com/p1337/OpenR4d10/archive/refs/heads/main.tar.gz"

die() {
    echo "ERROR: $*" >&2
    exit 1
}

note() {
    echo "==> $*"
}

for command_name in mktemp tar sha256sum; do
    command -v "$command_name" >/dev/null 2>&1 \
        || die "Required base-system command is missing: $command_name"
done

temporary_root="$(mktemp -d -t openr4d10.XXXXXXXX)"
readonly temporary_root
trap 'rm -rf -- "$temporary_root"' EXIT

archive="$temporary_root/openr4d10.tar.gz"
archive_listing="$temporary_root/archive-list.txt"
source_root="$temporary_root/source"

note "Downloading the complete OpenR4d10 source archive (Git is not required)"
if command -v curl >/dev/null 2>&1; then
    curl --proto '=https' --tlsv1.2 --location --fail --silent --show-error \
        --output "$archive" "$ARCHIVE_URL"
elif command -v wget >/dev/null 2>&1; then
    wget --https-only --quiet --output-document="$archive" "$ARCHIVE_URL"
else
    die "Neither curl nor wget is installed. Install curl with: apt-get update && apt-get install -y ca-certificates curl"
fi

[[ -s "$archive" ]] || die "Downloaded archive is empty"
tar -tzf "$archive" >"$archive_listing" \
    || die "Downloaded archive is incomplete or invalid"
if grep -Eq '(^/|(^|/)\.\.(/|$))' "$archive_listing"; then
    die "Archive contains an unsafe path"
fi
note "Archive SHA-256: $(sha256sum "$archive" | awk '{print $1}')"

install -d -m 0700 "$source_root"
tar -xzf "$archive" -C "$source_root" --strip-components=1 \
    --no-same-owner --no-same-permissions

[[ -f "$source_root/install.sh" ]] || die "Archive does not contain install.sh"
[[ -f "$source_root/VERSION" ]] || die "Archive does not contain VERSION"
chmod 0755 "$source_root/install.sh"

note "Archive is complete; starting the local installer"
"$source_root/install.sh" "$@"
