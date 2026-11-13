#!/usr/bin/env python3
"""Record and check the SHA-256 of each skill against its last eval.

The hashed bytes are SKILL.md as stored, with no newline normalization.
``evals/eval-hash.json`` holds that hash. ``basis`` is ``baseline`` when the
hash was sealed without a model run, and ``run`` when ``scripts/run_evals.py``
wrote ``evals/last-run.md`` for those same bytes.

``check`` fails when the file and the record disagree. When ``--base`` already
has a record for the skill and SKILL.md differs from that base, ``check`` also
fails until the head record is a run whose last-run.md names the new hash.
Sealing a fresh baseline does not satisfy that second check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from ruleslib import ROOT, split_frontmatter

RECORD_NAME = "eval-hash.json"
LAST_RUN_NAME = "last-run.md"
SUBJECT = "SKILL.md"
RECORD_KEYS = frozenset({"basis", "skill_sha256", "subject"})
BASES = frozenset({"baseline", "run"})


def skill_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record_payload(digest: str, basis: str) -> dict[str, str]:
    if basis not in BASES:
        raise ValueError(f"basis must be baseline or run, got {basis!r}")
    return {"basis": basis, "skill_sha256": digest, "subject": SUBJECT}


def write_record(folder: Path, basis: str) -> str:
    digest = skill_hash((folder / "SKILL.md").read_bytes())
    path = folder / "evals" / RECORD_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record_payload(digest, basis), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return digest


def write_last_run(folder: Path, *, runner: str, ran_at: str, body: str) -> str:
    if "\n" in runner or "\n" in ran_at:
        raise ValueError("runner and ran_at must be single lines")
    digest = skill_hash((folder / "SKILL.md").read_bytes())
    text = (
        "---\n"
        f"skill_sha256: {digest}\n"
        f"runner: {runner}\n"
        f"ran_at: {ran_at}\n"
        "---\n\n"
        + body.strip()
        + "\n"
    )
    path = folder / "evals" / LAST_RUN_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    write_record(folder, "run")
    return digest


def read_record(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"evals/{RECORD_NAME} is not valid JSON: {exc}"
    if not isinstance(data, dict):
        return None, f"evals/{RECORD_NAME} must be a JSON object"
    return data, None


def read_last_run(path: Path) -> tuple[dict[str, str] | None, str | None]:
    if not path.is_file():
        return None, None
    try:
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        return None, f"evals/{LAST_RUN_NAME} frontmatter: {exc}"
    return meta, None


def ref_exists(root: Path, ref: str) -> bool:
    probe = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=root,
        capture_output=True,
    )
    return probe.returncode == 0


def git_bytes(root: Path, ref: str, path: str) -> tuple[bytes | None, str | None]:
    """Return ``(bytes, error)``. A missing path is ``(None, None)``."""
    spec = f"{ref}:{path}"
    probe = subprocess.run(
        ["git", "cat-file", "-e", spec],
        cwd=root,
        capture_output=True,
    )
    if probe.returncode != 0:
        return None, None
    shown = subprocess.run(
        ["git", "show", spec],
        cwd=root,
        capture_output=True,
    )
    if shown.returncode != 0:
        detail = shown.stderr.decode("utf-8", errors="replace").strip()
        return None, f"cannot read {path} at {ref}: {detail}"
    return shown.stdout, None


def evaluation_errors(
    *,
    slug: str,
    skill_bytes: bytes,
    record: dict | None,
    last_run: dict[str, str] | None,
    base_skill_bytes: bytes | None,
    base_record: dict | None,
) -> list[str]:
    errors: list[str] = []
    digest = skill_hash(skill_bytes)
    if record is None:
        errors.append(f"{slug}: missing evals/{RECORD_NAME}")
        return errors
    unknown = sorted(set(record) - RECORD_KEYS)
    if unknown:
        errors.append(f"{slug}: evals/{RECORD_NAME} has unknown keys {unknown}")
    if record.get("subject") != SUBJECT:
        errors.append(f"{slug}: evals/{RECORD_NAME} subject must be {SUBJECT}")
    recorded = record.get("skill_sha256")
    basis = record.get("basis")
    if not isinstance(recorded, str) or recorded != digest:
        errors.append(
            f"{slug}: SKILL.md changed since evals/{RECORD_NAME}. "
            "Run python3 scripts/run_evals.py before this can pass."
        )
    if basis not in BASES:
        errors.append(f"{slug}: evals/{RECORD_NAME} basis must be baseline or run")
        return errors
    if basis == "baseline" and last_run is not None:
        errors.append(f"{slug}: a baseline record must not have evals/{LAST_RUN_NAME}")
    if basis == "run":
        if last_run is None:
            errors.append(f"{slug}: a run record is missing evals/{LAST_RUN_NAME}")
        else:
            if last_run.get("skill_sha256") != digest:
                errors.append(
                    f"{slug}: evals/{LAST_RUN_NAME} does not record the current SKILL.md hash"
                )
            if not last_run.get("runner", "").strip() or not last_run.get("ran_at", "").strip():
                errors.append(f"{slug}: evals/{LAST_RUN_NAME} needs runner and ran_at")
    changed = (
        base_record is not None
        and base_skill_bytes is not None
        and base_skill_bytes != skill_bytes
    )
    if changed and recorded == digest and (
        basis != "run" or last_run is None or last_run.get("skill_sha256") != digest
    ):
        errors.append(
            f"{slug}: skill changed since the recorded eval and the eval was not rerun. "
            "Run python3 scripts/run_evals.py."
        )
    return errors


def check_tree(root: Path, base_ref: str | None = None) -> list[str]:
    errors: list[str] = []
    if base_ref and not ref_exists(root, base_ref):
        return [f"git ref {base_ref} does not exist"]
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return ["skills/ is missing"]
    folders = sorted(path for path in skills_dir.iterdir() if path.is_dir())
    for folder in folders:
        skill_path = folder / "SKILL.md"
        if not skill_path.is_file():
            continue
        skill_bytes = skill_path.read_bytes()
        record_path = folder / "evals" / RECORD_NAME
        last_run_path = folder / "evals" / LAST_RUN_NAME
        record, record_error = read_record(record_path)
        last_run, last_run_error = read_last_run(last_run_path)
        if record_error:
            errors.append(f"{folder.name}: {record_error}")
        if last_run_error:
            errors.append(f"{folder.name}: {last_run_error}")
        base_skill: bytes | None = None
        base_record: dict | None = None
        if base_ref and not record_error:
            rel_skill = skill_path.relative_to(root).as_posix()
            rel_record = record_path.relative_to(root).as_posix()
            base_skill, skill_git_error = git_bytes(root, base_ref, rel_skill)
            if skill_git_error:
                errors.append(f"{folder.name}: {skill_git_error}")
            raw_record, record_git_error = git_bytes(root, base_ref, rel_record)
            if record_git_error:
                errors.append(f"{folder.name}: {record_git_error}")
            elif raw_record is not None:
                try:
                    parsed = json.loads(raw_record.decode("utf-8"))
                except (UnicodeError, json.JSONDecodeError) as exc:
                    errors.append(
                        f"{folder.name}: evals/{RECORD_NAME} at {base_ref} is not JSON: {exc}"
                    )
                else:
                    if isinstance(parsed, dict):
                        base_record = parsed
                    else:
                        errors.append(
                            f"{folder.name}: evals/{RECORD_NAME} at {base_ref} is not an object"
                        )
        if record_error:
            continue
        errors.extend(
            evaluation_errors(
                slug=folder.name,
                skill_bytes=skill_bytes,
                record=record,
                last_run=last_run,
                base_skill_bytes=base_skill,
                base_record=base_record,
            )
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="fail when a skill hash does not match its eval record")
    check.add_argument(
        "--base",
        metavar="REF",
        help="git ref that already records evals (for example origin/main)",
    )
    args = parser.parse_args()
    if args.command == "check":
        errors = check_tree(ROOT, args.base)
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 1
        print("ok: eval hashes")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
