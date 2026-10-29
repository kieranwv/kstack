#!/usr/bin/env python3
"""Write dist/rules.md from skills/principle-*/SKILL.md."""

from __future__ import annotations

import argparse
import sys

from ruleslib import DIST_PATH, ROOT, collect_errors, iter_skill_dirs, load_skill, render_rules


def build() -> str:
    return render_rules([load_skill(folder) for folder in iter_skill_dirs()])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when dist/rules.md differs from the generated text",
    )
    args = parser.parse_args()
    errors = collect_errors(None)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    text = build()
    if args.check:
        if not DIST_PATH.is_file():
            print("error: dist/rules.md is missing", file=sys.stderr)
            return 1
        current = DIST_PATH.read_text(encoding="utf-8")
        if current != text:
            print(
                "error: dist/rules.md is out of date. Run python3 scripts/generate_rules_doc.py",
                file=sys.stderr,
            )
            return 1
        print("ok: dist/rules.md")
        return 0
    DIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIST_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {DIST_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
