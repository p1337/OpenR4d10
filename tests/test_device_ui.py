from datetime import datetime
from io import BytesIO
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from openr4d10.adapters import WhisplayDisplay
from openr4d10.device_ui import (
    DEFAULT_ACCENT,
    DeviceUiState,
    HEIGHT,
    MAIN_MENU_ITEMS,
    WIDTH,
    _display_text,
    image_to_rgb565,
    render_device_ui,
)
from openr4d10.input_events import Control, InputEvent
from openr4d10.models import Frame
from openr4d10.whisplay import WhisplayPanel


class DeviceUiTests(unittest.TestCase):
    def _drawn_text(self, state: DeviceUiState, artwork=None) -> list[str]:
        drawn: list[str] = []
        original_text = ImageDraw.ImageDraw.text
        original_multiline = ImageDraw.ImageDraw.multiline_text

        def capture_text(draw, xy, text, *args, **kwargs):
            drawn.append(str(text))
            return original_text(draw, xy, text, *args, **kwargs)

        def capture_multiline(draw, xy, text, *args, **kwargs):
            drawn.append(str(text))
            return original_multiline(draw, xy, text, *args, **kwargs)

        with (
            patch.object(ImageDraw.ImageDraw, "text", new=capture_text),
            patch.object(
                ImageDraw.ImageDraw,
                "multiline_text",
                new=capture_multiline,
            ),
        ):
            render_device_ui(state, artwork)
        return drawn

    def test_renderer_produces_native_portrait_frame(self) -> None:
        state = DeviceUiState(
            volume=42,
            squelch=6,
            channel=17,
            service_index=3,
            ip_address="192.168.1.64",
            battery_percent=81,
            source="BrandMeister",
            title="Talkgroup 262",
            subtitle="Listening",
            timestamp=datetime(2026, 10, 30, 14, 5),
        )
        image = render_device_ui(state)
        self.assertEqual(image.size, (WIDTH, HEIGHT))
        self.assertEqual(image.mode, "RGB")
        self.assertNotEqual(image.getpixel((2, 120)), image.getpixel((120, 120)))

    def test_weather_frame_uses_the_large_native_image_area(self) -> None:
        state = DeviceUiState(
            service_index=2,
            source="Deutschland",
            title="DWD / EUMETSAT",
            image_file="weather-dwd-deutschland-20261031T060000Z.jpg",
        )
        frame = Image.new("RGB", (480, 360), (40, 90, 130))
        image = render_device_ui(state, frame)
        self.assertEqual(image.getpixel((120, 180)), (40, 90, 130))
        self.assertEqual(image.getpixel((2, 180)), DEFAULT_ACCENT)

    def test_radio_artwork_replaces_the_local_initials_tile(self) -> None:
        state = DeviceUiState(source="SWR3", service_index=1, playing=True)
        artwork = Image.new("RGB", (32, 32), (220, 20, 40))
        image = render_device_ui(state, artwork)
        self.assertEqual(image.getpixel((50, 180)), (220, 20, 40))
        self.assertEqual(image.getpixel((140, 240)), (220, 20, 40))

    def test_compact_header_and_localized_labels(self) -> None:
        self.assertEqual(_display_text("en")["controls"], ("VOL", "SQL", "CH", "SRV"))
        self.assertEqual(_display_text("de")["main_menu"], "HAUPTMENÜ")
        self.assertEqual(_display_text("pl")["main_menu"], "MENU GŁÓWNE")
        self.assertEqual(_display_text("fr")["main_menu"], "MENU PRINCIPAL")
        self.assertEqual(_display_text("es")["main_menu"], "MENÚ PRINCIPAL")
        self.assertEqual(DEFAULT_ACCENT, (253, 184, 19))
        image = render_device_ui(DeviceUiState())
        self.assertEqual(image.getpixel((100, 60)), (12, 20, 23))

    def test_date_and_redundant_player_text_are_not_rendered(self) -> None:
        first = DeviceUiState(
            service_index=1,
            playing=False,
            timestamp=datetime(2026, 10, 30, 14, 5),
        )
        second = DeviceUiState(
            service_index=1,
            playing=False,
            timestamp=datetime(2027, 6, 12, 14, 5),
        )
        self.assertEqual(render_device_ui(first).tobytes(), render_device_ui(second).tobytes())
        drawn = self._drawn_text(first)
        self.assertNotIn("PAUSED", drawn)
        self.assertNotIn("READY", drawn)
        self.assertNotIn("OpenR4d10", drawn)
        self.assertEqual(drawn.count("RADIO"), 1)

    def test_main_menu_hides_complete_player_and_uses_localized_heading(self) -> None:
        state = DeviceUiState(
            source="SWR3",
            title="Current programme",
            service_index=1,
            playing=True,
            menu_open=True,
            menu_kind="main_menu",
            language="de",
        )
        artwork = Image.new("RGB", (32, 32), (220, 20, 40))
        image = render_device_ui(state, artwork)
        colors = image.getcolors(maxcolors=WIDTH * HEIGHT)
        self.assertIsNotNone(colors)
        self.assertNotIn((220, 20, 40), {color for _, color in colors or []})
        drawn = self._drawn_text(state, artwork)
        self.assertIn("HAUPTMENÜ", drawn)
        for label in ("ANZEIGE", "AKZENTFARBE", "WLAN", "DIENSTMODULE"):
            self.assertIn(label, drawn)
        self.assertNotIn("SWR3", drawn)
        self.assertNotIn("Current programme", drawn)

    def test_main_menu_scroll_select_and_ptt_back_navigation(self) -> None:
        state = DeviceUiState(channel=3, language="de")
        state.apply(InputEvent(Control.LEFT_PRESS))
        state.apply(InputEvent(Control.RIGHT_OUTER, steps=4))
        self.assertEqual(state.channel, 3)
        self.assertEqual(state.selected_menu_item, "service_store")
        self.assertEqual(state.menu_selection, 4)
        drawn = self._drawn_text(state)
        self.assertIn("DIENST-STORE", drawn)

        state.apply(InputEvent(Control.RIGHT_PRESS))
        self.assertEqual(state.menu_kind, "service_store")
        self.assertTrue(state.menu_open)
        state.apply(InputEvent(Control.PTT, active=True))
        self.assertEqual(state.menu_kind, "main_menu")
        self.assertEqual(state.menu_selection, 4)
        state.apply(InputEvent(Control.PTT, active=False))
        self.assertTrue(state.menu_open)
        state.apply(InputEvent(Control.PTT, active=True))
        self.assertFalse(state.menu_open)

    def test_explicit_ptt_context_owns_button_and_uses_edge_badge(self) -> None:
        state = DeviceUiState(
            menu_open=True,
            menu_kind="main_menu",
            ptt_context_active=True,
        )
        state.apply(InputEvent(Control.PTT, active=True))
        self.assertTrue(state.ptt_active)
        self.assertEqual(state.menu_kind, "main_menu")
        image = render_device_ui(state)
        self.assertEqual(image.getpixel((239, 100)), (207, 38, 49))
        state.apply(InputEvent(Control.PTT, active=False))
        self.assertFalse(state.ptt_active)
        self.assertTrue(state.menu_open)

    def test_menu_back_arrow_uses_accent_below_battery(self) -> None:
        state = DeviceUiState(menu_open=True, menu_kind="main_menu")
        image = render_device_ui(state)
        self.assertEqual(image.getpixel((203, 104)), state.accent)
        self.assertEqual(len(MAIN_MENU_ITEMS), 10)

    def test_play_control_is_below_battery_and_footer_is_empty(self) -> None:
        state = DeviceUiState(playing=True)
        image = render_device_ui(state)
        self.assertEqual(image.getpixel((206, 88)), state.accent)
        self.assertEqual(image.getpixel((220, 247)), (6, 12, 15))

    def test_rgb565_uses_big_endian_wire_order(self) -> None:
        for color, expected in (
            ((255, 0, 0), b"\xF8\x00"),
            ((0, 255, 0), b"\x07\xE0"),
            ((0, 0, 255), b"\x00\x1F"),
        ):
            with self.subTest(color=color):
                frame = Image.new("RGB", (WIDTH, HEIGHT), color)
                encoded = image_to_rgb565(frame)
                self.assertEqual(len(encoded), WIDTH * HEIGHT * 2)
                self.assertEqual(encoded[:2], expected)

    def test_encoder_events_are_hardware_independent(self) -> None:
        state = DeviceUiState(volume=50, squelch=4, channel=10)
        state.apply(InputEvent(Control.LEFT_OUTER, steps=3))
        state.apply(InputEvent(Control.LEFT_INNER, steps=-2))
        state.apply(InputEvent(Control.RIGHT_OUTER, steps=5))
        state.apply(InputEvent(Control.RIGHT_INNER, steps=1))
        state.apply(InputEvent(Control.RIGHT_PRESS))
        state.ptt_context_active = True
        state.apply(InputEvent(Control.PTT, active=True))
        self.assertEqual(state.volume, 80)
        self.assertEqual(state.squelch, 2)
        self.assertEqual(state.channel, 15)
        self.assertEqual(state.service, "RADIO")
        self.assertTrue(state.playing)
        self.assertTrue(state.ptt_active)
        state.apply(InputEvent(Control.PTT, active=False))
        self.assertFalse(state.ptt_active)

    def test_receiver_service_selects_matching_header_mode(self) -> None:
        state = DeviceUiState()
        state.update_from_frame(
            Frame(
                screen="dashboard",
                title="Radio",
                fields={"receiver": {"service": "RADIO", "playing": True}},
            )
        )
        self.assertEqual(state.service, "RADIO")
        self.assertTrue(state.playing)
        self.assertEqual(state.right_action, "PAUSE")

        state.update_from_frame(
            Frame(
                screen="dashboard",
                title="Radio",
                fields={
                    "receiver": {
                        "service": "RADIO",
                        "station": "sunshine live",
                        "preset_id": "sunshine_live",
                        "channel": 2,
                        "volume": 73,
                        "playing": True,
                    }
                },
            )
        )
        self.assertEqual(state.source, "sunshine live")
        self.assertEqual(state.preset_id, "sunshine_live")
        self.assertEqual(state.channel, 2)
        self.assertEqual(state.volume, 73)

        state.update_from_frame(
            Frame(
                screen="dashboard",
                title="Radio",
                fields={"ui": {"language": "pl-PL"}},
            )
        )
        self.assertEqual(state.language, "pl")

    def test_invalid_input_shapes_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            InputEvent(Control.LEFT_OUTER)
        with self.assertRaises(ValueError):
            InputEvent(Control.LEFT_PRESS, steps=1)
        with self.assertRaises(ValueError):
            InputEvent(Control.PTT)
        with self.assertRaises(ValueError):
            InputEvent(Control.RIGHT_PRESS, active=True)


