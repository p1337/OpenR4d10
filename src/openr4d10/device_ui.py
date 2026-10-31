"""Native 240 x 280 OpenR4d10 device UI model and Pillow renderer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Mapping

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from .input_events import Control, InputEvent
from .models import Frame


WIDTH = 240
HEIGHT = 280
DISPLAY_CORNER_RADIUS = 43
MEDIA_TOP_RADIUS = 12
MEDIA_MARGIN = 7
DEFAULT_ACCENT = (253, 184, 19)
SERVICES = ("SYSTEM", "RADIO", "WEATHER", "DMR", "PLAYER", "REC")
MAIN_MENU_ITEMS = (
    "display",
    "accent_color",
    "wlan",
    "service_modules",
    "service_store",
    "bluetooth",
    "input_speech",
    "language",
    "system",
    "about_support",
)
FONT_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
DISPLAY_TEXT = {
    "en": {
        "controls": ("VOL", "SQL", "CH", "SRV"),
        "menu": "MENU",
        "play": "PLAY",
        "pause": "PAUSE",
        "info": "INFO",
        "weather_service": "WX",
        "main_menu": "MAIN MENU",
        "service_settings": "SERVICE SETTINGS",
        "quick_menu": "QUICK MENU",
        "display": "DISPLAY",
        "accent_color": "ACCENT COLOR",
        "wlan": "WI-FI",
        "service_modules": "SERVICE MODULES",
        "service_store": "SERVICE STORE",
        "bluetooth": "BLUETOOTH",
        "input_speech": "INPUT & SPEECH",
        "language": "LANGUAGE",
        "system": "SYSTEM",
        "about_support": "ABOUT & SUPPORT",
        "wifi_setup": "WI-FI SETUP",
        "wifi_name": "NETWORK",
        "wifi_password": "PASSWORD",
        "wifi_open": "OPEN ON PHONE",
        "play_audio_service": "Press PLAY to start this audio service",
        "receiver_ready": "Receiver ready",
        "system_online": "System online",
        "select_media_play": "Select media and press PLAY",
        "select_channel_play": "Select a channel and press PLAY",
        "recording_controls": "Recording controls",
        "ready": "Ready",
        "paused": "Paused",
        "audio_stream_active": "Audio stream active",
        "settings_active_service": "Settings for the active service",
        "rotate_service_select": "Rotate SERVICE to select",
        "recording_playback_actions": "Recording and playback actions",
        "radar_loading": "Loading rain radar",
        "satellite_loading": "Loading satellite images",
        "title_loading": "Loading title information",
        "title_unavailable": "No title information",
    },
    "de": {
        "controls": ("LAU", "SQL", "KAN", "DST"),
        "menu": "MENÜ",
        "play": "PLAY",
        "pause": "PAUSE",
        "info": "INFO",
        "weather_service": "WET",
        "main_menu": "HAUPTMENÜ",
        "service_settings": "DIENST-EINSTELLUNGEN",
        "quick_menu": "SCHNELLMENÜ",
        "display": "ANZEIGE",
        "accent_color": "AKZENTFARBE",
        "wlan": "WLAN",
        "service_modules": "DIENSTMODULE",
        "service_store": "DIENST-STORE",
        "bluetooth": "BLUETOOTH",
        "input_speech": "EINGABE & SPRACHE",
        "language": "SPRACHE",
        "system": "SYSTEM",
        "about_support": "INFO & SUPPORT",
        "wifi_setup": "WLAN-EINRICHTUNG",
        "wifi_name": "NETZWERK",
        "wifi_password": "KENNWORT",
        "wifi_open": "AM HANDY ÖFFNEN",
        "play_audio_service": "Mit PLAY diesen Audiodienst starten",
        "receiver_ready": "Empfänger bereit",
        "system_online": "System online",
        "select_media_play": "Medium wählen und PLAY drücken",
        "select_channel_play": "Kanal wählen und PLAY drücken",
        "recording_controls": "Aufnahmesteuerung",
        "ready": "Bereit",
        "paused": "Pausiert",
        "audio_stream_active": "Audiostream aktiv",
        "settings_active_service": "Einstellungen des aktiven Dienstes",
        "rotate_service_select": "DIENST drehen zum Auswählen",
        "recording_playback_actions": "Aufnahme- und Wiedergabeaktionen",
        "radar_loading": "Regenradar wird geladen",
        "satellite_loading": "Satellitenbilder werden geladen",
        "title_loading": "Titel wird ermittelt",
        "title_unavailable": "Keine Titelinformation",
    },
    "pl": {
        "controls": ("GŁO", "SQL", "KAN", "USŁ"),
        "menu": "MENU",
        "play": "GRAJ",
        "pause": "PAUZA",
        "info": "INFO",
        "weather_service": "POG",
        "main_menu": "MENU GŁÓWNE",
        "service_settings": "USTAWIENIA USŁUGI",
        "quick_menu": "SZYBKIE MENU",
        "display": "EKRAN",
        "accent_color": "KOLOR AKCENTU",
        "wlan": "WI-FI",
        "service_modules": "MODUŁY USŁUG",
        "service_store": "SKLEP USŁUG",
        "bluetooth": "BLUETOOTH",
        "input_speech": "STEROWANIE I MOWA",
        "language": "JĘZYK",
        "system": "SYSTEM",
        "about_support": "INFO I WSPARCIE",
        "wifi_setup": "KONFIGURACJA WI-FI",
        "wifi_name": "SIEĆ",
        "wifi_password": "HASŁO",
        "wifi_open": "OTWÓRZ W TELEFONIE",
        "play_audio_service": "Naciśnij GRAJ, aby uruchomić audio",
        "receiver_ready": "Odbiornik gotowy",
        "system_online": "System online",
        "select_media_play": "Wybierz plik i naciśnij GRAJ",
        "select_channel_play": "Wybierz kanał i naciśnij GRAJ",
        "recording_controls": "Sterowanie nagrywaniem",
        "ready": "Gotowe",
        "paused": "Pauza",
        "audio_stream_active": "Strumień audio aktywny",
        "settings_active_service": "Ustawienia aktywnej usługi",
        "rotate_service_select": "Obróć USŁ, aby wybrać",
        "recording_playback_actions": "Nagrywanie i odtwarzanie",
        "radar_loading": "Ładowanie radaru opadów",
        "satellite_loading": "Ładowanie zdjęć satelitarnych",
        "title_loading": "Pobieranie tytułu",
        "title_unavailable": "Brak informacji o utworze",
    },
    "fr": {
        "controls": ("VOL", "SQL", "CAN", "SRV"),
        "menu": "MENU",
        "play": "LIRE",
        "pause": "PAUSE",
        "info": "INFO",
        "weather_service": "MÉT",
        "main_menu": "MENU PRINCIPAL",
        "service_settings": "RÉGLAGES SERVICE",
        "quick_menu": "MENU RAPIDE",
        "display": "ÉCRAN",
        "accent_color": "COULEUR D’ACCENT",
        "wlan": "WI-FI",
        "service_modules": "MODULES DE SERVICE",
        "service_store": "BOUTIQUE SERVICES",
        "bluetooth": "BLUETOOTH",
        "input_speech": "ENTRÉE ET PAROLE",
        "language": "LANGUE",
        "system": "SYSTÈME",
        "about_support": "INFOS ET SOUTIEN",
        "wifi_setup": "CONFIGURATION WI-FI",
        "wifi_name": "RÉSEAU",
        "wifi_password": "MOT DE PASSE",
        "wifi_open": "OUVRIR SUR MOBILE",
        "play_audio_service": "Appuyer sur LIRE pour lancer l’audio",
        "receiver_ready": "Récepteur prêt",
        "system_online": "Système en ligne",
        "select_media_play": "Choisir un média puis LIRE",
        "select_channel_play": "Choisir un canal puis LIRE",
        "recording_controls": "Commandes d’enregistrement",
        "ready": "Prêt",
        "paused": "En pause",
        "audio_stream_active": "Flux audio actif",
        "settings_active_service": "Réglages du service actif",
        "rotate_service_select": "Tourner SERVICE pour choisir",
        "recording_playback_actions": "Enregistrement et lecture",
        "radar_loading": "Chargement du radar pluie",
        "satellite_loading": "Chargement des images satellite",
        "title_loading": "Recherche du titre",
        "title_unavailable": "Titre indisponible",
    },
    "es": {
        "controls": ("VOL", "SQL", "CAN", "SRV"),
        "menu": "MENÚ",
        "play": "PLAY",
        "pause": "PAUSA",
        "info": "INFO",
        "weather_service": "MET",
        "main_menu": "MENÚ PRINCIPAL",
        "service_settings": "AJUSTES SERVICIO",
        "quick_menu": "MENÚ RÁPIDO",
        "display": "PANTALLA",
        "accent_color": "COLOR DE ACENTO",
        "wlan": "WI-FI",
        "service_modules": "MÓDULOS DE SERVICIO",
        "service_store": "TIENDA DE SERVICIOS",
        "bluetooth": "BLUETOOTH",
        "input_speech": "ENTRADA Y VOZ",
        "language": "IDIOMA",
        "system": "SISTEMA",
        "about_support": "INFO Y SOPORTE",
        "wifi_setup": "CONFIGURACIÓN WI-FI",
        "wifi_name": "RED",
        "wifi_password": "CONTRASEÑA",
        "wifi_open": "ABRIR EN EL MÓVIL",
        "play_audio_service": "Pulsa PLAY para iniciar el audio",
        "receiver_ready": "Receptor listo",
        "system_online": "Sistema en línea",
        "select_media_play": "Elige un medio y pulsa PLAY",
        "select_channel_play": "Elige un canal y pulsa PLAY",
        "recording_controls": "Controles de grabación",
        "ready": "Listo",
        "paused": "En pausa",
        "audio_stream_active": "Flujo de audio activo",
        "settings_active_service": "Ajustes del servicio activo",
        "rotate_service_select": "Gira SERVICIO para elegir",
        "recording_playback_actions": "Grabación y reproducción",
        "radar_loading": "Cargando radar de lluvia",
        "satellite_loading": "Cargando imágenes de satélite",
        "title_loading": "Buscando el título",
        "title_unavailable": "Sin información del título",
    },
}

DEVICE_TEXT_KEYS = {
    "Play starts this audio service": "play_audio_service",
    "Receiver ready": "receiver_ready",
    "System online": "system_online",
    "Select media and press play": "select_media_play",
    "Select a channel and press play": "select_channel_play",
    "Recording controls": "recording_controls",
    "Ready": "ready",
    "Paused": "paused",
    "Audio stream active": "audio_stream_active",
    "Settings for the active service": "settings_active_service",
    "Rotate SERVICE to select": "rotate_service_select",
    "Recording and playback actions": "recording_playback_actions",
    "Regenradar wird geladen": "radar_loading",
    "Satellitenbilder werden geladen": "satellite_loading",
    "Loading title information": "title_loading",
    "No title information": "title_unavailable",
}


@dataclass(slots=True)
class DeviceUiState:
    volume: int = 30
    squelch: int = 5
    channel: int = 1
    service_index: int = 0
    left_action: str = "MENU"
    right_action: str = "PLAY"
    wifi_label: str = "OFFLINE"
    ip_address: str = "--"
    battery_percent: int | None = None
    source: str = "OPENR4D10"
    preset_id: str | None = None
    image_file: str | None = None
    title: str = "System online"
    subtitle: str = "Receiver ready"
    playing: bool = False
    recording: bool = False
    menu_open: bool = False
    menu_kind: str | None = None
    menu_selection: int = 0
    menu_stack: list[tuple[str, int]] = field(default_factory=list)
    menu_return_title: str | None = None
    menu_return_subtitle: str | None = None
    ptt_active: bool = False
    ptt_context_active: bool = False
    hotspot_active: bool = False
    hotspot_ssid: str = ""
    hotspot_passphrase: str = ""
    hotspot_url: str = ""
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
            "menu_selection": self.menu_selection,
            "menu_item": self.selected_menu_item,
            "ptt_active": self.ptt_active,
            "ptt_context_active": self.ptt_context_active,
            "language": self.language,
            "title": self.title,
            "subtitle": self.subtitle,
            "preset_id": self.preset_id,
            "image_file": self.image_file,
            "accent_color": "#{:02X}{:02X}{:02X}".format(*self.accent),
        }

    @property
    def selected_menu_item(self) -> str | None:
        if self.menu_kind != "main_menu" or not 0 <= self.menu_selection < len(
            MAIN_MENU_ITEMS
        ):
            return None
        return MAIN_MENU_ITEMS[self.menu_selection]

    def _open_menu(self, kind: str) -> None:
        if not self.menu_open:
            self.menu_return_title = self.title
            self.menu_return_subtitle = self.subtitle
        self.menu_open = True
        self.menu_kind = kind
        self.menu_selection = 0
        self.menu_stack.clear()

    def _select_menu_item(self) -> None:
        if self.menu_kind != "main_menu":
            return
        selected = self.selected_menu_item
        if selected is None:
            return
        self.menu_stack.append(("main_menu", self.menu_selection))
        self.menu_kind = selected
        self.menu_selection = 0

    def _menu_back(self) -> None:
        if self.menu_stack:
            self.menu_kind, self.menu_selection = self.menu_stack.pop()
            return
        self.menu_open = False
        self.menu_kind = None
        self.menu_selection = 0
        if self.menu_return_title is not None:
            self.title = self.menu_return_title
        if self.menu_return_subtitle is not None:
            self.subtitle = self.menu_return_subtitle
        self.menu_return_title = None
        self.menu_return_subtitle = None

    def apply(self, event: InputEvent) -> None:
        if event.control == Control.LEFT_OUTER:
            self.volume = max(0, min(100, self.volume + event.steps * 10))
        elif event.control == Control.LEFT_INNER:
            self.squelch = max(0, min(9, self.squelch + event.steps))
        elif event.control == Control.RIGHT_OUTER:
            if self.menu_open and self.menu_kind == "main_menu":
                self.menu_selection = max(
                    0,
                    min(len(MAIN_MENU_ITEMS) - 1, self.menu_selection + event.steps),
                )
            elif not self.menu_open:
                self.channel = max(1, min(999, self.channel + event.steps))
        elif event.control == Control.RIGHT_INNER:
            self.service_index = (self.service_index + event.steps) % len(SERVICES)
        elif event.control == Control.LEFT_PRESS:
            if event.held_seconds >= 2.0:
                self._open_menu("service_settings")
                self.title = "Service settings"
                self.subtitle = "Settings for the active service"
            else:
                self._open_menu("main_menu")
                self.title = "Main menu"
                self.subtitle = "Rotate SERVICE to select"
        elif event.control == Control.RIGHT_PRESS:
            if event.held_seconds >= 2.0:
                self._open_menu("quick_menu")
                self.title = "Quick menu"
                self.subtitle = "Recording and playback actions"
            elif self.menu_open:
                self._select_menu_item()
            elif self.service in {"RADIO", "DMR", "PLAYER"}:
                self.playing = not self.playing
                self.right_action = "PAUSE" if self.playing else "PLAY"
        elif event.control == Control.PTT:
            if self.ptt_context_active:
                self.ptt_active = bool(event.active)
            else:
                self.ptt_active = False
                if event.active and self.menu_open:
                    self._menu_back()

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

        ptt_context = ui.get("ptt_context_active")
        self.ptt_context_active = (
            ptt_context if isinstance(ptt_context, bool) else False
        )
        if not self.ptt_context_active:
            self.ptt_active = False

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
        image_file = receiver.get("image_file")
        self.image_file = image_file if isinstance(image_file, str) else None
        if not self.menu_open:
            self.title = str(receiver.get("title") or frame.title)[:48]
            self.subtitle = str(receiver.get("subtitle") or frame.body)[:72]
        self.wifi_label = str(receiver.get("wifi") or "OFFLINE")[:32]
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
        else:
            self.battery_percent = None

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


def _localized_device_text(value: str, text: Mapping[str, object]) -> str:
    key = DEVICE_TEXT_KEYS.get(value)
    return str(text.get(key, value)) if key is not None else value


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
    image.alpha_composite(
        rotated,
        (x, max(6, (header_height - rotated.height) // 2 + 5)),
    )


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
    # The physical 240 px panel needs the reviewed 1.2x larger header controls.
    small = _font(12, bold=True)
    large = _font(14, bold=True)
    glyph_top = y + 3
    label_box = draw.textbbox((0, 0), label, font=small)
    value_box = draw.textbbox((0, 0), value, font=large)
    draw.text(
        (x, glyph_top - label_box[1]),
        label,
        font=small,
        fill=(128, 140, 145),
    )
    draw.text(
        (x + 34, glyph_top - value_box[1]),
        value,
        font=large,
        fill=accent,
    )


def _draw_menu_heading(
    draw: ImageDraw.ImageDraw,
    title: str,
    top: int,
    accent: tuple[int, int, int],
) -> None:
    font = _font(20, bold=True)
    fitted = _fit_text(draw, title, font, WIDTH - 76)
    draw.text((14, top + 4), fitted, font=font, fill=accent)


def _draw_back_or_ptt(
    draw: ImageDraw.ImageDraw,
    accent: tuple[int, int, int],
    ptt_active: bool,
    content_top: int,
) -> None:
    badge_left = 188
    badge_top = content_top + 5
    badge_right = WIDTH + 8
    badge_bottom = badge_top + 30
    if ptt_active:
        draw.rounded_rectangle(
            (badge_left, badge_top, badge_right, badge_bottom),
            radius=9,
            fill=(207, 38, 49),
        )
        draw.rectangle((198, badge_top, badge_right, badge_bottom), fill=(207, 38, 49))
        font = _font(12, bold=True)
        bounds = draw.textbbox((0, 0), "PTT", font=font)
        draw.text(
            (213 - (bounds[2] - bounds[0]) / 2, badge_top + 7),
            "PTT",
            font=font,
            fill=(255, 255, 255),
        )
        return
    background = (6, 12, 15)
    draw.rounded_rectangle(
        (badge_left, badge_top, badge_right, badge_bottom),
        radius=9,
        fill=accent,
    )
    draw.rectangle((198, badge_top, badge_right, badge_bottom), fill=accent)
    draw.rounded_rectangle(
        (badge_left + 2, badge_top + 2, badge_right + 2, badge_bottom - 2),
        radius=7,
        fill=background,
    )
    draw.rectangle(
        (198, badge_top + 2, badge_right + 2, badge_bottom - 2),
        fill=background,
    )
    draw.polygon(
        (
            (202, badge_top + 15),
            (209, badge_top + 8),
            (209, badge_top + 12),
            (219, badge_top + 12),
            (219, badge_top + 18),
            (209, badge_top + 18),
            (209, badge_top + 22),
        ),
        fill=accent,
    )


def _draw_player_edge_glow(
    image: Image.Image,
    top: int,
    accent: tuple[int, int, int],
) -> None:
    """Glow inward from the physical player contour without a crisp line."""
    padding = 24
    outside_offset = 6
    left = padding - outside_offset
    right = padding + WIDTH - 1 + outside_offset
    bottom = padding + HEIGHT - 1 + outside_offset
    radius = DISPLAY_CORNER_RADIUS + outside_offset
    tangent_y = bottom - radius

    def draw_path(
        target: ImageDraw.ImageDraw,
        color: tuple[int, ...],
        width: int,
    ) -> None:
        glow_top = padding + top - outside_offset
        target.line((left, glow_top, right, glow_top), fill=color, width=width)
        target.line((left, glow_top, left, tangent_y), fill=color, width=width)
        target.arc(
            (left, bottom - 2 * radius, left + 2 * radius, bottom),
            90,
            180,
            fill=color,
            width=width,
        )
        target.line(
            (left + radius, bottom, right - radius, bottom),
            fill=color,
            width=width,
        )
        target.arc(
            (right - 2 * radius, bottom - 2 * radius, right, bottom),
            0,
            90,
            fill=color,
            width=width,
        )
        target.line((right, tangent_y, right, glow_top), fill=color, width=width)

    # Combine a broad halo with a tighter bright halo. Both sources are
    # blurred before cropping, so the stronger effect still has no solid line.
    def blurred_pass(alpha: int, width: int, blur_radius: int) -> Image.Image:
        glow = Image.new(
            "RGBA",
            (WIDTH + 2 * padding, HEIGHT + 2 * padding),
            (0, 0, 0, 0),
        )
        draw_path(ImageDraw.Draw(glow), (*accent, alpha), width)
        blurred = glow.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        return blurred.crop((padding, padding, padding + WIDTH, padding + HEIGHT))

    broad = blurred_pass(alpha=220, width=21, blur_radius=10)
    tight = blurred_pass(alpha=245, width=11, blur_radius=4)
    visible = Image.alpha_composite(broad, tight)
    panel_mask = Image.new("L", (WIDTH, HEIGHT), 0)
    ImageDraw.Draw(panel_mask).rounded_rectangle(
        (0, 0, WIDTH - 1, HEIGHT - 1),
        radius=DISPLAY_CORNER_RADIUS,
        fill=255,
    )
    content_mask = Image.new("L", (WIDTH, HEIGHT), 0)
    ImageDraw.Draw(content_mask).rectangle((0, top, WIDTH - 1, HEIGHT - 1), fill=255)
    panel_mask = ImageChops.multiply(panel_mask, content_mask)
    # The real panel preview showed excessive light pooling in the two lower
    # curves. Attenuate only those corner zones while preserving the strong
    # straight-edge glow that gives the frame its useful depth.
    corner_balance = Image.new("L", (WIDTH, HEIGHT), 255)
    corner_draw = ImageDraw.Draw(corner_balance)
    corner_draw.rectangle((0, HEIGHT - 62, 61, HEIGHT - 1), fill=135)
    corner_draw.rectangle((WIDTH - 62, HEIGHT - 62, WIDTH - 1, HEIGHT - 1), fill=135)
    corner_balance = corner_balance.filter(ImageFilter.GaussianBlur(radius=10))
    alpha = ImageChops.multiply(visible.getchannel("A"), panel_mask)
    visible.putalpha(ImageChops.multiply(alpha, corner_balance))
    image.alpha_composite(visible)


def _draw_main_menu_items(
    draw: ImageDraw.ImageDraw,
    state: DeviceUiState,
    text: Mapping[str, object],
    content_top: int,
) -> None:
    visible_rows = 5
    start = max(
        0,
        min(
            state.menu_selection - visible_rows // 2,
            len(MAIN_MENU_ITEMS) - visible_rows,
        ),
    )
    font = _font(14, bold=True)
    row_top = content_top + 33
    for row, key in enumerate(MAIN_MENU_ITEMS[start : start + visible_rows]):
        index = start + row
        y = row_top + row * 31
        selected = index == state.menu_selection
        if selected:
            draw.rounded_rectangle(
                (11, y - 2, 229, y + 24),
                radius=6,
                fill=(42, 34, 13),
                outline=state.accent,
                width=2,
            )
            draw.polygon(
                ((18, y + 6), (24, y + 11), (18, y + 16)),
                fill=state.accent,
            )
        label = _fit_text(draw, str(text[key]), font, 191)
        draw.text(
            (31, y + 2),
            label,
            font=font,
            fill=(250, 250, 248) if selected else (178, 187, 189),
        )
    if start > 0:
        draw.polygon(((235, 124), (231, 130), (239, 130)), fill=state.accent)
    if start + visible_rows < len(MAIN_MENU_ITEMS):
        draw.polygon(((231, 264), (239, 264), (235, 270)), fill=state.accent)


def _draw_hotspot_setup(
    draw: ImageDraw.ImageDraw,
    state: DeviceUiState,
    text: Mapping[str, object],
    content_top: int,
) -> None:
    heading_font = _font(18, bold=True)
    label_font = _font(8, bold=True)
    value_font = _font(12, bold=True)
    url_font = _font(11, bold=True)
    draw.text(
        (14, content_top + 7),
        _fit_text(draw, str(text["wifi_setup"]), heading_font, 212),
        font=heading_font,
        fill=state.accent,
    )
    rows = (
        (content_top + 37, str(text["wifi_name"]), state.hotspot_ssid, value_font),
        (content_top + 86, str(text["wifi_password"]), state.hotspot_passphrase, value_font),
        (content_top + 135, str(text["wifi_open"]), state.hotspot_url, url_font),
    )
    for top, label, value, font in rows:
        draw.text((15, top), label, font=label_font, fill=(128, 140, 145))
        draw.rounded_rectangle(
            (13, top + 13, 226, top + 42),
            radius=7,
            fill=(13, 25, 28),
            outline=(75, 92, 96),
            width=1,
        )
        draw.text(
            (21, top + 20),
            _fit_text(draw, value, font, 196),
            font=font,
            fill=(245, 248, 249),
        )


def _media_mask(size: tuple[int, int]) -> Image.Image:
    """Return small top corners and panel-matched lower display corners."""
    width, height = size
    mask = Image.new("L", size, 0)
    shape = ImageDraw.Draw(mask)
    bottom_radius = min(DISPLAY_CORNER_RADIUS, width // 2, height // 2)
    top_radius = min(MEDIA_TOP_RADIUS, width // 2, height // 2)
    shape.rounded_rectangle(
        (0, 0, width - 1, height - 1),
        radius=bottom_radius,
        fill=255,
    )
    shape.rectangle(
        (0, top_radius, width - 1, height - bottom_radius),
        fill=255,
    )
    shape.rounded_rectangle(
        (0, 0, width - 1, min(height - 1, top_radius * 2)),
        radius=top_radius,
        fill=255,
    )
    return mask


def _fill_media_shape(
    image: Image.Image,
    bounds: tuple[int, int, int, int],
    color: tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = bounds
    size = (x1 - x0 + 1, y1 - y0 + 1)
    image.paste((*color, 255), (x0, y0, x1 + 1, y1 + 1), _media_mask(size))


def _outline_media_shape(
    image: Image.Image,
    bounds: tuple[int, int, int, int],
    color: tuple[int, int, int],
) -> None:
    x0, y0, x1, y1 = bounds
    size = (x1 - x0 + 1, y1 - y0 + 1)
    outer = _media_mask(size)
    inner_shape = _media_mask((size[0] - 2, size[1] - 2))
    inner = Image.new("L", size, 0)
    inner.paste(inner_shape, (1, 1))
    border = ImageChops.subtract(outer, inner)
    image.paste((*color, 255), (x0, y0, x1 + 1, y1 + 1), border)


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
    if state.menu_open:
        right_action = "OK"
    elif state.service in {"RADIO", "DMR", "PLAYER"}:
        right_action = str(text["pause"] if state.playing else text["play"])
    else:
        right_action = str(text["info"])

    header_height = 40
    draw.rectangle((0, 0, WIDTH - 1, 39), fill=(2, 5, 7), outline=(35, 47, 51))
    draw.line((17, 19, 222, 19), fill=(25, 35, 39), width=1)
    draw.line((119, 2, 119, 37), fill=(25, 35, 39), width=1)
    _vertical_label(image, left_action, 8, clockwise=False, header_height=header_height)
    _vertical_label(image, right_action, 221, clockwise=False, header_height=header_height)
    _control_value(draw, 19, 1, str(controls[0]), f"{state.volume}%", accent)
    _control_value(draw, 19, 20, str(controls[1]), str(state.squelch), accent)
    _control_value(draw, 122, 1, str(controls[2]), f"{state.channel:03d}", accent)
    service_label = str(text["weather_service"]) if state.service == "WEATHER" else state.service
    _control_value(draw, 122, 20, str(controls[3]), service_label, accent)

    draw.rectangle((0, 40, WIDTH - 1, 62), fill=(12, 20, 23))
    _wifi_icon(draw, 5, 45, accent)
    # SSID and IP use the same requested 1.2x scale while keeping the clock fixed.
    status_font = _font(8)
    draw.text((22, 41), _fit_text(draw, state.wifi_label, status_font, 67), font=status_font, fill=(213, 222, 224))
    draw.text((22, 51), _fit_text(draw, state.ip_address, status_font, 73), font=status_font, fill=(112, 130, 134))
    clock = state.timestamp.strftime("%H:%M")
    clock_font = _font(15, bold=True)
    clock_width = draw.textbbox((0, 0), clock, font=clock_font)[2]
    draw.text(((WIDTH - clock_width) / 2, 41), clock, font=clock_font, fill=(235, 240, 241))
    _battery(draw, 207, 47, state.battery_percent, accent)
    if state.battery_percent is not None:
        pct = f"{state.battery_percent}%"
        pct_font = _font(9, bold=True)
        width = draw.textbbox((0, 0), pct, font=pct_font)[2]
        draw.text((203 - width, 47), pct, font=pct_font, fill=(213, 222, 224))

    content_top = 63
    draw.rectangle((0, content_top, WIDTH - 1, HEIGHT - 1), fill=(6, 12, 15))
    if state.hotspot_active:
        draw.rectangle((0, content_top, 3, HEIGHT - 1), fill=accent)
        _draw_hotspot_setup(draw, state, text, content_top)
        return image.convert("RGB")
    if state.menu_open:
        draw.rectangle((0, content_top, 3, HEIGHT - 1), fill=accent)
        menu_key = state.menu_kind or "main_menu"
        menu_title = str(text.get(menu_key, text["main_menu"]))
        _draw_menu_heading(draw, menu_title, content_top, accent)
        _draw_back_or_ptt(draw, accent, state.ptt_active, content_top)
        if menu_key == "main_menu":
            _draw_main_menu_items(draw, state, text, content_top)
        return image.convert("RGB")

    if state.service in {"SYSTEM", "REC"}:
        draw.rectangle((0, content_top, 3, HEIGHT - 1), fill=accent)
        heading_font = _font(19, bold=True)
        body_font = _font(13, bold=True)
        small_font = _font(10)
        draw.text(
            (14, content_top + 9),
            _fit_text(draw, state.source, heading_font, 212),
            font=heading_font,
            fill=(245, 248, 249),
        )
        draw.line((14, content_top + 40, 226, content_top + 40), fill=(52, 67, 71), width=1)
        draw.multiline_text(
            (14, content_top + 56),
            _fit_text(draw, _localized_device_text(state.title, text), body_font, 208),
            font=body_font,
            fill=accent,
            spacing=4,
        )
        draw.multiline_text(
            (14, content_top + 100),
            _fit_text(
                draw,
                _localized_device_text(state.subtitle, text),
                small_font,
                208,
            ),
            font=small_font,
            fill=(178, 187, 189),
            spacing=4,
        )
        return image.convert("RGB")

    _draw_player_edge_glow(image, content_top, accent)
    draw = ImageDraw.Draw(image)

    station_font = _font(18, bold=True)
    station = _fit_text(draw, state.source, station_font, 164)
    draw.text((14, content_top + 4), station, font=station_font, fill=(245, 248, 249))

    if state.service == "WEATHER":
        credit_font = _font(8, bold=True)
        credit = _fit_text(draw, state.title, credit_font, 128)
        credit_width = draw.textbbox((0, 0), credit, font=credit_font)[2]
        draw.text((226 - credit_width, content_top + 25), credit, font=credit_font, fill=accent)
        weather_bounds = (
            MEDIA_MARGIN,
            content_top + 40,
            WIDTH - 1 - MEDIA_MARGIN,
            HEIGHT - 1 - MEDIA_MARGIN,
        )
        weather_xy = (weather_bounds[0] + 1, weather_bounds[1] + 1)
        weather_size = (
            weather_bounds[2] - weather_bounds[0] - 1,
            weather_bounds[3] - weather_bounds[1] - 1,
        )
        if artwork is not None:
            weather = ImageOps.contain(
                artwork.convert("RGB"),
                weather_size,
                method=Image.Resampling.LANCZOS,
            )
            weather_x = weather_xy[0] + (weather_size[0] - weather.width) // 2
            weather_y = weather_xy[1] + (weather_size[1] - weather.height) // 2
            weather_mask = _media_mask(weather.size)
            image.paste(weather, (weather_x, weather_y), weather_mask)
        else:
            _fill_media_shape(image, weather_bounds, (13, 31, 35))
            loading_font = _font(13, bold=True)
            loading = _fit_text(
                draw,
                _localized_device_text(state.subtitle, text),
                loading_font,
                180,
            )
            bounds = draw.textbbox((0, 0), loading, font=loading_font)
            draw.text(
                (120 - (bounds[2] - bounds[0]) / 2, content_top + 107),
                loading,
                font=loading_font,
                fill=(196, 207, 209),
            )
        _outline_media_shape(image, weather_bounds, (75, 92, 96))
        return image.convert("RGB")

    # Radio/player artwork spans the content width. ImageOps.fit deliberately
    # crops the lower edge instead of squeezing a square logo into a side tile.
    media_bounds = (
        MEDIA_MARGIN,
        content_top + 42,
        WIDTH - 1 - MEDIA_MARGIN,
        HEIGHT - 1 - MEDIA_MARGIN,
    )
    tile_xy = (media_bounds[0] + 1, media_bounds[1] + 1)
    tile_size = (
        media_bounds[2] - media_bounds[0] - 1,
        media_bounds[3] - media_bounds[1] - 1,
    )
    if artwork is not None:
        tile = ImageOps.fit(
            artwork.convert("RGB"),
            tile_size,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.35),
        )
        mask = _media_mask(tile_size)
        image.paste(tile, tile_xy, mask)
    else:
        _fill_media_shape(image, media_bounds, (13, 31, 35))
        initials = "".join(part[:1] for part in state.source.split()[:2]).upper() or "OR"
        initials_font = _font(34, bold=True)
        bounds = draw.textbbox((0, 0), initials, font=initials_font)
        draw.text(
            (120 - (bounds[2] - bounds[0]) / 2, content_top + 125 - (bounds[3] - bounds[1]) / 2),
            initials,
            font=initials_font,
            fill=accent,
        )
    _outline_media_shape(image, media_bounds, (75, 92, 96))

    title = (
        state.title
        if state.title.casefold() != state.source.casefold()
        else _localized_device_text(state.subtitle, text)
    )
    detail_font = _font(9, bold=True)
    draw.text(
        (14, content_top + 27),
        _fit_text(draw, title, detail_font, 164),
        font=detail_font,
        fill=(196, 207, 209),
    )

    if state.ptt_active:
        _draw_back_or_ptt(draw, accent, True, content_top)
    else:
        # Exactly one compact metadata block high (station + track), never taller.
        draw.ellipse((200, content_top + 5, 234, content_top + 39), fill=(12, 23, 27), outline=accent, width=2)
        if state.playing:
            draw.rectangle((211, content_top + 15, 214, content_top + 29), fill=accent)
            draw.rectangle((220, content_top + 15, 223, content_top + 29), fill=accent)
        else:
            draw.polygon(((211, content_top + 13), (211, content_top + 31), (225, content_top + 22)), fill=accent)
    if state.recording:
        draw.ellipse((190, content_top + 4, 198, content_top + 12), fill=(255, 78, 78))
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
