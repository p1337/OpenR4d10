"""Isolated Unix-socket protocol for optional external service modules."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import socket
from typing import Any
import tomllib
from urllib.parse import SplitResult, urlsplit, urlunsplit


PROTOCOL_VERSION = 1
MAX_REQUEST_BYTES = 16 * 1024
MAX_RESPONSE_BYTES = 64 * 1024
DEFAULT_SOCKET_ROOT = Path("/run/openr4d10-adapters")
_SAFE_ID = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_SECRET_KEY = re.compile(
    r"(^|[._-])(auth|bearer|cookie|credential|password|passwd|session|token|secret|api[_-]?key|private[_-]?key)($|[._-])",
    re.IGNORECASE,
)


class ServiceAdapterError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ServiceAdapterManifest:
    service_id: str
    socket_path: Path
    timeout_seconds: float


def _public_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        raise ServiceAdapterError("adapter response nesting is too deep")
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if len(value) > 4096:
            raise ServiceAdapterError("adapter response string is too long")
        parsed = urlsplit(value)
        if parsed.scheme in {"http", "https"}:
            value = urlunsplit(
                SplitResult(parsed.scheme, parsed.hostname or "", parsed.path, "", "")
            )
        return value
    if isinstance(value, list):
        if len(value) > 500:
            raise ServiceAdapterError("adapter response list is too long")
        return [_public_value(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        if len(value) > 200:
            raise ServiceAdapterError("adapter response object is too large")
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key or _SECRET_KEY.search(key):
                raise ServiceAdapterError("adapter response contains a forbidden field")
            result[key] = _public_value(item, depth=depth + 1)
        return result
    raise ServiceAdapterError("adapter response contains an unsupported value")


def _request_parameters(value: object) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("adapter parameters must be a JSON object")
    public = _public_value(value)
    assert isinstance(public, dict)
    return public


class ServiceAdapterRegistry:
    def __init__(
        self,
        manifests: dict[str, ServiceAdapterManifest] | None = None,
    ) -> None:
        self.manifests = manifests or {}

    @classmethod
    def from_directory(
        cls,
        directory: Path,
        allowed_services: set[str],
        *,
        socket_root: Path = DEFAULT_SOCKET_ROOT,
    ) -> "ServiceAdapterRegistry":
        if not directory.is_absolute():
            raise ValueError("service adapter directory must be absolute")
        if not directory.exists():
            return cls()
        if not directory.is_dir():
            raise ServiceAdapterError(f"service adapter path is not a directory: {directory}")
        root = socket_root.resolve(strict=False)
        manifests: dict[str, ServiceAdapterManifest] = {}
        for path in sorted(directory.glob("*.toml")):
            service_id = path.stem
            if service_id not in allowed_services or not _SAFE_ID.fullmatch(service_id):
                raise ServiceAdapterError(f"unknown service adapter manifest: {path.name}")
            try:
                with path.open("rb") as handle:
                    data = tomllib.load(handle)
            except (OSError, tomllib.TOMLDecodeError) as exc:
                raise ServiceAdapterError(f"cannot read adapter manifest {path}: {exc}") from exc
            adapter = data.get("adapter")
            if not isinstance(adapter, dict):
                raise ServiceAdapterError(f"{path}: [adapter] table is required")
            if set(adapter) - {"protocol", "socket", "timeout_seconds"}:
                raise ServiceAdapterError(f"{path}: unsupported adapter setting")
            if adapter.get("protocol", PROTOCOL_VERSION) != PROTOCOL_VERSION:
                raise ServiceAdapterError(f"{path}: unsupported adapter protocol")
            socket_value = adapter.get("socket")
            timeout = adapter.get("timeout_seconds", 2.0)
            if not isinstance(socket_value, str) or not socket_value:
                raise ServiceAdapterError(f"{path}: adapter.socket is required")
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0.1 <= timeout <= 10:
                raise ServiceAdapterError(f"{path}: timeout_seconds must be between 0.1 and 10")
            socket_path = Path(socket_value)
            resolved = socket_path.resolve(strict=False)
            expected = root / f"{service_id}.sock"
            if not socket_path.is_absolute() or resolved != expected:
                raise ServiceAdapterError(
                    f"{path}: socket must be exactly {expected}"
                )
            manifests[service_id] = ServiceAdapterManifest(
                service_id=service_id,
                socket_path=socket_path,
                timeout_seconds=float(timeout),
            )
        return cls(manifests)

    def configured(self, service_id: str) -> bool:
        return service_id in self.manifests

    def call(
        self,
        service_id: str,
        operation: str,
        parameters: object = None,
    ) -> dict[str, Any]:
        manifest = self.manifests.get(service_id)
        if manifest is None:
            raise ServiceAdapterError(f"service adapter is not configured: {service_id}")
        if not _SAFE_ID.fullmatch(operation) or len(operation) > 64:
            raise ValueError("adapter operation is invalid")
        request = {
            "protocol": PROTOCOL_VERSION,
            "service_id": service_id,
            "operation": operation,
            "parameters": _request_parameters(parameters),
        }
        payload = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(payload) > MAX_REQUEST_BYTES:
            raise ValueError("adapter request is too large")
        response = bytearray()
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(manifest.timeout_seconds)
                connection.connect(str(manifest.socket_path))
                connection.sendall(payload)
                connection.shutdown(socket.SHUT_WR)
                while b"\n" not in response:
                    block = connection.recv(min(8192, MAX_RESPONSE_BYTES + 1 - len(response)))
                    if not block:
                        break
                    response.extend(block)
                    if len(response) > MAX_RESPONSE_BYTES:
                        raise ServiceAdapterError("adapter response is too large")
        except (OSError, TimeoutError) as exc:
            raise ServiceAdapterError(f"service adapter unavailable: {service_id}: {exc}") from exc
        line = bytes(response).split(b"\n", 1)[0]
        try:
            value = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ServiceAdapterError("adapter returned invalid JSON") from exc
        public = _public_value(value)
        if not isinstance(public, dict) or not isinstance(public.get("ok"), bool):
            raise ServiceAdapterError("adapter response must contain boolean ok")
        if not public["ok"]:
            message = public.get("error", "adapter operation failed")
            raise ServiceAdapterError(str(message))
        return public

    def status(self, service_id: str) -> dict[str, Any]:
        return self.call(service_id, "status")
