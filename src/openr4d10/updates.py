"""Bounded unprivileged side of the root-owned system update boundary."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import Any


UPDATE_STATES = {"idle", "queued", "running", "failed", "rebooting", "completed"}


class UpdateController:
    def __init__(
        self,
        runtime_directory: Path,
        state_directory: Path,
        *,
        boot_id_path: Path = Path("/proc/sys/kernel/random/boot_id"),
    ) -> None:
        self.request_path = runtime_directory / "update.request"
        self.status_path = state_directory / "update-status.json"
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
        if not isinstance(value, dict) or value.get("state") not in UPDATE_STATES:
            return None
        result: dict[str, Any] = {"state": value["state"]}
        for key, limit in (("message", 300), ("updated_at", 64), ("version", 64)):
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
                "message": "Update wurde angefordert und wird gleich gestartet.",
            }
        result = self._read_status() or {
            "state": "idle",
            "message": "Kein Update läuft.",
        }
        if result["state"] == "rebooting":
            previous_boot = result.get("boot_id")
            current_boot = self._boot_id()
            if previous_boot and current_boot and previous_boot != current_boot:
                result["state"] = "completed"
                result["message"] = "Update und Neustart wurden abgeschlossen."
        result.pop("boot_id", None)
        return result

    def request(self, payload: dict[str, object]) -> dict[str, object]:
        if set(payload) != {"action", "confirmed"} or payload.get("confirmed") is not True:
            raise ValueError("system update requires explicit confirmation")
        current = self.status()
        if current["state"] in {"queued", "running", "rebooting"}:
            raise RuntimeError("a system update is already in progress")
        self.request_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self.request_path, flags, 0o640)
        except FileExistsError as exc:
            raise RuntimeError("a system update is already queued") from exc
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(b"update\n")
            handle.flush()
            os.fsync(handle.fileno())
        return {"update": self.status()}
