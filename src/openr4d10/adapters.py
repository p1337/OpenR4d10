"""Generic, non-vendor hardware adapter boundary."""

from __future__ import annotations

from collections.abc import Mapping
import json
import logging
import os
from pathlib import Path
import socket
import subprocess
import tempfile
from typing import Any, Protocol

from .config import AdapterConfig, HardwareConfig
from .device_ui import DeviceUiState, image_to_rgb565, render_device_ui
from .models import Frame
from .whisplay import WhisplayError, WhisplayPanel

LOG = logging.getLogger(__name__)


class AdapterError(RuntimeError):
    pass


class Display(Protocol):
    def render(self, frame: Frame) -> None: ...


class Telemetry(Protocol):
    def read(self) -> Mapping[str, Any]: ...


class UnconfiguredDisplay:
    def __init__(self) -> None:
        self._warned = False

    def render(self, frame: Frame) -> None:
        if not self._warned:
            LOG.warning(
                "Display backend is unconfigured; running headless. Last screen: %s",
                frame.screen,
            )
            self._warned = True
        LOG.debug("Semantic frame: %s", frame.as_dict())


class FileDisplay:
    """Atomically writes the latest semantic frame as UTF-8 JSON."""

    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path

    def render(self, frame: Frame) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            frame.as_dict(), ensure_ascii=False, sort_keys=True, indent=2
        ) + "\n"
        fd, temporary = tempfile.mkstemp(
            prefix=f".{self.output_path.name}.", dir=self.output_path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.output_path)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise


def _run_json_command(config: AdapterConfig, payload: object | None) -> Any:
    stdin = None if payload is None else json.dumps(payload, ensure_ascii=False)
    try:
        completed = subprocess.run(
            config.command,
            input=stdin,
            text=True,
            capture_output=True,
            timeout=config.timeout_seconds,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AdapterError(f"adapter command failed: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "no error output"
        raise AdapterError(
            f"adapter command exited with {completed.returncode}: {detail[:300]}"
        )
    if payload is not None and not completed.stdout.strip():
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AdapterError("adapter command returned invalid JSON") from exc


class CommandDisplay:
    def __init__(self, config: AdapterConfig) -> None:
        self.config = config

    def render(self, frame: Frame) -> None:
        _run_json_command(self.config, frame.as_dict())


class WhisplayDisplay:
    """Render semantic frames as the agreed native 240 x 280 device UI."""

    def __init__(self, panel: WhisplayPanel | None = None) -> None:
        self.panel = panel or WhisplayPanel()
        self.state = DeviceUiState()

    def render(self, frame: Frame) -> None:
        # Keep the approved native animation visible until the first real UI
        # frame is ready instead of replacing it with the semantic text fallback.
        if frame.screen == "boot":
            return
        self.state.update_from_frame(frame)
        try:
            self.panel.show(image_to_rgb565(render_device_ui(self.state)))
        except (OSError, RuntimeError, WhisplayError) as exc:
            raise AdapterError(f"Whisplay display failed: {exc}") from exc

    def close(self) -> None:
        self.panel.close()


class UnconfiguredTelemetry:
    def __init__(self, component: str) -> None:
        self.component = component

    def read(self) -> Mapping[str, Any]:
        return {"state": "unconfigured", "component": self.component}


class SystemTelemetry:
    @staticmethod
    def _local_ipv4() -> str | None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("192.0.2.1", 9))
                return str(probe.getsockname()[0])
        except OSError:
            return None

    def read(self) -> Mapping[str, Any]:
        uptime = None
        try:
            uptime = int(float(Path("/proc/uptime").read_text().split()[0]))
        except (OSError, ValueError, IndexError):
            pass
        try:
            load = round(os.getloadavg()[0], 2)
        except (AttributeError, OSError):
            load = None
        return {
            "state": "online",
            "hostname": socket.gethostname(),
            "wifi": "WLAN",
            "ip_address": self._local_ipv4(),
            "uptime_seconds": uptime,
            "load_1m": load,
        }


class CommandTelemetry:
    def __init__(self, config: AdapterConfig) -> None:
        self.config = config

    def read(self) -> Mapping[str, Any]:
        value = _run_json_command(self.config, None)
        if not isinstance(value, dict):
            raise AdapterError("telemetry command must return one JSON object")
        return value


def build_adapters(
    config: HardwareConfig,
) -> tuple[Display, Telemetry, Telemetry]:
    if config.display.backend == "file":
        assert config.display.output_path is not None
        display: Display = FileDisplay(config.display.output_path)
    elif config.display.backend == "command":
        display = CommandDisplay(config.display)
    elif config.display.backend == "whisplay":
        display = WhisplayDisplay()
    else:
        display = UnconfiguredDisplay()

    power: Telemetry
    if config.power.backend == "command":
        power = CommandTelemetry(config.power)
    else:
        power = UnconfiguredTelemetry("power")

    receiver: Telemetry
    if config.receiver.backend == "command":
        receiver = CommandTelemetry(config.receiver)
    else:
        receiver = SystemTelemetry()
    return display, power, receiver
