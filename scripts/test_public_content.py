"""Tests for the public-content scan."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from check_public_content import hits_in, scan, term_pattern
from ruleslib import ROOT

TERM = "Ma" + "ia"
OTHER = "Kie" + "ran"
MARK = "\u98de\u4e66"


def write_config(folder: Path) -> Path:
    path = folder / "terms.json"
    path.write_text(
        json.dumps(
            {
                "terms": [TERM, OTHER, MARK],
                "patterns": ["\\boc_[0-9A-Za-z]{8,}\\b"],
                "allow_paths": ["LICENSE"],
            }
        ),
        encoding="utf-8",
    )
    return path


class PublicContentTests(unittest.TestCase):
    def test_tokens_do_not_match_a_longer_word(self) -> None:
        config = {"terms": [(OTHER, term_pattern(OTHER))], "patterns": []}
        longer = OTHER.lower() + "wv"
        hyphen = OTHER.lower() + "-stack"
        self.assertEqual(hits_in(longer, config), [])
        self.assertEqual(hits_in(hyphen, config), [(1, OTHER)])
        marked = {"terms": [(MARK, term_pattern(MARK))], "patterns": []}
        self.assertEqual(hits_in(MARK, marked), [(1, MARK)])

    def test_scan_flags_a_file_and_skips_the_config_and_allow_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = write_config(root)
            (root / "LICENSE").write_text(f"Copyright {OTHER}\n", encoding="utf-8")
            (root / "note.md").write_text(f"Hello {TERM}.\n", encoding="utf-8")
            ident = "oc_" + "1234abcd"
            (root / "ids.md").write_text(f"chat {ident}\n", encoding="utf-8")
            errors = scan(root, config)
        joined = "\n".join(errors)
        self.assertIn("note.md:1", joined)
        self.assertIn("ids.md:1", joined)
        self.assertNotIn("LICENSE", joined)
        self.assertNotIn("terms.json", joined)

    def test_repository_is_clean(self) -> None:
        self.assertEqual(scan(ROOT, ROOT / "config" / "public-content.json"), [])


if __name__ == "__main__":
    unittest.main()
