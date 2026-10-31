"""Generic, non-vendor hardware adapter boundary."""

from __future__ import annotations

from collections.abc import Mapping
import ctypes
from io import BytesIO
import json
import logging
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import tempfile
import threading
from typing import Any, Callable, Protocol

from PIL import Image

from .ambient import AMBIENT_ARTWORK_ROOT, AMBIENT_BY_ID
from .config import AdapterConfig, HardwareConfig
from .device_ui import DISPLAY_TEXT, DeviceUiState, image_to_rgb565, render_device_ui
from .input_events import Control, InputEvent
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

    def __init__(
        self,
        panel: WhisplayPanel | None = None,
        artwork_cache_root: Path | None = None,
        ambient_artwork_root: Path | None = None,
        state_directory: Path | None = None,
    ) -> None:
        self.panel = panel or WhisplayPanel()
        self.state = DeviceUiState()
        self.artwork_cache_root = artwork_cache_root
        self.ambient_artwork_root = ambient_artwork_root or AMBIENT_ARTWORK_ROOT
        self.hotspot_status_path = (
            state_directory / "hotspot-status.json"
            if state_directory is not None
            else None
        )
        self.hotspot_secret_path = (
            state_directory / "hotspot-passphrase"
            if state_directory is not None
            else None
        )
        self.brightness_percent = 100
        self._input_handler: Callable[[InputEvent], object] | None = None
        self._lock = threading.Lock()

    def set_input_handler(
        self, handler: Callable[[InputEvent], object] | None
    ) -> None:
        """Connect the verified physical Whisplay button to logical PTT."""

        self._input_handler = handler
        setter = getattr(self.panel, "set_button_callback", None)
        if callable(setter):
            setter(self._on_button_state if handler is not None else None)

    def _on_button_state(self, active: bool) -> None:
        handler = self._input_handler
        if handler is None:
            return
        try:
            handler(InputEvent(Control.PTT, active=active))
        except Exception:
            LOG.exception("Whisplay button input failed")

    def _show_state(self) -> None:
        self._refresh_hotspot_setup()
        try:
            self.panel.show(image_to_rgb565(self._render_image()))
        except (OSError, RuntimeError, WhisplayError) as exc:
            raise AdapterError(f"Whisplay display failed: {exc}") from exc

    @staticmethod
    def _read_small_regular_text(path: Path, limit: int) -> str | None:
        try:
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        except OSError:
            return None
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
                return None
            with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
                descriptor = -1
                return handle.read(limit + 1)
        except (OSError, UnicodeDecodeError):
            return None
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def _refresh_hotspot_setup(self) -> None:
        self.state.hotspot_active = False
        self.state.hotspot_ssid = ""
        self.state.hotspot_passphrase = ""
        self.state.hotspot_url = ""
        if self.hotspot_status_path is None or self.hotspot_secret_path is None:
            return
        status_text = self._read_small_regular_text(self.hotspot_status_path, 4096)
        secret_text = self._read_small_regular_text(self.hotspot_secret_path, 128)
        if status_text is None or secret_text is None:
            return
        try:
            status = json.loads(status_text)
        except json.JSONDecodeError:
            return
        if not isinstance(status, dict) or status.get("state") != "hotspot":
            return
        ssid = status.get("ssid")
        address = status.get("address")
        passphrase = secret_text.strip()
        if (
            not isinstance(ssid, str)
            or not ssid
            or len(ssid.encode("utf-8")) > 32
            or any(ord(character) < 32 or ord(character) == 127 for character in ssid)
            or not isinstance(address, str)
            or not re.fullmatch(r"10\.42\.0\.1", address)
            or not 8 <= len(passphrase) <= 63
            or not all(32 <= ord(character) <= 126 for character in passphrase)
        ):
            return
        self.state.hotspot_active = True
        self.state.hotspot_ssid = ssid
        self.state.hotspot_passphrase = passphrase
        self.state.hotspot_url = f"http://{address}/"

    def _render_image(self) -> Image.Image:
        artwork = None
        if (
            self.artwork_cache_root is not None
            and self.state.image_file is not None
            and re.fullmatch(
                r"weather-[a-z][a-z0-9_-]{1,63}-\d{8}T\d{6}Z\.jpg",
                self.state.image_file,
            )
        ):
            path = self.artwork_cache_root / self.state.image_file
            try:
                with Image.open(path) as source:
                    artwork = source.convert("RGB").copy()
            except OSError:
                artwork = None
        elif (
            self.state.service == "AMBIENT"
            and self.state.preset_id in AMBIENT_BY_ID
        ):
            path = self.ambient_artwork_root / f"{self.state.preset_id}.jpg"
            try:
                with Image.open(path) as source:
                    artwork = source.convert("RGB").copy()
            except OSError:
                artwork = None
        elif (
            self.artwork_cache_root is not None
            and self.state.preset_id is not None
            and re.fullmatch(r"[a-z][a-z0-9_]{1,63}", self.state.preset_id)
        ):
            path = self.artwork_cache_root / f"radio-{self.state.preset_id}.jpg"
            try:
                with Image.open(path) as source:
                    artwork = source.convert("RGB").copy()
            except OSError:
                artwork = None
        return render_device_ui(self.state, artwork)

    def render(self, frame: Frame) -> None:
        # Keep the approved native animation visible until the first real UI
        # frame is ready instead of replacing it with the semantic text fallback.
        if frame.screen == "boot":
            return
        with self._lock:
            self.state.update_from_frame(frame)
            self._show_state()

    def apply_input(self, event: InputEvent) -> dict[str, object]:
        """Apply the same logical event used by the future GPIO adapter."""
        with self._lock:
            self.state.apply(event)
            self._show_state()
            return self._public_state()

    def set_brightness(self, brightness_percent: int) -> None:
        with self._lock:
            try:
                self.panel.set_brightness(brightness_percent)
            except (OSError, RuntimeError, ValueError, WhisplayError) as exc:
                raise AdapterError(f"Whisplay brightness failed: {exc}") from exc
            self.brightness_percent = brightness_percent

    def set_appearance(
        self,
        accent_color: str,
        *,
        redraw: bool = False,
    ) -> None:
        if not isinstance(accent_color, str) or re.fullmatch(
            r"#[0-9A-Fa-f]{6}", accent_color
        ) is None:
            raise ValueError("accent color must use #RRGGBB")
        with self._lock:
            self.state.accent = tuple(
                int(accent_color[index : index + 2], 16) for index in (1, 3, 5)
            )
            if redraw:
                self._show_state()

    def set_language(self, language: str, *, redraw: bool = False) -> None:
        normalized = language.casefold().split("-", 1)[0] if isinstance(language, str) else ""
        if normalized not in DISPLAY_TEXT:
            raise ValueError("display language must be one of en, de, pl, fr or es")
        with self._lock:
            self.state.language = normalized
            if redraw:
                self._show_state()

    def _public_state(self) -> dict[str, object]:
        state = self.state.public_state()
        state["brightness_percent"] = self.brightness_percent
        return state

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return self._public_state()

    def screen_png(self) -> bytes:
        """Return the exact native renderer output used for the physical panel."""
        with self._lock:
            self._refresh_hotspot_setup()
            output = BytesIO()
            self._render_image().save(output, format="PNG", optimize=False)
            return output.getvalue()

    def close(self) -> None:
        with self._lock:
            self._input_handler = None
            setter = getattr(self.panel, "set_button_callback", None)
            if callable(setter):
                setter(None)
            self.panel.close()


