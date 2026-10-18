"""Regression tests for constellation behavior now merged into flashcards_app.

Run from the repository root with:
    .venv/Scripts/python.exe -m pytest modules/constellations/test_constellations.py -p no:cacheprovider

The module-local suite imports the merged application implementation. It does not expect copies of
models.py, state_core.py, user_state_service.py, panels.py, or callbacks.py under changes/.
Constellations are runtime-only: derived from visible cards and stored links, never serialized.
"""

import dataclasses
import json
import importlib.util
import inspect
import subprocess
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from flashcards_app import callbacks
from flashcards_app.models import CardGroup, CardLink, CardProgress, Constellation, Flashcard
from flashcards_app.state_core import StateCore
from flashcards_app.user_state_service import UserStateService, derive_components
from flashcards_app.visualization import panels


class RecordingPersistence:
    """StatePersistence stand-in: nothing is read, every write is kept."""

    def __init__(self):
        self.writes = []

    def read(self):
        return None

    def write(self, state):
        self.writes.append(state)


class FakeCatalog:
    def __init__(self, decks=("a", "b")):
        self.decks = list(decks)

    def available(self):
        return list(self.decks)

    def is_available(self, deck_name):
        return deck_name in self.decks

    def reload(self):
        return True


def make_service(pairs, card_ids, cards=None):
    """A service over a real StateCore holding the cards (ids of `card_ids` in deck "a") and the links `pairs`."""
    persistence = RecordingPersistence()
    core = StateCore(persistence, lambda decks: [], lambda ids, seed: [])
    core.links[:] = [CardLink(source, target) for source, target in pairs]
    core.cards[:] = cards if cards is not None else [Flashcard(comb_id=i, deck="a", question="q", answer="a") for i in card_ids]
    return UserStateService(core, FakeCatalog()), core, persistence


def shown(service):
    """{const_id: members} of the service's constellations."""
    return {item.const_id: item.members for item in service.constellations}


def link_pairs(core):
    return [(link.source_id, link.target_id) for link in core.links]


def refresh_all(service, core):
    return service.refresh_constellations(core.cards)


def refresh_without(service, core, *hidden):
    return service.refresh_constellations([card for card in core.cards if card.id not in hidden])


class ConstellationModelTest(unittest.TestCase):
    def test_default_name_follows_const_id(self) -> None:
        self.assertEqual(Constellation("3").name, "constellation 3")
        self.assertEqual(Constellation(7).const_id, "7")  # always a string

    def test_explicit_name_is_kept(self) -> None:
        self.assertEqual(Constellation("1", name="mine").name, "mine")

    def test_members_are_not_shared_between_instances(self) -> None:
        first, second = Constellation("1"), Constellation("2")
        first.members.append("a")
        self.assertEqual(second.members, [])


class DeleteLinksForMembersTest(unittest.TestCase):
    # members {a, b, c}; d is outside (e.g. hidden by a focus); d-c is stored in the other direction
    LINKS = [("a", "b"), ("b", "c"), ("d", "c"), ("d", "e"), ("x", "y")]

    def make(self, pairs=LINKS):
        persistence = RecordingPersistence()
        core = StateCore(persistence, lambda decks: [], lambda ids, seed: [])
        core.links[:] = [CardLink(source, target) for source, target in pairs]
        return core, persistence

    def test_removes_links_between_members_in_either_direction_and_keeps_the_rest(self) -> None:
        core, _ = self.make()
        self.assertEqual(core.delete_links_for_members(["a", "b", "c"]), 2)
        self.assertEqual(link_pairs(core), [("d", "c"), ("d", "e"), ("x", "y")])
        core, _ = self.make([("a", "b"), ("c", "a"), ("b", "z")])
        self.assertEqual(core.delete_links_for_members({"a", "b", "c"}), 2)
        self.assertEqual(link_pairs(core), [("b", "z")])

    def test_persists_once_with_the_remaining_links(self) -> None:
        core, persistence = self.make()
        core.delete_links_for_members(iter(["a", "b", "c"]))  # any iterable
        self.assertEqual(len(persistence.writes), 1)
        self.assertEqual([(l.source_id, l.target_id) for l in persistence.writes[0].links], link_pairs(core))

    def test_changes_the_links_list_in_place(self) -> None:
        core, _ = self.make()
        links = core.links
        core.delete_links_for_members(["a", "b", "c"])
        self.assertIs(core.links, links)

    def test_without_a_matching_link_nothing_changes_or_is_written(self) -> None:
        for members in ([], ["a"], ["a", "e"], ["q", "r"]):
            core, persistence = self.make()
            self.assertEqual(core.delete_links_for_members(members), 0)
            self.assertEqual(link_pairs(core), self.LINKS)
            self.assertEqual(persistence.writes, [])

    def test_ordinary_disconnect_removes_only_the_selected_link_and_does_not_save(self) -> None:
        core, persistence = self.make()
        core.disconnect_link("a", "b")
        self.assertEqual(link_pairs(core), self.LINKS[1:])
        self.assertEqual(persistence.writes, [])


