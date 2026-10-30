from pathlib import Path
import json
import tempfile
import unittest

from openr4d10.adapters import FileDisplay
from openr4d10.models import Frame


class AdapterTests(unittest.TestCase):
    def test_file_display_writes_semantic_frame_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "display.json"
            FileDisplay(output).render(
                Frame(screen="dashboard", title="Test", fields={"value": 42})
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["screen"], "dashboard")
            self.assertEqual(payload["fields"]["value"], 42)
            self.assertEqual(list(output.parent.glob(".display.json.*")), [])


if __name__ == "__main__":
    unittest.main()
