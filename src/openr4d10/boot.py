"""Text boot-sequence loader; binary animation belongs in a display adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .config import ConfigError
from .models import Frame


@dataclass(frozen=True, slots=True)
class BootFrame:
    frame: Frame
    duration_seconds: float


def load_boot_sequence(path: Path) -> list[BootFrame]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"boot manifest not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid boot manifest {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read boot manifest {path}: {exc}") from exc

    if data.get("version") != 1:
        raise ConfigError("boot manifest version must be 1")
    raw_frames = data.get("frames")
    if not isinstance(raw_frames, list) or not raw_frames:
        raise ConfigError("boot manifest requires at least one [[frames]] entry")

    result: list[BootFrame] = []
    for index, item in enumerate(raw_frames, start=1):
        if not isinstance(item, dict):
            raise ConfigError(f"boot frame {index} must be a table")
        title = item.get("title")
        body = item.get("body", "")
        duration = item.get("duration_ms")
        if not isinstance(title, str) or not title:
            raise ConfigError(f"boot frame {index} requires a title")
        if not isinstance(body, str):
            raise ConfigError(f"boot frame {index} body must be a string")
        if (
            isinstance(duration, bool)
            or not isinstance(duration, int)
            or not 50 <= duration <= 30_000
        ):
            raise ConfigError(
                f"boot frame {index} duration_ms must be between 50 and 30000"
            )
        result.append(
            BootFrame(
                Frame(screen="boot", title=title, body=body), duration / 1000.0
            )
        )
    return result
