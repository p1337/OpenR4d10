"""Hardware-independent controls for the two future dual-concentric encoders."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Control(str, Enum):
    LEFT_OUTER = "left_outer"
    LEFT_INNER = "left_inner"
    RIGHT_OUTER = "right_outer"
    RIGHT_INNER = "right_inner"
    LEFT_PRESS = "left_press"
    RIGHT_PRESS = "right_press"


@dataclass(frozen=True, slots=True)
class InputEvent:
    """One logical input action, independent of GPIO numbering and wiring."""

    control: Control
    steps: int = 0
    held_seconds: float = 0.0

    def __post_init__(self) -> None:
        rotary = self.control in {
            Control.LEFT_OUTER,
            Control.LEFT_INNER,
            Control.RIGHT_OUTER,
            Control.RIGHT_INNER,
        }
        if rotary and self.steps == 0:
            raise ValueError("rotary input requires non-zero steps")
        if not rotary and self.steps != 0:
            raise ValueError("press input cannot contain rotary steps")
        if self.held_seconds < 0:
            raise ValueError("held_seconds cannot be negative")
