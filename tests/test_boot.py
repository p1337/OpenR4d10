from pathlib import Path
import unittest

from openr4d10.boot import load_boot_sequence


class BootTests(unittest.TestCase):
    def test_checked_in_text_sequence_is_valid(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sequence = load_boot_sequence(root / "assets" / "boot" / "text-sequence.toml")
        self.assertEqual(len(sequence), 3)
        self.assertTrue(all(item.frame.screen == "boot" for item in sequence))


if __name__ == "__main__":
    unittest.main()
