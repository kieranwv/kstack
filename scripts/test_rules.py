#!/usr/bin/env python3
"""Tests for rule-number growth, frontmatter, and the generated document."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ruleslib import (
    layout_errors,
    load_skill,
    monotonicity_errors,
    parse_extends,
)


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


class FrontmatterTests(unittest.TestCase):
    def test_extends_is_a_comma_separated_list(self) -> None:
        self.assertEqual(parse_extends("principle-prove-it-works"), ("principle-prove-it-works",))
        self.assertEqual(
            parse_extends("why, show-me-your-work"),
            ("why", "show-me-your-work"),
        )

    def test_extends_rejects_a_blank_or_a_repeat(self) -> None:
        with self.assertRaises(ValueError):
            parse_extends(" ")
        with self.assertRaises(ValueError):
            parse_extends("why, why")
        with self.assertRaises(ValueError):
            parse_extends("Not A Skill")

    def test_moved_and_audience_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "principle-example"
            folder.mkdir()
            (folder / "SKILL.md").write_text(
                "---\n"
                "name: principle-example\n"
                'description: "Example."\n'
                "rule: R9\n"
                "status: moved\n"
                "audience: author\n"
                "extends: why\n"
                "---\n\n"
                "# Example\n",
                encoding="utf-8",
            )
            skill = load_skill(folder)
        self.assertEqual(skill.status, "moved")
        self.assertEqual(skill.audience, "author")
        self.assertEqual(skill.extends, ("why",))

    def test_unknown_status_and_audience_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "principle-example"
            folder.mkdir()
            (folder / "SKILL.md").write_text(
                "---\n"
                "name: principle-example\n"
                'description: "Example."\n'
                "rule: R9\n"
                "status: gone\n"
                "---\n\n"
                "# Example\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_skill(folder)

    def test_eval_record_files_are_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "principle-example"
            evals = folder / "evals"
            cases = evals / "cases"
            cases.mkdir(parents=True)
            (folder / "SKILL.md").write_text("x", encoding="utf-8")
            (evals / "rubric.md").write_text("x", encoding="utf-8")
            (evals / "eval-hash.json").write_text("{}\n", encoding="utf-8")
            (evals / "last-run.md").write_text("x", encoding="utf-8")
            (cases / "01.md").write_text("x", encoding="utf-8")
            self.assertEqual(layout_errors(folder), [])
            (evals / "notes.txt").write_text("x", encoding="utf-8")
            self.assertTrue(layout_errors(folder))


if __name__ == "__main__":
    unittest.main()
