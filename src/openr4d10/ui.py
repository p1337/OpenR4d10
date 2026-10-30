"""Hardware-independent UI composition."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import Frame


def dashboard_frame(
    title: str,
    receiver: Mapping[str, Any],
    power: Mapping[str, Any],
    adapter_errors: list[str] | None = None,
) -> Frame:
    errors = adapter_errors or []
    fields = {
        "receiver": dict(receiver),
        "power": dict(power),
        "adapter_errors": errors,
    }
    body = "Hardware configuration required"
    severity = "warning"
    if power.get("state") != "unconfigured" and not errors:
        body = "Receiver ready"
        severity = "info"
    if errors:
        body = "Adapter error"
        severity = "error"
    return Frame(
        screen="dashboard",
        title=title,
        body=body,
        fields=fields,
        severity=severity,
    )