class UnconfiguredTelemetry:
    def __init__(self, component: str) -> None:
        self.component = component

    def read(self) -> Mapping[str, Any]:
        return {"state": "unconfigured", "component": self.component}


class _I2cSmbusData(ctypes.Union):
    _fields_ = (
        ("byte", ctypes.c_uint8),
        ("word", ctypes.c_uint16),
        ("block", ctypes.c_uint8 * 34),
    )


class _I2cSmbusRequest(ctypes.Structure):
    _fields_ = (
        ("read_write", ctypes.c_uint8),
        ("command", ctypes.c_uint8),
        ("size", ctypes.c_uint32),
        ("data", ctypes.POINTER(_I2cSmbusData)),
    )


class PiSugar3Telemetry:
    """Read the documented PiSugar 3 battery percentage over I2C.

    The adapter deliberately reads only the identity/mode registers and the
    calculated battery percentage. It never changes charging, RTC, shutdown or
    any other controller state.
    """

    I2C_SLAVE = 0x0703
    I2C_SMBUS = 0x0720
    I2C_SMBUS_READ = 1
    I2C_SMBUS_BYTE_DATA = 2
    ADDRESS = 0x57
    VERSION_REGISTER = 0x00
    MODE_REGISTER = 0x01
    CAPACITY_REGISTER = 0x2A
    VERSION_PISUGAR3 = 0x03
    MODE_APPLICATION = 0x0F

    def __init__(self, device: Path = Path("/dev/i2c-1")) -> None:
        self.device = device
        self._lock = threading.Lock()

    @classmethod
    def _register(cls, fd: int, register: int) -> int:
        """Read one byte with the combined transaction used by the vendor driver."""
        data = _I2cSmbusData()
        request = _I2cSmbusRequest(
            cls.I2C_SMBUS_READ,
            register,
            cls.I2C_SMBUS_BYTE_DATA,
            ctypes.pointer(data),
        )
        libc = ctypes.CDLL(None, use_errno=True)
        ioctl = libc.ioctl
        ioctl.argtypes = (ctypes.c_int, ctypes.c_ulong, ctypes.c_void_p)
        ioctl.restype = ctypes.c_int
        if ioctl(fd, cls.I2C_SMBUS, ctypes.byref(request)) < 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        return int(data.byte)

    def read(self) -> Mapping[str, Any]:
        try:
            import fcntl
        except ImportError as exc:  # pragma: no cover - Linux target boundary
            raise AdapterError("PiSugar 3 I2C access is available only on Linux") from exc

        flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        with self._lock:
            try:
                fd = os.open(self.device, flags)
            except OSError as exc:
                raise AdapterError(f"PiSugar 3 I2C device is unavailable: {self.device}") from exc
            try:
                fcntl.ioctl(fd, self.I2C_SLAVE, self.ADDRESS)
                version = self._register(fd, self.VERSION_REGISTER)
                mode = self._register(fd, self.MODE_REGISTER)
                if version != self.VERSION_PISUGAR3 or mode != self.MODE_APPLICATION:
                    raise AdapterError(
                        "I2C address 0x57 did not identify a PiSugar 3 in application mode"
                    )
                capacity = self._register(fd, self.CAPACITY_REGISTER)
            except OSError as exc:
                raise AdapterError("PiSugar 3 I2C read failed") from exc
            finally:
                os.close(fd)

        if not 0 <= capacity <= 100:
            raise AdapterError("PiSugar 3 returned an invalid battery percentage")
        return {
            "state": "ready",
            "model": "PiSugar 3",
            "battery_percent": capacity,
        }


