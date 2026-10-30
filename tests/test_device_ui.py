from datetime import datetime
import unittest

from PIL import Image

from openr4d10.adapters import WhisplayDisplay
from openr4d10.device_ui import (
    DeviceUiState,
    HEIGHT,
    WIDTH,
    image_to_rgb565,
    render_device_ui,
)
from openr4d10.input_events import Control, InputEvent
from openr4d10.models import Frame


class DeviceUiTests(unittest.TestCase):
    def test_renderer_produces_native_portrait_frame(self) -> None:
        state = DeviceUiState(
            volume=42,
            squelch=6,
            channel=17,
            service_index=2,
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
        self.assertEqual(state.volume, 53)
        self.assertEqual(state.squelch, 2)
        self.assertEqual(state.channel, 15)
        self.assertEqual(state.service, "RADIO")
        self.assertTrue(state.playing)

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

    def test_invalid_input_shapes_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            InputEvent(Control.LEFT_OUTER)
        with self.assertRaises(ValueError):
            InputEvent(Control.LEFT_PRESS, steps=1)


class FakePanel:
    def __init__(self) -> None:
        self.frames: list[bytes] = []
        self.closed = False

    def show(self, frame: bytes) -> None:
        self.frames.append(frame)

    def close(self) -> None:
        self.closed = True


class WhisplayDisplayTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
