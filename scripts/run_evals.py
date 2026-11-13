#!/usr/bin/env python3
"""Run each skill's cases and record the skill hash.

The model call is a subprocess named by ``KSTACK_EVAL_RUNNER``. This file does
not import a provider SDK. The command is split on whitespace and is not a
shell. It reads one JSON object from stdin and writes one JSON object to
stdout:

    {"role": "candidate" or "judge", "model": "<name>", "prompt": "<text>"}
    {"text": "<completion>"}

``config/eval-runner.json`` lists candidate model names and one judge model
name. Those strings are passed through. Empty lists mean the runner is not
configured: this command writes nothing and exits 2.

See docs/eval-runner.md for the pstack playbook this follows and for the
reply format the judge is asked to use. That format is an assumption.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from eval_hash import write_last_run
from ruleslib import ROOT, iter_skill_dirs, load_skill, rubric_criteria, section_body

MODELS_PATH = ROOT / "config" / "eval-runner.json"


def load_models(path: Path) -> tuple[list[str], str] | str:
    """Return ``(candidates, judge)`` or an error string."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return f"cannot read {path}: {exc}"
    if not isinstance(data, dict):
        return f"{path} must be a JSON object"
    raw_candidates = data.get("candidates", [])
    judge = data.get("judge", "")
    if not isinstance(raw_candidates, list) or not all(
        isinstance(item, str) for item in raw_candidates
    ):
        return "candidates must be a list of strings"
    if not isinstance(judge, str):
        return "judge must be a string"
    candidates = [item.strip() for item in raw_candidates if item.strip()]
    judge = judge.strip()
    if not candidates or not judge:
        return "config/eval-runner.json needs at least one candidate and a judge"
    if judge in candidates:
        return "the judge model must not also be a candidate"
    return candidates, judge


def criterion_numbers(rubric: str) -> list[int]:
    numbers: list[int] = []
    for line in rubric_criteria(rubric):
        numbers.append(int(line.split(".", 1)[0]))
    return numbers


def judge_prompt(case_name: str, rubric: str, outputs: list[str]) -> str:
    blocks: list[str] = []
    for index, output in enumerate(outputs):
        label = chr(ord("A") + index)
        blocks.append(f"## Candidate {label}\n\n{output}")
    return (
        "Score every candidate against the rubric. "
        "You do not know which model wrote a reply.\n\n"
        "Reply with the case file name on its own line, then one line per criterion. "
        "A score line is the criterion number, a space, and either pass or fail. "
        "No other lines.\n\n"
        f"CASE {case_name}\n\n"
        "# Rubric\n\n"
        f"{rubric.strip()}\n\n"
        + "\n\n".join(blocks)
        + "\n"
    )


def parse_judgment(text: str, case_name: str, numbers: list[int]) -> list[str] | None:
    """Return pass/fail in criterion order, or None when the reply is not usable."""
    scores: dict[int, str] = {}
    saw_case = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        case_match = re.fullmatch(r"CASE\s+(\S+)", line)
        if case_match:
            if case_match.group(1) != case_name or saw_case:
                return None
            saw_case = True
            continue
        score_match = re.fullmatch(r"(\d+)\s+(pass|fail)", line, re.IGNORECASE)
        if not score_match:
            return None
        number = int(score_match.group(1))
        if number in scores:
            return None
        scores[number] = score_match.group(2).lower()
    if not saw_case or set(scores) != set(numbers) or len(scores) != len(numbers):
        return None
    return [scores[number] for number in numbers]


def fence_for(text: str) -> str:
    longest = 0
    current = 0
    for char in text:
        if char == "`":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return "`" * max(3, longest + 1)


def render_last_run(case_results: list[dict[str, object]]) -> str:
    lines = [
        "# Eval run",
        "",
        "`scripts/run_evals.py` wrote this file after the runner returned a judgment for every case.",
        "The lines below are that judgment. A failed criterion is still a completed run.",
        "",
    ]
    failed = False
    for case in case_results:
        lines.append(f"## {case['case']}")
        lines.append("")
        outputs = case["outputs"]
        models = case["models"]
        scores = case["scores"]
        numbers = case["numbers"]
        if not isinstance(outputs, list) or not isinstance(models, list):
            raise TypeError("case outputs and models must be lists")
        if not isinstance(scores, list) or not isinstance(numbers, list):
            raise TypeError("case scores and numbers must be lists")
        for index, output in enumerate(outputs):
            label = chr(ord("A") + index)
            model = str(models[index])
            text = output if isinstance(output, str) and output.strip() else "(no text)"
            fence = fence_for(str(text))
            lines.append(f"Candidate {label} used `{model}`.")
            lines.append("")
            lines.append(f"{fence}text")
            lines.append(str(text).rstrip("\n"))
            lines.append(fence)
            lines.append("")
        shown = ", ".join(
            f"{number} {score}" for number, score in zip(numbers, scores, strict=True)
        )
        if any(score != "pass" for score in scores):
            failed = True
        lines.append(f"Judge: {shown}.")
        lines.append("")
    lines.append(f"Result: {'failed' if failed else 'passed'}.")
    lines.append("")
    return "\n".join(lines)


