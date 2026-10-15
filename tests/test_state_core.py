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
        self.assertEqual([p.comb_id for p in core.positions], ["alpha:1", "gamma:1"])  # gamma is not enabled
        self.assertEqual(spy.calls, [])

    def test_refresh_fills_missing_and_strips_out_of_scope(self) -> None:
        core, _, spy = make_core(stored_raw())
        core.refresh_deck_state(seed=STARTUP_SEED)
        self.assertEqual([c.id for c in core.cards], ["alpha:1", "alpha:2", "beta:1"])
        self.assertEqual([p.comb_id for p in core.positions], ["alpha:1", "alpha:2", "beta:1"])
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

    def test_refresh_strips_related_ids_like_group_members(self) -> None:
        # phase 2: related_ids hold comb_ids and get the same filter as groups and links
        raw = stored_raw()
        raw.positions[0].related_ids = ["beta:1", "gamma:1", "unknown"]
        core, _, _ = make_core(raw)
        core.refresh_deck_state(seed=STARTUP_SEED)
        self.assertEqual(core.position_by_id["alpha:1"].related_ids, ["beta:1"])

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
        self.assertEqual([p.comb_id for p in written.positions], ["alpha:1", "alpha:2", "beta:1"])
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
            self.assertEqual([(p.comb_id, p.x, p.y, p.z) for p in second.positions],
                             [(p.comb_id, p.x, p.y, p.z) for p in first.positions])


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

    def test_delete_group_never_touches_links(self) -> None:
        # unlike removing a deck, deleting a group leaves its members on the map, so their links stay
        self.core.create_link("alpha:1", "alpha:2")
        self.core.create_link("alpha:1", "beta:1")
        group_id = self.core.create_group("alpha:1", "A", "#1")
        self.core.add_to_group("alpha:2", group_id)
        self.core.delete_group(group_id)
        self.assertEqual(self.core.groups, [])
        self.assertEqual([(l.source_id, l.target_id) for l in self.core.links], [("alpha:1", "alpha:2"), ("alpha:1", "beta:1")])

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


class GroupRankTest(unittest.TestCase):
    def setUp(self) -> None:
        self.core, _, _ = make_core(None)
        self.core.refresh_deck_state(seed=1)
        # x1 is in A (oldest), B and C; x2 only in A; x3 only in C
        self.a = self.core.create_group("alpha:1", "A", "#a")
        self.core.add_to_group("alpha:2", self.a)
        self.b = self.core.create_group("alpha:1", "B", "#b")
        self.c = self.core.create_group("alpha:1", "C", "#c")
        self.core.add_to_group("beta:1", self.c)

    def color(self, card_id, focused=None):
        group = self.core.deciding_group(card_id, focused)
        return group.color if group else None

    def test_new_groups_get_rising_ranks(self) -> None:
        self.assertEqual([g.rank for g in self.core.groups], [1, 2, 3])

    def test_the_oldest_group_decides_when_nothing_is_focused(self) -> None:
        self.assertEqual(self.color("alpha:1"), "#a")
        self.assertEqual(self.color("alpha:2"), "#a")
        self.assertEqual(self.color("beta:1"), "#c")
        self.assertIsNone(self.color("gamma:1"))

    def test_a_focused_group_decides_for_its_members(self) -> None:
        self.assertEqual(self.color("alpha:1", self.b), "#b")
        self.assertEqual(self.color("alpha:1", self.c), "#c")
        self.assertEqual(self.color("alpha:1", self.a), "#a")

    def test_focus_on_a_group_the_card_is_not_in_falls_back_to_the_oldest(self) -> None:
        self.assertEqual(self.color("beta:1", self.a), "#c")
        self.assertEqual(self.color("alpha:1", "missing"), "#a")

    def test_deleting_the_oldest_group_passes_the_colour_to_the_next_oldest(self) -> None:
        self.core.delete_group(self.a)
        self.assertEqual(self.color("alpha:1"), "#b")
        self.assertIsNone(self.color("alpha:2"))
        self.core.delete_group(self.b)
        self.assertEqual(self.color("alpha:1"), "#c")

    def test_a_group_created_later_is_younger_than_every_existing_one(self) -> None:
        self.core.delete_group(self.c)
        d = self.core.create_group("alpha:1", "D", "#d")
        self.assertEqual([g.rank for g in self.core.groups], [1, 2, 3])  # the number of the deleted group is free again
        self.assertEqual(self.color("alpha:1"), "#a")
        self.core.delete_group(self.a)
        self.core.delete_group(self.b)
        self.assertEqual(self.color("alpha:1"), "#d")
        self.assertEqual(self.core.groups[0].id, d)

    def test_groups_without_rank_get_one_in_list_order_when_refreshed(self) -> None:
        raw = RawState(groups=[CardGroup("g1", "X", "#1", ["alpha:1"]), CardGroup("g2", "Y", "#2", ["alpha:1"])])
        core, _, _ = make_core(raw)
        core.refresh_deck_state(seed=1)
        self.assertEqual([g.rank for g in core.groups], [1, 2])
        self.assertEqual(core.deciding_group("alpha:1").id, "g1")

    def test_existing_ranks_are_kept_and_missing_ones_follow(self) -> None:
        raw = RawState(groups=[CardGroup("g1", "X", "#1", [], None), CardGroup("g2", "Y", "#2", [], 5), CardGroup("g3", "Z", "#3", [], None)])
        core, _, _ = make_core(raw)
        core.refresh_deck_state(seed=1)
        self.assertEqual([g.rank for g in core.groups], [6, 5, 7])

    def test_equal_ranks_are_decided_by_list_order(self) -> None:
        raw = RawState(groups=[CardGroup("g1", "X", "#1", ["alpha:1"], 4), CardGroup("g2", "Y", "#2", ["alpha:1"], 4)])
        core, _, _ = make_core(raw)
        core.refresh_deck_state(seed=1)
        self.assertEqual(core.deciding_group("alpha:1").id, "g1")

    def test_group_that_was_never_ranked_counts_as_youngest(self) -> None:
        self.core.groups.append(CardGroup("late", "L", "#l", ["alpha:2"]))  # added by hand, rank None
        self.assertEqual(self.core.deciding_group("alpha:2").id, self.a)


if __name__ == "__main__":
    unittest.main()
