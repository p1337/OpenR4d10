"""Application lifecycle and render loop."""

from __future__ import annotations

import logging
import signal
import threading
import time
from typing import Any

from . import __version__
from .adapters import AdapterError, Display, Telemetry
from .boot import load_boot_sequence
from .config import AppConfig, ConfigError, HardwareConfig
from .cpu_affinity import (
    pin_current_thread_to_background_cores,
    pin_current_thread_to_ui_core,
)
from .input_events import Control, InputEvent
from .models import Frame
from .services import ServiceCatalog
from .updates import UpdateController
from .wifi import WifiRepairController
from .ui import dashboard_frame
from .web import WebServer

LOG = logging.getLogger(__name__)

VOICE_DOUBLE_CLICK_SECONDS = 0.45
VOICE_TAP_MAX_SECONDS = 0.35
RECORDER_FRAME_INTERVAL_SECONDS = 0.1
RECORDER_INTERACTION_QUIET_SECONDS = 0.2
DMR_PTT_HOLD_SECONDS = 2.0


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
        self._last_device_input_at = 0.0
        self._status_lock = threading.Lock()
        self._view_initialized = False
        self._pending_initial_view_overlay: dict[str, object] | None = None
        self._ptt_pressed_at: float | None = None
        self._dmr_hold_timer: threading.Timer | None = None
        self._dmr_hold_generation = 0
        self._dmr_hold_triggered = False
        self._voice_last_release_at: float | None = None
        self._voice_pressed_at: float | None = None
        self._voice_ignore_release = False
        self._voice_ignore_until = 0.0
        self._radio_last_release_at: float | None = None
        self._radio_ignore_release = False
        self._radio_ignore_until = 0.0
        self._latest_frame = Frame(
            screen="startup", title=config.title, body="Dienst wird gestartet"
        ).as_dict()
        self._web_server: WebServer | None = None
        self._last_receiver_telemetry: dict[str, object] = {}
        self._last_power_telemetry: dict[str, object] = {}
        brightness_reader = getattr(self.services, "display_brightness", None)
        brightness_setter = getattr(self.display, "set_brightness", None)
        if callable(brightness_reader) and callable(brightness_setter):
            brightness_setter(brightness_reader())
        appearance_reader = getattr(self.services, "display_appearance", None)
        appearance_setter = getattr(self.display, "set_appearance", None)
        if callable(appearance_reader) and callable(appearance_setter):
            appearance = appearance_reader()
            appearance_setter(appearance["accent_color"])
        language_reader = getattr(self.services, "display_language", None)
        language_setter = getattr(self.display, "set_language", None)
        if callable(language_reader) and callable(language_setter):
            language_setter(language_reader())
        input_setter = getattr(self.display, "set_input_handler", None)
        if callable(input_setter):
            input_setter(self._apply_hardware_input)

    def _apply_hardware_input(self, event: InputEvent) -> dict[str, object]:
        """Route physical controls through the same serialized application path."""

        if self.stop_event.is_set():
            return {}
        handler = getattr(self.display, "apply_input", None)
        if not callable(handler):
            raise RuntimeError("the configured display does not accept device input")
        self._last_device_input_at = time.perf_counter()
        with self._device_input_lock:
            return self._apply_device_event(event, handler)

    def request_stop(self, signum: int | None = None, _frame: object = None) -> None:
        if signum is not None:
            LOG.info("Received signal %s; stopping", signum)
        self.stop_event.set()
        self._cancel_dmr_hold_timer()

    def _recorder_interaction_active(self) -> bool:
        return (
            time.perf_counter() - self._last_device_input_at
            < RECORDER_INTERACTION_QUIET_SECONDS
        )

    def _cancel_dmr_hold_timer(self) -> None:
        """Invalidate and cancel the one pending DMR hold action, if any."""

        self._dmr_hold_generation += 1
        timer = self._dmr_hold_timer
        self._dmr_hold_timer = None
        if timer is not None:
            timer.cancel()

    def _start_dmr_hold_timer(self) -> None:
        """Open the DMR country menu at the hold threshold, not on release."""

        self._cancel_dmr_hold_timer()
        self._dmr_hold_triggered = False
        generation = self._dmr_hold_generation
        timer = threading.Timer(
            DMR_PTT_HOLD_SECONDS,
            self._on_dmr_hold_threshold,
            args=(generation,),
        )
        timer.daemon = True
        self._dmr_hold_timer = timer
        timer.start()

    def _on_dmr_hold_threshold(self, generation: int) -> None:
        """Resolve a still-held DMR PTT press through the serialized input path."""

        try:
            with self._device_input_lock:
                if (
                    self.stop_event.is_set()
                    or generation != self._dmr_hold_generation
                    or self._ptt_pressed_at is None
                    or self._dmr_hold_triggered
                    or self.services is None
                ):
                    return
                fast_context = getattr(self.display, "input_context", None)
                snapshot = getattr(self.display, "snapshot", None)
                current_ui = (
                    fast_context()
                    if callable(fast_context)
                    else snapshot()
                    if callable(snapshot)
                    else {}
                )
                if not isinstance(current_ui, dict) or (
                    current_ui.get("service") != "DMR"
                    or current_ui.get("menu_open") is True
                ):
                    return

                self._dmr_hold_timer = None
                self._dmr_hold_triggered = True
                self._last_device_input_at = time.perf_counter()
                self.services.control({"action": "brandmeister_country_menu_open"})

                hold_event = InputEvent(
                    Control.PTT,
                    held_seconds=DMR_PTT_HOLD_SECONDS,
                    active=False,
                )
                state_only_handler = getattr(self.display, "apply_input_state", None)
                handler = getattr(self.display, "apply_input", None)
                if callable(state_only_handler):
                    state_only_handler(hold_event)
                elif callable(handler):
                    handler(hold_event)
                else:
                    raise RuntimeError("the configured display does not accept device input")
                self.render_interaction_once("DMR")
        except Exception:
            LOG.exception("DMR PTT hold action failed")

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
        if request.get("action") == "display_language":
            if self.services is None:
                raise RuntimeError("settings control is unavailable")
            language = request.get("language")
            display_setter = getattr(self.display, "set_language", None)
            persist = getattr(self.services, "set_display_language", None)
            current = getattr(self.services, "display_language", None)
            if not callable(display_setter):
                raise RuntimeError("the configured display does not support language settings")
            if not callable(persist) or not callable(current):
                raise RuntimeError("persistent settings are unavailable")
            previous = current()
            display_setter(language, redraw=True)
            try:
                saved = persist(language)
            except Exception:
                display_setter(previous, redraw=True)
                raise
            return {
                "settings": {"language": saved},
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
        self._last_device_input_at = time.perf_counter()
        with self._device_input_lock:
            return self._apply_device_event(event, handler)

    def _apply_device_event(self, event: InputEvent, handler: Any) -> dict[str, object]:
        """Resolve one logical input and repaint it as one serialized action."""
        media_result: dict[str, object] | None = None
        display_snapshot = getattr(self.display, "snapshot", None)
        fast_context = getattr(self.display, "input_context", None)
        if event.control == Control.PTT and callable(fast_context):
            current_ui = fast_context()
        else:
            current_ui = display_snapshot() if callable(display_snapshot) else {}
        menu_open = isinstance(current_ui, dict) and current_ui.get("menu_open") is True
        menu_kind = (
            str(current_ui.get("menu_kind"))
            if isinstance(current_ui, dict) and current_ui.get("menu_kind")
            else None
        )
        selected_service = (
            str(current_ui.get("service"))
            if isinstance(current_ui, dict) and current_ui.get("service")
            else {
                "webradio": "RADIO",
                "weather": "WEATHER",
                "ambient": "AMBIENT",
                "local_media": "PLAYER",
                "podcasts": "PLAYER",
                "brandmeister": "DMR",
                "recorder": "REC",
            }.get(getattr(self.services, "active_service", "system"), "SYSTEM")
        )
        dmr_hold_consumed = False
        if event.control == Control.PTT and selected_service == "DMR":
            if event.active is True and not menu_open:
                if self._ptt_pressed_at is None:
                    self._ptt_pressed_at = time.monotonic()
                    self._start_dmr_hold_timer()
            elif event.active is False:
                started = self._ptt_pressed_at
                self._ptt_pressed_at = None
                dmr_hold_consumed = self._dmr_hold_triggered
                self._dmr_hold_triggered = False
                self._cancel_dmr_hold_timer()
                held_seconds = (
                    max(0.0, time.monotonic() - started)
                    if started is not None
                    else 0.0
                )
                event = InputEvent(
                    Control.PTT,
                    held_seconds=held_seconds,
                    active=False,
                )
        if (
            self.services is not None
            and event.control == Control.LEFT_INNER
            and not menu_open
            and selected_service == "REC"
        ):
            media_result = self.services.control(
                {"action": "voice_recorder_boundary", "end": event.steps > 0}
            )
        elif (
            self.services is not None
            and event.control == Control.RIGHT_OUTER
            and not menu_open
            and selected_service == "REC"
        ):
            media_result = self.services.control(
                {"action": "voice_recorder_seek", "delta_ms": event.steps * 1000}
            )
        elif (
            self.services is not None
            and event.control == Control.LEFT_OUTER
            and not menu_open
            and selected_service == "REC"
        ):
            media_result = self.services.control(
                {"action": "voice_recorder_seek", "delta_ms": event.steps * 100}
            )
        elif self.services is not None and event.control == Control.LEFT_OUTER:
            media_result = self.services.control(
                {"action": "volume_step", "steps": event.steps}
            )
        elif (
            self.services is not None
            and event.control == Control.LEFT_INNER
            and menu_open
            and menu_kind == "ambient_layers"
        ):
            media_result = self.services.control(
                {"action": "ambient_layer_volume_step", "steps": event.steps}
            )
        elif (
            self.services is not None
            and event.control == Control.RIGHT_OUTER
            and menu_open
            and menu_kind == "ambient_layers"
        ):
            media_result = self.services.control(
                {"action": "ambient_layer_step", "steps": event.steps}
            )
        elif (
            self.services is not None
            and event.control == Control.RIGHT_PRESS
            and event.held_seconds < 2.0
            and menu_open
            and menu_kind == "ambient_layers"
        ):
            media_result = self.services.control({"action": "ambient_layer_toggle"})
        elif (
            self.services is not None
            and event.control == Control.RIGHT_OUTER
            and menu_open
            and menu_kind == "dmr_countries"
        ):
            media_result = self.services.control(
                {"action": "brandmeister_country_step", "steps": event.steps}
            )
        elif (
            self.services is not None
            and event.control == Control.RIGHT_PRESS
            and event.held_seconds < 2.0
            and menu_open
            and menu_kind == "dmr_countries"
        ):
            media_result = self.services.control({"action": "brandmeister_country_select"})
        elif (
            self.services is not None
            and event.control == Control.RIGHT_OUTER
            and menu_open
            and menu_kind == "dmr_replace"
        ):
            media_result = self.services.control(
                {"action": "brandmeister_replacement_step", "steps": event.steps}
            )
        elif (
            self.services is not None
            and event.control == Control.RIGHT_PRESS
            and event.held_seconds < 2.0
            and menu_open
            and menu_kind == "dmr_replace"
        ):
            media_result = self.services.control({"action": "brandmeister_replacement_confirm"})
        elif (
            self.services is not None
            and event.control == Control.PTT
            and event.active is True
            and menu_open
            and menu_kind == "dmr_replace"
        ):
            media_result = self.services.control({"action": "brandmeister_replacement_cancel"})
        elif (
            self.services is not None
            and event.control == Control.LEFT_INNER
            and not menu_open
            and selected_service == "DMR"
        ):
            media_result = self.services.control(
                {"action": "brandmeister_step", "steps": event.steps * 25}
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
            self.services is not None
            and event.control == Control.RIGHT_OUTER
            and not menu_open
            and selected_service == "AMBIENT"
        ):
            media_result = self.services.control(
                {"action": "ambient_step", "steps": event.steps}
            )
        elif (
            self.services is not None
            and event.control == Control.RIGHT_OUTER
            and not menu_open
            and selected_service == "DMR"
        ):
            media_result = self.services.control(
                {"action": "brandmeister_step", "steps": event.steps}
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
            elif selected_service == "AMBIENT":
                action = "ambient_toggle"
            elif selected_service == "DMR":
                action = "brandmeister_toggle"
            elif selected_service == "REC":
                action = "voice_recorder_play_toggle"
            else:
                action = None
            if action is not None:
                media_result = self.services.control({"action": action})
        elif (
            self.services is not None
            and event.control == Control.PTT
            and event.active is False
            and not menu_open
            and selected_service == "DMR"
            and not dmr_hold_consumed
        ):
            media_result = self.services.control(
                {"action": "brandmeister_toggle_selected"}
            )
        elif (
            self.services is not None
            and event.control == Control.PTT
            and not menu_open
            and selected_service == "RADIO"
        ):
            now = time.monotonic()
            radio_buffer = getattr(self.services, "radio_buffer", None)
            snapshot = getattr(radio_buffer, "snapshot", None)
            buffered = snapshot() if callable(snapshot) else {}
            if event.active is True:
                if now < self._radio_ignore_until:
                    self._radio_ignore_release = True
                elif buffered.get("continuous") is True:
                    media_result = self.services.control(
                        {"action": "radio_capture_mode", "enabled": False}
                    )
                    self._radio_ignore_release = True
                    self._radio_ignore_until = now + 0.6
                    self._radio_last_release_at = None
                elif (
                    self._radio_last_release_at is not None
                    and now - self._radio_last_release_at <= 0.45
                ):
                    media_result = self.services.control(
                        {"action": "radio_capture_mode", "enabled": True}
                    )
                    self._radio_ignore_release = True
                    self._radio_last_release_at = None
                else:
                    media_result = self.services.control(
                        {"action": "radio_keep_current"}
                    )
                    self._radio_ignore_release = False
            elif self._radio_ignore_release or now < self._radio_ignore_until:
                self._radio_ignore_release = False
            else:
                self._radio_last_release_at = now
        elif (
            self.services is not None
            and event.control == Control.PTT
            and not menu_open
            and selected_service == "REC"
        ):
            now = time.monotonic()
            recorder = getattr(self.services, "recorder", None)
            snapshot = getattr(recorder, "voice_snapshot", None)
            voice = snapshot() if callable(snapshot) else {}
            if event.active is True:
                self._voice_pressed_at = now
                if now < self._voice_ignore_until:
                    self._voice_ignore_release = True
                elif voice.get("continuous") is True:
                    media_result = self.services.control(
                        {"action": "voice_recorder_pause"}
                    )
                    self._voice_ignore_release = True
                    self._voice_ignore_until = now + 0.6
                    self._voice_last_release_at = None
                elif (
                    self._voice_last_release_at is not None
                    and now - self._voice_last_release_at <= VOICE_DOUBLE_CLICK_SECONDS
                ):
                    media_result = self.services.control(
                        {"action": "voice_recorder_continuous"}
                    )
                    self._voice_ignore_release = True
                    self._voice_last_release_at = None
                else:
                    media_result = self.services.control(
                        {"action": "voice_recorder_hold"}
                    )
                    self._voice_ignore_release = False
            elif self._voice_ignore_release or now < self._voice_ignore_until:
                self._voice_pressed_at = None
                self._voice_ignore_release = False
            else:
                pressed_at = self._voice_pressed_at
                self._voice_pressed_at = None
                media_result = self.services.control(
                    {"action": "voice_recorder_pause"}
                )
                held_seconds = (
                    max(0.0, now - pressed_at) if pressed_at is not None else 0.0
                )
                self._voice_last_release_at = (
                    now if held_seconds <= VOICE_TAP_MAX_SECONDS else None
                )
        recorder_ptt_event = (
            event.control == Control.PTT
            and not menu_open
            and selected_service == "REC"
        )
        recorder_semantic_event = (
            selected_service == "REC"
            and not menu_open
            and media_result is not None
            and event.control
            in {
                Control.LEFT_OUTER,
                Control.LEFT_INNER,
                Control.RIGHT_OUTER,
                Control.RIGHT_PRESS,
            }
        )
        state_only_handler = getattr(self.display, "apply_input_state", None)
        service_navigation_event = (
            event.control == Control.RIGHT_INNER
            and not menu_open
            and callable(state_only_handler)
        )
        if recorder_ptt_event:
            # Audio edges must never wait for the physical full-frame SPI path.
            # The priority renderer below paints only the glow asynchronously.
            device_state = current_ui if isinstance(current_ui, dict) else {}
            priority_glow = getattr(self.display, "request_recorder_glow", None)
            recording_state = (
                media_result.get("recording")
                if isinstance(media_result, dict)
                else None
            )
            if callable(priority_glow) and isinstance(recording_state, dict):
                priority_glow(
                    recording=recording_state.get("state") == "recording",
                    continuous=recording_state.get("continuous") is True,
                )
        elif recorder_semantic_event:
            # The service result is authoritative.  A presentation-only
            # apply_input() here would transfer one stale full frame before the
            # resolved recorder frame and doubles cursor latency.
            device_state = current_ui if isinstance(current_ui, dict) else {}
        elif service_navigation_event:
            # Service entry/exit may stop audio or prepare the recorder.  Apply
            # only the ordered UI mutation now and present one resolved frame
            # after that lifecycle work, never a stale intermediate frame.
            device_state = state_only_handler(event)
        else:
            device_state = handler(event)
        new_service = (
            str(device_state.get("service"))
            if isinstance(device_state, dict) and device_state.get("service")
            else selected_service
        )
        service_changed = new_service != selected_service
        if self.services is not None and service_changed:
            if selected_service == "DMR":
                self._ptt_pressed_at = None
                self._dmr_hold_triggered = False
                self._cancel_dmr_hold_timer()
            if selected_service == "RADIO":
                self._radio_last_release_at = None
                self._radio_ignore_release = False
                self._radio_ignore_until = 0.0
            if selected_service == "REC":
                media_result = self.services.control(
                    {"action": "voice_recorder_close"}
                )
                self._voice_last_release_at = None
                self._voice_pressed_at = None
                self._voice_ignore_release = False
                self._voice_ignore_until = 0.0
            if new_service == "REC":
                media_result = self.services.control(
                    {"action": "voice_recorder_open"}
                )
        self._view_initialized = True
        if not recorder_ptt_event and (
            media_result is not None or (service_navigation_event and service_changed)
        ):
            if service_navigation_event and service_changed:
                self.render_interaction_once(new_service)
            elif recorder_semantic_event:
                self.render_recorder_once()
            else:
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
                if selected_service == "DMR":
                    response["brandmeister_channel_id"] = media_result["channel_id"]
                else:
                    response["weather_channel_id"] = media_result["channel_id"]
            if "scene_id" in media_result:
                response["ambient_scene_id"] = media_result["scene_id"]
            if "brandmeister" in media_result:
                response["brandmeister"] = media_result["brandmeister"]
            if "radio_buffer" in media_result:
                response["radio_buffer"] = media_result["radio_buffer"]
            if "recording" in media_result:
                response["recording"] = media_result["recording"]
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

    def _initialize_restored_view(self) -> None:
        """Run the entry lifecycle for the restored view exactly once."""

        if self.services is None or self._view_initialized:
            return
        overlay = dict(self.services.receiver_overlay(None))
        restored_service = str(overlay.get("service") or "").upper()
        if restored_service == "REC":
            self.services.control({"action": "voice_recorder_open"})
            overlay = dict(self.services.receiver_overlay("REC"))
        self._pending_initial_view_overlay = overlay
        self._view_initialized = True

    def render_once(self) -> None:
        receiver, receiver_error = self._safe_read(self.receiver, "receiver")
        self._last_receiver_telemetry = dict(receiver)
        if self.services is not None:
            self._initialize_restored_view()
            if self._pending_initial_view_overlay is not None:
                overlay = self._pending_initial_view_overlay
                self._pending_initial_view_overlay = None
            else:
                snapshot = getattr(self.display, "snapshot", None)
                current_ui = snapshot() if callable(snapshot) else {}
                view_service = (
                    str(current_ui.get("service"))
                    if isinstance(current_ui, dict) and current_ui.get("service")
                    else None
                )
                overlay = self.services.receiver_overlay(view_service)
            receiver.update(overlay)
        power, power_error = self._safe_read(self.power, "power")
        self._last_power_telemetry = dict(power)
        errors = [error for error in (receiver_error, power_error) if error]
        self._publish(dashboard_frame(self.config.title, receiver, power, errors))

    def render_recorder_once(self) -> None:
        """Refresh the recorder without putting telemetry/network work in its path."""

        self.render_interaction_once("REC")

    def render_interaction_once(self, view_service: str) -> None:
        """Resolve one interactive view from cached telemetry and repaint once."""

        if self.services is None or not self._last_receiver_telemetry:
            self.render_once()
            return
        receiver = dict(self._last_receiver_telemetry)
        receiver.update(self.services.receiver_overlay(view_service))
        self._publish(
            dashboard_frame(
                self.config.title,
                receiver,
                dict(self._last_power_telemetry),
                [],
            )
        )

    def close(self) -> None:
        self._cancel_dmr_hold_timer()
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
            # Web and other threads created during startup inherit the two
            # background cores on the verified Pi Zero 2 W.
            pin_current_thread_to_background_cores()
            # Restoring REC is an application-entry event, not a presentation
            # detail. Silence every other audio owner before the web server,
            # boot wait or first recorder frame can proceed.
            self._initialize_restored_view()
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
            # The application loop owns native rendering and SPI.  Keep it on
            # its dedicated core; the Whisplay button monitor pins itself to
            # the separate input core when the panel opens.
            pin_current_thread_to_ui_core()
            self.show_boot()
            while not self.stop_event.is_set():
                cycle_started = time.monotonic()
                try:
                    input_context = getattr(self.display, "input_context", None)
                    context = input_context() if callable(input_context) else {}
                    if (
                        isinstance(context, dict)
                        and context.get("service") == "REC"
                        and self._last_receiver_telemetry
                    ):
                        if not self._recorder_interaction_active():
                            self.render_recorder_once()
                        delay = max(
                            0.0,
                            RECORDER_FRAME_INTERVAL_SECONDS
                            - (time.monotonic() - cycle_started),
                        )
                    else:
                        self.render_once()
                        delay = self.config.refresh_interval_seconds
                except (AdapterError, OSError, ValueError) as exc:
                    LOG.error("Display adapter failed: %s", exc)
                    delay = self.config.refresh_interval_seconds
                self.stop_event.wait(delay)
        finally:
            if self._web_server is not None:
                self._web_server.stop()
            self.close()
            LOG.info("OpenR4d10 service stopped")
