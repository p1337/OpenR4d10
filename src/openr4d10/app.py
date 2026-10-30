"""Application lifecycle and render loop."""

from __future__ import annotations

import logging
import signal
import threading

from .adapters import AdapterError, Display, Telemetry
from .boot import load_boot_sequence
from .config import AppConfig, ConfigError
from .ui import dashboard_frame

LOG = logging.getLogger(__name__)


class OpenR4d10App:
    def __init__(
        self,
        config: AppConfig,
        display: Display,
        power: Telemetry,
        receiver: Telemetry,
    ) -> None:
        self.config = config
        self.display = display
        self.power = power
        self.receiver = receiver
        self.stop_event = threading.Event()

    def request_stop(self, signum: int | None = None, _frame: object = None) -> None:
        if signum is not None:
            LOG.info("Received signal %s; stopping", signum)
        self.stop_event.set()

    def install_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self.request_stop)
        signal.signal(signal.SIGINT, self.request_stop)

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
            self.display.render(item.frame)
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
        self.display.render(
            dashboard_frame(self.config.title, receiver, power, errors)
        )

    def run(self) -> None:
        self.install_signal_handlers()
        LOG.info("OpenR4d10 service starting")
        self.show_boot()
        while not self.stop_event.is_set():
            try:
                self.render_once()
            except (AdapterError, OSError, ValueError) as exc:
                LOG.error("Display adapter failed: %s", exc)
            self.stop_event.wait(self.config.refresh_interval_seconds)
        LOG.info("OpenR4d10 service stopped")
