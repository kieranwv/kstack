#!/usr/bin/env python3
"""Readers and checks shared by the rule-set scripts.

SKILL.md headings this package requires, in English:

- Rule
- Why
- Failure examples

Source and Provenance are not part of a rule. A heading or labeled line by
those names is an error. Case files have Prompt and Expected. Rubrics have at
least three numbered pass/fail criteria.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
DIST_PATH = ROOT / "dist" / "rules.md"
README_PATH = ROOT / "README.md"

REQUIRED_HEADINGS = ("Rule", "Why", "Failure examples")
FORBIDDEN_HEADINGS = ("Source", "Provenance")
CASE_HEADINGS = ("Prompt", "Expected")
ALLOWED_FRONTMATTER = ("name", "description", "rule", "status")
RULE_RE = re.compile(r"^R([1-9][0-9]*)$")
SLUG_RE = re.compile(r"^principle-[a-z0-9]+(?:-[a-z0-9]+)*$")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
SOURCE_LINE_RE = re.compile(r"(?im)^(source|provenance)\s*:")
CRITERION_RE = re.compile(r"^\d+\.\s+Pass:\s+\S.+\s+Fail:\s+\S.+")
README_LINK_RE = re.compile(r"\(\./skills/(principle-[a-z0-9-]+)/SKILL\.md\)")


@dataclass
class Skill:
    slug: str
    path: Path
    meta: dict[str, str]
    body: str
    number: int
    title: str
    status: str


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("frontmatter must start with ---")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("frontmatter is not closed")
    raw = text[4:end]
    body = text[end + 5 :]
    if body.startswith("\n"):
        body = body[1:]
    meta: dict[str, str] = {}
    for index, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        if line[0] in " \t":
            raise ValueError(f"frontmatter line {index} is indented")
        if ":" not in line:
            raise ValueError(f"frontmatter line {index} has no key")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not key:
            raise ValueError(f"frontmatter line {index} has an empty key")
        if key in meta:
            raise ValueError(f"duplicate frontmatter key {key}")
        meta[key] = value
    return meta, body


def headings(body: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    fenced = False
    for line in body.splitlines():
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING_RE.match(line)
        if match:
            found.append((len(match.group(1)), match.group(2).strip()))
    return found


def section_body(body: str, name: str, level: int = 2) -> str:
    lines = body.splitlines()
    start: int | None = None
    fenced = False
    for index, line in enumerate(lines):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) == level and match.group(2).strip() == name:
            start = index + 1
            break
    if start is None:
        return ""
    end = len(lines)
    fenced = False
    for index in range(start, len(lines)):
        line = lines[index]
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) <= level:
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def load_skill(folder: Path) -> Skill:
    path = folder / "SKILL.md"
    meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
    unknown = sorted(set(meta) - set(ALLOWED_FRONTMATTER))
    if unknown:
        raise ValueError(f"unknown frontmatter keys: {', '.join(unknown)}")
    for key in ("name", "description", "rule"):
        if key not in meta or not meta[key].strip():
            raise ValueError(f"frontmatter missing {key}")
    rule_match = RULE_RE.match(meta["rule"])
    if not rule_match:
        raise ValueError(f"rule must look like R1, got {meta['rule']!r}")
    status = meta.get("status", "active")
    if status not in ("active", "retired"):
        raise ValueError(f"status must be active or retired, got {status!r}")
    found = headings(body)
    title = next((text for level, text in found if level == 1), "")
    if not title:
        raise ValueError("SKILL.md needs an h1 title")
    return Skill(
        slug=folder.name,
        path=path,
        meta=meta,
        body=body,
        number=int(rule_match.group(1)),
        title=title,
        status=status,
    )


def iter_skill_dirs() -> list[Path]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(path for path in SKILLS_DIR.iterdir() if path.is_dir())


def layout_errors(folder: Path) -> list[str]:
    errors: list[str] = []
    prefix = folder.name
    if not SLUG_RE.match(folder.name):
        errors.append(f"{prefix}: folder name must match principle-<slug>")
    allowed = {"SKILL.md", "evals"}
    present = {path.name for path in folder.iterdir()}
    extra = present - allowed
    missing = allowed - present
    if extra:
        errors.append(f"{prefix}: unexpected files {sorted(extra)}")
    if missing:
        errors.append(f"{prefix}: missing {sorted(missing)}")
        return errors
    evals = folder / "evals"
    eval_present = {path.name for path in evals.iterdir()}
    eval_allowed = {"rubric.md", "cases"}
    if eval_present - eval_allowed:
        errors.append(f"{prefix}: unexpected eval files {sorted(eval_present - eval_allowed)}")
    if not (evals / "rubric.md").is_file():
        errors.append(f"{prefix}: missing evals/rubric.md")
    cases = evals / "cases"
    if not cases.is_dir():
        errors.append(f"{prefix}: missing evals/cases/")
        return errors
    case_files = sorted(cases.iterdir())
    if not case_files:
        errors.append(f"{prefix}: evals/cases/ is empty")
    for case in case_files:
        if not case.is_file() or case.suffix != ".md":
            errors.append(f"{prefix}: case is not a markdown file: {case.name}")
    return errors


def skill_text_errors(skill: Skill) -> list[str]:
    errors: list[str] = []
    prefix = skill.slug
    if skill.meta["name"] != skill.slug:
        errors.append(f"{prefix}: frontmatter name {skill.meta['name']!r} does not match the folder")
    if SOURCE_LINE_RE.search(skill.body):
        errors.append(f"{prefix}: source lines are not allowed")
    found = headings(skill.body)
    h2 = [text for level, text in found if level == 2]
    for name in FORBIDDEN_HEADINGS:
        if name in h2:
            errors.append(f"{prefix}: remove the {name} heading")
    for name in REQUIRED_HEADINGS:
        if name not in h2:
            errors.append(f"{prefix}: missing heading ## {name}")
            continue
        text = section_body(skill.body, name)
        if not text:
            errors.append(f"{prefix}: ## {name} is empty")
        elif name == "Failure examples" and not any(line.startswith("- ") for line in text.splitlines()):
            errors.append(f"{prefix}: ## Failure examples needs at least one bullet")
    return errors


def rubric_errors(folder: Path) -> list[str]:
    path = folder / "evals" / "rubric.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    found = headings(text)
    errors: list[str] = []
    prefix = folder.name
    if SOURCE_LINE_RE.search(text):
        errors.append(f"{prefix}: rubric has a source line")
    if not any(level == 1 and text_ == "Rubric" for level, text_ in found):
        errors.append(f"{prefix}: rubric needs an h1 'Rubric'")
    if not any(level == 2 and text_ == "Criteria" for level, text_ in found):
        errors.append(f"{prefix}: rubric needs ## Criteria")
    criteria = [
        line
        for line in section_body(text, "Criteria").splitlines()
        if CRITERION_RE.match(line)
    ]
    if len(criteria) < 3:
        errors.append(f"{prefix}: rubric needs at least three 'Pass: ... Fail: ...' criteria")
    return errors


def case_errors(folder: Path) -> list[str]:
    cases = folder / "evals" / "cases"
    if not cases.is_dir():
        return []
    errors: list[str] = []
    prefix = folder.name
    for case in sorted(cases.glob("*.md")):
        text = case.read_text(encoding="utf-8")
        label = f"{prefix}/{case.name}"
        if SOURCE_LINE_RE.search(text):
            errors.append(f"{label}: source lines are not allowed")
        found = headings(text)
        h2 = [name for level, name in found if level == 2]
        other = [(level, name) for level, name in found if level != 2]
        if h2 != list(CASE_HEADINGS):
            errors.append(f"{label}: headings must be ## Prompt then ## Expected")
        if other:
            errors.append(f"{label}: a case is only a prompt and the expected behavior")
        for name in CASE_HEADINGS:
            if not section_body(text, name):
                errors.append(f"{label}: ## {name} is empty")
    return errors


def readme_errors(slugs: set[str]) -> list[str]:
    if not README_PATH.is_file():
        return ["README.md is missing"]
    linked = set(README_LINK_RE.findall(README_PATH.read_text(encoding="utf-8")))
    errors: list[str] = []
    missing = sorted(slugs - linked)
    unknown = sorted(linked - slugs)
    if missing:
        errors.append(f"README.md does not link skills: {missing}")
    if unknown:
        errors.append(f"README.md links missing skills: {unknown}")
    return errors


def monotonicity_errors(base: dict[int, str], head: dict[int, str]) -> list[str]:
    """Rule numbers stay contiguous from R1 and only grow.

    `base` and `head` map a rule number to the skill slug that holds it.
    An empty base is the initial port: any contiguous R1..Rn set is allowed.
    After that, every base number and slug must remain, and new numbers append.
    """
    errors: list[str] = []
    if not head:
        if base:
            errors.append("every rule disappeared")
        return errors
    expected = set(range(1, max(head) + 1))
    if set(head) != expected:
        missing = sorted(expected - set(head))
        extra = sorted(set(head) - expected)
        errors.append(
            "rule numbers must be contiguous from R1"
            + (f"; missing {missing}" if missing else "")
            + (f"; unexpected {extra}" if extra else "")
        )
    disappeared = sorted(set(base) - set(head))
    if disappeared:
        errors.append(
            "rule numbers disappeared: " + ", ".join(f"R{number}" for number in disappeared)
        )
    for number, slug in sorted(base.items()):
        if number in head and head[number] != slug:
            errors.append(f"R{number} changed from {slug} to {head[number]}")
    if base:
        base_max = max(base)
        invented = sorted(number for number in head if number <= base_max and number not in base)
        if invented:
            errors.append(
                "rule numbers were inserted: " + ", ".join(f"R{number}" for number in invented)
            )
    return errors


def rules_at_ref(ref: str) -> dict[int, str]:
    listed = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    found: dict[int, str] = {}
    for path in listed.stdout.splitlines():
        parts = path.split("/")
        if len(parts) != 3 or parts[0] != "skills" or parts[2] != "SKILL.md":
            continue
        slug = parts[1]
        if not SLUG_RE.match(slug):
            continue
        shown = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        meta, _body = split_frontmatter(shown.stdout)
        rule = meta.get("rule", "")
        match = RULE_RE.match(rule)
        if not match:
            raise ValueError(f"{ref}:{path} has no rule number")
        number = int(match.group(1))
        if number in found:
            raise ValueError(f"{ref} has two skills numbered R{number}")
        found[number] = slug
    return found


def demote_body(body: str) -> str:
    lines_out: list[str] = []
    fenced = False
    skipped_title = False
    for line in body.splitlines():
        if line.startswith("```"):
            fenced = not fenced
            lines_out.append(line.rstrip())
            continue
        if not fenced:
            match = HEADING_RE.match(line)
            if match:
                level = len(match.group(1))
                if level == 1 and not skipped_title:
                    skipped_title = True
                    continue
                lines_out.append(f"{'#' * min(level + 1, 6)} {match.group(2).strip()}")
                continue
        lines_out.append(line.rstrip())
    collapsed: list[str] = []
    blank = False
    for line in lines_out:
        if line == "":
            if blank:
                continue
            blank = True
        else:
            blank = False
        collapsed.append(line)
    return "\n".join(collapsed).strip()


def render_rules(skills: list[Skill]) -> str:
    ordered = sorted(skills, key=lambda skill: skill.number)
    chunks = [
        "# Rules",
        "",
        "Generated from `skills/` by `scripts/generate_rules_doc.py`. Do not edit this file.",
        "",
    ]
    for skill in ordered:
        chunks.append(f"## R{skill.number}. {skill.title}")
        chunks.append("")
        if skill.status == "retired":
            chunks.append("Status: retired.")
            chunks.append("")
        relative = skill.path.relative_to(ROOT).as_posix()
        chunks.append(f"Skill: `{relative}`")
        chunks.append("")
        chunks.append(skill.meta["description"])
        chunks.append("")
        chunks.append(demote_body(skill.body))
        chunks.append("")
    text = "\n".join(chunks).strip() + "\n"
    collapsed: list[str] = []
    blank = False
    for line in text.splitlines():
        if line == "":
            if blank:
                continue
            blank = True
        else:
            blank = False
        collapsed.append(line)
    return "\n".join(collapsed).strip() + "\n"


def collect_errors(base_ref: str | None) -> list[str]:
    errors: list[str] = []
    skills: list[Skill] = []
    for folder in iter_skill_dirs():
        errors.extend(layout_errors(folder))
        try:
            skill = load_skill(folder)
        except (OSError, ValueError) as exc:
            errors.append(f"{folder.name}: {exc}")
            continue
        skills.append(skill)
        errors.extend(skill_text_errors(skill))
        errors.extend(rubric_errors(folder))
        errors.extend(case_errors(folder))
    numbers = [skill.number for skill in skills]
    if len(numbers) != len(set(numbers)):
        errors.append("rule numbers are not unique")
    head = {skill.number: skill.slug for skill in skills}
    if base_ref:
        try:
            base = rules_at_ref(base_ref)
        except (subprocess.CalledProcessError, ValueError) as exc:
            errors.append(f"cannot read rules at {base_ref}: {exc}")
            base = {}
        else:
            errors.extend(monotonicity_errors(base, head))
    else:
        errors.extend(monotonicity_errors({}, head))
    errors.extend(readme_errors({skill.slug for skill in skills}))
    return errors
