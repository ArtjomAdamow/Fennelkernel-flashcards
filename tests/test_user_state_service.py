"""Unit tests for flashcards_app.user_state_service (run from the project root).

    python -m unittest tests.test_user_state_service -v
"""

import json
import tempfile
import unittest
from pathlib import Path

from flashcards_app.deck_catalog import JsonDeckCatalog
from flashcards_app.parser import CardsFile
from flashcards_app.models import CardGroup, CardPosition, Flashcard
from flashcards_app.state import RawState
from flashcards_app.state_core import StateCore
from flashcards_app.user_state_service import UserStateService

DECKS = {"alpha": ["alpha:1", "alpha:2"], "beta": ["beta:1"], "gamma": ["gamma:1"]}


class FakePersistence:
    def __init__(self):
        self.writes = []

    def read(self):
        return RawState()

    def write(self, state):
        self.writes.append(state)


def card_source(deck_names):
    return [Flashcard(card_id, deck, "Q", "A") for deck in sorted(deck_names) for card_id in DECKS[deck]]


def write_course(path, *names):
    # phase 2: the catalog reads the deck names from the course file; the cards come from card_source
    decks = [{"id": f"{index:02d}", "name": name, "cards": []} for index, name in enumerate(names, 1)]
    path.write_text(json.dumps({"courseName": "c", "version": 2, "decks": decks}), encoding="utf-8")


def positions(card_ids, seed):
    return [CardPosition(card_id, 0.0, 0.0, 0.0) for card_id in card_ids]


class UserStateServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.course = Path(self._tmp.name) / "cards.json"
        write_course(self.course, "alpha", "beta", "gamma", "README", "None")
        self.persistence = FakePersistence()
        self.core = StateCore(self.persistence, card_source, positions)
        self.catalog = JsonDeckCatalog(CardsFile(self.course), exclude={"readme", "None"})
        self.service = UserStateService(self.core, self.catalog)
        self.core.load(["alpha", "beta"])
        self.core.refresh_deck_state(seed=1)

    def test_containers_are_the_cores_own_objects(self) -> None:
        for name in ("cards", "positions", "progress", "groups", "links", "enabled_decks", "card_by_id", "position_by_id"):
            self.assertIs(getattr(self.service, name), getattr(self.core, name), name)

    def test_only_existing_decks_can_be_enabled(self) -> None:
        self.assertFalse(self.service.enable_deck("does-not-exist"))
        self.assertFalse(self.service.enable_deck("None"))
        self.assertFalse(self.service.enable_deck("README"))
        self.assertFalse(self.service.enable_deck("alpha"))  # already enabled
        self.assertEqual(self.service.enabled_decks, ["alpha", "beta"])
        self.assertTrue(self.service.enable_deck("gamma"))
        self.assertEqual(self.service.enabled_decks, ["alpha", "beta", "gamma"])
        self.assertIn("gamma:1", self.service.position_by_id)

    def test_disable_deck(self) -> None:
        self.assertTrue(self.service.disable_deck("alpha"))
        self.assertFalse(self.service.disable_deck("alpha"))
        self.assertEqual([c.id for c in self.service.cards], ["beta:1"])

    def test_available_decks_follow_the_course_file_after_a_reload(self) -> None:
        # phase 2: the file is read again only by reload_decks() (the deck "Add" button)
        self.assertEqual(self.service.available_decks(), ["alpha", "beta", "gamma"])
        write_course(self.course, "alpha", "beta", "gamma", "delta")
        self.assertEqual(self.service.available_decks(), ["alpha", "beta", "gamma"])
        self.assertTrue(self.service.reload_decks())
        self.assertEqual(self.service.available_decks(), ["alpha", "beta", "delta", "gamma"])

    def test_an_invalid_course_file_on_reload_keeps_the_decks(self) -> None:
        self.course.write_text("{", encoding="utf-8")
        self.assertFalse(self.service.reload_decks())
        self.assertEqual(self.service.available_decks(), ["alpha", "beta", "gamma"])

    def test_mutations_reach_the_core(self) -> None:
        self.service.set_position("alpha:1", 0.1, 0.2, 0.3)
        self.service.set_difficulty("alpha:1", 42)
        self.service.mark_read("alpha:1")
        group_id = self.service.create_group("alpha:1", "G", "#123456")
        self.service.add_to_group("alpha:2", group_id)
        self.service.create_link("alpha:1", "alpha:2")
        self.assertEqual((self.core.position_by_id["alpha:1"].x, self.core.progress["alpha:1"].difficulty), (0.1, 42))
        self.assertTrue(self.core.progress["alpha:1"].read)
        self.assertEqual(self.core.groups[0].card_ids, ["alpha:1", "alpha:2"])
        self.assertEqual(len(self.core.links), 1)
        self.service.disconnect_link("alpha:2", "alpha:1")
        self.service.remove_from_group("alpha:2", group_id)
        self.service.delete_group(group_id)
        self.assertEqual((self.core.links, self.core.groups), ([], []))

    def test_new_group_ids_do_not_collide_with_duplicates_that_already_exist(self) -> None:
        # a state file written by the old numbering can contain the same id twice
        self.service.groups.extend([CardGroup("group-5", "B", "#1", []), CardGroup("group-5", "C", "#2", [])])
        self.assertEqual(self.service.create_group("alpha:1", "N", "#3"), "group-6")
        self.assertEqual([g.id for g in self.service.groups], ["group-5", "group-5", "group-6"])  # left as they are

    def test_deciding_group_comes_from_the_core(self) -> None:
        first = self.service.create_group("alpha:1", "A", "#aa0000")
        second = self.service.create_group("alpha:1", "B", "#00aa00")
        self.assertEqual(self.service.deciding_group("alpha:1").id, first)
        self.assertEqual(self.service.deciding_group("alpha:1", second).id, second)
        self.assertIsNone(self.service.deciding_group("beta:1"))

    def test_queries(self) -> None:
        self.assertEqual([c.id for c in self.service.visible_cards("beta")], ["beta:1"])
        self.assertEqual([c.id for c in self.service.visible_cards()], ["alpha:1", "alpha:2", "beta:1"])
        self.assertEqual(self.service.get_card_by_id("beta:1").deck, "beta")
        self.assertIsNone(self.service.get_position_by_id("nope"))

    def test_save_and_reset(self) -> None:
        self.service.set_difficulty("alpha:1", 50)
        self.service.save()
        self.assertEqual(self.persistence.writes[-1].progress["alpha:1"].difficulty, 50)
        self.service.reset_all_state(seed=3)
        self.assertEqual(self.core.progress["alpha:1"].difficulty, 1)


if __name__ == "__main__":
    unittest.main()
