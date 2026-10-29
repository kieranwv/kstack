#!/usr/bin/env python3
"""Check skill layout, English section headings, evals, and rule numbers.

Required headings in each SKILL.md are Rule, Why, and Failure examples.
Source lines are not required and are rejected when present. Rule numbers are
unique and contiguous from R1. Compared with --base, a number that already
exists must keep its skill, and new numbers may only be appended.
"""

from __future__ import annotations

import argparse
import sys

from ruleslib import collect_errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        metavar="REF",
        help="git ref whose rule numbers must still be present (for example origin/main)",
    )
    args = parser.parse_args()
    errors = collect_errors(args.base)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("ok: skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
