import tempfile
import unittest
from pathlib import Path
from unittest import mock

from project.content import parser
from project.content.parser import CardsFile, MarkdownSourceDisabled, format_technical_terms, load_decks

# phase 3: plain unittest (no pytest import), so the test explorer's unittest runner can load it without pytest
DATA = Path(__file__).resolve().parents[1] / "data"

# The real .md decks moved out of data/cards (now modules/book/data/cards, git-ignored), so the kept
# .md parser is tested on a deck in the same format: <details>/<summary> blocks, "<sd" artifacts,
# a placeholder card and a block without a summary (both skipped).
MD_DECK = """# Fundamentals

<details>
  <summary><b> <sd

  What is a Heuristic?</b></summary>

  Definition: a practical, experience-based shortcut
  Trade-off: fast, but no guarantee of optimality
</details>

<details>
  <summary><b>Which helper splits the data?</b></summary>

  Use train_test_split() from scikit-learn
</details>

<details>
  <summary><b>[Question]:</b></summary>

  placeholder, skipped
</details>

<details>
  no summary, skipped
</details>
"""


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
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "Fundamentals.md").write_text(MD_DECK, encoding="utf-8")
            (folder / "Other deck.md").write_text("# Other deck\n", encoding="utf-8")
            with mock.patch.object(parser, "MD_SOURCE_ENABLED", True):
                cards = load_decks(folder)
                selected = load_decks(folder, ["Other deck"])

        self.assertEqual([card.id for card in cards], ["Fundamentals:1", "Fundamentals:2"])
        self.assertTrue(all(card.deck == "Fundamentals" for card in cards))
        self.assertEqual(cards[0].question, "What is a Heuristic?")
        self.assertEqual(
            cards[0].answer,
            "Definition: a practical, experience-based shortcut Trade-off: fast, but no guarantee of optimality",
        )
        self.assertEqual(cards[1].answer, "Use `train_test_split()` from scikit-learn")
        self.assertEqual(selected, [])

    def test_technical_term_formatting_preserves_existing_code(self) -> None:
        formatted = format_technical_terms("Use snake_case and already `safe_name`.")

        self.assertEqual(formatted, "Use `snake_case` and already `safe_name`.")


if __name__ == "__main__":
    unittest.main()
