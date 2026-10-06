"""Tests for flashcards_app.deck_catalog (run from the project root).

    python -m unittest tests.test_deck_catalog -v

Uses only the standard library; `python -m pytest tests/test_deck_catalog.py` works too.
"""

import tempfile
import unittest
from pathlib import Path

from flashcards_app.deck_catalog import DeckCatalog


class DeckCatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cards_dir = Path(self._tmp.name)

    def touch(self, *names: str) -> None:
        for name in names:
            (self.cards_dir / name).write_text("x", encoding="utf-8")

    def test_lists_sorted_stems_of_md_files_only(self) -> None:
        self.touch("beta.md", "alpha.md", "notes.txt", "gamma.md.bak")
        self.assertEqual(DeckCatalog(self.cards_dir).available(), ["alpha", "beta"])

    def test_excluded_names_are_ignored_case_insensitively(self) -> None:
        self.touch("alpha.md", "README.md", "readme_extra.md", "None.md", "NONE2.md")
        catalog = DeckCatalog(self.cards_dir, exclude={"readme", "None"})
        self.assertEqual(catalog.available(), ["NONE2", "alpha", "readme_extra"])
        self.touch("Readme.md", "none.md")
        self.assertEqual(catalog.available(), ["NONE2", "alpha", "readme_extra"])

    def test_without_exclusions_everything_is_listed(self) -> None:
        self.touch("alpha.md", "README.md")
        self.assertEqual(DeckCatalog(self.cards_dir).available(), ["README", "alpha"])

    def test_directory_is_re_read_on_every_call(self) -> None:
        self.touch("alpha.md")
        catalog = DeckCatalog(self.cards_dir)
        self.assertEqual(catalog.available(), ["alpha"])
        self.touch("beta.md")
        self.assertEqual(catalog.available(), ["alpha", "beta"])
        (self.cards_dir / "alpha.md").unlink()
        self.assertEqual(catalog.available(), ["beta"])

    def test_missing_directory_gives_empty_list(self) -> None:
        self.assertEqual(DeckCatalog(self.cards_dir / "does-not-exist").available(), [])

    def test_is_available(self) -> None:
        self.touch("alpha.md", "None.md")
        catalog = DeckCatalog(self.cards_dir, exclude={"None"})
        self.assertTrue(catalog.is_available("alpha"))
        self.assertFalse(catalog.is_available("None"))
        self.assertFalse(catalog.is_available("missing"))


if __name__ == "__main__":
    unittest.main()
