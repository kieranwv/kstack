#!/usr/bin/env python3
"""Tests for rule-number growth and the generated document."""

from __future__ import annotations

import unittest

from ruleslib import monotonicity_errors


class MonotonicityTests(unittest.TestCase):
    def test_initial_port_may_start_at_r1(self) -> None:
        self.assertEqual(monotonicity_errors({}, {1: "a", 2: "b"}), [])

    def test_initial_port_rejects_a_gap(self) -> None:
        errors = monotonicity_errors({}, {1: "a", 3: "c"})
        self.assertTrue(errors)

    def test_existing_numbers_may_grow_by_one(self) -> None:
        base = {1: "a", 2: "b"}
        self.assertEqual(monotonicity_errors(base, {1: "a", 2: "b", 3: "c"}), [])

    def test_a_retired_number_still_has_to_be_present(self) -> None:
        errors = monotonicity_errors({1: "a", 2: "b"}, {1: "a"})
        self.assertTrue(any("disappeared" in error for error in errors))

    def test_a_number_cannot_change_skill(self) -> None:
        errors = monotonicity_errors({1: "a", 2: "b"}, {1: "b", 2: "a"})
        self.assertTrue(any("changed" in error for error in errors))

    def test_a_gap_cannot_be_filled_later(self) -> None:
        errors = monotonicity_errors({1: "a", 3: "c"}, {1: "a", 2: "b", 3: "c"})
        self.assertTrue(any("inserted" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
