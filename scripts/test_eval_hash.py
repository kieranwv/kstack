"""Tests for the skill-hash gate."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from eval_hash import check_tree, write_last_run, write_record
from ruleslib import ROOT

SKILL = """---
name: principle-example
description: "Example."
rule: R1
status: active
---

# Example

## Rule

Do the thing.

## Why

Because.

## Failure examples

- A miss.
"""


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    return env


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        env=git_env(),
    )


def write_skill(folder: Path, text: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(text, encoding="utf-8")
    (folder / "evals").mkdir(exist_ok=True)


class EvalHashTests(unittest.TestCase):
    def test_a_character_edit_fails_until_a_run_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "skills" / "principle-example"
            write_skill(folder, SKILL)
            write_record(folder, "baseline")
            git(root, "init")
            git(root, "add", ".")
            git(root, "commit", "-m", "seal")
            changed = SKILL.replace("Do the thing.", "Do the thing!")
            (folder / "SKILL.md").write_text(changed, encoding="utf-8")
            edited = check_tree(root, "HEAD")
            self.assertTrue(any("run_evals.py" in error for error in edited))
            write_record(folder, "baseline")
            resealed = check_tree(root, "HEAD")
            self.assertTrue(any("was not rerun" in error for error in resealed))
            write_last_run(
                folder,
                runner="fixture",
                ran_at="2026-11-13T00:00:00Z",
                body="# Eval run\n\nResult: passed.\n",
            )
            self.assertEqual(check_tree(root, "HEAD"), [])

    def test_the_first_baseline_does_not_require_a_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "skills" / "principle-example"
            write_skill(folder, SKILL)
            git(root, "init")
            git(root, "add", ".")
            git(root, "commit", "-m", "skill only")
            changed = SKILL.replace("Do the thing.", "Do the thing!")
            (folder / "SKILL.md").write_text(changed, encoding="utf-8")
            write_record(folder, "baseline")
            self.assertEqual(check_tree(root, "HEAD"), [])

    def test_a_missing_base_ref_is_an_error(self) -> None:
        errors = check_tree(ROOT, "refs/does-not-exist")
        self.assertTrue(any("does not exist" in error for error in errors))

    def test_workspace_records_match(self) -> None:
        self.assertEqual(check_tree(ROOT, None), [])
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", "origin/main"],
            cwd=ROOT,
            capture_output=True,
        )
        if probe.returncode != 0:
            self.skipTest("origin/main is not available")
        self.assertEqual(check_tree(ROOT, "origin/main"), [])


if __name__ == "__main__":
    unittest.main()
