"""Installation and hardware readiness diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import platform

from .boot import load_boot_sequence
from .config import AppConfig, HardwareConfig


@dataclass(frozen=True, slots=True)
class Check:
    level: str
    message: str


def _os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return result
    for line in lines:
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        result[key] = value.strip().strip('"')
    return result


def _model(path: Path = Path("/proc/device-tree/model")) -> str:
    try:
        return path.read_text(encoding="utf-8").rstrip("\x00\n")
    except OSError:
        return ""


def _platform_checks(allow_unsupported: bool) -> list[Check]:
    fallback = "WARN" if allow_unsupported else "ERROR"
    checks: list[Check] = []
    release = _os_release()
    if release.get("ID") == "debian" and release.get("VERSION_ID") == "13":
        checks.append(Check("OK", "Operating system is Debian 13"))
    else:
        label = release.get("PRETTY_NAME", "unknown operating system")
        checks.append(Check(fallback, f"Expected Debian 13; found {label}"))

    machine = platform.machine().lower()
    if machine in {"aarch64", "arm64"}:
        checks.append(Check("OK", f"Architecture is {machine}"))
    else:
        checks.append(Check(fallback, f"Expected aarch64; found {machine or 'unknown'}"))

    model = _model()
    if "Raspberry Pi Zero 2 W" in model:
        checks.append(Check("OK", f"Board is {model}"))
    else:
        checks.append(
            Check(fallback, f"Expected Raspberry Pi Zero 2 W; found {model or 'unknown'}")
        )
    return checks


def _command_check(component: str, command: tuple[str, ...]) -> Check:
    executable = Path(command[0])
    if executable.is_file() and os.access(executable, os.X_OK):
        return Check("OK", f"{component} helper is executable: {executable}")
    return Check("ERROR", f"{component} helper is not executable: {executable}")


def run_checks(
    app: AppConfig,
    hardware: HardwareConfig,
    *,
    allow_unsupported_platform: bool = False,
) -> list[Check]:
    checks = _platform_checks(allow_unsupported_platform)

    try:
        frames = load_boot_sequence(app.boot_manifest) if app.boot_enabled else []
        detail = f" ({len(frames)} text frames)" if frames else " (disabled)"
        checks.append(Check("OK", f"Boot sequence is valid{detail}"))
    except ValueError as exc:
        checks.append(Check("ERROR", str(exc)))

    for component, adapter in (
        ("display", hardware.display),
        ("power", hardware.power),
        ("receiver", hardware.receiver),
    ):
        if adapter.backend == "unconfigured":
            checks.append(
                Check(
                    "WARN",
                    f"{component} backend is unconfigured; documented hardware details required",
                )
            )
        elif adapter.backend == "command":
            checks.append(_command_check(component, adapter.command))
        else:
            checks.append(Check("OK", f"{component} backend is {adapter.backend}"))
    return checks


def exit_code(checks: list[Check], allow_unconfigured: bool = False) -> int:
    if any(check.level == "ERROR" for check in checks):
        return 1
    if not allow_unconfigured and any(check.level == "WARN" for check in checks):
        return 2
    return 0
