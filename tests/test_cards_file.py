"""Tests for the course file data/cards.json: flashcards_app.parser.CardsFile (run from the project root).

    python -m unittest tests.test_cards_file -v

phase 3: moved here from the retired modules/loader/test_loader_draft.py; plain unittest, no pytest.
The catalog over the course file (JsonDeckCatalog) is tested in tests/test_deck_catalog.py.
"""

import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest import mock

from flashcards_app import parser
from flashcards_app.deck_catalog import DeckCatalog, JsonDeckCatalog
from flashcards_app.models import CardPosition, CardProgress, Flashcard
from flashcards_app.parser import CardsFile, MarkdownSourceDisabled, comb_id, format_markdown_terms, load_decks, parse_deck

CARDS_FILE = Path(__file__).resolve().parents[1] / "data" / "cards.json"


def deck(deck_id: str, name: str, *cards: dict) -> dict:
    return {"id": deck_id, "name": name, "cards": list(cards)}


def card(card_id: str, **extra) -> dict:
    return {"card_id": card_id, "question": f"Q {card_id}", "feedback": f"A {card_id}", **extra}


class CourseFileTest(unittest.TestCase):
    """The real data/cards.json, read once for the class."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.course = CardsFile(CARDS_FILE)
        cls.cards = {c.id: c for c in cls.course.load_decks()}

    def test_every_card_has_a_stack_a_unique_comb_id_and_texts(self) -> None:
        cards = self.course.load_decks()
        self.assertGreaterEqual(len(cards), 20)
        self.assertEqual(len(self.cards), len(cards))
        self.assertLessEqual({c.stack for c in cards}, {1, 2, 3})
        self.assertTrue(all(c.question and c.answer for c in cards))

    def test_every_card_resolves_by_comb_id(self) -> None:
        self.assertTrue(all(self.course.card(key) is c for key, c in self.cards.items()))

    def test_comb_id_is_stack_deck_id_card_id(self) -> None:
        graded = self.cards["302032"]
        self.assertEqual((graded.question, graded.stack, graded.difficulty), ("What is Git, fundamentally?", 3, "easy"))
        self.assertEqual(graded.weblink, "https://en.wikipedia.org/wiki/Git")
        self.assertEqual((self.cards["202044"].stack, self.cards["202044"].difficulty), (2, None))
        self.assertEqual(self.cards["102001"].stack, 1)

    def test_markdown_survives_parsing(self) -> None:
        # fenced code keeps its lines and gets no backticks inside
        self.assertIn("```\nmy_string = 'DS-Bootcamp'\nmy_string[3:7]\n```", self.cards["201002"].question)
        # <placeholders> are kept, not stripped as HTML tags
        self.assertEqual(self.cards["102013"].question, "What does git switch -c <branch> do, and what is its older equivalent?")
        # bullet lists keep their line breaks
        self.assertEqual(self.cards["103001"].answer.count("\n- "), 3)

    def test_the_catalog_lists_the_decks_of_the_cards(self) -> None:
        self.assertEqual(JsonDeckCatalog(self.course).available(), sorted({c.deck for c in self.cards.values()}))


class CardsFileTest(unittest.TestCase):
    """CardsFile on small course files in a temp folder."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "cards.json"

    def write(self, *decks: dict, version=2) -> Path:
        self.path.write_text(json.dumps({"courseName": "c", "version": version, "decks": list(decks)}), encoding="utf-8")
        return self.path

    def test_stack_is_decided_by_keys(self) -> None:
        self.write(deck("07", "d", card("001"), card("002", quiz=True), card("003", quiz=True, difficulty="hard")))
        self.assertEqual([(c.id, c.stack, c.difficulty) for c in CardsFile(self.path).load_decks()],
                         [("107001", 1, None), ("207002", 2, None), ("307003", 3, "hard")])

    def test_decks_are_filtered_and_ordered_by_name(self) -> None:
        cards_file = CardsFile(self.write(deck("01", "beta", card("001")), deck("02", "alpha", card("001"))))
        self.assertEqual(cards_file.deck_names, ("alpha", "beta"))
        self.assertEqual([c.deck for c in cards_file.load_decks()], ["alpha", "beta"])
        self.assertEqual([c.id for c in cards_file.load_decks(["beta"])], ["101001"])
        self.assertEqual(cards_file.load_decks([]), [])

    def test_load_decks_returns_a_new_list(self) -> None:
        cards_file = CardsFile(self.write(deck("01", "d", card("001"))))
        cards_file.load_decks().clear()
        self.assertEqual(len(cards_file.load_decks()), 1)

    def test_the_file_is_read_once(self) -> None:
        cards_file = CardsFile(self.write(deck("01", "alpha", card("001"))))
        self.write(deck("01", "alpha", card("001")), deck("02", "beta", card("001")))
        self.assertEqual(cards_file.deck_names, ("alpha",))
        self.assertEqual([c.id for c in cards_file.load_decks()], ["101001"])
        self.path.unlink()
        self.assertEqual(len(cards_file.load_decks(["alpha"])), 1)

    def test_reload_reads_the_file_again(self) -> None:
        # phase 2: the deck "Add" button reloads, so decks added to the file can be enabled without a restart
        cards_file = CardsFile(self.write(deck("01", "alpha", card("001"))))
        self.write(deck("01", "alpha", card("001")), deck("02", "beta", card("001")))
        self.assertTrue(cards_file.reload())
        self.assertEqual(cards_file.deck_names, ("alpha", "beta"))
        self.assertEqual(cards_file.card("102001").deck, "beta")
        self.assertEqual([c.id for c in cards_file.load_decks(["beta"])], ["102001"])

    def test_a_failed_reload_keeps_the_course(self) -> None:
        for broken in ("{", None):  # None: the file is deleted
            with self.subTest(broken=broken):
                cards_file = CardsFile(self.write(deck("01", "alpha", card("001"))))
                if broken is None:
                    self.path.unlink()
                else:
                    self.path.write_text(broken, encoding="utf-8")
                self.assertFalse(cards_file.reload())
                self.assertEqual(cards_file.deck_names, ("alpha",))
                self.assertIsNotNone(cards_file.card("101001"))

    def test_every_card_is_readable_by_comb_id_enabled_or_not(self) -> None:
        cards_file = CardsFile(self.write(deck("01", "alpha", card("001")), deck("02", "beta", card("001", quiz=True))))
        self.assertEqual([c.id for c in cards_file.load_decks(["alpha"])], ["101001"])
        beta = cards_file.card("202001")  # deck beta is not loaded above
        self.assertEqual((beta.deck, beta.question, beta.answer), ("beta", "Q 001", "A 001"))
        self.assertIsNone(cards_file.card("999999"))

    def test_a_missing_file_is_an_error(self) -> None:
        with self.assertRaises(FileNotFoundError):
            CardsFile(self.path)

    def test_an_empty_question_is_skipped(self) -> None:
        self.write(deck("01", "d", {"card_id": "001", "question": "  ", "feedback": "A"}))
        self.assertEqual(CardsFile(self.path).load_decks(), [])

    def test_other_versions_are_refused(self) -> None:
        for version in (None, 1, 3, "2"):
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, "unsupported version"):
                CardsFile(self.write(deck("01", "d", card("001")), version=version))

    def test_invalid_cards_and_decks_are_refused(self) -> None:
        # 1 + "1" + "1001" and 1 + "11" + "001" both give "111001"
        self.assertEqual(comb_id(1, "1", "1001"), comb_id(1, "11", "001"))
        cases = {
            "'quiz' must be true": [deck("01", "d", card("001", quiz=False))],
            "'feedback' must be a string": [deck("01", "d", {"card_id": "001", "question": "Q"})],
            "duplicate deck name": [deck("01", "d"), deck("02", "d")],
            "duplicate comb_id": [deck("1", "a", card("1001")), deck("11", "b", card("001"))],
        }
        for message, decks in cases.items():
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                CardsFile(self.write(*decks))


