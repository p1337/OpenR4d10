from datetime import datetime
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from PIL import Image, ImageDraw

from openr4d10.adapters import WhisplayDisplay
from openr4d10.device_ui import (
    DEFAULT_ACCENT,
    DeviceUiState,
    HEIGHT,
    MAIN_MENU_ITEMS,
    SERVICES,
    WIDTH,
    _display_text,
    _font,
    image_to_rgb565,
    render_device_ui,
)
from openr4d10.input_events import Control, InputEvent
from openr4d10.models import Frame
from openr4d10.whisplay import WhisplayPanel, _KernelPwmBacklight


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
        self.assertNotEqual(image.getpixel((5, 180)), (6, 12, 15))
        self.assertNotEqual(image.getpixel((5, 180)), DEFAULT_ACCENT)

    def test_radio_artwork_replaces_the_local_initials_tile(self) -> None:
        state = DeviceUiState(source="SWR3", service_index=1, playing=True)
        artwork = Image.new("RGB", (32, 32), (220, 20, 40))
        image = render_device_ui(state, artwork)
        self.assertNotEqual(image.getpixel((14, 106)), (220, 20, 40))
        self.assertEqual(image.getpixel((120, 106)), (220, 20, 40))
        self.assertEqual(image.getpixel((50, 180)), (220, 20, 40))
        self.assertEqual(image.getpixel((140, 240)), (220, 20, 40))
        self.assertEqual(image.getpixel((220, 240)), (220, 20, 40))

    def test_media_uses_tight_equal_margins_and_smaller_top_corners(self) -> None:
        color = (220, 20, 40)
        image = render_device_ui(
            DeviceUiState(source="SWR3", service_index=1),
            Image.new("RGB", (32, 32), color),
        )
        self.assertEqual(image.getpixel((8, 180)), color)
        self.assertEqual(image.getpixel((231, 180)), color)
        self.assertEqual(image.getpixel((120, 271)), color)
        self.assertNotEqual(image.getpixel((8, 106)), color)
        self.assertEqual(image.getpixel((20, 106)), color)
        self.assertNotEqual(image.getpixel((8, 271)), color)
        self.assertEqual(image.getpixel((50, 271)), color)

    def test_compact_header_and_localized_labels(self) -> None:
        self.assertEqual(_display_text("en")["controls"], ("VOL", "SQL", "CH", "SRV"))
        self.assertEqual(_display_text("de")["main_menu"], "HAUPTMENÜ")
        self.assertEqual(_display_text("pl")["main_menu"], "MENU GŁÓWNE")
        self.assertEqual(_display_text("fr")["main_menu"], "MENU PRINCIPAL")
        self.assertEqual(_display_text("es")["main_menu"], "MENÚ PRINCIPAL")
        self.assertEqual(DEFAULT_ACCENT, (253, 184, 19))
        image = render_device_ui(DeviceUiState())
        # Sample below the font bounding boxes so this remains independent of
        # platform-specific DejaVu glyph rasterisation.
        self.assertEqual(image.getpixel((100, 61)), (12, 20, 23))
        for corner in ((0, 0, 13, 6), (227, 0, 240, 6)):
            self.assertNotIn(
                (135, 143, 148),
                {color for _count, color in image.crop(corner).getcolors() or []},
            )

        with patch("openr4d10.device_ui._vertical_label") as vertical_label:
            render_device_ui(DeviceUiState())
        self.assertEqual(vertical_label.call_count, 2)
        self.assertEqual(
            [call.kwargs["clockwise"] for call in vertical_label.call_args_list],
            [False, False],
        )
        self.assertEqual(
            [call.args[2] for call in vertical_label.call_args_list],
            [8, 221],
        )

    def test_header_controls_and_network_text_use_requested_larger_fonts(self) -> None:
        sizes = {}
        positions = {}
        original_text = ImageDraw.ImageDraw.text

        def capture_text(draw, xy, text, *args, **kwargs):
            font = kwargs.get("font")
            sizes.setdefault(str(text), getattr(font, "size", None))
            positions.setdefault(str(text), (xy, font))
            return original_text(draw, xy, text, *args, **kwargs)

        state = DeviceUiState(
            wifi_label="p1337",
            ip_address="192.168.1.64",
            battery_percent=87,
            language="de",
        )
        with patch.object(ImageDraw.ImageDraw, "text", new=capture_text):
            render_device_ui(state)
        self.assertEqual(sizes["LAU"], 12)
        self.assertEqual(sizes["30%"], 14)
        self.assertEqual(sizes["p1337"], 8)
        self.assertEqual(sizes["192.168.1.64"], 8)
        self.assertGreaterEqual(sizes["87%"], sizes["p1337"])
        measure = ImageDraw.Draw(Image.new("RGB", (100, 100)))
        for label, value in (("LAU", "30%"), ("SQL", "5"), ("KAN", "001"), ("DST", "SYSTEM")):
            label_xy, label_font = positions[label]
            value_xy, value_font = positions[value]
            label_top = measure.textbbox(label_xy, label, font=label_font)[1]
            value_top = measure.textbbox(value_xy, value, font=value_font)[1]
            self.assertEqual(label_top, value_top)
        self.assertLess(positions["LAU"][0][0], positions["30%"][0][0])
        self.assertEqual(positions["LAU"][0][0], 22)
        self.assertEqual(positions["SQL"][0][0], 22)
        self.assertEqual(positions["30%"][0][0], 53)
        self.assertEqual(positions["5"][0][0], 53)
        self.assertLess(positions["001"][0][0], positions["KAN"][0][0])
        self.assertLess(positions["SYSTEM"][0][0], positions["DST"][0][0])
        for label in ("KAN", "DST"):
            label_xy, label_font = positions[label]
            label_right = measure.textbbox(label_xy, label, font=label_font)[2]
            self.assertEqual(label_right, 212)

    def test_dmr_header_shows_real_encoder_functions_and_talkgroup(self) -> None:
        labels = []
        original_text = ImageDraw.ImageDraw.text

        def capture_text(draw, xy, text, *args, **kwargs):
            labels.append(str(text))
            return original_text(draw, xy, text, *args, **kwargs)

        state = DeviceUiState(
            service_index=SERVICES.index("DMR"),
            channel=27,
            channel_label="262",
            language="de",
        )
        with patch.object(ImageDraw.ImageDraw, "text", new=capture_text):
            render_device_ui(state)
        for expected in ("LAU", "SPR", "25", "TG", "262", "DST", "DMR", "AN"):
            self.assertIn(expected, labels)
        self.assertNotIn("SQL", labels)
        self.assertNotIn("KAN", labels)

        labels.clear()
        state.dmr_selected_enabled = True
        with patch.object(ImageDraw.ImageDraw, "text", new=capture_text):
            render_device_ui(state)
        self.assertIn("AUS", labels)

    def test_dmr_view_pins_active_call_above_scrollable_catalog_rows(self) -> None:
        state = DeviceUiState(
            service_index=SERVICES.index("DMR"),
            source="TG 262",
            title="DL1TEST",
            playing=True,
            dmr_catalog_position=2,
            dmr_catalog_count=1700,
            activity_rows=[
                {
                    "talkgroup": 262,
                    "name": "Germany",
                    "country_code": "DE",
                    "active": True,
                    "source": 2621234,
                    "alias": "DL1TEST",
                },
            ],
            dmr_catalog_rows=[
                {
                    "talkgroup": 91,
                    "name": "Worldwide",
                    "country_code": "",
                    "enabled": True,
                    "selected": False,
                    "position": 1,
                },
                {
                    "talkgroup": 3100,
                    "name": "Inactive example",
                    "country_code": "US",
                    "enabled": False,
                    "selected": True,
                    "position": 2,
                },
            ],
        )
        drawn = self._drawn_text(state)
        self.assertIn("TG 262", drawn)
        self.assertTrue(any("DL1TEST" in value for value in drawn))
        self.assertIn("TG 91  Worldwide", drawn)
        self.assertIn("TG 3100  Inactive example", drawn)
        self.assertIn("2/1700", drawn)
        self.assertIn("ON", drawn)
        self.assertIn("OFF", drawn)
        self.assertNotIn("PAUSE", drawn)

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

    def test_device_language_localizes_fixed_player_help_text(self) -> None:
        state = DeviceUiState(
            source="SWR3",
            title="SWR3",
            subtitle="Play starts this audio service",
            service_index=1,
            language="de",
        )
        drawn = self._drawn_text(state)
        self.assertTrue(any(value.startswith("Mit PLAY") for value in drawn))
        self.assertNotIn("Play starts this audio service", drawn)

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

    def test_hotspot_setup_replaces_player_and_keeps_secret_out_of_public_state(self) -> None:
        state = DeviceUiState(
            wifi_label="OpenR4d10-Setup-8FDE",
            hotspot_active=True,
            hotspot_ssid="OpenR4d10-Setup-8FDE",
            hotspot_passphrase="LocalOnlyA1B2C3D4",
            hotspot_url="http://10.42.0.1/",
            language="de",
        )
        drawn = self._drawn_text(state)
        self.assertIn("WLAN-EINRICHTUNG", drawn)
        self.assertIn("OpenR4d10-Setup-8FDE", drawn)
        self.assertIn("LocalOnlyA1B2C3D4", drawn)
        self.assertIn("http://10.42.0.1/", drawn)
        self.assertNotIn("hotspot_passphrase", state.public_state())
        self.assertNotIn("LocalOnlyA1B2C3D4", json.dumps(state.public_state()))

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
        self.assertEqual(image.getpixel((239, 87)), (207, 38, 49))
        state.apply(InputEvent(Control.PTT, active=False))
        self.assertFalse(state.ptt_active)
        self.assertTrue(state.menu_open)

    def test_menu_back_arrow_uses_accent_below_battery(self) -> None:
        state = DeviceUiState(menu_open=True, menu_kind="main_menu")
        image = render_device_ui(state)
        self.assertEqual(image.getpixel((188, 83)), state.accent)
        self.assertEqual(image.getpixel((190, 83)), (6, 12, 15))
        self.assertEqual(image.getpixel((203, 83)), state.accent)
        self.assertEqual(image.getpixel((239, 83)), (6, 12, 15))
        self.assertEqual(len(MAIN_MENU_ITEMS), 10)

    def test_player_accent_rail_glows_but_menu_rail_stays_crisp(self) -> None:
        player = render_device_ui(DeviceUiState(service_index=1))
        menu = render_device_ui(DeviceUiState(menu_open=True, menu_kind="main_menu"))
        self.assertNotEqual(player.getpixel((7, 180)), (6, 12, 15))
        self.assertEqual(menu.getpixel((7, 180)), (6, 12, 15))

    def test_permanent_player_glow_has_no_crisp_line_and_follows_round_corners(self) -> None:
        image = render_device_ui(DeviceUiState(service_index=1))
        background = (6, 12, 15)
        for point in ((0, 180), (4, 180), (120, 279), (239, 180), (235, 180)):
            pixel = image.getpixel(point)
            self.assertNotEqual(pixel, background)
            self.assertNotEqual(pixel, DEFAULT_ACCENT)
            self.assertGreaterEqual(
                sum(abs(channel - base) for channel, base in zip(pixel, background)),
                90,
            )
        for clipped_corner in ((0, HEIGHT - 1), (WIDTH - 1, HEIGHT - 1)):
            self.assertEqual(image.getpixel(clipped_corner), background)
        for top_point in ((120, 63), (120, 71)):
            pixel = image.getpixel(top_point)
            self.assertNotEqual(pixel, background)
            self.assertNotEqual(pixel, DEFAULT_ACCENT)
            self.assertGreaterEqual(
                sum(abs(channel - base) for channel, base in zip(pixel, background)),
                35,
            )
        self.assertLess(
            sum(image.getpixel((60, HEIGHT - 1))),
            sum(image.getpixel((120, HEIGHT - 1))),
        )

    def test_play_control_is_below_battery_and_footer_is_empty(self) -> None:
        state = DeviceUiState(playing=True, service_index=1)
        image = render_device_ui(state)
        self.assertEqual(image.getpixel((217, 68)), state.accent)
        self.assertEqual(image.getpixel((234, 85)), state.accent)
        self.assertNotEqual(image.getpixel((235, 85)), state.accent)
        self.assertNotEqual(image.getpixel((220, 270)), state.accent)

    def test_clock_is_centered_on_the_full_display_width(self) -> None:
        positions: dict[str, tuple[float, float]] = {}
        original_text = ImageDraw.ImageDraw.text

        def capture_text(draw, xy, text, *args, **kwargs):
            positions[str(text)] = xy
            return original_text(draw, xy, text, *args, **kwargs)

        state = DeviceUiState(timestamp=datetime(2026, 10, 31, 14, 5))
        with patch.object(ImageDraw.ImageDraw, "text", new=capture_text):
            render_device_ui(state)
        clock_font = positions["14:05"]
        image = Image.new("RGB", (WIDTH, HEIGHT))
        draw = ImageDraw.Draw(image)
        width = draw.textbbox((0, 0), "14:05", font=_font(15, bold=True))[2]
        self.assertAlmostEqual(clock_font[0] + width / 2, WIDTH / 2)

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
        self.button_callback = None
        self.closed = False

    def show(self, frame: bytes) -> None:
        self.frames.append(frame)

    def set_brightness(self, brightness_percent: int) -> None:
        self.brightness.append(brightness_percent)

    def set_button_callback(self, callback) -> None:
        self.button_callback = callback

    def emit_button(self, active: bool) -> None:
        if self.button_callback is not None:
            self.button_callback(active)

    def close(self) -> None:
        self.closed = True