class SystemTelemetry:
    NMCLI = "/usr/bin/nmcli"

    @staticmethod
    def _local_ipv4() -> str | None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("192.0.2.1", 9))
                return str(probe.getsockname()[0])
        except OSError:
            return None

    @classmethod
    def _run_nmcli(cls, *arguments: str) -> str | None:
        try:
            completed = subprocess.run(
                [cls.NMCLI, *arguments],
                text=True,
                capture_output=True,
                timeout=1.0,
                check=False,
                shell=False,
                env={"LC_ALL": "C", "PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0 or len(completed.stdout) > 1024:
            return None
        return completed.stdout.strip()

    @classmethod
    def _active_wifi(cls) -> tuple[str, str]:
        connection_uuid = cls._run_nmcli(
            "--get-values", "GENERAL.CON-UUID", "device", "show", "wlan0"
        )
        if not connection_uuid or not re.fullmatch(r"[0-9A-Fa-f-]{36}", connection_uuid):
            return "OFFLINE", "disconnected"
        profile = cls._run_nmcli(
            "--get-values",
            "802-11-wireless.ssid,802-11-wireless.mode",
            "connection",
            "show",
            "uuid",
            connection_uuid,
        )
        if not profile:
            return "OFFLINE", "disconnected"
        values = profile.splitlines()
        if len(values) != 2:
            return "OFFLINE", "disconnected"
        ssid, mode = values
        if (
            not ssid
            or len(ssid.encode("utf-8")) > 32
            or any(ord(character) < 32 or ord(character) == 127 for character in ssid)
            or mode not in {"infrastructure", "ap"}
        ):
            return "OFFLINE", "disconnected"
        return ssid, "hotspot" if mode == "ap" else "client"

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
        wifi, wifi_mode = self._active_wifi()
        return {
            "state": "online",
            "hostname": socket.gethostname(),
            "wifi": wifi,
            "wifi_mode": wifi_mode,
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
    state_directory: Path | None = None,
) -> tuple[Display, Telemetry, Telemetry]:
    if config.display.backend == "file":
        assert config.display.output_path is not None
        display: Display = FileDisplay(config.display.output_path)
    elif config.display.backend == "command":
        display = CommandDisplay(config.display)
    elif config.display.backend == "whisplay":
        cache_root = (
            state_directory / "cache" if state_directory is not None else None
        )
        display = WhisplayDisplay(
            artwork_cache_root=cache_root,
            state_directory=state_directory,
        )
    else:
        display = UnconfiguredDisplay()

    power: Telemetry
    if config.power.backend == "command":
        power = CommandTelemetry(config.power)
    elif config.power.backend == "pisugar3":
        power = PiSugar3Telemetry()
    else:
        power = UnconfiguredTelemetry("power")

    receiver: Telemetry
    if config.receiver.backend == "command":
        receiver = CommandTelemetry(config.receiver)
    else:
        receiver = SystemTelemetry()
    return display, power, receiver
