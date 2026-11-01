from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openr4d10.brandmeister import (
    BrandmeisterReceiver,
    BrandmeisterTalkgroupCatalog,
    MAX_TALKGROUPS,
    country_code,
    group_message,
)


class _Process:
    def __init__(self) -> None:
        self.stdin = BytesIO()
        self.terminated = False

    def poll(self):
        return None if not self.terminated else 0

    def wait(self, timeout=None):
        self.terminated = True
        return 0

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.terminated = True


class BrandmeisterReceiverTests(unittest.TestCase):
    def test_subscription_message_and_country_mapping_match_hoseline(self) -> None:
        self.assertEqual(group_message(1, (91,)), bytes((0x92, 1, 0x91, 91)))
        six = (91, 92, 260, 262, 3100, 505)
        self.assertEqual(group_message(1, six)[2], 0x90 + MAX_TALKGROUPS)
        with self.assertRaisesRegex(ValueError, "one to six"):
            group_message(1, six + (234,))
        self.assertEqual(country_code(262), "DE")
        self.assertEqual(country_code(260), "PL")
        self.assertIsNone(country_code(91))

    def test_call_metadata_and_mulaw_audio_reach_only_aplay(self) -> None:
        messages = {
            b"start": [11, 0, 3196125, 91],
            b"alias": [21, "KW4JM"],
            b"audio": [20, bytes((0xFF, 0x7F, 0x00))],
            b"stop": [13],
        }
        processes = []
        commands = []

        def popen(command, **_kwargs):
            commands.append(command)
            process = _Process()
            processes.append(process)
            return process

        receiver = BrandmeisterReceiver(
            unpacker=messages.__getitem__,
            popen=popen,
        )
        receiver._receive(b"start")
        receiver._receive(b"alias")
        state = receiver.snapshot()
        self.assertEqual(state["status"], "call")
        self.assertEqual(state["destination"], 91)
        self.assertEqual(state["source"], 3196125)
        self.assertEqual(state["alias"], "KW4JM")
        self.assertEqual(state["activity"][0]["talkgroup"], 91)
        self.assertEqual(state["activity"][0]["source"], 3196125)
        self.assertEqual(state["activity"][0]["alias"], "KW4JM")
        self.assertTrue(state["activity"][0]["active"])
        receiver._receive(b"audio")
        self.assertEqual(commands[0][0], "/usr/bin/aplay")
        self.assertIn("whisplaysound", commands[0])
        self.assertEqual(len(processes[0].stdin.getvalue()), 6)
        receiver._receive(b"stop")
        stopped = receiver.snapshot()
        self.assertEqual(stopped["status"], "listening")
        self.assertFalse(stopped["activity"][0]["active"])
        self.assertEqual(stopped["activity"][0]["alias"], "KW4JM")
        receiver.close()


class BrandmeisterCatalogTests(unittest.TestCase):
    def test_public_catalog_is_bounded_filtered_and_cached(self) -> None:
        raw = json.dumps(
            {"1": "Local", "91": "World-wide", "262": "Germany", "bad": "x"}
        ).encode("utf-8")

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return raw

        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory).resolve() / "talkgroups.json"
            catalog = BrandmeisterTalkgroupCatalog(cache)
            with patch("openr4d10.brandmeister.urlopen", return_value=Response()):
                payload = json.loads(catalog.payload())
            self.assertEqual(
                [item["talkgroup"] for item in payload["talkgroups"]],
                [91, 262],
            )
            self.assertEqual(payload["talkgroups"][1]["country_code"], "DE")
            self.assertEqual(
                [item["name"] for item in catalog.entries()],
                ["World-wide", "Germany"],
            )
            self.assertTrue(cache.is_file())


if __name__ == "__main__":
    unittest.main()
