from __future__ import annotations

import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest

from openr4d10.service_adapters import (
    ServiceAdapterError,
    ServiceAdapterManifest,
    ServiceAdapterRegistry,
)


class ServiceAdapterTests(unittest.TestCase):
    def test_manifest_is_restricted_to_its_named_runtime_socket(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            manifests = root / "manifests"
            sockets = root / "sockets"
            manifests.mkdir()
            manifests.joinpath("mumble.toml").write_text(
                '[adapter]\nprotocol = 1\nsocket = "/tmp/wrong.sock"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ServiceAdapterError, "must be exactly"):
                ServiceAdapterRegistry.from_directory(
                    manifests, {"mumble"}, socket_root=sockets
                )

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Unix sockets unavailable")
    def test_bounded_json_protocol_and_public_response_filter(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            manifests = root / "manifests"
            sockets = root / "sockets"
            manifests.mkdir()
            sockets.mkdir()
            socket_path = sockets / "mumble.sock"
            manifests.joinpath("mumble.toml").write_text(
                "[adapter]\n"
                "protocol = 1\n"
                f"socket = {json.dumps(str(socket_path))}\n"
                "timeout_seconds = 1\n",
                encoding="utf-8",
            )
            received: list[dict[str, object]] = []
            ready = threading.Event()

            def serve() -> None:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                    server.bind(str(socket_path))
                    server.listen(1)
                    ready.set()
                    connection, _ = server.accept()
                    with connection:
                        payload = b""
                        while b"\n" not in payload:
                            payload += connection.recv(4096)
                        received.append(json.loads(payload.split(b"\n", 1)[0]))
                        connection.sendall(
                            b'{"ok":true,"ready":true,"url":"https://example.test/a?token=hidden"}\n'
                        )

            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            self.assertTrue(ready.wait(2))
            registry = ServiceAdapterRegistry.from_directory(
                manifests, {"mumble"}, socket_root=sockets
            )
            result = registry.status("mumble")
            thread.join(2)
            self.assertEqual(received[0]["operation"], "status")
            self.assertEqual(result["url"], "https://example.test/a")

    def test_secret_shaped_request_fields_are_rejected_before_transport(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw).resolve() / "mumble.sock"
            registry = ServiceAdapterRegistry(
                {
                    "mumble": ServiceAdapterManifest(
                        "mumble", path, 1.0
                    )
                }
            )
            with self.assertRaisesRegex(ServiceAdapterError, "forbidden field"):
                registry.call(
                    "mumble", "connect", {"access_token": "never-forward"}
                )


if __name__ == "__main__":
    unittest.main()
