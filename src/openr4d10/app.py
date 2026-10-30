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
from .models import Frame
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
    ) -> None:
        self.config = config
        self.display = display
        self.power = power
        self.receiver = receiver
        self.hardware = hardware
        self.stop_event = threading.Event()
        self._status_lock = threading.Lock()
        self._latest_frame = Frame(
            screen="startup", title=config.title, body="Dienst wird gestartet"
        ).as_dict()
        self._web_server: WebServer | None = None

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
        return {
            "service": "online" if not self.stop_event.is_set() else "stopping",
            "version": __version__,
            "frame": frame,
            "adapters": adapters,
        }

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
        power, power_error = self._safe_read(self.power, "power")
        errors = [error for error in (receiver_error, power_error) if error]
        self._publish(dashboard_frame(self.config.title, receiver, power, errors))

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
            LOG.info("OpenR4d10 service stopped")
