from __future__ import annotations

import unittest
from unittest.mock import call, patch

from openr4d10 import cpu_affinity


class CpuAffinityTests(unittest.TestCase):
    def test_verified_four_core_layout_separates_background_ui_and_input(self) -> None:
        cpu_affinity.target_cpu_sets.cache_clear()
        with (
            patch.object(cpu_affinity.os, "cpu_count", return_value=4),
            patch.object(cpu_affinity.os, "sched_setaffinity", create=True),
            patch.object(
                cpu_affinity.Path,
                "read_text",
                return_value="Raspberry Pi Zero 2 W Rev 1.0\x00",
            ),
        ):
            self.assertEqual(cpu_affinity.target_cpu_sets(), (frozenset({0, 1}), 2, 3))
        cpu_affinity.target_cpu_sets.cache_clear()

    def test_affinity_helpers_apply_each_role_without_overlapping(self) -> None:
        with (
            patch.object(
                cpu_affinity,
                "target_cpu_sets",
                return_value=(frozenset({0, 1}), 2, 3),
            ),
            patch.object(cpu_affinity.os, "sched_setaffinity", create=True) as setter,
            patch.object(cpu_affinity.threading, "get_native_id", return_value=77),
        ):
            self.assertTrue(cpu_affinity.pin_current_thread_to_background_cores())
            self.assertTrue(cpu_affinity.pin_current_thread_to_ui_core())
            self.assertTrue(cpu_affinity.pin_current_thread_to_input_core())
            self.assertTrue(cpu_affinity.pin_process_to_background_cores(1234))

        self.assertEqual(
            setter.call_args_list,
            [
                call(0, frozenset({0, 1})),
                call(77, {2}),
                call(77, {3}),
                call(1234, frozenset({0, 1})),
            ],
        )


if __name__ == "__main__":
    unittest.main()
