"""Best-effort CPU placement for the verified four-core Pi Zero 2 W."""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import threading


@lru_cache(maxsize=1)
def target_cpu_sets() -> tuple[frozenset[int], int, int] | None:
    """Return background, UI and input cores only on verified hardware."""

    if not hasattr(os, "sched_setaffinity"):
        return None
    count = os.cpu_count() or 0
    if count < 4:
        return None
    try:
        model = Path("/proc/device-tree/model").read_text(
            encoding="utf-8"
        ).rstrip("\x00\n")
    except OSError:
        return None
    if "Raspberry Pi Zero 2" not in model:
        return None
    input_cpu = count - 1
    ui_cpu = count - 2
    return frozenset(range(ui_cpu)), ui_cpu, input_cpu


def pin_current_thread_to_background_cores() -> bool:
    placement = target_cpu_sets()
    if placement is None:
        return False
    background_cpus, _ui_cpu, _input_cpu = placement
    try:
        os.sched_setaffinity(0, background_cpus)
    except OSError:
        return False
    return True


def pin_current_thread_to_ui_core() -> bool:
    placement = target_cpu_sets()
    if placement is None:
        return False
    _background_cpus, ui_cpu, _input_cpu = placement
    try:
        os.sched_setaffinity(threading.get_native_id(), {ui_cpu})
    except OSError:
        return False
    return True


def pin_current_thread_to_input_core() -> bool:
    placement = target_cpu_sets()
    if placement is None:
        return False
    _background_cpus, _ui_cpu, input_cpu = placement
    try:
        os.sched_setaffinity(threading.get_native_id(), {input_cpu})
    except OSError:
        return False
    return True


def pin_process_to_background_cores(process_id: int) -> bool:
    placement = target_cpu_sets()
    if placement is None:
        return False
    background_cpus, _ui_cpu, _input_cpu = placement
    try:
        os.sched_setaffinity(process_id, background_cpus)
    except OSError:
        return False
    return True