def call_runner(
    command: list[str],
    *,
    role: str,
    model: str,
    prompt: str,
    timeout: float,
) -> tuple[str | None, str | None]:
    payload = json.dumps({"role": role, "model": model, "prompt": prompt}).encode("utf-8")
    try:
        proc = subprocess.run(
            command,
            input=payload,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        return None, f"runner exited {proc.returncode}: {detail}"
    try:
        data = json.loads(proc.stdout.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        return None, f"runner stdout is not JSON: {exc}"
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        return None, "runner JSON needs a string field text"
    return data["text"], None


def run_skill(
    folder: Path,
    *,
    command: list[str],
    candidates: list[str],
    judge: str,
    timeout: float,
) -> str | None:
    """Run every case. Return an error string, or None after the record is written."""
    try:
        load_skill(folder)
    except (OSError, ValueError) as exc:
        return f"{folder.name}: {exc}"
    before = (folder / "SKILL.md").read_bytes()
    rubric_path = folder / "evals" / "rubric.md"
    cases = sorted((folder / "evals" / "cases").glob("*.md"))
    if not rubric_path.is_file() or not cases:
        return f"{folder.name}: missing rubric or cases"
    rubric = rubric_path.read_text(encoding="utf-8")
    numbers = criterion_numbers(rubric)
    if not numbers:
        return f"{folder.name}: rubric has no criteria"
    results: list[dict[str, object]] = []
    for case in cases:
        case_text = case.read_text(encoding="utf-8")
        prompt = section_body(case_text, "Prompt")
        if not prompt:
            return f"{folder.name}/{case.name}: Prompt is empty"
        outputs: list[str] = []
        for model in candidates:
            text, error = call_runner(
                command,
                role="candidate",
                model=model,
                prompt=prompt,
                timeout=timeout,
            )
            if error or text is None:
                return f"{folder.name}/{case.name}: candidate {model}: {error}"
            outputs.append(text)
        judged, error = call_runner(
            command,
            role="judge",
            model=judge,
            prompt=judge_prompt(case.name, rubric, outputs),
            timeout=timeout,
        )
        if error or judged is None:
            return f"{folder.name}/{case.name}: judge: {error}"
        scores = parse_judgment(judged, case.name, numbers)
        if scores is None:
            return f"{folder.name}/{case.name}: judge reply was not usable"
        results.append(
            {
                "case": case.name,
                "models": list(candidates),
                "outputs": outputs,
                "scores": scores,
                "numbers": numbers,
            }
        )
    if (folder / "SKILL.md").read_bytes() != before:
        return f"{folder.name}: SKILL.md changed while the eval ran; nothing was written"
    ran_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_last_run(
        folder,
        runner=" ".join(command),
        ran_at=ran_at,
        body=render_last_run(results),
    )
    return None


def runner_command() -> list[str] | None:
    raw = os.environ.get("KSTACK_EVAL_RUNNER", "").strip()
    if not raw:
        return None
    return shlex.split(raw)


def run_skills(
    root: Path,
    slugs: list[str] | None,
    *,
    command: list[str] | None,
    models_path: Path,
    timeout: float,
) -> int:
    if command is None:
        print(
            "error: KSTACK_EVAL_RUNNER is not set. Nothing was written.",
            file=sys.stderr,
        )
        return 2
    loaded = load_models(models_path)
    if isinstance(loaded, str):
        print(f"error: {loaded}. Nothing was written.", file=sys.stderr)
        return 2
    candidates, judge = loaded
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        print("error: no skills to run", file=sys.stderr)
        return 1
    if root == ROOT:
        folders = iter_skill_dirs()
    else:
        folders = sorted(path for path in skills_dir.iterdir() if path.is_dir())
    if slugs is not None:
        wanted = set(slugs)
        folders = [folder for folder in folders if folder.name in wanted]
        missing = wanted - {folder.name for folder in folders}
        if missing:
            print(f"error: unknown skills {sorted(missing)}", file=sys.stderr)
            return 1
    if not folders:
        print("error: no skills to run", file=sys.stderr)
        return 1
    for folder in folders:
        error = run_skill(
            folder,
            command=command,
            candidates=candidates,
            judge=judge,
            timeout=timeout,
        )
        if error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        print(f"ok: {folder.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill",
        action="append",
        dest="skills",
        help="skill directory name; repeat for more than one. Default: every skill.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--config", type=Path, default=MODELS_PATH)
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("KSTACK_EVAL_TIMEOUT", "180")),
    )
    args = parser.parse_args(argv)
    return run_skills(
        args.root,
        args.skills,
        command=runner_command(),
        models_path=args.config,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    sys.exit(main())
