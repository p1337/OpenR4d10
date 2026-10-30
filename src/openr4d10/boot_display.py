"""The actual physical UI calls this only when ready to render its first frame."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import time


@contextmanager
def claim_display(timeout: float = 2.0, runtime: Path = Path("/run/openr4d10-boot")):
    """Ask the early player to release SPI/GPIO, then exclusively own the LCD.

    Call before initializing WhisplayBoard and keep this context for the UI's
    entire lifetime. Web API readiness is intentionally unrelated to this hook.
    """
    try:
        import fcntl
    except ImportError as exc:
        raise RuntimeError("Display ownership is available only on Linux") from exc
    if not runtime.is_dir():
        raise RuntimeError("Boot display runtime is absent; physical UI ownership must be configured")
    fd = os.open(runtime / "display.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o660)
    deadline = time.monotonic() + timeout
    try:
        (runtime / "release").touch(mode=0o660, exist_ok=True)
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Boot player did not release the display")
                time.sleep(0.01)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
