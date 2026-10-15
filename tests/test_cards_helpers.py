"""Unit tests for the pure card helpers in flashcards_app.services.cards (run from the project root).

    python -m unittest tests.test_cards_helpers -v
"""

import unittest

from flashcards_app.models import CardProgress, Flashcard
from flashcards_app.services.cards import adjacent_card, choose_random_card, select_from_click


def cards(*ids):
    return [Flashcard(card_id, card_id.split(":")[0], "Q", "A") for card_id in ids]


class RecordingRng:
    """Stands in for the random module: records what choices() was asked and returns the first candidate."""

    def __init__(self):
        self.asked = None

    def choices(self, candidates, weights, k):
        self.asked = (list(candidates), list(weights), k)
        return [candidates[0]]


class ChooseRandomCardTest(unittest.TestCase):
    def test_nothing_to_choose_from(self) -> None:
        self.assertIsNone(choose_random_card([], {}, RecordingRng()))

    def test_only_read_cards_are_candidates_when_there_are_any(self) -> None:
        progress = {"a:2": CardProgress("a:2", True, 10), "a:3": CardProgress("a:3", False, 10)}
        rng = RecordingRng()
        choose_random_card(cards("a:1", "a:2", "a:3"), progress, rng)
        self.assertEqual([c.id for c in rng.asked[0]], ["a:2"])

    def test_all_cards_are_candidates_when_none_was_read(self) -> None:
        rng = RecordingRng()
        choose_random_card(cards("a:1", "a:2"), {"a:1": CardProgress("a:1")}, rng)
        self.assertEqual([c.id for c in rng.asked[0]], ["a:1", "a:2"])

    def test_the_lower_the_difficulty_the_higher_the_weight(self) -> None:
        progress = {"a:1": CardProgress("a:1", True, 1), "a:2": CardProgress("a:2", True, 50), "a:3": CardProgress("a:3", True, 100)}
        rng = RecordingRng()
        choose_random_card(cards("a:1", "a:2", "a:3"), progress, rng)
        self.assertEqual(rng.asked[1], [100, 51, 1])
        self.assertEqual(rng.asked[2], 1)

    def test_a_card_without_progress_weighs_like_difficulty_one(self) -> None:
        rng = RecordingRng()
        choose_random_card(cards("a:1"), {}, rng)
        self.assertEqual(rng.asked[1], [100])


class AdjacentCardTest(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertIsNone(adjacent_card([], None, 1))

    def test_without_a_selection_next_starts_at_the_first_and_previous_at_the_last(self) -> None:
        deck = cards("a:1", "a:2", "a:3")
        self.assertEqual(adjacent_card(deck, None, 1).id, "a:1")
        self.assertEqual(adjacent_card(deck, None, -1).id, "a:3")
        self.assertEqual(adjacent_card(deck, "elsewhere:9", 1).id, "a:1")

    def test_moves_and_wraps_around(self) -> None:
        deck = cards("a:1", "a:2", "a:3")
        self.assertEqual(adjacent_card(deck, "a:1", 1).id, "a:2")
        self.assertEqual(adjacent_card(deck, "a:3", 1).id, "a:1")
        self.assertEqual(adjacent_card(deck, "a:1", -1).id, "a:3")
        self.assertEqual(adjacent_card(deck, "a:2", -1).id, "a:1")


class SelectFromClickTest(unittest.TestCase):
    def test_the_hovered_point_wins_over_the_clicked_one(self) -> None:
        click = {"points": [{"customdata": "a:1"}]}
        self.assertEqual(select_from_click(click, {"points": [{"customdata": "a:2"}]}), "a:2")
        self.assertEqual(select_from_click(click, None), "a:1")
        self.assertEqual(select_from_click(click, {"points": []}), "a:1")
        self.assertEqual(select_from_click(click, {"points": [{"customdata": None}]}), "a:1")


if __name__ == "__main__":
    unittest.main()
