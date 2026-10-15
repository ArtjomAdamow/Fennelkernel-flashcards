import unittest
from pathlib import Path
from unittest import mock

from flashcards_app import parser
from flashcards_app.parser import CardsFile, MarkdownSourceDisabled, format_technical_terms, load_decks

# phase 3: plain unittest (no pytest import), so the test explorer's unittest runner can load it without pytest
DATA = Path(__file__).resolve().parents[1] / "data"


class ParserTest(unittest.TestCase):
    def test_course_file_is_parsed(self) -> None:
        # phase 2: the decks come from data/cards.json
        cards_file = CardsFile(DATA / "cards.json")
        cards = cards_file.load_decks()
        self.assertTrue(len(cards) >= 20 and len(cards_file.deck_names) >= 2)
        self.assertTrue(all(card.question and card.answer for card in cards))
        self.assertTrue(all(cards_file.card(card.id) is card for card in cards))

    def test_md_source_is_switched_off(self) -> None:
        with self.assertRaisesRegex(MarkdownSourceDisabled, "will be used for other content"):
            load_decks(DATA / "cards")

    def test_populated_decks_are_parsed(self) -> None:
        # the .md parser is kept: switched on, it works as before
        with mock.patch.object(parser, "MD_SOURCE_ENABLED", True):
            cards = load_decks(DATA / "cards")
        self.assertGreaterEqual(len(cards), 20)
        self.assertTrue(any(card.question.startswith("What is a Heuristic?") for card in cards))
        self.assertTrue(all(card.answer for card in cards))

    def test_technical_term_formatting_preserves_existing_code(self) -> None:
        formatted = format_technical_terms("Use snake_case and already `safe_name`.")

        self.assertEqual(formatted, "Use `snake_case` and already `safe_name`.")


if __name__ == "__main__":
    unittest.main()
