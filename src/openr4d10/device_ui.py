"""Native 240 x 280 OpenR4d10 device UI model and Pillow renderer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Mapping

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .input_events import Control, InputEvent
from .models import Frame


WIDTH = 240
HEIGHT = 280
DEFAULT_ACCENT = (73, 222, 204)
SERVICES = ("SYSTEM", "RADIO", "DMR", "PLAYER", "REC")
FONT_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
DISPLAY_TEXT = {
    "en": {
        "controls": ("VOL", "SQL", "CH", "SRV"),
        "menu": "MENU",
        "play": "PLAY",
        "pause": "PAUSE",
        "main_menu": "MAIN MENU",
        "service_settings": "SERVICE SETTINGS",
        "quick_menu": "QUICK MENU",
    },
    "de": {
        "controls": ("LAU", "SQL", "KAN", "DST"),
        "menu": "MENÜ",
        "play": "PLAY",
        "pause": "PAUSE",
        "main_menu": "HAUPTMENÜ",
        "service_settings": "DIENST-EINSTELLUNGEN",
        "quick_menu": "SCHNELLMENÜ",
    },
    "pl": {
        "controls": ("GŁO", "SQL", "KAN", "USŁ"),
        "menu": "MENU",
        "play": "GRAJ",
        "pause": "PAUZA",
        "main_menu": "MENU GŁÓWNE",
        "service_settings": "USTAWIENIA USŁUGI",
        "quick_menu": "SZYBKIE MENU",
    },
    "fr": {
        "controls": ("VOL", "SQL", "CAN", "SRV"),
        "menu": "MENU",
        "play": "LIRE",
        "pause": "PAUSE",
        "main_menu": "MENU PRINCIPAL",
        "service_settings": "RÉGLAGES SERVICE",
        "quick_menu": "MENU RAPIDE",
    },
    "es": {
        "controls": ("VOL", "SQL", "CAN", "SRV"),
        "menu": "MENÚ",
        "play": "PLAY",
        "pause": "PAUSA",
        "main_menu": "MENÚ PRINCIPAL",
        "service_settings": "AJUSTES SERVICIO",
        "quick_menu": "MENÚ RÁPIDO",
    },
}


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
    preset_id: str | None = None
    title: str = "System online"
    subtitle: str = "Receiver ready"
    playing: bool = False
    recording: bool = False
    menu_open: bool = False
    menu_kind: str | None = None
    ptt_active: bool = False
    language: str = "en"
    accent: tuple[int, int, int] = DEFAULT_ACCENT
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def service(self) -> str:
        return SERVICES[self.service_index % len(SERVICES)]

    def public_state(self) -> dict[str, object]:
        """Return the bounded, non-secret state exposed to virtual controls."""
        return {
            "volume": self.volume,
            "squelch": self.squelch,
            "channel": self.channel,
            "service": self.service,
            "left_action": self.left_action,
            "right_action": self.right_action,
            "playing": self.playing,
            "menu_open": self.menu_open,
            "menu_kind": self.menu_kind,
            "ptt_active": self.ptt_active,
            "language": self.language,
            "title": self.title,
            "subtitle": self.subtitle,
            "preset_id": self.preset_id,
        }

    def apply(self, event: InputEvent) -> None:
        if event.control == Control.LEFT_OUTER:
            self.volume = max(0, min(100, self.volume + event.steps * 10))
        elif event.control == Control.LEFT_INNER:
            self.squelch = max(0, min(9, self.squelch + event.steps))
        elif event.control == Control.RIGHT_OUTER:
            self.channel = max(1, min(999, self.channel + event.steps))
        elif event.control == Control.RIGHT_INNER:
            self.service_index = (self.service_index + event.steps) % len(SERVICES)
        elif event.control == Control.LEFT_PRESS:
            self.menu_open = True
            if event.held_seconds >= 2.0:
                self.menu_kind = "service_settings"
                self.title = "Service settings"
                self.subtitle = "Settings for the active service"
            else:
                self.menu_kind = "main_menu"
                self.title = "Main menu"
                self.subtitle = "Rotate SERVICE to select"
        elif event.control == Control.RIGHT_PRESS:
            if event.held_seconds >= 2.0:
                self.menu_open = True
                self.menu_kind = "quick_menu"
                self.title = "Quick menu"
                self.subtitle = "Recording and playback actions"
            else:
                self.playing = not self.playing
                self.right_action = "PAUSE" if self.playing else "PLAY"
        elif event.control == Control.PTT:
            self.ptt_active = bool(event.active)
            self.title = "PTT input active" if self.ptt_active else "PTT released"
            self.subtitle = "No PTT service adapter configured"

    def update_from_frame(self, frame: Frame) -> None:
        fields = frame.fields
        receiver = fields.get("receiver", {})
        power = fields.get("power", {})
        controls = fields.get("controls", {})
        ui = fields.get("ui", {})
        if not isinstance(receiver, Mapping):
            receiver = {}
        if not isinstance(power, Mapping):
            power = {}
        if not isinstance(controls, Mapping):
            controls = {}
        if not isinstance(ui, Mapping):
            ui = {}

        language = ui.get("language")
        if isinstance(language, str):
            language_key = language.casefold().split("-", 1)[0]
            if language_key in DISPLAY_TEXT:
                self.language = language_key

        self.timestamp = datetime.now()
        self.source = str(
            receiver.get("station")
            or receiver.get("hostname")
            or "OPENR4D10"
        )[:28]
        preset_id = receiver.get("preset_id")
        self.preset_id = preset_id if isinstance(preset_id, str) else None
        if not self.menu_open:
            self.title = str(receiver.get("title") or frame.title)[:48]
            self.subtitle = str(receiver.get("subtitle") or frame.body)[:72]
        self.wifi_label = str(receiver.get("wifi") or "WLAN")[:12]
        self.ip_address = str(receiver.get("ip_address") or "--")[:15]
        self.playing = bool(receiver.get("playing", self.playing))
        self.right_action = "PAUSE" if self.playing else "PLAY"
        self.recording = bool(receiver.get("recording", False))
        volume = receiver.get("volume")
        if isinstance(volume, int) and not isinstance(volume, bool):
            self.volume = max(0, min(100, volume))
        channel = receiver.get("channel")
        if isinstance(channel, int) and not isinstance(channel, bool):
            self.channel = max(1, min(999, channel))
        service = str(receiver.get("service") or "").upper()
        if service in SERVICES:
            self.service_index = SERVICES.index(service)

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
    fallback = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for candidate in (str(path), fallback):
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _display_text(language: str) -> dict[str, object]:
    key = language.casefold().split("-", 1)[0]
    return DISPLAY_TEXT.get(key, DISPLAY_TEXT["en"])


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
    header_height: int,
) -> None:
    font = _font(9, bold=True)
    bbox = font.getbbox(text)
    label = Image.new("RGBA", (bbox[2] + 6, bbox[3] - bbox[1] + 6), (0, 0, 0, 0))
    ImageDraw.Draw(label).text((3, 2 - bbox[1]), text, font=font, fill=(135, 143, 148, 255))
    rotated = label.rotate(-90 if clockwise else 90, expand=True)
    image.alpha_composite(rotated, (x, max(1, (header_height - rotated.height) // 2)))


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
    small = _font(10, bold=True)
    large = _font(12, bold=True)
    draw.text((x, y), label, font=small, fill=(128, 140, 145))
    draw.text((x + 36, y - 2), value, font=large, fill=accent)


def _draw_centered_menu(
    draw: ImageDraw.ImageDraw,
    title: str,
    top: int,
    accent: tuple[int, int, int],
) -> None:
    words = title.split()
    lines = words if len(words) > 1 else [title]
    font = _font(25, bold=True)
    line_height = 31
    block_height = len(lines) * line_height
    y = top + (HEIGHT - top - block_height) // 2
    for line in lines:
        fitted = _fit_text(draw, line, font, WIDTH - 28)
        bounds = draw.textbbox((0, 0), fitted, font=font)
        width = bounds[2] - bounds[0]
        draw.text(((WIDTH - width) / 2, y), fitted, font=font, fill=accent)
        y += line_height


def render_device_ui(
    state: DeviceUiState,
    artwork: Image.Image | None = None,
) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (4, 8, 10, 255))
    draw = ImageDraw.Draw(image)
    accent = state.accent
    text = _display_text(state.language)
    controls = text["controls"]
    assert isinstance(controls, tuple)
    left_action = str(text["menu"])
    right_action = str(text["pause"] if state.playing else text["play"])

    header_height = 53
    draw.rectangle((0, 0, WIDTH - 1, 52), fill=(2, 5, 7), outline=(35, 47, 51))
    draw.line((17, 26, 222, 26), fill=(25, 35, 39), width=1)
    draw.line((119, 3, 119, 49), fill=(25, 35, 39), width=1)
    _vertical_label(image, left_action, 1, clockwise=False, header_height=header_height)
    _vertical_label(image, right_action, 227, clockwise=True, header_height=header_height)
    _control_value(draw, 19, 7, str(controls[0]), f"{state.volume}%", accent)
    _control_value(draw, 19, 32, str(controls[1]), str(state.squelch), accent)
    _control_value(draw, 122, 7, str(controls[2]), f"{state.channel:03d}", accent)
    _control_value(draw, 122, 32, str(controls[3]), state.service, accent)

    draw.rectangle((0, 53, WIDTH - 1, 81), fill=(12, 20, 23))
    _wifi_icon(draw, 5, 61, accent)
    status_font = _font(7)
    draw.text((22, 57), _fit_text(draw, state.wifi_label, status_font, 67), font=status_font, fill=(213, 222, 224))
    draw.text((22, 69), _fit_text(draw, state.ip_address, status_font, 73), font=status_font, fill=(112, 130, 134))
    clock = state.timestamp.strftime("%H:%M")
    clock_font = _font(15, bold=True)
    clock_width = draw.textbbox((0, 0), clock, font=clock_font)[2]
    draw.text((139 - clock_width / 2, 58), clock, font=clock_font, fill=(235, 240, 241))
    _battery(draw, 207, 62, state.battery_percent, accent)
    if state.battery_percent is not None:
        pct = f"{state.battery_percent}%"
        pct_font = _font(6, bold=True)
        width = draw.textbbox((0, 0), pct, font=pct_font)[2]
        draw.text((205 - width, 65), pct, font=pct_font, fill=(180, 190, 192))

    content_top = 82
    draw.rectangle((0, content_top, WIDTH - 1, HEIGHT - 1), fill=(6, 12, 15))
    draw.rectangle((0, content_top, 3, HEIGHT - 1), fill=accent)
    if state.menu_open:
        menu_key = state.menu_kind or "main_menu"
        menu_title = str(text.get(menu_key, text["main_menu"]))
        _draw_centered_menu(draw, menu_title, content_top, accent)
        return image.convert("RGB")

    station_font = _font(18, bold=True)
    station = _fit_text(draw, state.source, station_font, 164)
    draw.text((14, 94), station, font=station_font, fill=(245, 248, 249))

    tile_size = 138
    tile_xy = (14, 126)
    if artwork is not None:
        tile = ImageOps.fit(
            artwork.convert("RGB"),
            (tile_size, tile_size),
            method=Image.Resampling.LANCZOS,
        )
        mask = Image.new("L", (tile_size, tile_size), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, tile_size - 1, tile_size - 1),
            radius=12,
            fill=255,
        )
        image.paste(tile, tile_xy, mask)
    else:
        draw.rounded_rectangle(
            (14, 126, 151, 263),
            radius=12,
            fill=(13, 31, 35),
            outline=accent,
            width=2,
        )
        initials = "".join(part[:1] for part in state.source.split()[:2]).upper() or "OR"
        initials_font = _font(34, bold=True)
        bounds = draw.textbbox((0, 0), initials, font=initials_font)
        draw.text(
            (83 - (bounds[2] - bounds[0]) / 2, 195 - (bounds[3] - bounds[1]) / 2),
            initials,
            font=initials_font,
            fill=accent,
        )
    draw.rounded_rectangle((13, 125, 152, 264), radius=12, outline=(75, 92, 96), width=1)

    title = state.title if state.title.casefold() != state.source.casefold() else state.subtitle
    detail_font = _font(10, bold=True)
    draw.multiline_text(
        (161, 144),
        _fit_text(draw, title, detail_font, 66),
        font=detail_font,
        fill=(196, 207, 209),
        spacing=3,
    )

    draw.ellipse((184, 88, 228, 132), fill=(12, 23, 27), outline=accent, width=2)
    if state.playing:
        draw.rectangle((200, 101, 204, 119), fill=accent)
        draw.rectangle((209, 101, 213, 119), fill=accent)
    else:
        draw.polygon(((200, 99), (200, 121), (216, 110)), fill=accent)
    if state.recording:
        draw.ellipse((220, 87, 228, 95), fill=(255, 78, 78))
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
