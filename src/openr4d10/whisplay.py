"""Verified PiSugar Whisplay ST7789 transport for Raspberry Pi Zero 2 W.

The controller setup and physical pin mapping follow PiSugar/Whisplay
commit b2ccecab528caf939f0e3a900547cd094029f13e (Apache-2.0). The repository
retains the vendor notice and license in boot/native/.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
import time
from typing import Any

from .boot_display import claim_display


WIDTH = 240
HEIGHT = 280
FRAME_BYTES = WIDTH * HEIGHT * 2
PANEL_MARKER = Path("/run/openr4d10-boot/panel.ready")
PANEL_ID = "ST7789-240x280-C0-y20\n"


class WhisplayError(RuntimeError):
    pass


class _LgpioPwm:
    """C-timed PWM on an arbitrary gpiochip line.

    BCM22 has no native PWM function on the Zero 2 W.  ``lgpio.tx_pwm`` keeps
    the software timing in the packaged C library instead of a Python thread,
    avoiding the scheduler jitter visible on the real Whisplay backlight.
    """

    def __init__(
        self,
        lgpio: Any,
        chip_number: int,
        line_offset: int,
        *,
        initial_high: bool,
        frequency_hz: int = 1_000,
    ) -> None:
        self._lgpio = lgpio
        self._line_offset = line_offset
        self._frequency_hz = frequency_hz
        self._pwm_active = False
        self._handle = lgpio.gpiochip_open(chip_number)
        try:
            lgpio.gpio_claim_output(
                self._handle,
                line_offset,
                1 if initial_high else 0,
            )
        except Exception:
            lgpio.gpiochip_close(self._handle)
            self._handle = None
            raise

    def set_duty_cycle(self, duty_percent: int) -> None:
        if self._handle is None:
            return
        if duty_percent <= 0 or duty_percent >= 100:
            if self._pwm_active:
                self._lgpio.tx_pwm(self._handle, self._line_offset, 0, 0)
                self._pwm_active = False
            self._lgpio.gpio_write(
                self._handle,
                self._line_offset,
                1 if duty_percent >= 100 else 0,
            )
            return
        self._lgpio.tx_pwm(
            self._handle,
            self._line_offset,
            self._frequency_hz,
            duty_percent,
        )
        self._pwm_active = True

    def close(self, *, final_high: bool) -> None:
        if self._handle is None:
            return
        try:
            if self._pwm_active:
                self._lgpio.tx_pwm(self._handle, self._line_offset, 0, 0)
                self._pwm_active = False
            self._lgpio.gpio_write(
                self._handle,
                self._line_offset,
                1 if final_high else 0,
            )
            self._lgpio.gpio_free(self._handle, self._line_offset)
        finally:
            self._lgpio.gpiochip_close(self._handle)
            self._handle = None


class WhisplayPanel:
    """Own SPI0/CS0 and the three verified LCD GPIO lines until closed."""

    RESET_BCM = 4
    DC_BCM = 27
    BACKLIGHT_BCM = 22

    def __init__(self, speed_hz: int = 32_000_000) -> None:
        if not 1_000_000 <= speed_hz <= 100_000_000:
            raise ValueError("SPI speed must be between 1 and 100 MHz")
        self.speed_hz = speed_hz
        self._owner: AbstractContextManager[None] | None = None
        self._chip: Any = None
        self._reset: Any = None
        self._dc: Any = None
        self._spi: Any = None
        self._value_active: Any = None
        self._value_inactive: Any = None
        self._brightness_percent = 100
        self._backlight_pwm: _LgpioPwm | None = None

    def open(self) -> None:
        if self._spi is not None:
            return
        self._owner = claim_display(timeout=3.0)
        try:
            self._owner.__enter__()
            self._open_hardware()
        except Exception:
            self.close()
            raise

    def _open_hardware(self) -> None:
        try:
            import gpiod
            import lgpio
            import spidev
            from gpiod.line import Direction, Value
        except (ImportError, AttributeError) as exc:
            raise WhisplayError(
                "Whisplay requires Debian packages python3-libgpiod, "
                "python3-lgpio and python3-spidev"
            ) from exc

        if not hasattr(gpiod, "LineSettings"):
            raise WhisplayError("Whisplay requires the libgpiod v2 Python API")

        try:
            model = Path("/proc/device-tree/model").read_text(
                encoding="utf-8"
            ).rstrip("\x00\n")
        except OSError as exc:
            raise WhisplayError("cannot verify Raspberry Pi model") from exc
        if "Raspberry Pi Zero 2" not in model:
            raise WhisplayError(f"refusing unverified board model: {model}")

        initialized = self._already_initialized()
        self._value_active = Value.ACTIVE
        self._value_inactive = Value.INACTIVE
        try:
            self._chip = gpiod.Chip("/dev/gpiochip0")
            chip_label = str(self._chip.get_info().label)
            if "bcm2835" not in chip_label:
                raise WhisplayError(
                    f"refusing unverified GPIO controller: {chip_label}"
                )
            self._reset = self._request_output(
                gpiod, Direction, self.RESET_BCM, high=True
            )
            self._dc = self._request_output(gpiod, Direction, self.DC_BCM, high=True)
            self._backlight_pwm = _LgpioPwm(
                lgpio,
                0,
                self.BACKLIGHT_BCM,
                initial_high=initialized,
            )
            self._spi = spidev.SpiDev()
            self._spi.open(0, 0)
            self._spi.max_speed_hz = self.speed_hz
            self._spi.mode = 0
            self._spi.bits_per_word = 8
            if not initialized:
                self._initialize_panel()
        except Exception as exc:
            raise WhisplayError(f"cannot open Whisplay SPI/GPIO: {exc}") from exc

    def _request_output(self, gpiod: Any, direction: Any, offset: int, *, high: bool) -> Any:
        settings = gpiod.LineSettings(
            direction=direction.OUTPUT,
            output_value=self._value_active if high else self._value_inactive,
        )
        return self._chip.request_lines(
            consumer="openr4d10-ui",
            config={offset: settings},
        )

    @staticmethod
    def _already_initialized() -> bool:
        try:
            return PANEL_MARKER.read_text(encoding="ascii") == PANEL_ID
        except OSError:
            return False

    def _set(self, request: Any, offset: int, high: bool) -> None:
        request.set_value(
            offset,
            self._value_active if high else self._value_inactive,
        )

    def set_brightness(self, brightness_percent: int) -> None:
        if (
            isinstance(brightness_percent, bool)
            or not isinstance(brightness_percent, int)
            or not 0 <= brightness_percent <= 100
        ):
            raise ValueError("display brightness must be an integer from 0 to 100")
        self._brightness_percent = brightness_percent
        if self._backlight_pwm is not None:
            self._apply_brightness()

    def _apply_brightness(self) -> None:
        if self._backlight_pwm is None:
            return
        duty_percent = 100 - self._brightness_percent
        # The Whisplay backlight is active-low, so the GPIO high-time is the
        # inverse of the user-visible brightness percentage.
        self._backlight_pwm.set_duty_cycle(duty_percent)

    def _write(self, data: bytes) -> None:
        if hasattr(self._spi, "writebytes2"):
            self._spi.writebytes2(data)
            return
        for offset in range(0, len(data), 4096):
            self._spi.xfer2(list(data[offset : offset + 4096]))

    def _command(self, command: int, data: bytes = b"") -> None:
        self._set(self._dc, self.DC_BCM, False)
        self._write(bytes((command,)))
        if data:
            self._set(self._dc, self.DC_BCM, True)
            self._write(data)

    def _initialize_panel(self) -> None:
        self._set(self._reset, self.RESET_BCM, True)
        time.sleep(0.1)
        self._set(self._reset, self.RESET_BCM, False)
        time.sleep(0.1)
        self._set(self._reset, self.RESET_BCM, True)
        time.sleep(0.12)
        self._command(0x11)
        time.sleep(0.12)
        for command, data in (
            (0x36, b"\xC0"),
            (0x3A, b"\x05"),
            (0xB2, b"\x0C\x0C\x00\x33\x33"),
            (0xB7, b"\x35"),
            (0xBB, b"\x32"),
            (0xC2, b"\x01"),
            (0xC3, b"\x15"),
            (0xC4, b"\x20"),
            (0xC6, b"\x0F"),
            (0xD0, b"\xA4\xA1"),
            (0xE0, b"\xD0\x08\x0E\x09\x09\x05\x31\x33\x48\x17\x14\x15\x31\x34"),
            (0xE1, b"\xD0\x08\x0E\x09\x09\x15\x31\x33\x48\x17\x14\x15\x31\x34"),
        ):
            self._command(command, data)
        self._command(0x21)
        self._command(0x29)

    def show(self, rgb565: bytes) -> None:
        if len(rgb565) != FRAME_BYTES:
            raise ValueError(f"Whisplay frame must contain {FRAME_BYTES} bytes")
        self.open()
        self._command(0x2A, b"\x00\x00\x00\xEF")
        self._command(0x2B, b"\x00\x14\x01\x2B")
        self._command(0x2C)
        self._set(self._dc, self.DC_BCM, True)
        self._write(rgb565)
        self._apply_brightness()

    def close(self) -> None:
        if self._backlight_pwm is not None:
            self._backlight_pwm.close(final_high=self._brightness_percent == 0)
            self._backlight_pwm = None
        for request_name in ("_dc", "_reset"):
            request = getattr(self, request_name)
            if request is not None:
                try:
                    request.release()
                except Exception:
                    pass
                setattr(self, request_name, None)
        if self._spi is not None:
            try:
                self._spi.close()
            except Exception:
                pass
            self._spi = None
        if self._chip is not None:
            try:
                self._chip.close()
            except Exception:
                pass
            self._chip = None
        if self._owner is not None:
            try:
                self._owner.__exit__(None, None, None)
            except Exception:
                pass
            self._owner = None
