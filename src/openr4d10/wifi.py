"""Bounded unprivileged side of the root-owned WLAN repair boundary."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
from typing import Any


WIFI_REPAIR_STATES = {"idle", "queued", "running", "succeeded", "failed"}


def _valid_ssid(value: object) -> bool:
    if not isinstance(value, str) or not value or "\x00" in value:
        return False
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return False
    return len(value.encode("utf-8")) <= 32


def _valid_wpa_psk(value: object) -> bool:
    if not isinstance(value, str):
        return False
    if re.fullmatch(r"[0-9A-Fa-f]{64}", value):
        return True
    return 8 <= len(value) <= 63 and all(32 <= ord(character) <= 126 for character in value)


class WifiRepairController:
    """Create only the fixed transient request consumed by the root helper."""

    def __init__(
        self,
        runtime_directory: Path,
        state_directory: Path,
        *,
        boot_id_path: Path = Path("/proc/sys/kernel/random/boot_id"),
    ) -> None:
        self.request_path = runtime_directory / "wifi-repair.request"
        self.status_path = state_directory / "wifi-repair-status.json"
        self.boot_id_path = boot_id_path

    def _boot_id(self) -> str | None:
        try:
            value = self.boot_id_path.read_text(encoding="ascii").strip()
        except OSError:
            return None
        return value[:64] if value else None

    def _read_status(self) -> dict[str, Any] | None:
        try:
            descriptor = os.open(
                self.status_path,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            )
        except OSError:
            return None
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 4096:
                return None
            with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
                descriptor = -1
                value = json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        if not isinstance(value, dict) or value.get("state") not in WIFI_REPAIR_STATES:
            return None
        result: dict[str, Any] = {"state": value["state"]}
        for key, limit in (("message", 300), ("updated_at", 64)):
            item = value.get(key)
            if isinstance(item, str):
                result[key] = item[:limit]
        boot_id = value.get("boot_id")
        if isinstance(boot_id, str):
            result["boot_id"] = boot_id[:64]
        return result

    def status(self) -> dict[str, Any]:
        if self.request_path.is_file() and not self.request_path.is_symlink():
            return {
                "state": "queued",
                "message": "Wi-Fi repair was requested.",
            }
        result = self._read_status() or {
            "state": "idle",
            "message": "No Wi-Fi repair is running.",
        }
        if result["state"] == "running":
            previous_boot = result.get("boot_id")
            current_boot = self._boot_id()
            if previous_boot and current_boot and previous_boot != current_boot:
                result["state"] = "failed"
                result["message"] = "The previous Wi-Fi repair was interrupted by a restart; retry is available."
        result.pop("boot_id", None)
        return result

    def request(self, payload: dict[str, object]) -> dict[str, object]:
        expected = {
            "action",
            "ssid",
            "passphrase",
            "replace_existing",
            "confirmed",
        }
        if set(payload) != expected or payload.get("action") != "wifi_repair":
            raise ValueError("invalid WLAN repair request")
        if payload.get("confirmed") is not True:
            raise ValueError("WLAN repair requires explicit confirmation")
        replace_existing = payload.get("replace_existing")
        if not isinstance(replace_existing, bool):
            raise ValueError("replace_existing must be a boolean")
        ssid = payload.get("ssid")
        passphrase = payload.get("passphrase")
        if not _valid_ssid(ssid):
            raise ValueError("SSID must contain 1 to 32 valid UTF-8 bytes")
        if not _valid_wpa_psk(passphrase):
            raise ValueError("WLAN passphrase must be 8 to 63 printable characters or 64 hexadecimal digits")
        if self.status()["state"] in {"queued", "running"}:
            raise RuntimeError("a WLAN repair is already in progress")

        self.request_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self.request_path, flags, 0o600)
        except FileExistsError as exc:
            raise RuntimeError("a WLAN repair is already queued") from exc
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        request = {
            "ssid": ssid,
            "passphrase": passphrase,
            "replace_existing": replace_existing,
            "confirmed": True,
        }
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(request, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        return {"wifi_repair": self.status()}