class DeriveComponentsTest(unittest.TestCase):
    def test_chain_with_intermediate_cards(self) -> None:
        links = [CardLink(*pair) for pair in [("a", "b"), ("b", "c"), ("c", "d")]]
        self.assertEqual(derive_components(["a", "b", "c", "d", "e"], links), [["a", "b", "c", "d"]])

    def test_ignores_lone_cards_hidden_ends_and_self_links(self) -> None:
        links = [CardLink(*pair) for pair in [("a", "b"), ("b", "h"), ("e", "e")]]
        self.assertEqual(derive_components(["a", "b", "e", "f"], links), [["a", "b"]])


class ConstellationServiceTest(unittest.TestCase):
    def test_constellations_are_numbered_with_visible_names_and_the_larger_group_first(self) -> None:
        service, core, _ = make_service([("a", "b"), ("c", "d"), ("d", "e")], "abcde")
        refresh_all(service, core)
        self.assertEqual(
            [(item.const_id, item.name) for item in service.constellations],
            [("1", "constellation 1"), ("2", "constellation 2")],
        )
        self.assertEqual(shown(service), {"1": ["c", "d", "e"], "2": ["a", "b"]})

    def test_reading_does_not_recalculate_and_returns_copies(self) -> None:
        service, core, _ = make_service([("a", "b")], "ab")
        self.assertEqual(service.constellations, [])
        service.visible_cards(None, None)
        self.assertEqual(service.constellations, [])
        refresh_all(service, core)
        first = shown(service)
        service.constellations[0].members.append("zzz")
        self.assertEqual(shown(service), first)

    def test_connect_merge_keeps_the_lower_id(self) -> None:
        service, core, _ = make_service([("a", "b"), ("c", "d")], "abcd")
        refresh_all(service, core)
        self.assertEqual(shown(service), {"1": ["a", "b"], "2": ["c", "d"]})
        service.create_link("b", "c")
        self.assertEqual(shown(service), {"1": ["a", "b", "c", "d"]})

    def test_connect_adds_a_member_and_forms_a_new_constellation(self) -> None:
        service, core, _ = make_service([("a", "b")], "abcde")
        refresh_all(service, core)
        service.create_link("b", "c")
        self.assertEqual(shown(service), {"1": ["a", "b", "c"]})
        service.create_link("d", "e")
        self.assertEqual(shown(service), {"1": ["a", "b", "c"], "2": ["d", "e"]})

    def test_disconnect_split_keeps_the_id_on_the_larger_branch(self) -> None:
        service, core, _ = make_service([("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")], "abcde")
        refresh_all(service, core)
        service.disconnect_link("c", "d")
        self.assertEqual(shown(service), {"1": ["a", "b", "c"], "2": ["d", "e"]})

    def test_disconnect_split_of_equal_branches_gives_one_of_them_the_next_id(self) -> None:
        service, core, _ = make_service([("a", "b"), ("b", "c"), ("c", "d")], "abcd")
        refresh_all(service, core)
        service.disconnect_link("b", "c")
        result = shown(service)
        self.assertEqual(sorted(result), ["1", "2"])
        self.assertEqual(sorted(map(sorted, result.values())), [["a", "b"], ["c", "d"]])

    def test_last_link_dissolves_and_a_new_pair_reuses_the_gap(self) -> None:
        service, core, _ = make_service([("a", "b"), ("c", "d"), ("e", "f")], "abcdef")
        refresh_all(service, core)
        self.assertEqual(sorted(shown(service)), ["1", "2", "3"])
        service.disconnect_link("c", "d")
        remaining = shown(service)
        self.assertEqual(len(remaining), 2)
        gap = ({"1", "2", "3"} - set(remaining)).pop()
        service.create_link("c", "d")
        self.assertEqual(shown(service)[gap], ["c", "d"])

    def test_filtering_a_card_out_splits_and_it_rejoins_with_the_lower_id(self) -> None:
        service, core, _ = make_service([("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")], "abcde")
        refresh_all(service, core)
        self.assertEqual(shown(service), {"1": ["a", "b", "c", "d", "e"]})
        refresh_without(service, core, "c")
        split = shown(service)
        self.assertEqual(sorted(split), ["1", "2"])
        self.assertEqual(sorted(map(sorted, split.values())), [["a", "b"], ["d", "e"]])
        refresh_all(service, core)
        self.assertEqual(shown(service), {"1": ["a", "b", "c", "d", "e"]})
        self.assertEqual(len(core.links), 4)

    def test_a_constellation_that_loses_all_links_to_the_filter_dissolves_and_returns(self) -> None:
        service, core, _ = make_service([("a", "b")], "abc")
        refresh_all(service, core)
        refresh_without(service, core, "b")
        self.assertEqual(service.constellations, [])
        refresh_all(service, core)
        self.assertEqual(shown(service), {"1": ["a", "b"]})

    def test_group_focus_is_just_another_visible_set(self) -> None:
        service, core, _ = make_service([("a", "b"), ("b", "c")], "abc")
        core.groups.append(CardGroup("group-1", "g", "#fff", ["a", "b"], 1))
        service.refresh_constellations(service.visible_cards(None, "group-1"))
        self.assertEqual(shown(service), {"1": ["a", "b"]})

    def test_delete_removes_member_links_keeps_hidden_links_and_saves_once(self) -> None:
        service, core, persistence = make_service([("a", "b"), ("b", "c"), ("c", "h"), ("x", "y")], "abcxy")
        refresh_all(service, core)  # h is not a visible card: c-h is a link to a hidden card
        self.assertEqual(shown(service), {"1": ["a", "b", "c"], "2": ["x", "y"]})
        self.assertEqual(service.delete_constellation_links("1"), 2)
        self.assertEqual(link_pairs(core), [("c", "h"), ("x", "y")])
        self.assertEqual(len(persistence.writes), 1)
        self.assertEqual(shown(service), {"2": ["x", "y"]})

    def test_delete_of_an_unknown_constellation_changes_and_writes_nothing(self) -> None:
        service, core, persistence = make_service([("a", "b")], "ab")
        self.assertEqual(service.delete_constellation_links("1"), 0)  # nothing refreshed yet
        refresh_all(service, core)
        self.assertEqual(service.delete_constellation_links("9"), 0)
        self.assertEqual(link_pairs(core), [("a", "b")])
        self.assertEqual(persistence.writes, [])

    def test_ordinary_disconnect_keeps_the_other_links_and_writes_nothing(self) -> None:
        service, core, persistence = make_service([("a", "b"), ("b", "c")], "abc")
        refresh_all(service, core)
        service.disconnect_link("a", "b")
        self.assertEqual(link_pairs(core), [("b", "c")])
        self.assertEqual(persistence.writes, [])

    def test_constellations_are_never_serialized_and_are_derived_again_at_startup(self) -> None:
        service, core, persistence = make_service([("a", "b"), ("c", "d")], "abcd")
        refresh_all(service, core)
        service.save()
        written = persistence.writes[-1]
        self.assertFalse(any("constellation" in field.name for field in dataclasses.fields(written)))
        restarted = UserStateService(core, FakeCatalog())  # a new session over the same stored links
        self.assertEqual(restarted.constellations, [])
        refresh_all(restarted, core)
        self.assertEqual(shown(restarted), shown(service))

    def test_reset_clears_the_links_and_the_constellations(self) -> None:
        service, core, _ = make_service([("a", "b")], "ab")
        refresh_all(service, core)
        service.reset_all_state(seed=1)
        self.assertEqual(service.constellations, [])