class WhisplayDisplayTests(unittest.TestCase):
    def test_physical_button_monitor_debounces_active_high_edges(self) -> None:
        class FakeButton:
            def __init__(self) -> None:
                self.value = 0
                self.released = False

            def get_value(self, _offset):
                return self.value

            def release(self) -> None:
                self.released = True

        panel = WhisplayPanel()
        button = FakeButton()
        panel._button = button
        panel._value_active = 1
        panel.BUTTON_POLL_SECONDS = 0.002
        panel.BUTTON_DEBOUNCE_SECONDS = 0.01
        events = []
        first_edge = threading.Event()
        second_edge = threading.Event()

        def received(active):
            events.append(active)
            (first_edge if len(events) == 1 else second_edge).set()

        panel.set_button_callback(received)
        panel._start_button_monitor()
        time.sleep(0.02)
        button.value = 1
        self.assertTrue(first_edge.wait(0.5))
        button.value = 0
        self.assertTrue(second_edge.wait(0.5))
        panel.close()

        self.assertEqual(events, [True, False])
        self.assertTrue(button.released)

    def test_physical_button_uses_verified_bcm17_and_logical_ptt_edges(self) -> None:
        self.assertEqual(WhisplayPanel.BUTTON_BCM, 17)
        panel = FakePanel()
        display = WhisplayDisplay(panel=panel)  # type: ignore[arg-type]
        events = []
        display.set_input_handler(events.append)

        panel.emit_button(True)
        panel.emit_button(False)

        self.assertEqual(
            [(event.control, event.active) for event in events],
            [(Control.PTT, True), (Control.PTT, False)],
        )
        display.close()
        self.assertIsNone(panel.button_callback)

    def test_brightness_is_bounded_without_opening_hardware(self) -> None:
        panel = WhisplayPanel()
        panel.set_brightness(0)
        panel.set_brightness(100)
        for invalid in (-1, 101, True, 50.0):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                panel.set_brightness(invalid)  # type: ignore[arg-type]

    def test_brightness_is_queued_for_kernel_pwm(self) -> None:
        panel = WhisplayPanel()
        backlight = Mock()
        panel._backlight = backlight
        panel._spi = Mock()
        panel.set_brightness(35)
        backlight.set_brightness.assert_called_once_with(35)
        panel.set_brightness(80)
        backlight.set_brightness.assert_called_with(80)

    def test_kernel_pwm_request_is_atomic_and_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            request = Path(raw) / "brightness.request"
            backlight = _KernelPwmBacklight(request)

            backlight.set_brightness(35)
            first_stat = request.stat()
            self.assertEqual(request.read_text(encoding="ascii"), "35\n")
            if os.name != "nt":
                self.assertEqual(first_stat.st_mode & 0o777, 0o600)

            backlight.set_brightness(35)
            self.assertEqual(request.stat().st_mtime_ns, first_stat.st_mtime_ns)

            backlight.set_brightness(80)
            self.assertEqual(request.read_text(encoding="ascii"), "80\n")

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
        self.assertEqual(state["volume"], 70)
        self.assertEqual(display.snapshot()["volume"], 70)
        self.assertEqual(len(panel.frames), 2)
        display.close()

    def test_native_screen_preview_uses_same_renderer(self) -> None:
        panel = FakePanel()
        display = WhisplayDisplay(panel=panel)  # type: ignore[arg-type]
        display.render(Frame(screen="dashboard", title="OpenR4d10"))
        payload = display.screen_png()
        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(Image.open(BytesIO(payload)).size, (WIDTH, HEIGHT))

    def test_ambient_scene_uses_its_bundled_artwork(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            artwork_root = root / "ambient"
            artwork_root.mkdir()
            Image.new("RGB", (32, 32), (12, 98, 44)).save(
                artwork_root / "forest.jpg"
            )
            display = WhisplayDisplay(
                panel=FakePanel(),  # type: ignore[arg-type]
                ambient_artwork_root=artwork_root,
            )
            display.state.service_index = 3
            display.state.preset_id = "forest"
            with patch("openr4d10.adapters.render_device_ui") as renderer:
                renderer.return_value = Image.new("RGB", (WIDTH, HEIGHT))
                display._render_image()
            loaded = renderer.call_args.args[1]
            self.assertIsNotNone(loaded)
            self.assertTrue(
                all(
                    abs(actual - expected) <= 2
                    for actual, expected in zip(
                        loaded.getpixel((16, 16)), (12, 98, 44), strict=True
                    )
                )
            )

    def test_hotspot_secret_is_read_only_by_the_physical_display_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state_root = Path(raw)
            (state_root / "hotspot-status.json").write_text(
                json.dumps(
                    {
                        "state": "hotspot",
                        "ssid": "OpenR4d10-Setup-8FDE",
                        "address": "10.42.0.1",
                    }
                ),
                encoding="utf-8",
            )
            (state_root / "hotspot-passphrase").write_text(
                "LocalOnlyA1B2C3D4\n", encoding="ascii"
            )
            panel = FakePanel()
            display = WhisplayDisplay(
                panel=panel,  # type: ignore[arg-type]
                state_directory=state_root,
            )
            display.render(Frame(screen="dashboard", title="OpenR4d10"))
            self.assertTrue(display.state.hotspot_active)
            self.assertEqual(display.state.hotspot_passphrase, "LocalOnlyA1B2C3D4")
            self.assertNotIn("LocalOnlyA1B2C3D4", json.dumps(display.snapshot()))
            self.assertEqual(len(panel.frames), 1)

    def test_display_brightness_reaches_panel_and_public_state(self) -> None:
        panel = FakePanel()
        display = WhisplayDisplay(panel=panel)  # type: ignore[arg-type]
        display.set_brightness(35)
        self.assertEqual(panel.brightness, [35])
        self.assertEqual(display.snapshot()["brightness_percent"], 35)

    def test_display_language_updates_native_state_and_redraws(self) -> None:
        panel = FakePanel()
        display = WhisplayDisplay(panel=panel)  # type: ignore[arg-type]
        display.render(Frame(screen="dashboard", title="OpenR4d10"))
        display.set_language("de-DE", redraw=True)
        self.assertEqual(display.snapshot()["language"], "de")
        self.assertEqual(len(panel.frames), 2)
        with self.assertRaises(ValueError):
            display.set_language("it", redraw=True)
        self.assertEqual(len(panel.frames), 2)


if __name__ == "__main__":
    unittest.main()
