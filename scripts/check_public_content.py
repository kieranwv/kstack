#!/usr/bin/env python3
"""Fail when configured terms or id patterns appear outside the allow list.

The term list and the patterns live in config/public-content.json. That file
is not scanned. allow_paths are paths relative to the repository root.
ASCII terms match only as whole tokens, so a longer token that merely starts
with the same letters is not a hit. Other terms match as substrings.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from ruleslib import ROOT

DEFAULT_CONFIG = ROOT / "config" / "public-content.json"
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache"}


def term_pattern(term: str) -> re.Pattern[str]:
    if term.isascii():
        return re.compile(rf"(?i)(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])")
    return re.compile(re.escape(term))


def load_config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    terms = data.get("terms")
    patterns = data.get("patterns")
    allow = data.get("allow_paths", [])
    if not isinstance(terms, list) or not all(isinstance(item, str) and item for item in terms):
        raise ValueError("terms must be a list of non-empty strings")
    if not isinstance(patterns, list) or not all(isinstance(item, str) and item for item in patterns):
        raise ValueError("patterns must be a list of non-empty strings")
    if not isinstance(allow, list) or not all(isinstance(item, str) for item in allow):
        raise ValueError("allow_paths must be a list of strings")
    return {
        "terms": [(item, term_pattern(item)) for item in terms],
        "patterns": [(item, re.compile(item)) for item in patterns],
        "allow_paths": {item.lstrip("./") for item in allow},
    }


def hits_in(text: str, config: dict) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        labels: list[str] = []
        for term, pattern in config["terms"]:
            if pattern.search(line):
                labels.append(term)
        for raw, pattern in config["patterns"]:
            if pattern.search(line):
                labels.append(raw)
        if labels:
            found.append((lineno, ", ".join(labels)))
    return found


def iter_files(root: Path, config_path: Path, allow: set[str]) -> list[Path]:
    config_rel = config_path.resolve().relative_to(root.resolve()).as_posix()
    skipped = allow | {config_rel}
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in skipped:
            continue
        files.append(path)
    return files


def scan(root: Path, config_path: Path) -> list[str]:
    config = load_config(config_path)
    errors: list[str] = []
    for path in iter_files(root, config_path, config["allow_paths"]):
        relative = path.relative_to(root).as_posix()
        for _lineno, label in hits_in(relative, config):
            errors.append(f"{relative}: path matches {label}")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for lineno, label in hits_in(text, config):
            errors.append(f"{relative}:{lineno}: {label}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        errors = scan(args.root, args.config)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, re.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("ok: public content")
    return 0


if __name__ == "__main__":
    sys.exit(main())