# --- panels ---


def components(node):
    """The node and every Dash component below it."""
    if node is None or isinstance(node, (str, int, float)):
        return
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from components(child)
    elif children is not None:
        yield from components(children)


def by_id(node, component_id):
    return next((item for item in components(node) if getattr(item, "id", None) == component_id), None)


def texts(node):
    found = []
    for item in components(node):
        children = getattr(item, "children", None)
        if isinstance(children, str):
            found.append(children)
        elif isinstance(children, (list, tuple)):
            found.extend(child for child in children if isinstance(child, str))
    return found


def class_names(node):
    return [getattr(item, "className", None) or "" for item in components(node)]


def constellation_state(*groups):
    """A stand-in for the service: runtime constellations and a recording Delete."""
    deleted = []
    items = [Constellation(str(number), members=list(members)) for number, members in groups]

    def delete_constellation_links(const_id):
        deleted.append(const_id)
        return 3

    return SimpleNamespace(constellations=items, delete_constellation_links=delete_constellation_links, deleted=deleted)


def a_card(card_id="a"):
    return Flashcard(comb_id=card_id, deck="d", question=f"question {card_id}", answer="answer")


class ConnectionPanelTest(unittest.TestCase):
    def test_the_servers_two_argument_call_still_builds_the_panel(self) -> None:
        panel = panels.connection_control(None, [])
        for component_id in ("create-link", "disconnect-link", "link-target", "constellation-select"):
            self.assertIsNotNone(by_id(panel, component_id), component_id)
        self.assertTrue(by_id(panel, "delete-constellation").disabled)
        self.assertEqual(by_id(panel, "constellation-select").options, [])
        self.assertIsNone(by_id(panel, "constellation-dialog").data)
        self.assertIn("No visible constellations.", texts(panel))

    def test_the_card_options_are_unchanged(self) -> None:
        cards = [a_card(name) for name in "abc"]
        panel = panels.connection_control(cards[0], cards)
        self.assertEqual([option["value"] for option in by_id(panel, "link-target").options], ["b", "c"])
        self.assertFalse(by_id(panel, "create-link").disabled)

    def test_lists_constellations_without_swatches(self) -> None:
        panel = panels.connection_control(None, [], constellation_state((1, ["a", "b", "c"]), (2, ["x", "y"])))
        for text in ("constellation 1", "constellation 2", "3 cards", "2 cards"):
            self.assertIn(text, texts(panel))
        self.assertNotIn("No visible constellations.", texts(panel))
        self.assertFalse(any("swatch" in name for name in class_names(panel)))

    def test_delete_button_and_dropdown_use_the_const_id(self) -> None:
        panel = panels.connection_control(None, [], constellation_state((1, ["a", "b"]), (3, ["x", "y"])))
        self.assertFalse(by_id(panel, "delete-constellation").disabled)
        self.assertEqual(
            by_id(panel, "constellation-select").options,
            [{"label": "constellation 1", "value": "1"}, {"label": "constellation 3", "value": "3"}],
        )

    def test_delete_dialog_is_hidden_until_asked_for_and_its_state_is_kept_in_the_panel(self) -> None:
        state = constellation_state((1, ["a", "b"]))
        closed = panels.connection_control(None, [], state)
        opened = panels.connection_control(None, [], state, "delete")
        self.assertIn("group-dialog group-dialog-hidden", class_names(closed))
        self.assertIn("group-dialog", class_names(opened))
        self.assertNotIn("group-dialog group-dialog-hidden", class_names(opened))
        self.assertIsNone(by_id(closed, "constellation-dialog").data)
        self.assertEqual(by_id(opened, "constellation-dialog").data, "delete")

    def test_delete_dialog_shows_the_message_next_to_confirm_and_cancel(self) -> None:
        panel = panels.connection_control(None, [], constellation_state((1, ["a", "b"])), "delete")
        confirm = by_id(panel, "constellation-dialog-submit")
        row = next(
            item for item in components(panel)
            if isinstance(getattr(item, "children", None), list)
            and any(child is confirm for child in getattr(item, "children", []))
        )
        self.assertIn(panels.DELETE_CONSTELLATION_NOTE, texts(row))
        self.assertTrue(any(child is by_id(panel, "constellation-dialog-cancel") for child in getattr(row, "children", [])))

    def test_delete_constellation_asks_the_service_and_returns_the_count(self) -> None:
        state = constellation_state((1, ["a", "b"]))
        self.assertEqual(panels.delete_constellation(state, "1"), 3)
        self.assertEqual(state.deleted, ["1"])

    def test_panel_helpers_still_require_a_state(self) -> None:
        with self.assertRaises(TypeError):
            panels.delete_constellation(None, "1")
        with self.assertRaises(TypeError):
            panels.constellation_options(None)


