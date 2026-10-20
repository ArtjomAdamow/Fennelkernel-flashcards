"""Tests for project.content.deck_catalog (run from the project root).

    python -m unittest tests.test_deck_catalog -v

Uses only the standard library; `python -m pytest tests/test_deck_catalog.py` works too.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from project.content import parser
from project.content.deck_catalog import DeckCatalog, JsonDeckCatalog
from project.content.parser import CardsFile, MarkdownSourceDisabled


class DeckCatalogTest(unittest.TestCase):
    """The .md catalog (phase 2: switched off in the app; switched on here to keep its behaviour covered)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cards_dir = Path(self._tmp.name)
        switch = mock.patch.object(parser, "MD_SOURCE_ENABLED", True)
        switch.start()
        self.addCleanup(switch.stop)

    def test_is_switched_off_with_the_notice(self) -> None:
        # phase 2: .md decks will be used for other content
        self.touch("alpha.md")
        catalog = DeckCatalog(self.cards_dir)
        with mock.patch.object(parser, "MD_SOURCE_ENABLED", False):
            for call in (lambda: DeckCatalog(self.cards_dir), catalog.available):
                with self.assertRaisesRegex(MarkdownSourceDisabled, "will be used for other content"):
                    call()

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


class JsonDeckCatalogTest(unittest.TestCase):
    """The decks of the course file (phase 2)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "cards.json"

    def write(self, *names: str) -> None:
        decks = [{"id": f"{index:02d}", "name": name, "cards": []} for index, name in enumerate(names, 1)]
        self.path.write_text(json.dumps({"courseName": "c", "version": 2, "decks": decks}), encoding="utf-8")

    def test_lists_sorted_names_without_excluded_ones(self) -> None:
        self.write("beta", "alpha", "README", "None")
        catalog = JsonDeckCatalog(CardsFile(self.path), exclude={"readme", "none"})
        self.assertEqual(catalog.available(), ["alpha", "beta"])
        self.assertTrue(catalog.is_available("alpha"))
        self.assertFalse(catalog.is_available("None"))
        self.assertFalse(catalog.is_available("missing"))

    def test_the_file_is_read_again_only_on_reload(self) -> None:
        self.write("alpha")
        catalog = JsonDeckCatalog(CardsFile(self.path))
        self.write("alpha", "beta")
        self.assertEqual(catalog.available(), ["alpha"])
        self.assertTrue(catalog.reload())
        self.assertEqual(catalog.available(), ["alpha", "beta"])

    def test_an_invalid_file_on_reload_keeps_the_decks(self) -> None:
        self.write("alpha")
        catalog = JsonDeckCatalog(CardsFile(self.path))
        self.path.write_text("{", encoding="utf-8")
        self.assertFalse(catalog.reload())
        self.assertEqual(catalog.available(), ["alpha"])


if __name__ == "__main__":
    unittest.main()