class FakePanel:
    def __init__(self) -> None:
        self.frames: list[bytes] = []
        self.brightness: list[int] = []
        self.closed = False

    def show(self, frame: bytes) -> None:
        self.frames.append(frame)

    def set_brightness(self, brightness_percent: int) -> None:
        self.brightness.append(brightness_percent)

    def close(self) -> None:
        self.closed = True


class WhisplayDisplayTests(unittest.TestCase):
    def test_brightness_is_bounded_without_opening_hardware(self) -> None:
        panel = WhisplayPanel()
        panel.set_brightness(0)
        panel.set_brightness(100)
        for invalid in (-1, 101, True, 50.0):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                panel.set_brightness(invalid)  # type: ignore[arg-type]

    def test_brightness_uses_active_low_vendor_pwm_mapping(self) -> None:
        panel = WhisplayPanel()
        panel._backlight = object()  # Simulate the already requested GPIO line.
        with patch("openr4d10.whisplay._SoftPwm") as pwm:
            panel.set_brightness(35)
            self.assertEqual(pwm.call_args.args[1], 65)
            panel.set_brightness(80)
            pwm.return_value.set_duty_cycle.assert_called_once_with(20)

    def test_boot_animation_is_not_replaced_by_text_fallback(self) -> None:
        panel = FakePanel()
        display = WhisplayDisplay(panel=panel)  # type: ignore[arg-type]
        display.render(Frame(screen="boot", title="OpenR4d10"))
        self.assertEqual(panel.frames, [])

    def test_dashboard_frame_reaches_panel(self) -> None:
        panel = FakePanel()
        display = WhisplayDisplay(panel=panel)  # type: ignore[arg-type]
        display.render(
            Frame(
                screen="dashboard",
                title="OpenR4d10",
                body="Receiver ready",
                fields={
                    "receiver": {
                        "hostname": "OpenR4d10",
                        "ip_address": "192.168.1.64",
                    },
                    "power": {"battery_percent": 75},
                },
            )
        )
        self.assertEqual(len(panel.frames), 1)
        self.assertEqual(len(panel.frames[0]), WIDTH * HEIGHT * 2)
        display.close()
        self.assertTrue(panel.closed)

    def test_virtual_input_uses_the_native_display_state(self) -> None:
        panel = FakePanel()
        display = WhisplayDisplay(panel=panel)  # type: ignore[arg-type]
        display.render(Frame(screen="dashboard", title="OpenR4d10"))
        state = display.apply_input(InputEvent(Control.LEFT_OUTER, steps=4))
        self.assertEqual(state["volume"], 76)
        self.assertEqual(display.snapshot()["volume"], 76)
        self.assertEqual(len(panel.frames), 2)
        display.close()

    def test_native_screen_preview_uses_same_renderer(self) -> None:
        panel = FakePanel()
        display = WhisplayDisplay(panel=panel)  # type: ignore[arg-type]
        display.render(Frame(screen="dashboard", title="OpenR4d10"))
        payload = display.screen_png()
        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(Image.open(BytesIO(payload)).size, (WIDTH, HEIGHT))

    def test_display_brightness_reaches_panel_and_public_state(self) -> None:
        panel = FakePanel()
        display = WhisplayDisplay(panel=panel)  # type: ignore[arg-type]
        display.set_brightness(35)
        self.assertEqual(panel.brightness, [35])
        self.assertEqual(display.snapshot()["brightness_percent"], 35)


if __name__ == "__main__":
    unittest.main()