# --- callbacks ---

OUT_CONNECTION, OUT_STATUS = 5, 6

NEW_DEPENDENCIES = [
    ("Input", "delete-constellation", "n_clicks"),
    ("Input", "constellation-dialog-submit", "n_clicks"),
    ("Input", "constellation-dialog-cancel", "n_clicks"),
    ("State", "constellation-dialog", "data"),
    ("State", "constellation-select", "value"),
]
NEW_PARAMETERS = [
    "delete_constellation_clicks", "constellation_submit_clicks", "constellation_cancel_clicks",
    "constellation_dialog", "constellation_select",
]

# c1-c2 (deck a), c2-c3 (c3 is in deck b), c3-c4 (deck b): one constellation across two decks; c5-c6: a second one
APP_CARDS = [("c1", "a"), ("c2", "a"), ("c3", "b"), ("c4", "b"), ("c5", "a"), ("c6", "a")]
APP_LINKS = [("c1", "c2"), ("c2", "c3"), ("c3", "c4"), ("c5", "c6")]


class RecordingApp:
    def __init__(self):
        self.dependencies = ()

    def callback(self, *dependencies):
        self.dependencies = dependencies
        return lambda function: function


def make_app_service(pairs=APP_LINKS, cards=APP_CARDS):
    flashcards = [Flashcard(comb_id=i, deck=d, question=f"question {i}", answer="a") for i, d in cards]
    service, core, persistence = make_service(pairs, [], flashcards)
    core.enabled_decks[:] = sorted({deck for _, deck in cards})
    core.progress.update({i: CardProgress(i) for i, _ in cards})
    core._rebuild_indexes()
    return service, core, persistence


