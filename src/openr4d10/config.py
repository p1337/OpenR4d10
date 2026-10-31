"""Strict TOML configuration loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import tomllib


class ConfigError(ValueError):
    pass


def _is_absolute_target_path(path: Path) -> bool:
    """Accept native host paths plus Linux target paths during Windows tests."""
    return path.is_absolute() or str(path).startswith(("/", "\\"))


@dataclass(frozen=True, slots=True)
class WebConfig:
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 80
    static_directory: Path = Path("/opt/openr4d10/current/web")


@dataclass(frozen=True, slots=True)
class AppConfig:
    log_level: str
    refresh_interval_seconds: float
    title: str
    boot_manifest: Path
    boot_enabled: bool
    runtime_directory: Path
    state_directory: Path
    service_adapter_directory: Path = Path("/etc/openr4d10/services.d")
    web: WebConfig = field(default_factory=WebConfig)


@dataclass(frozen=True, slots=True)
class AdapterConfig:
    backend: str
    command: tuple[str, ...] = ()
    timeout_seconds: float = 2.0
    output_path: Path | None = None


@dataclass(frozen=True, slots=True)
class HardwareConfig:
    display: AdapterConfig
    power: AdapterConfig
    receiver: AdapterConfig


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read configuration file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError(f"configuration root must be a table: {path}")
    return value


def _table(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"[{name}] must be a TOML table")
    return value


def _positive_number(table: dict[str, Any], key: str, default: float) -> float:
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigError(f"{key} must be a positive number")
    return float(value)


def load_app_config(path: Path) -> AppConfig:
    data = _read_toml(path)
    application = _table(data, "application")
    ui = _table(data, "ui")
    paths = _table(data, "paths")
    web = _table(data, "web")

    log_level = str(application.get("log_level", "INFO")).upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigError("application.log_level is invalid")

    title = ui.get("title", "OpenR4d10")
    manifest = ui.get("boot_manifest", "")
    if not isinstance(title, str) or not title.strip():
        raise ConfigError("ui.title must be a non-empty string")
    if not isinstance(manifest, str) or not manifest:
        raise ConfigError("ui.boot_manifest must be a path string")
    boot_enabled = ui.get("boot_enabled", True)
    if not isinstance(boot_enabled, bool):
        raise ConfigError("ui.boot_enabled must be true or false")

    runtime = paths.get("runtime_directory", "/run/openr4d10")
    state = paths.get("state_directory", "/var/lib/openr4d10")
    service_adapters = paths.get(
        "service_adapter_directory", "/etc/openr4d10/services.d"
    )
    if not all(isinstance(value, str) for value in (runtime, state, service_adapters)):
        raise ConfigError("configured directories must be path strings")
    manifest_path = Path(manifest)
    runtime_path = Path(runtime)
    state_path = Path(state)
    service_adapter_path = Path(service_adapters)
    if not all(
        _is_absolute_target_path(path)
        for path in (manifest_path, runtime_path, state_path, service_adapter_path)
    ):
        raise ConfigError("boot manifest, runtime, state and adapter paths must be absolute")

    web_enabled = web.get("enabled", True)
    web_host = web.get("host", "0.0.0.0")
    web_port = web.get("port", 80)
    web_static = web.get("static_directory", "/opt/openr4d10/current/web")
    if not isinstance(web_enabled, bool):
        raise ConfigError("web.enabled must be true or false")
    if not isinstance(web_host, str) or not web_host.strip():
        raise ConfigError("web.host must be a non-empty string")
    if isinstance(web_port, bool) or not isinstance(web_port, int) or not 1 <= web_port <= 65535:
        raise ConfigError("web.port must be an integer between 1 and 65535")
    if not isinstance(web_static, str) or (web_enabled and not Path(web_static).is_absolute()):
        raise ConfigError("web.static_directory must be an absolute path")

    return AppConfig(
        log_level=log_level,
        refresh_interval_seconds=_positive_number(
            application, "refresh_interval_seconds", 2.0
        ),
        title=title.strip(),
        boot_manifest=manifest_path,
        boot_enabled=boot_enabled,
        runtime_directory=runtime_path,
        state_directory=state_path,
        service_adapter_directory=service_adapter_path,
        web=WebConfig(
            enabled=web_enabled,
            host=web_host.strip(),
            port=web_port,
            static_directory=Path(web_static),
        ),
    )


def _adapter(
    data: dict[str, Any], section: str, allowed_backends: set[str]
) -> AdapterConfig:
    table = _table(data, section)
    backend = table.get("backend", "unconfigured")
    if not isinstance(backend, str) or backend not in allowed_backends:
        choices = ", ".join(sorted(allowed_backends))
        raise ConfigError(f"{section}.backend must be one of: {choices}")

    raw_command = table.get("command", [])
    if not isinstance(raw_command, list) or not all(
        isinstance(item, str) and item for item in raw_command
    ):
        raise ConfigError(f"{section}.command must be an array of non-empty strings")
    command = tuple(raw_command)
    if backend == "command":
        if not command:
            raise ConfigError(f"{section}.command is required for command backend")
        if not Path(command[0]).is_absolute():
            raise ConfigError(f"{section}.command executable must be an absolute path")

    raw_output = table.get("output_path")
    output_path = None
    if raw_output is not None:
        if not isinstance(raw_output, str) or not raw_output:
            raise ConfigError(f"{section}.output_path must be a path string")
        output_path = Path(raw_output)
    if backend == "file":
        if output_path is None:
            raise ConfigError(f"{section}.output_path is required for file backend")
        if not output_path.is_absolute():
            raise ConfigError(f"{section}.output_path must be absolute")

    return AdapterConfig(
        backend=backend,
        command=command,
        timeout_seconds=_positive_number(table, "timeout_seconds", 2.0),
        output_path=output_path,
    )


def load_hardware_config(path: Path) -> HardwareConfig:
    data = _read_toml(path)
    return HardwareConfig(
        display=_adapter(
            data, "display", {"unconfigured", "file", "command", "whisplay"}
        ),
        power=_adapter(data, "power", {"unconfigured", "command", "pisugar3"}),
        receiver=_adapter(data, "receiver", {"system", "command"}),
    )
