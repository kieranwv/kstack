"""Tests for pstack extends checks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from check_refs import extends_errors, pstack_skill_names
from ruleslib import Skill, iter_skill_dirs, load_skill


def skill_with(*, extends: tuple[str, ...]) -> Skill:
    return Skill(
        slug="principle-example",
        path=Path("SKILL.md"),
        meta={},
        body="",
        number=1,
        title="Example",
        status="active",
        extends=extends,
        audience="agent",
    )


class RefTests(unittest.TestCase):
    def test_a_missing_directory_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "skills" / "principle-prove-it-works"
            root.mkdir(parents=True)
            (root / "SKILL.md").write_text("x", encoding="utf-8")
            (Path(tmp) / "skills" / "empty").mkdir()
            names = pstack_skill_names(Path(tmp))
        self.assertEqual(names, {"principle-prove-it-works"})
        errors = extends_errors(
            [skill_with(extends=("principle-prove-it-works", "missing-skill"))],
            names,
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("missing-skill", errors[0])

    def test_recorded_parents(self) -> None:
        skills = {folder.name: load_skill(folder) for folder in iter_skill_dirs()}
        self.assertEqual(
            skills["principle-verify-like-a-user"].extends,
            ("principle-prove-it-works",),
        )
        self.assertEqual(
            skills["principle-single-writer"].extends,
            ("principle-separate-before-serializing-shared-state",),
        )
        self.assertEqual(skills["principle-verify-before-you-speak"].extends, ())
        self.assertEqual(skills["principle-designated-directory"].extends, ())
        for skill in skills.values():
            self.assertEqual(skill.audience, "agent")
            self.assertEqual(skill.status, "active")


if __name__ == "__main__":
    unittest.main()
