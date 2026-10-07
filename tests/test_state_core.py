"""Unit tests for flashcards_app.state_core with fake sources (run from the project root).

    python -m unittest tests.test_state_core -v
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from flashcards_app.models import CardGroup, CardLink, CardPosition, CardProgress, Flashcard
from flashcards_app.state import JsonStateStore, RawState
from flashcards_app.state_core import STARTUP_SEED, StateCore

DECKS = {
    "alpha": ["alpha:1", "alpha:2"],
    "beta": ["beta:1"],
    "gamma": ["gamma:1", "gamma:2"],
}


class FakePersistence:
    def __init__(self, raw=None):
        self.raw = raw
        self.writes = []

    def read(self):
        return self.raw

    def write(self, state):
        self.writes.append(state)


def card_source(deck_names):
    return [
        Flashcard(card_id, deck, f"Q {card_id}", f"A {card_id}")
        for deck in sorted(deck_names)
        for card_id in DECKS[deck]
    ]


class PositionSpy:
    """Position source whose coordinates reveal the seed that was used."""

    def __init__(self):
        self.calls = []

    def __call__(self, card_ids, seed):
        self.calls.append((list(card_ids), seed))
        return [CardPosition(card_id, seed % 100 / 100, index / 10, 0.0) for index, card_id in enumerate(card_ids)]


def make_core(raw=None, available=("alpha", "beta", "gamma")):
    persistence = FakePersistence(raw)
    spy = PositionSpy()
    core = StateCore(persistence, card_source, spy)
    core.load(list(available))
    return core, persistence, spy


def stored_raw():
    return RawState(
        positions=[CardPosition("alpha:1", 0.5, 0.5, 0.5), CardPosition("gamma:1", 0.9, 0.9, 0.9)],
        progress={"alpha:1": CardProgress("alpha:1", True, 55), "gamma:1": CardProgress("gamma:1", True, 80)},
        groups=[CardGroup("group-1", "X", "#fff", ["alpha:1", "gamma:1"])],
        links=[CardLink("alpha:1", "beta:1"), CardLink("alpha:1", "gamma:1")],
        decks=["alpha", "beta"],
    )


class LifecycleTest(unittest.TestCase):
    def test_load_without_file_enables_all_decks_and_generates_nothing(self) -> None:
        core, _, spy = make_core(None)
        self.assertEqual(core.enabled_decks, ["alpha", "beta", "gamma"])
        self.assertEqual(len(core.cards), 5)
        self.assertEqual(core.positions, [])
        self.assertEqual(core.progress, {})
        self.assertEqual(spy.calls, [])

    def test_load_keeps_saved_order_and_drops_unknown_decks(self) -> None:
        raw = RawState(decks=["gamma", "gone", "alpha"])
        core, _, _ = make_core(raw)
        self.assertEqual(core.enabled_decks, ["gamma", "alpha"])

    def test_load_without_decks_key_enables_all_but_empty_list_enables_none(self) -> None:
        self.assertEqual(make_core(RawState(decks=None))[0].enabled_decks, ["alpha", "beta", "gamma"])
        self.assertEqual(make_core(RawState(decks=[]))[0].enabled_decks, [])

    def test_load_is_passive_and_does_not_strip(self) -> None:
        core, _, spy = make_core(stored_raw())
        self.assertEqual([p.card_id for p in core.positions], ["alpha:1", "gamma:1"])  # gamma is not enabled
        self.assertEqual(spy.calls, [])

    def test_refresh_fills_missing_and_strips_out_of_scope(self) -> None:
        core, _, spy = make_core(stored_raw())
        core.refresh_deck_state(seed=STARTUP_SEED)
        self.assertEqual([c.id for c in core.cards], ["alpha:1", "alpha:2", "beta:1"])
        self.assertEqual([p.card_id for p in core.positions], ["alpha:1", "alpha:2", "beta:1"])
        self.assertEqual((core.position_by_id["alpha:1"].x, core.position_by_id["alpha:1"].y), (0.5, 0.5))  # stored wins
        self.assertEqual(core.position_by_id["alpha:2"].x, STARTUP_SEED % 100 / 100)  # generated with the seed
        self.assertEqual(list(core.progress), ["alpha:1", "alpha:2", "beta:1"])
        self.assertEqual((core.progress["alpha:1"].read, core.progress["alpha:1"].difficulty), (True, 55))
        self.assertEqual((core.progress["alpha:2"].read, core.progress["alpha:2"].difficulty), (False, 1))
        self.assertEqual(core.groups[0].card_ids, ["alpha:1"])  # group stays, member of the disabled deck goes
        self.assertEqual([(l.source_id, l.target_id) for l in core.links], [("alpha:1", "beta:1")])
        self.assertEqual(set(core.card_by_id), {"alpha:1", "alpha:2", "beta:1"})
        self.assertEqual(set(core.position_by_id), {"alpha:1", "alpha:2", "beta:1"})
        self.assertEqual(spy.calls[-1][1], STARTUP_SEED)

    def test_refresh_without_seed_uses_the_clock(self) -> None:
        core, _, spy = make_core(None)
        with mock.patch("flashcards_app.state_core.time.time_ns", return_value=12345):
            core.refresh_deck_state()
        self.assertEqual(spy.calls[-1][1], 12345)

    def test_containers_keep_their_identity_everywhere(self) -> None:
        core, _, _ = make_core(stored_raw())
        names = ["enabled_decks", "cards", "positions", "progress", "groups", "links", "card_by_id", "position_by_id"]
        before = {name: getattr(core, name) for name in names}
        core.refresh_deck_state(seed=1)
        core.enable_deck("gamma")
        core.disable_deck("alpha")
        core.reset_all_state(seed=2)
        core.load(["alpha", "beta", "gamma"])
        for name in names:
            self.assertIs(getattr(core, name), before[name], name)

    def test_enable_and_disable_deck(self) -> None:
        core, _, _ = make_core(stored_raw())
        core.refresh_deck_state(seed=1)
        self.assertFalse(core.enable_deck("alpha"))
        self.assertTrue(core.enable_deck("gamma"))
        self.assertEqual(core.enabled_decks, ["alpha", "beta", "gamma"])
        self.assertEqual(len(core.cards), 5)
        self.assertIn("gamma:2", core.position_by_id)
        core.set_difficulty("alpha:1", 70)
        self.assertTrue(core.disable_deck("alpha"))
        self.assertFalse(core.disable_deck("alpha"))
        self.assertEqual(core.enabled_decks, ["beta", "gamma"])
        self.assertNotIn("alpha:1", core.progress)
        self.assertNotIn("alpha:1", core.position_by_id)
        # gamma:1 was stripped from the group by the first refresh (its deck was disabled then)
        # and is not restored by enabling the deck again; alpha:1 goes with the alpha deck
        self.assertEqual(core.groups[0].card_ids, [])

    def test_reset_all_state(self) -> None:
        core, _, _ = make_core(stored_raw())
        core.refresh_deck_state(seed=1)
        positions = list(core.positions)
        core.reset_all_state(seed=7)
        self.assertEqual([id(p) for p in core.positions], [id(p) for p in positions])  # changed in place
        self.assertTrue(all(p.x == 0.07 for p in core.positions))
        self.assertTrue(all((p.read, p.difficulty) == (False, 1) for p in core.progress.values()))
        self.assertEqual((core.groups, core.links), ([], []))
        self.assertEqual(core.enabled_decks, ["alpha", "beta"])  # scope is not state to reset

    def test_save_writes_everything_including_enabled_decks(self) -> None:
        core, persistence, _ = make_core(stored_raw())
        core.refresh_deck_state(seed=1)
        core.save()
        written = persistence.writes[-1]
        self.assertEqual(written.decks, ["alpha", "beta"])
        self.assertEqual([p.card_id for p in written.positions], ["alpha:1", "alpha:2", "beta:1"])
        self.assertEqual(list(written.progress), ["alpha:1", "alpha:2", "beta:1"])

    def test_nothing_saves_by_itself(self) -> None:
        core, persistence, _ = make_core(stored_raw())
        core.refresh_deck_state(seed=1)
        core.enable_deck("gamma")
        core.create_group("alpha:1", "Y", "#000")
        core.reset_all_state(seed=1)
        self.assertEqual(persistence.writes, [])

    def test_round_trip_through_a_real_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = JsonStateStore(Path(tmp) / "state.json")
            first = StateCore(store, card_source, PositionSpy())
            first.load(["alpha", "beta", "gamma"])
            first.refresh_deck_state(seed=STARTUP_SEED)
            first.set_difficulty("alpha:1", 33)
            first.create_group("alpha:1", "G", "#123456")
            first.disable_deck("gamma")
            first.save()

            second = StateCore(store, card_source, PositionSpy())
            second.load(["alpha", "beta", "gamma"])
            second.refresh_deck_state(seed=STARTUP_SEED)
            self.assertEqual(second.enabled_decks, ["alpha", "beta"])
            self.assertEqual(second.progress["alpha:1"].difficulty, 33)
            self.assertEqual([g.name for g in second.groups], ["G"])
            self.assertEqual([(p.card_id, p.x, p.y, p.z) for p in second.positions],
                             [(p.card_id, p.x, p.y, p.z) for p in first.positions])


class MutationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.core, _, _ = make_core(None)
        self.core.refresh_deck_state(seed=1)

    def test_position_and_difficulty(self) -> None:
        self.core.set_position("alpha:1", "0.1", 0, -1)
        position = self.core.get_position_by_id("alpha:1")
        self.assertEqual((position.x, position.y, position.z), (0.1, 0.0, -1.0))
        self.core.set_difficulty("alpha:1", 40)
        self.assertEqual(self.core.progress["alpha:1"].difficulty, 40)
        self.core.set_difficulty("alpha:1", 500)
        self.assertEqual(self.core.progress["alpha:1"].difficulty, 100)
        self.core.set_difficulty("alpha:1", -3)
        self.assertEqual(self.core.progress["alpha:1"].difficulty, 1)

    def test_mark_read_ignores_unknown_cards(self) -> None:
        self.core.mark_read("alpha:1")
        self.core.mark_read("nope:1")
        self.assertTrue(self.core.progress["alpha:1"].read)
        self.assertNotIn("nope:1", self.core.progress)

    def test_group_ids_stay_unique_after_deleting_a_group(self) -> None:
        first = self.core.create_group("alpha:1", " A ", "#1")
        second = self.core.create_group("alpha:2", "B", "#2")
        self.assertEqual((first, second), ("group-1", "group-2"))
        self.assertEqual(self.core.groups[0].name, "A")  # name is stripped as before
        self.core.delete_group(first)
        third = self.core.create_group("beta:1", "C", "#3")
        self.assertEqual(third, "group-3")  # the old count+1 rule gave "group-2" again
        self.assertEqual(len({g.id for g in self.core.groups}), 2)

    def test_group_id_ignores_foreign_ids(self) -> None:
        self.core.groups.append(CardGroup("custom", "Z", "#0", []))
        self.core.groups.append(CardGroup("group-7", "Y", "#0", []))
        self.assertEqual(self.core.create_group("alpha:1", "N", "#0"), "group-8")

    def test_group_membership(self) -> None:
        group_id = self.core.create_group("alpha:1", "A", "#1")
        self.core.add_to_group("alpha:2", group_id)
        self.core.add_to_group("alpha:2", group_id)
        self.core.add_to_group("alpha:2", "missing")
        self.assertEqual(self.core.groups[0].card_ids, ["alpha:1", "alpha:2"])
        self.core.remove_from_group("alpha:1", group_id)
        self.core.remove_from_group("alpha:1", "missing")
        self.assertEqual(self.core.groups[0].card_ids, ["alpha:2"])

    def test_links_are_undirected_and_deduplicated(self) -> None:
        self.core.create_link("alpha:1", "alpha:2")
        self.core.create_link("alpha:2", "alpha:1")
        self.core.create_link("alpha:1", "alpha:2")
        self.assertEqual(len(self.core.links), 1)
        self.core.create_link("alpha:1", "beta:1")
        self.core.disconnect_link("alpha:2", "alpha:1")
        self.assertEqual([(l.source_id, l.target_id) for l in self.core.links], [("alpha:1", "beta:1")])

    def test_delete_group_removes_links_that_belong_to_it(self) -> None:
        self.core.links.append(CardLink("alpha:1", "alpha:2", "group-1"))
        self.core.links.append(CardLink("alpha:1", "beta:1"))
        self.core.groups.append(CardGroup("group-1", "A", "#1", ["alpha:1"]))
        self.core.delete_group("group-1")
        self.assertEqual([(l.source_id, l.target_id) for l in self.core.links], [("alpha:1", "beta:1")])

    def test_visible_cards(self) -> None:
        ids = lambda cards: [card.id for card in cards]
        self.assertEqual(ids(self.core.visible_cards()), ["alpha:1", "alpha:2", "beta:1", "gamma:1", "gamma:2"])
        self.assertEqual(ids(self.core.visible_cards("beta")), ["beta:1"])
        group_id = self.core.create_group("alpha:2", "A", "#1")
        self.core.add_to_group("beta:1", group_id)
        self.assertEqual(ids(self.core.visible_cards(None, group_id)), ["alpha:2", "beta:1"])
        self.assertEqual(ids(self.core.visible_cards("beta", group_id)), ["beta:1"])
        self.assertEqual(self.core.visible_cards(None, "missing"), [])

    def test_lookups(self) -> None:
        self.assertEqual(self.core.get_card_by_id("beta:1").deck, "beta")
        self.assertIsNone(self.core.get_card_by_id("nope"))
        self.assertIsNone(self.core.get_position_by_id("nope"))


if __name__ == "__main__":
    unittest.main()
