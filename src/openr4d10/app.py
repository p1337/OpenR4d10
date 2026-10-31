"""Application lifecycle and render loop."""

from __future__ import annotations

import logging
import signal
import threading
from typing import Any

from . import __version__
from .adapters import AdapterError, Display, Telemetry
from .boot import load_boot_sequence
from .config import AppConfig, ConfigError, HardwareConfig
from .input_events import Control, InputEvent
from .models import Frame
from .services import ServiceCatalog
from .updates import UpdateController
from .wifi import WifiRepairController
from .ui import dashboard_frame
from .web import WebServer

LOG = logging.getLogger(__name__)


class OpenR4d10App:
    def __init__(
        self,
        config: AppConfig,
        display: Display,
        power: Telemetry,
        receiver: Telemetry,
        hardware: HardwareConfig | None = None,
        services: ServiceCatalog | None = None,
        updates: UpdateController | None = None,
        wifi_repair: WifiRepairController | None = None,
    ) -> None:
        self.config = config
        self.display = display
        self.power = power
        self.receiver = receiver
        self.hardware = hardware
        self.services = services
        self.updates = updates or UpdateController(
            config.runtime_directory,
            config.state_directory,
        )
        self.wifi_repair = wifi_repair or WifiRepairController(
            config.runtime_directory,
            config.state_directory,
        )
        self.stop_event = threading.Event()
        self._device_input_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._view_initialized = False
        self._latest_frame = Frame(
            screen="startup", title=config.title, body="Dienst wird gestartet"
        ).as_dict()
        self._web_server: WebServer | None = None
        brightness_reader = getattr(self.services, "display_brightness", None)
        brightness_setter = getattr(self.display, "set_brightness", None)
        if callable(brightness_reader) and callable(brightness_setter):
            brightness_setter(brightness_reader())
        appearance_reader = getattr(self.services, "display_appearance", None)
        appearance_setter = getattr(self.display, "set_appearance", None)
        if callable(appearance_reader) and callable(appearance_setter):
            appearance = appearance_reader()
            appearance_setter(appearance["accent_color"])

    def request_stop(self, signum: int | None = None, _frame: object = None) -> None:
        if signum is not None:
            LOG.info("Received signal %s; stopping", signum)
        self.stop_event.set()

    def install_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self.request_stop)
        signal.signal(signal.SIGINT, self.request_stop)

    def _publish(self, frame: Frame) -> None:
        with self._status_lock:
            self._latest_frame = frame.as_dict()
        self.display.render(frame)

    def status_snapshot(self) -> dict[str, Any]:
        with self._status_lock:
            frame = dict(self._latest_frame)
        adapters = {
            "display": self.hardware.display.backend if self.hardware else "unknown",
            "power": self.hardware.power.backend if self.hardware else "unknown",
            "receiver": self.hardware.receiver.backend if self.hardware else "unknown",
        }
        snapshot = {
            "service": "online" if not self.stop_event.is_set() else "stopping",
            "version": __version__,
            "frame": frame,
            "adapters": adapters,
            "update": self.updates.status(),
            "wifi_repair": self.wifi_repair.status(),
        }
        display_snapshot = getattr(self.display, "snapshot", None)
        if callable(display_snapshot):
            snapshot["device_ui"] = display_snapshot()
        if self.services is not None:
            snapshot["services"] = self.services.snapshot()
        return snapshot

    def control(self, request: dict[str, object]) -> dict[str, object]:
        """Route bounded local browser controls to existing application boundaries."""
        if request.get("action") == "system_update":
            return self.updates.request(request)
        if request.get("action") == "wifi_repair":
            return self.wifi_repair.request(request)
        if request.get("action") == "display_brightness":
            if self.services is None:
                raise RuntimeError("settings control is unavailable")
            brightness = request.get("brightness_percent")
            if (
                isinstance(brightness, bool)
                or not isinstance(brightness, int)
                or not 0 <= brightness <= 100
            ):
                raise ValueError("display brightness must be an integer from 0 to 100")
            display_setter = getattr(self.display, "set_brightness", None)
            persist = getattr(self.services, "set_display_brightness", None)
            current = getattr(self.services, "display_brightness", None)
            if not callable(display_setter):
                raise RuntimeError("the configured display does not support brightness")
            if not callable(persist) or not callable(current):
                raise RuntimeError("persistent settings are unavailable")
            previous = current()
            display_setter(brightness)
            try:
                persist(brightness)
            except Exception:
                display_setter(previous)
                raise
            return {
                "settings": {"display_brightness_percent": brightness},
                "device_ui": (
                    self.display.snapshot()
                    if callable(getattr(self.display, "snapshot", None))
                    else {}
                ),
            }
        if request.get("action") == "display_appearance":
            if self.services is None:
                raise RuntimeError("settings control is unavailable")
            accent_color = request.get("accent_color")
            display_setter = getattr(self.display, "set_appearance", None)
            persist = getattr(self.services, "set_display_appearance", None)
            current = getattr(self.services, "display_appearance", None)
            if not callable(display_setter):
                raise RuntimeError("the configured display does not support appearance settings")
            if not callable(persist) or not callable(current):
                raise RuntimeError("persistent settings are unavailable")
            previous = current()
            display_setter(accent_color, redraw=True)
            try:
                settings = persist(accent_color)
            except Exception:
                display_setter(previous["accent_color"], redraw=True)
                raise
            return {
                "settings": settings,
                "device_ui": (
                    self.display.snapshot()
                    if callable(getattr(self.display, "snapshot", None))
                    else {}
                ),
            }
        if request.get("action") != "device_input":
            if self.services is None:
                raise RuntimeError("service control is unavailable")
            return self.services.control(request)

        raw_control = request.get("control")
        try:
            control = Control(raw_control)
        except (TypeError, ValueError) as exc:
            raise ValueError("unknown device control") from exc

        rotary = control in {
            Control.LEFT_OUTER,
            Control.LEFT_INNER,
            Control.RIGHT_OUTER,
            Control.RIGHT_INNER,
        }
        raw_steps = request.get("steps", 0)
        raw_held = request.get("held_seconds", 0.0)
        raw_active = request.get("active")
        if isinstance(raw_steps, bool) or not isinstance(raw_steps, int):
            raise ValueError("steps must be an integer")
        if isinstance(raw_held, bool) or not isinstance(raw_held, (int, float)):
            raise ValueError("held_seconds must be a number")
        held_seconds = float(raw_held)
        if rotary:
            if raw_steps == 0 or abs(raw_steps) > 10:
                raise ValueError("rotary steps must be between -10 and 10, excluding zero")
            if held_seconds != 0:
                raise ValueError("rotary input cannot contain a hold duration")
            if raw_active is not None:
                raise ValueError("rotary input cannot contain an active state")
        elif control == Control.PTT:
            if raw_steps != 0 or held_seconds != 0:
                raise ValueError("PTT input accepts only an active state")
            if not isinstance(raw_active, bool):
                raise ValueError("PTT active state must be a boolean")
        else:
            if raw_steps != 0:
                raise ValueError("press input cannot contain rotary steps")
            if not 0 <= held_seconds <= 5:
                raise ValueError("held_seconds must be between 0 and 5")
            if raw_active is not None:
                raise ValueError("press input cannot contain an active state")

        handler = getattr(self.display, "apply_input", None)
        if not callable(handler):
            raise RuntimeError("the configured display does not accept device input")
        event = InputEvent(
            control,
            steps=raw_steps,
            held_seconds=held_seconds,
            active=raw_active if control == Control.PTT else None,
        )
        with self._device_input_lock:
            return self._apply_device_event(event, handler)

    def _apply_device_event(self, event: InputEvent, handler: Any) -> dict[str, object]:
        """Resolve one logical input and repaint it as one serialized action."""
        media_result: dict[str, object] | None = None
        display_snapshot = getattr(self.display, "snapshot", None)
        current_ui = display_snapshot() if callable(display_snapshot) else {}
        menu_open = isinstance(current_ui, dict) and current_ui.get("menu_open") is True
        selected_service = (
            str(current_ui.get("service"))
            if isinstance(current_ui, dict) and current_ui.get("service")
            else {
                "webradio": "RADIO",
                "weather": "WEATHER",
                "local_media": "PLAYER",
                "brandmeister": "DMR",
                "recorder": "REC",
            }.get(getattr(self.services, "active_service", "system"), "SYSTEM")
        )
        if self.services is not None and event.control == Control.LEFT_OUTER:
            media_result = self.services.control(
                {"action": "volume_step", "steps": event.steps}
            )
        elif (
            self.services is not None
            and event.control == Control.RIGHT_OUTER
            and not menu_open
            and selected_service == "RADIO"
        ):
            media_result = self.services.control(
                {"action": "preset_step", "steps": event.steps}
            )
        elif (
            self.services is not None
            and event.control == Control.RIGHT_OUTER
            and not menu_open
            and selected_service == "WEATHER"
        ):
            media_result = self.services.control(
                {"action": "weather_step", "steps": event.steps}
            )
        elif (
            event.control == Control.RIGHT_PRESS
            and event.held_seconds < 2.0
            and not menu_open
        ):
            if self.services is None:
                raise RuntimeError("media control is unavailable")
            if selected_service == "WEATHER":
                action = "weather_open"
            elif selected_service == "RADIO":
                action = "radio_toggle"
            else:
                action = None
            if action is not None:
                media_result = self.services.control({"action": action})
        elif (
            self.services is not None
            and event.control == Control.PTT
            and event.active is True
            and not menu_open
            and selected_service == "RADIO"
        ):
            media_result = self.services.control({"action": "radio_keep_current"})
        device_state = handler(event)
        self._view_initialized = True
        if media_result is not None:
            self.render_once()
            snapshot = getattr(self.display, "snapshot", None)
            if callable(snapshot):
                device_state = snapshot()
        response: dict[str, object] = {
            "accepted": {
                "control": event.control.value,
                "steps": event.steps,
                "held_seconds": event.held_seconds,
                "active": event.active,
            },
            "device_ui": device_state,
        }
        if media_result is not None:
            if "playback" in media_result:
                response["playback"] = media_result["playback"]
            if "selected_preset" in media_result:
                response["selected_preset"] = media_result.get("selected_preset")
            if "channel_id" in media_result:
                response["weather_channel_id"] = media_result["channel_id"]
            if "radio_buffer" in media_result:
                response["radio_buffer"] = media_result["radio_buffer"]
        return response

    def device_screen(self) -> bytes | None:
        """Return the native device pixels when the display owns that renderer."""
        provider = getattr(self.display, "screen_png", None)
        return provider() if callable(provider) else None

    def show_boot(self) -> None:
        if not self.config.boot_enabled:
            return
        try:
            sequence = load_boot_sequence(self.config.boot_manifest)
        except ConfigError as exc:
            LOG.warning("Skipping boot sequence: %s", exc)
            return
        for item in sequence:
            if self.stop_event.is_set():
                break
            self._publish(item.frame)
            self.stop_event.wait(item.duration_seconds)

    @staticmethod
    def _safe_read(source: Telemetry, name: str) -> tuple[dict[str, object], str | None]:
        try:
            return dict(source.read()), None
        except (AdapterError, OSError, ValueError) as exc:
            LOG.error("%s adapter failed: %s", name, exc)
            return {"state": "error", "component": name}, f"{name}: {exc}"

    def render_once(self) -> None:
        receiver, receiver_error = self._safe_read(self.receiver, "receiver")
        if self.services is not None:
            snapshot = getattr(self.display, "snapshot", None)
            current_ui = snapshot() if callable(snapshot) else {}
            view_service = (
                str(current_ui.get("service"))
                if self._view_initialized
                and isinstance(current_ui, dict)
                and current_ui.get("service")
                else None
            )
            receiver.update(self.services.receiver_overlay(view_service))
            self._view_initialized = True
        power, power_error = self._safe_read(self.power, "power")
        errors = [error for error in (receiver_error, power_error) if error]
        self._publish(dashboard_frame(self.config.title, receiver, power, errors))

    def close(self) -> None:
        close_display = getattr(self.display, "close", None)
        if callable(close_display):
            close_display()
        if self.services is not None:
            self.services.close()
            self.services = None

    def run(self) -> None:
        self.install_signal_handlers()
        LOG.info("OpenR4d10 service starting")
        try:
            if self.config.web.enabled:
                self._web_server = WebServer(
                    self.config.web.host,
                    self.config.web.port,
                    self.config.web.static_directory,
                    self.status_snapshot,
                    self.control,
                    self.services.content_asset if self.services is not None else None,
                    self.device_screen,
                )
                self._web_server.start()
                LOG.info(
                    "Web dashboard listening on %s:%s",
                    self.config.web.host,
                    self.config.web.port,
                )
            self.show_boot()
            while not self.stop_event.is_set():
                try:
                    self.render_once()
                except (AdapterError, OSError, ValueError) as exc:
                    LOG.error("Display adapter failed: %s", exc)
                self.stop_event.wait(self.config.refresh_interval_seconds)
        finally:
            if self._web_server is not None:
                self._web_server.stop()
            self.close()
            LOG.info("OpenR4d10 service stopped")
