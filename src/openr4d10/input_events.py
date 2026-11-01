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
    HOME = "home"
    PTT = "ptt"


@dataclass(frozen=True, slots=True)
class InputEvent:
    """One logical input action, independent of GPIO numbering and wiring."""

    control: Control
    steps: int = 0
    held_seconds: float = 0.0
    active: bool | None = None

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
        if rotary and self.held_seconds != 0:
            raise ValueError("rotary input cannot contain a hold duration")
        if self.control == Control.PTT:
            if not isinstance(self.active, bool):
                raise ValueError("PTT input requires an active state")
            if self.active and self.held_seconds != 0:
                raise ValueError("an active PTT edge cannot contain a hold duration")
        elif self.active is not None:
            raise ValueError("only PTT input accepts an active state")
