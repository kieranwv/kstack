#!/usr/bin/env python3
"""Check that every extends target is a skill on pstack's default branch.

The target is the directory name under pstack/skills/. This script looks at
whatever checkout you pass, or it shallow-clones https://github.com/cursor/plugins
at main. It does not record a commit, a tag, or a version.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from ruleslib import Skill, iter_skill_dirs, load_skill

PSTACK_CLONE_URL = "https://github.com/cursor/plugins.git"
PSTACK_BRANCH = "main"


def pstack_skill_names(pstack_root: Path) -> set[str]:
    skills = pstack_root / "skills"
    if not skills.is_dir():
        raise ValueError(f"{pstack_root} has no skills directory")
    return {
        path.name
        for path in skills.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }


def extends_errors(skills: list[Skill], names: set[str]) -> list[str]:
    errors: list[str] = []
    for skill in skills:
        for target in skill.extends:
            if target not in names:
                errors.append(
                    f"{skill.slug}: extends {target}, which is not a skill directory on pstack"
                )
    return errors


def pstack_sha(pstack_root: Path) -> str | None:
    shown = subprocess.run(
        ["git", "-C", str(pstack_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if shown.returncode != 0:
        return None
    return shown.stdout.strip() or None


def clone_pstack(dest: Path) -> Path:
    """Shallow-clone cursor/plugins at main and return the pstack directory."""
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            PSTACK_BRANCH,
            "--filter=blob:none",
            "--sparse",
            PSTACK_CLONE_URL,
            str(dest),
        ],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(dest), "sparse-checkout", "set", "pstack"],
        check=True,
    )
    return dest / "pstack"


def load_skills() -> tuple[list[Skill], list[str]]:
    skills: list[Skill] = []
    errors: list[str] = []
    for folder in iter_skill_dirs():
        try:
            skills.append(load_skill(folder))
        except (OSError, ValueError) as exc:
            errors.append(f"{folder.name}: {exc}")
    return skills, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pstack",
        type=Path,
        help="pstack directory (the one that contains skills/). Omit to clone main.",
    )
    args = parser.parse_args()
    skills, errors = load_skills()
    if args.pstack is not None:
        pstack_root = args.pstack
        sha = pstack_sha(pstack_root)
        try:
            names = pstack_skill_names(pstack_root)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        errors.extend(extends_errors(skills, names))
    else:
        with tempfile.TemporaryDirectory(prefix="kstack-pstack-") as tmp:
            try:
                pstack_root = clone_pstack(Path(tmp) / "plugins")
            except subprocess.CalledProcessError as exc:
                print(f"error: could not clone pstack main: {exc}", file=sys.stderr)
                return 1
            sha = pstack_sha(pstack_root)
            try:
                names = pstack_skill_names(pstack_root)
            except ValueError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            errors.extend(extends_errors(skills, names))
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    where = f" at {sha}" if sha else ""
    print(f"ok: refs (pstack {PSTACK_BRANCH}{where})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
