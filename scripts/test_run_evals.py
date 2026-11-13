"""Tests for the eval runner scaffold."""

from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from run_evals import main, parse_judgment, run_skills

FIXTURE = """---
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

RUBRIC = """# Rubric

## Criteria

1. Pass: The agent does the thing. Fail: The agent skips it.
2. Pass: The agent says what it saw. Fail: The agent only describes intent.
3. Pass: The agent stops when blocked. Fail: The agent invents a result.
"""

CASE = """## Prompt

Open the form and say whether the work is done.

## Expected

The agent opens the form or says what blocked it.
"""

RUNNER = """#!/usr/bin/env python3
import json
import re
import sys

req = json.load(sys.stdin)
if req["role"] == "candidate":
    json.dump({"text": "I opened the form."}, sys.stdout)
    raise SystemExit(0)
prompt = req["prompt"]
name = re.search(r"(?m)^CASE (\\S+)$", prompt)
count = len(re.findall(r"(?m)^\\d+\\. Pass:", prompt))
if name is None or count < 1:
    raise SystemExit("bad prompt")
lines = [f"CASE {name.group(1)}"] + [f"{index} pass" for index in range(1, count + 1)]
json.dump({"text": "\\n".join(lines)}, sys.stdout)
"""


class RunnerTests(unittest.TestCase):
    def test_parse_judgment_rejects_extra_lines(self) -> None:
        self.assertEqual(parse_judgment("CASE 01.md\n1 pass\n2 fail\n", "01.md", [1, 2]), ["pass", "fail"])
        self.assertIsNone(parse_judgment("CASE 01.md\n1 pass\nthanks\n", "01.md", [1]))
        self.assertIsNone(parse_judgment("1 pass\n", "01.md", [1]))

    def test_missing_runner_writes_nothing(self) -> None:
        previous = os.environ.pop("KSTACK_EVAL_RUNNER", None)
        try:
            self.assertEqual(main([]), 2)
        finally:
            if previous is not None:
                os.environ["KSTACK_EVAL_RUNNER"] = previous

    def test_a_run_records_the_skill_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "skills" / "principle-example"
            (folder / "evals" / "cases").mkdir(parents=True)
            (folder / "SKILL.md").write_text(FIXTURE, encoding="utf-8")
            (folder / "evals" / "rubric.md").write_text(RUBRIC, encoding="utf-8")
            (folder / "evals" / "cases" / "01.md").write_text(CASE, encoding="utf-8")
            config = root / "models.json"
            config.write_text(
                json.dumps({"candidates": ["model-a", "model-b"], "judge": "model-c"}),
                encoding="utf-8",
            )
            runner = root / "runner.py"
            runner.write_text(RUNNER, encoding="utf-8")
            runner.chmod(runner.stat().st_mode | stat.S_IEXEC)
            code = run_skills(
                root,
                None,
                command=["python3", str(runner)],
                models_path=config,
                timeout=30,
            )
            self.assertEqual(code, 0, "runner failed")
            record = json.loads((folder / "evals" / "eval-hash.json").read_text(encoding="utf-8"))
            last_run = (folder / "evals" / "last-run.md").read_text(encoding="utf-8")
            self.assertEqual(record["basis"], "run")
            self.assertIn(record["skill_sha256"], last_run)
            (folder / "SKILL.md").write_text(FIXTURE.replace("Do the thing.", "Do the thing!"), encoding="utf-8")
            from eval_hash import check_tree

            errors = check_tree(root, None)
            self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
