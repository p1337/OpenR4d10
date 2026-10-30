"""Native 240 x 280 OpenR4d10 device UI model and Pillow renderer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Mapping

from PIL import Image, ImageDraw, ImageFont

from .input_events import Control, InputEvent
from .models import Frame


WIDTH = 240
HEIGHT = 280
DEFAULT_ACCENT = (73, 222, 204)
SERVICES = ("SYSTEM", "RADIO", "DMR", "PLAYER", "REC")
FONT_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


@dataclass(slots=True)
class DeviceUiState:
    volume: int = 36
    squelch: int = 5
    channel: int = 1
    service_index: int = 0
    left_action: str = "MENU"
    right_action: str = "PLAY"
    wifi_label: str = "WLAN"
    ip_address: str = "--"
    battery_percent: int | None = None
    source: str = "OPENR4D10"
    title: str = "System online"
    subtitle: str = "Receiver ready"
    playing: bool = False
    recording: bool = False
    menu_open: bool = False
    accent: tuple[int, int, int] = DEFAULT_ACCENT
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def service(self) -> str:
        return SERVICES[self.service_index % len(SERVICES)]

    def apply(self, event: InputEvent) -> None:
        if event.control == Control.LEFT_OUTER:
            self.volume = max(0, min(100, self.volume + event.steps))
        elif event.control == Control.LEFT_INNER:
            self.squelch = max(0, min(9, self.squelch + event.steps))
        elif event.control == Control.RIGHT_OUTER:
            self.channel = max(1, min(999, self.channel + event.steps))
        elif event.control == Control.RIGHT_INNER:
            self.service_index = (self.service_index + event.steps) % len(SERVICES)
        elif event.control == Control.LEFT_PRESS:
            self.menu_open = True
            if event.held_seconds >= 2.0:
                self.title = "Service settings"
                self.subtitle = "Settings for the active service"
            else:
                self.title = "Main menu"
                self.subtitle = "Rotate SERVICE to select"
        elif event.control == Control.RIGHT_PRESS:
            if event.held_seconds >= 2.0:
                self.menu_open = True
                self.title = "Quick menu"
                self.subtitle = "Recording and playback actions"
            else:
                self.playing = not self.playing
                self.right_action = "PAUSE" if self.playing else "PLAY"

    def update_from_frame(self, frame: Frame) -> None:
        fields = frame.fields
        receiver = fields.get("receiver", {})
        power = fields.get("power", {})
        controls = fields.get("controls", {})
        if not isinstance(receiver, Mapping):
            receiver = {}
        if not isinstance(power, Mapping):
            power = {}
        if not isinstance(controls, Mapping):
            controls = {}

        self.timestamp = datetime.now()
        self.source = str(
            receiver.get("station")
            or receiver.get("hostname")
            or "OPENR4D10"
        )[:28]
        if not self.menu_open:
            self.title = str(receiver.get("title") or frame.title)[:48]
            self.subtitle = str(receiver.get("subtitle") or frame.body)[:72]
        self.wifi_label = str(receiver.get("wifi") or "WLAN")[:12]
        self.ip_address = str(receiver.get("ip_address") or "--")[:15]
        self.playing = bool(receiver.get("playing", self.playing))
        self.recording = bool(receiver.get("recording", False))

        battery = power.get("battery_percent")
        if isinstance(battery, (int, float)) and not isinstance(battery, bool):
            self.battery_percent = max(0, min(100, round(battery)))

        for key, low, high in (
            ("volume", 0, 100),
            ("squelch", 0, 9),
            ("channel", 1, 999),
        ):
            value = controls.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                setattr(self, key, max(low, min(high, value)))


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    try:
        return ImageFont.truetype(str(path), size=size)
    except OSError:
        return ImageFont.load_default()


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    width: int,
) -> str:
    if draw.textbbox((0, 0), text, font=font)[2] <= width:
        return text
    shortened = text
    while shortened and draw.textbbox((0, 0), shortened + "…", font=font)[2] > width:
        shortened = shortened[:-1]
    return shortened + "…" if shortened else ""


def _vertical_label(
    image: Image.Image,
    text: str,
    x: int,
    *,
    clockwise: bool,
) -> None:
    font = _font(8, bold=True)
    bbox = font.getbbox(text)
    label = Image.new("RGBA", (bbox[2] + 6, bbox[3] - bbox[1] + 6), (0, 0, 0, 0))
    ImageDraw.Draw(label).text((3, 2 - bbox[1]), text, font=font, fill=(135, 143, 148, 255))
    rotated = label.rotate(-90 if clockwise else 90, expand=True)
    image.alpha_composite(rotated, (x, max(1, (66 - rotated.height) // 2)))


def _wifi_icon(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple[int, int, int]) -> None:
    draw.arc((x, y, x + 14, y + 12), 205, 335, fill=color, width=1)
    draw.arc((x + 3, y + 4, x + 11, y + 11), 205, 335, fill=color, width=1)
    draw.ellipse((x + 6, y + 10, x + 8, y + 12), fill=color)


def _battery(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    percent: int | None,
    color: tuple[int, int, int],
) -> None:
    draw.rounded_rectangle((x, y, x + 19, y + 9), radius=2, outline=(158, 167, 170), width=1)
    draw.rectangle((x + 20, y + 3, x + 21, y + 6), fill=(158, 167, 170))
    if percent is not None:
        fill_width = max(1, round(15 * percent / 100))
        draw.rectangle((x + 2, y + 2, x + 1 + fill_width, y + 7), fill=color)


def _control_value(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    label: str,
    value: str,
    accent: tuple[int, int, int],
) -> None:
    small = _font(7, bold=True)
    large = _font(9, bold=True)
    draw.text((x, y), label, font=small, fill=(128, 140, 145))
    draw.text((x + 58, y - 1), value, font=large, fill=accent)


def render_device_ui(state: DeviceUiState) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (4, 8, 10, 255))
    draw = ImageDraw.Draw(image)
    accent = state.accent

    draw.rectangle((0, 0, WIDTH - 1, 65), fill=(2, 5, 7), outline=(35, 47, 51))
    draw.line((17, 33, 222, 33), fill=(25, 35, 39), width=1)
    draw.line((119, 3, 119, 62), fill=(25, 35, 39), width=1)
    _vertical_label(image, state.left_action, 2, clockwise=False)
    _vertical_label(image, state.right_action, 226, clockwise=True)
    _control_value(draw, 21, 12, "VOLUME", f"{state.volume}%", accent)
    _control_value(draw, 21, 43, "SQUELCH", str(state.squelch), accent)
    _control_value(draw, 124, 12, "CHANNEL", f"{state.channel:03d}", accent)
    _control_value(draw, 124, 43, "SERVICE", state.service, accent)

    draw.rectangle((0, 66, WIDTH - 1, 88), fill=(12, 20, 23))
    _wifi_icon(draw, 5, 70, accent)
    status_font = _font(7)
    draw.text((22, 69), _fit_text(draw, state.wifi_label, status_font, 62), font=status_font, fill=(213, 222, 224))
    draw.text((22, 78), _fit_text(draw, state.ip_address, status_font, 70), font=status_font, fill=(112, 130, 134))
    clock = state.timestamp.strftime("%H:%M")
    date = state.timestamp.strftime("%d.%m")
    draw.text((102, 69), clock, font=_font(10, bold=True), fill=(235, 240, 241))
    draw.text((104, 79), date, font=_font(6), fill=(115, 130, 134))
    _battery(draw, 207, 72, state.battery_percent, accent)
    if state.battery_percent is not None:
        pct = f"{state.battery_percent}%"
        pct_font = _font(6, bold=True)
        width = draw.textbbox((0, 0), pct, font=pct_font)[2]
        draw.text((205 - width, 74), pct, font=pct_font, fill=(180, 190, 192))

    draw.rectangle((0, 89, WIDTH - 1, HEIGHT - 1), fill=(6, 12, 15))
    draw.rectangle((0, 89, 3, HEIGHT - 1), fill=accent)
    draw.text((14, 101), state.service, font=_font(8, bold=True), fill=accent)
    draw.text(
        (14, 114),
        _fit_text(draw, state.source.upper(), _font(11, bold=True), 210),
        font=_font(11, bold=True),
        fill=(237, 242, 243),
    )
    title = _fit_text(draw, state.title, _font(15, bold=True), 210)
    draw.text((14, 136), title, font=_font(15, bold=True), fill=(245, 248, 249))
    subtitle = _fit_text(draw, state.subtitle, _font(8), 210)
    draw.text((14, 158), subtitle, font=_font(8), fill=(130, 148, 153))

    base_y = 215
    for index, height in enumerate((9, 18, 29, 16, 35, 24, 12, 27, 19, 8, 15, 11)):
        x = 15 + index * 11
        active = state.playing or index % 3 == 1
        bar = accent if active else (44, 61, 66)
        draw.rounded_rectangle((x, base_y - height, x + 5, base_y), radius=2, fill=bar)

    draw.ellipse((166, 183, 214, 231), fill=(12, 23, 27), outline=accent, width=2)
    if state.playing:
        draw.rectangle((183, 197, 187, 217), fill=accent)
        draw.rectangle((193, 197, 197, 217), fill=accent)
    else:
        draw.polygon(((184, 195), (184, 219), (201, 207)), fill=accent)
    if state.recording:
        draw.ellipse((207, 178, 216, 187), fill=(255, 78, 78))

    footer = "PLAYING" if state.playing else "READY"
    if state.recording:
        footer = "RECORDING"
    draw.line((14, 247, 226, 247), fill=(28, 40, 44), width=1)
    draw.text((14, 256), footer, font=_font(8, bold=True), fill=accent)
    draw.text((170, 256), "OpenR4d10", font=_font(7, bold=True), fill=(88, 103, 108))
    return image.convert("RGB")


def frame_to_ui_state(frame: Frame, previous: DeviceUiState | None = None) -> DeviceUiState:
    state = previous if previous is not None else DeviceUiState()
    state.update_from_frame(frame)
    return state


def image_to_rgb565(image: Image.Image) -> bytes:
    rgb = image.convert("RGB")
    if rgb.size != (WIDTH, HEIGHT):
        raise ValueError(f"device image must be {WIDTH}x{HEIGHT}")
    source = memoryview(rgb.tobytes())
    output = bytearray(WIDTH * HEIGHT * 2)
    target = 0
    for offset in range(0, len(source), 3):
        value = (
            ((source[offset] & 0xF8) << 8)
            | ((source[offset + 1] & 0xFC) << 3)
            | (source[offset + 2] >> 3)
        )
        output[target] = value >> 8
        output[target + 1] = value & 0xFF
        target += 2
    return bytes(output)