def call_update(service, trigger, **inputs):
    """Run the callback as Dash would: by position, with the trigger set. Unlisted inputs are None; deck is "all"."""
    update = callbacks.register_callbacks(RecordingApp(), service, "None")
    values = {name: None for name in inspect.signature(update).parameters}
    values.update(deck="all", drag_enabled=False)
    values.update(inputs)
    with mock.patch("dash.ctx", SimpleNamespace(triggered_id=trigger)), \
            mock.patch.object(callbacks, "make_figure", return_value="figure"):
        return update(*values.values())


class ConstellationCallbackTest(unittest.TestCase):
    def test_dependencies_add_the_constellation_controls_in_order(self) -> None:
        app = RecordingApp()
        update = callbacks.register_callbacks(app, None)
        found = [(type(item).__name__, item.component_id, item.component_property) for item in app.dependencies]
        self.assertTrue(all(item in found for item in NEW_DEPENDENCIES))
        inputs_and_states = [item for item in found if item[0] != "Output"]
        kinds = [item[0] for item in inputs_and_states]
        self.assertEqual(kinds, sorted(kinds, key=("Input", "State").index))  # every Input before the first State
        parameters = list(inspect.signature(update).parameters)
        self.assertEqual(len(parameters), len(inputs_and_states))
        for dependency, name in zip(NEW_DEPENDENCIES, NEW_PARAMETERS):
            self.assertEqual(parameters[inputs_and_states.index(dependency)], name)

    def test_deck_focus_changes_the_constellations_and_never_the_links(self) -> None:
        service, core, _ = make_app_service()
        call_update(service, "deck-filter", deck="all")
        self.assertEqual(shown(service), {"1": ["c1", "c2", "c3", "c4"], "2": ["c5", "c6"]})
        call_update(service, "deck-filter", deck="a")
        self.assertEqual(shown(service), {"1": ["c1", "c2"], "2": ["c5", "c6"]})
        call_update(service, "deck-filter", deck="b")
        self.assertEqual(shown(service), {"1": ["c3", "c4"]})
        call_update(service, "deck-filter", deck="None")  # the empty-map deck
        self.assertEqual(service.constellations, [])
        call_update(service, "deck-filter", deck="all")
        self.assertEqual(shown(service), {"1": ["c1", "c2", "c3", "c4"], "2": ["c5", "c6"]})
        self.assertEqual(link_pairs(core), APP_LINKS)

    def test_group_focus_changes_the_constellations(self) -> None:
        service, core, _ = make_app_service()
        core.groups.append(CardGroup("group-1", "g", "#ffffff", ["c1", "c2", "c3"], 1))
        call_update(service, "deck-filter", deck="all", focused_group="group-1")
        self.assertEqual(shown(service), {"1": ["c1", "c2", "c3"]})
        call_update(service, "deck-filter", deck="all", focused_group=None)
        self.assertEqual(shown(service), {"1": ["c1", "c2", "c3", "c4"], "2": ["c5", "c6"]})

    def test_connect_and_disconnect_refresh_the_constellations(self) -> None:
        service, core, _ = make_app_service()
        call_update(service, "deck-filter", deck="all")
        call_update(service, "create-link", selected_id="c1", link_target="c5")
        self.assertEqual(shown(service), {"1": ["c1", "c2", "c3", "c4", "c5", "c6"]})
        call_update(service, "disconnect-link", selected_id="c1", link_target="c5")
        self.assertEqual(shown(service), {"1": ["c1", "c2", "c3", "c4"], "2": ["c5", "c6"]})
        self.assertEqual(link_pairs(core), APP_LINKS)

    def test_the_panel_shows_the_constellations_after_every_callback(self) -> None:
        service, _, _ = make_app_service()
        panel = call_update(service, "deck-filter", deck="all")[OUT_CONNECTION]
        self.assertIn("constellation 1", texts(panel))
        self.assertIn("constellation 2", texts(panel))
        self.assertFalse(by_id(panel, "delete-constellation").disabled)

    def test_delete_button_opens_and_cancel_closes_the_dialog_without_touching_links(self) -> None:
        service, core, _ = make_app_service()
        call_update(service, "deck-filter", deck="all")
        opened = call_update(service, "delete-constellation")[OUT_CONNECTION]
        self.assertEqual(by_id(opened, "constellation-dialog").data, "delete")
        closed = call_update(service, "constellation-dialog-cancel", constellation_dialog="delete")[OUT_CONNECTION]
        self.assertIsNone(by_id(closed, "constellation-dialog").data)
        self.assertEqual(link_pairs(core), APP_LINKS)

    def test_confirmed_delete_disconnects_members_and_the_callback_does_not_save_again(self) -> None:
        service, core, persistence = make_app_service()
        call_update(service, "deck-filter", deck="a")  # c3 and c4 are hidden by the deck focus
        self.assertEqual(shown(service), {"1": ["c1", "c2"], "2": ["c5", "c6"]})
        writes_before = len(persistence.writes)
        result = call_update(
            service, "constellation-dialog-submit", deck="a", constellation_dialog="delete", constellation_select="1"
        )
        remaining = [("c2", "c3"), ("c3", "c4"), ("c5", "c6")]  # only c1-c2 went: c2-c3 leads to the hidden c3
        self.assertEqual(link_pairs(core), remaining)
        self.assertEqual(len(persistence.writes), writes_before + 1)  # saved by the state core only
        self.assertEqual([(l.source_id, l.target_id) for l in persistence.writes[-1].links], remaining)
        self.assertEqual(shown(service), {"2": ["c5", "c6"]})
        panel = result[OUT_CONNECTION]
        self.assertIsNone(by_id(panel, "constellation-dialog").data)
        self.assertNotIn("constellation 1", texts(panel))
        self.assertEqual(result[OUT_STATUS], "Saved")
        call_update(service, "deck-filter", deck="all")  # the hidden links are back in the picture
        self.assertEqual(shown(service), {"1": ["c2", "c3", "c4"], "2": ["c5", "c6"]})

    def test_delete_without_a_selection_keeps_the_dialog_and_the_links(self) -> None:
        service, core, _ = make_app_service()
        call_update(service, "deck-filter", deck="all")
        result = call_update(
            service, "constellation-dialog-submit", constellation_dialog="delete", constellation_select=None
        )
        self.assertEqual(link_pairs(core), APP_LINKS)
        self.assertEqual(by_id(result[OUT_CONNECTION], "constellation-dialog").data, "delete")

    def test_delete_needs_the_open_dialog(self) -> None:
        service, core, _ = make_app_service()
        call_update(service, "deck-filter", deck="all")
        call_update(service, "constellation-dialog-submit", constellation_dialog=None, constellation_select="1")
        self.assertEqual(link_pairs(core), APP_LINKS)

    def test_the_other_triggers_still_save_as_before(self) -> None:
        service, _, persistence = make_app_service()
        call_update(service, "deck-filter", deck="all")
        call_update(service, "delete-constellation")
        self.assertEqual(len(persistence.writes), 2)

    def test_reset_clears_the_links_and_the_constellations(self) -> None:
        service, core, _ = make_app_service()
        call_update(service, "deck-filter", deck="all")
        call_update(service, "reset-confirm")
        self.assertEqual(core.links, [])
        self.assertEqual(service.constellations, [])