class MarkdownTermsTest(unittest.TestCase):
    def test_existing_code_is_preserved(self) -> None:
        self.assertEqual(format_markdown_terms("Use snake_case and already `safe_name`."), "Use `snake_case` and already `safe_name`.")

    def test_fences_math_and_placeholders_are_skipped(self) -> None:
        value = "Call my_func() on <branch_name>:\n```\nx_val = 1\n```\n$feature_{1}$ and $a_b$"
        expected = "Call `my_func()` on <branch_name>:\n```\nx_val = 1\n```\n$feature_{1}$ and $a_b$"
        self.assertEqual(format_markdown_terms(value), expected)


class MarkdownSourceSwitchTest(unittest.TestCase):
    """The .md source stays in the code, switched off (the catalog's notice: tests/test_deck_catalog.py)."""

    def test_the_parser_entry_points_raise_the_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "alpha.md").write_text("", encoding="utf-8")
            for name, call in (("parse_deck", lambda: parse_deck(folder / "alpha.md")), ("load_decks", lambda: load_decks(folder))):
                with self.subTest(name), self.assertRaisesRegex(MarkdownSourceDisabled, "will be used for other content"):
                    call()

    def test_a_catalog_built_while_switched_on_is_switched_off_later(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(parser, "MD_SOURCE_ENABLED", True):
                catalog = DeckCatalog(Path(tmp))
            with self.assertRaises(MarkdownSourceDisabled):
                catalog.available()


class ModelTest(unittest.TestCase):
    def test_flashcard_keeps_the_positional_constructor_and_id(self) -> None:
        # the app and its tests build cards as Flashcard(id, deck, question, answer)
        c = Flashcard("x:1", "x", "Q", "A")
        self.assertEqual((c.id, c.comb_id, c.stack, c.difficulty, c.explain, c.weblink), ("x:1", "x:1", 1, None, None, None))

    def test_state_models_are_keyed_by_comb_id(self) -> None:
        # asdict() gives the field names, so the keys of the state file follow the models
        self.assertEqual(next(iter(asdict(CardPosition("101001", 0.0, 0.0, 0.0)))), "comb_id")
        self.assertEqual(asdict(CardProgress("101001")), {"comb_id": "101001", "read": False, "difficulty": 1})
        self.assertEqual(CardProgress("101001", difficulty=500).difficulty, 100)


if __name__ == "__main__":
    unittest.main()
