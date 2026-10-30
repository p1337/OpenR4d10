"""UI data models shared by the core and hardware adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Frame:
    """A semantic display frame; a hardware adapter decides how to draw it."""

    screen: str
    title: str
    body: str = ""
    fields: dict[str, Any] = field(default_factory=dict)
    severity: str = "info"
    timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