if __name__ == "__main__":
    unittest.main()


# --- tranche 1: active module launcher contract ---------------------------

LAUNCHER_PATH = Path(__file__).resolve().parents[2] / "tools" / "loader" / "const_v1_launcher.py"


def load_launcher():
    """Load the actual launcher privately so these tests do not start the web app."""
    alias = "_constellations_test_launcher"
    spec = importlib.util.spec_from_file_location(alias, LAUNCHER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load launcher from {LAUNCHER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(alias, None)
        raise
    return module


# Fresh-process launcher probe. Importing the actual root app exercises the same composition path as launch.
LAUNCHER = Path(__file__).resolve().parents[2] / "tools" / "loader" / "const_v1_launcher.py"
LAUNCHER_PROBE = r"""
import builtins, importlib, importlib.util, io, json, sys
from pathlib import Path

launcher_path, workdir = Path(sys.argv[1]), Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("const_v1_launcher_probe", launcher_path)
launcher = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = launcher
spec.loader.exec_module(launcher)
scratch = workdir / "scratch" / "const_user_state.json"
launcher.SCRATCH_STATE = scratch
project_state = workdir / "project_state.json"
opened = []
real_open = io.open
def spy(file, *args, **kwargs):
    if isinstance(file, (str, Path)) and Path(file).resolve() == project_state.resolve():
        opened.append(str(file))
    return real_open(file, *args, **kwargs)
builtins.open = spy
io.open = spy
launcher.reroute_constellations_components()
launcher.reroute_constellations_components()
reroutes = {}
for name in launcher.REROUTES:
    module = sys.modules[name]
    parent, _, child = name.rpartition(".")
    reroutes[name] = [module.__spec__.origin, getattr(sys.modules[parent], child) is module]
launcher.redirect_state_store()
state = importlib.import_module("flashcards_app.state")
state.JsonStateStore(project_state).write(state.RawState())
app = launcher.load_app()
print("PROBE-RESULT " + json.dumps({
    "reroutes": reroutes,
    "redirected": state.JsonStateStore is launcher.ScratchStateStore,
    "scratch_exists": scratch.exists(),
    "project_state_exists": project_state.exists(),
    "project_state_opened": bool(opened),
    "app_origin": app.__spec__.origin,
}))
"""


def run_launcher_probe(workdir: Path) -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", LAUNCHER_PROBE, str(LAUNCHER), str(workdir)],
        cwd=LAUNCHER.parents[2], capture_output=True, text=True,
    )
    if completed.returncode:
        raise AssertionError(completed.stderr or completed.stdout)
    line = next(line for line in completed.stdout.splitlines() if line.startswith("PROBE-RESULT "))
    return json.loads(line.removeprefix("PROBE-RESULT "))




class LauncherIsolationTest(unittest.TestCase):
    def test_launcher_reroutes_tranche_three_overrides_and_server(self) -> None:
        launcher = load_launcher()
        try:
            self.assertEqual(
                list(launcher.REROUTES.items()),
                [
                    ("flashcards_app.visualization.map", launcher.CHANGES_DIR / "map.py"),
                    ("flashcards_app.visualization.panels", launcher.CHANGES_DIR / "panels.py"),
                    ("flashcards_app.callbacks", launcher.CHANGES_DIR / "callbacks.py"),
                    ("flashcards_app.server", launcher.CHANGES_DIR / "server.py"),
                ],
            )
            self.assertEqual(launcher.SCRATCH_STATE, launcher.LAUNCHER_DIR / "scratch" / "const_user_state.json")
            self.assertEqual(launcher.APP_SOURCE, launcher.ROOT / "app.py")
        finally:
            sys.modules.pop("_constellations_test_launcher", None)


    def test_launcher_loads_root_app_with_tranche_three_overrides_and_scratch_state(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory(prefix="constellation-launcher-probe-") as directory:
            result = run_launcher_probe(Path(directory))
        root = LAUNCHER.parents[2]
        self.assertEqual(
            result["reroutes"],
            {
                "flashcards_app.visualization.map": [str(root / "modules/constellations/changes/map.py"), True],
                "flashcards_app.visualization.panels": [str(root / "modules/constellations/changes/panels.py"), True],
                "flashcards_app.callbacks": [str(root / "modules/constellations/changes/callbacks.py"), True],
                "flashcards_app.server": [str(root / "modules/constellations/changes/server.py"), True],
            },
        )
        self.assertEqual(Path(result["app_origin"]).resolve(), (root / "app.py").resolve())
        self.assertTrue(result["redirected"])
        self.assertTrue(result["scratch_exists"])
        self.assertFalse(result["project_state_exists"])
        self.assertFalse(result["project_state_opened"])

    def test_state_store_wrapper_writes_only_to_module_scratch_path(self) -> None:
        launcher = load_launcher()
        alias = "_constellations_test_launcher"
        state_name = "flashcards_app.state"
        sentinel = object()
        previous_state = sys.modules.get(state_name, sentinel)

        class FakeJsonStateStore:
            def __init__(self, path, *args, **kwargs):
                self.path = Path(path)

            def read(self):
                return self.path.read_text(encoding="utf-8") if self.path.exists() else None

            def write(self, value):
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(value, encoding="utf-8")

        state_module = types.ModuleType(state_name)
        state_module.JsonStateStore = FakeJsonStateStore
        project_state = launcher.ROOT / "data" / "must-not-be-opened-by-constellation-tests.json"
        try:
            sys.modules[state_name] = state_module
            launcher._JSON_STATE_STORE = None
            # Use a unique temporary location outside the project tree.
            import tempfile
            with tempfile.TemporaryDirectory(prefix="constellation-state-test-") as directory:
                launcher.SCRATCH_STATE = Path(directory) / "scratch" / "state.json"
                launcher.redirect_state_store()
                store = state_module.JsonStateStore(project_state)
                store.write("scratch-only")
                self.assertEqual(store.read(), "scratch-only")
                self.assertEqual(store.path, launcher.SCRATCH_STATE)
                self.assertEqual(store.project_path, project_state)
                self.assertTrue(launcher.SCRATCH_STATE.is_file())
                self.assertFalse(project_state.exists())
        finally:
            if previous_state is sentinel:
                sys.modules.pop(state_name, None)
            else:
                sys.modules[state_name] = previous_state
            sys.modules.pop(alias, None)
