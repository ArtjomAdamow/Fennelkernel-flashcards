"""Builds a varied state through the services, then calls every function of colors, map and panels.

Started by tests/test_visualization_equivalence.py in a temporary copy of the project, with stand-ins for
dash and plotly (tests/stubs). Do not run it inside your real project.
"""

import inspect
import json
import sys
import time

SEED = [42]
time.time_ns = lambda: SEED[0]

from dash import to_json  # noqa: E402  (stand-in)
from flashcards_app import runtime  # noqa: E402
from flashcards_app.services import cards as cards_service  # noqa: E402
from flashcards_app.services import connections as connections_service  # noqa: E402
from flashcards_app.services import decks as decks_service  # noqa: E402
from flashcards_app.services import groups as groups_service  # noqa: E402
from flashcards_app.services import positions as positions_service  # noqa: E402
from flashcards_app.services import progress as progress_service  # noqa: E402
from flashcards_app.visualization import colors, panels  # noqa: E402
from flashcards_app.visualization import map as map_module  # noqa: E402

# --- build a state with: read cards of different difficulty, a card in two groups, links, a second deck ------
ids = [card.id for card in runtime.CARDS]
cards_service.toggle_reveal(ids[2], False)
progress_service.set_difficulty(ids[2], 20)
cards_service.toggle_reveal(ids[3], False)
progress_service.set_difficulty(ids[3], 90)
groups_service.create_group(ids[0], "A", "#aaaaaa")  # group-2; ids[0] is also in group-1 (fixture): two groups
groups_service.add_to_group(ids[1], "group-2")
groups_service.create_group(ids[4], "B", "#bbbbbb")  # group-3
connections_service.create_link(ids[1], ids[3])
connections_service.create_link(ids[0], ids[2])
connections_service.create_link(ids[3], ids[4])
connections_service.create_link(ids[0], ids[1])  # both are members of group-2: focusing that group still shows it
SEED[0] = 1111
decks_service.add_enabled_deck("gamma")
ids = [card.id for card in runtime.CARDS]
connections_service.create_link(ids[0], ids[5])
positions_service.set_position(ids[1], 0.1, 0.2, 0.3)

all_ids = ids + ["unknown:1"]
state = getattr(runtime, "USER_STATE", None)


def takes_state(func):
    return "state" in inspect.signature(func).parameters


explicit = {}


def snapshot(result):
    return result.to_dict() if hasattr(result, "to_dict") else to_json(result)


def with_explicit(name, func, *args):
    """Call func(*args) as the code does today and, if it accepts `state`, again with it passed explicitly."""
    result = func(*args)
    if takes_state(func):
        explicit[name] = snapshot(func(*args, state=state)) == snapshot(result)
    return result


out = {}

# --- colors ---------------------------------------------------------------------------------------------
out["colors"] = {
    "progress_by_card": {cid: with_explicit(f"progress_color:{cid}", colors.progress_color, cid) for cid in all_ids},
    "progress_by_value": {str(v): colors.progress_color(v) for v in (1, 17, 34, 35, 50, 69, 70, 100, 150, -3)},
    "group_by_card": {cid: with_explicit(f"group_color:{cid}", colors.group_color, cid) for cid in all_ids},
}

# --- map ------------------------------------------------------------------------------------------------
camera = {"eye": {"x": 1.0, "y": 2.0, "z": 3.0}, "up": {"x": 0, "y": 0, "z": 1}, "center": {"x": 0, "y": 0, "z": 0}}
combos = [("all", None), ("alpha", None), ("beta", None), ("gamma", None), ("all", "group-1"), ("all", "group-2"),
          ("all", "group-3"), ("alpha", "group-2"), ("beta", "group-2"), (runtime.NONE_DECK, None), ("all", "nope")]
figures = {"empty": map_module.make_figure([]).to_dict()}
links_visible = {}
for deck, group in combos:
    visible = runtime.visible_cards(deck, group)
    visible_ids = {card.id for card in visible}
    key = f"{deck}|{group}"
    figure = with_explicit(f"make_figure:{key}", map_module.make_figure, visible, None, None)
    figures[key] = figure.to_dict()
    drawn = [[round(c, 9) for c in (trace["x"][0], trace["y"][0], trace["z"][0], trace["x"][1], trace["y"][1], trace["z"][1])]
             for trace in figure.to_dict()["data"] if trace.get("name") == "Connection"]
    expected = []
    for link in runtime.LINKS:
        if link.source_id in visible_ids and link.target_id in visible_ids:
            a, b = runtime.POSITION_BY_ID[link.source_id], runtime.POSITION_BY_ID[link.target_id]
            expected.append([round(c, 9) for c in (a.x, a.y, a.z, b.x, b.y, b.z)])
    links_visible[key] = {"drawn": drawn, "expected": expected, "total_links": len(runtime.LINKS)}
all_cards = list(runtime.CARDS)
figures["selected"] = map_module.make_figure(all_cards, ids[1]).to_dict()
figures["selected_with_camera"] = map_module.make_figure(all_cards, ids[1], camera).to_dict()
figures["selected_not_visible"] = map_module.make_figure(runtime.visible_cards("beta", None), ids[0]).to_dict()
out["map"] = {"figures": figures, "links_visible": links_visible, "legend": to_json(map_module.color_legend())}

# --- panels ---------------------------------------------------------------------------------------------
unread, read_card, two_groups = runtime.CARD_BY_ID[ids[4]], runtime.CARD_BY_ID[ids[2]], runtime.CARD_BY_ID[ids[0]]
out["panels"] = {
    "card_panel": [to_json(panels.card_panel(c, r)) for c in (None, read_card) for r in (False, True)],
    "difficulty": [to_json(with_explicit(f"difficulty:{i}", panels.difficulty_control, c)) for i, c in enumerate((None, read_card, unread, two_groups))],
    "position": [to_json(with_explicit(f"position:{i}:{d}", panels.position_control, c, d)) for i, c in enumerate((None, read_card)) for d in (False, True)],
    "group": [to_json(with_explicit(f"group:{i}:{dialog}", panels.group_control, c, dialog))
              for i, c in enumerate((None, read_card, two_groups)) for dialog in (None, "new", "add", "remove", "delete", "focus")],
    "deck": [to_json(with_explicit(f"deck:{dialog}:{selected}", panels.deck_control, dialog, selected))
             for dialog in (None, "add", "remove", "focus") for selected in (runtime.NONE_DECK, "all", "alpha")],
    "connection": [to_json(with_explicit(f"connection:{i}:{deck}:{fg}", panels.connection_control, c, deck, fg))
                   for i, c in enumerate((None, read_card)) for deck in ("all", "alpha", "beta") for fg in (None, "group-1", "group-2", "nope")],
}
out["explicit_state_matches_default"] = explicit

# --- a second state with other content: functions that accept `state` must use the one they are given -----
foreign = None
if state is not None:
    from flashcards_app.models import CardPosition, Flashcard  # noqa: E402
    from flashcards_app.state_core import StateCore  # noqa: E402
    from flashcards_app.user_state_service import UserStateService  # noqa: E402

    class NothingStored:
        def read(self):
            return None

        def write(self, state):
            pass

    def make_other():
        core = StateCore(
            NothingStored(),
            lambda decks: [Flashcard(f"x:{i}", "x", f"Q{i}", f"A{i}") for i in (1, 2)],
            lambda card_ids, seed: [CardPosition(cid, 0.1 * (i + 1), 0.2, 0.3) for i, cid in enumerate(card_ids)],
        )
        core.load(["x"])
        core.refresh_deck_state(seed=1)
        return UserStateService(core, runtime.CATALOG)

    other = make_other()  # two cards, a group "Z" with both, a link, both read
    other.mark_read("x:1")
    other.set_difficulty("x:1", 100)
    other.mark_read("x:2")
    other.create_group("x:1", "Z", "#123456")  # group-1, which also exists in the shared state with other members
    other.add_to_group("x:2", "group-1")
    other.create_link("x:1", "x:2")
    empty = make_other()  # same cards, but no group at all (the shared state has groups)
    other_cards = list(other.cards)
    x1 = other.card_by_id["x:1"]
    foreign = {}
    if takes_state(colors.progress_color):
        foreign["progress_colors"] = [colors.progress_color(c, other) for c in ("x:1", "x:2", ids[0])]
    if takes_state(colors.group_color):
        foreign["group_colors"] = [colors.group_color(c, other) for c in ("x:1", "x:2", ids[0])]
    if takes_state(map_module.make_figure):
        figure = map_module.make_figure(other_cards, "x:1", None, other).to_dict()
        by_name = {trace.get("name"): trace for trace in figure["data"]}
        foreign["figure_trace_names"] = [trace.get("name") for trace in figure["data"]]
        foreign["figure_selected_customdata"] = by_name["Selected"]["customdata"]
        foreign["figure_cards_customdata"] = by_name["Cards"]["customdata"]
        foreign["figure_cards_text"] = by_name["Cards"]["text"]
        foreign["figure_marker_colors"] = {name: by_name[name]["marker"]["color"]
                                           for name in ("Card progress", "Cards", "Selected progress", "Selected")}
    if takes_state(panels.difficulty_control):
        foreign["difficulty_control"] = json.dumps(to_json(panels.difficulty_control(x1, state=other)))
    if takes_state(panels.position_control):
        foreign["position_control"] = json.dumps(to_json(panels.position_control(x1, False, state=other)))
    if takes_state(panels.group_control):
        foreign["group_control"] = json.dumps(to_json(panels.group_control(x1, "add", state=other)))
        foreign["group_control_with_groups"] = to_json(panels.group_control(x1, None, state=other))
        foreign["group_control_no_groups"] = to_json(panels.group_control(empty.card_by_id["x:1"], None, state=empty))
    if takes_state(panels.connection_control):
        foreign["connection_control"] = json.dumps(to_json(panels.connection_control(x1, "all", None, state=other)))
        foreign["connection_control_focused"] = json.dumps(to_json(panels.connection_control(x1, "all", "group-1", state=other)))
    if takes_state(panels.deck_control):
        foreign["deck_control_add"] = json.dumps(to_json(panels.deck_control("add", runtime.NONE_DECK, state=other)))
        foreign["deck_control_add_default"] = json.dumps(to_json(panels.deck_control("add", runtime.NONE_DECK)))
        foreign["deck_control_remove"] = json.dumps(to_json(panels.deck_control("remove", runtime.NONE_DECK, state=other)))
        foreign["deck_control_remove_default"] = json.dumps(to_json(panels.deck_control("remove", runtime.NONE_DECK)))
out["foreign_state"] = foreign

# --- the group colour rule (fix F2): focused group, then the oldest existing group -------------------------
rank_rule = None
if state is not None and "focused_group" in inspect.signature(colors.group_color).parameters:
    from flashcards_app.models import CardPosition, Flashcard  # noqa: E402
    from flashcards_app.state_core import StateCore  # noqa: E402
    from flashcards_app.user_state_service import UserStateService  # noqa: E402

    class NothingStoredEither:
        def read(self):
            return None

        def write(self, state):
            pass

    rule_core = StateCore(
        NothingStoredEither(),
        lambda decks: [Flashcard(f"x:{i}", "x", f"Q{i}", f"A{i}") for i in (1, 2, 3)],
        lambda card_ids, seed: [CardPosition(cid, 0.1 * (i + 1), 0.2, 0.3) for i, cid in enumerate(card_ids)],
    )
    rule_core.load(["x"])
    rule_core.refresh_deck_state(seed=1)
    rk = UserStateService(rule_core, runtime.CATALOG)
    a = rk.create_group("x:1", "A", "#a00001")
    rk.add_to_group("x:2", a)
    b = rk.create_group("x:1", "B", "#b00002")
    c = rk.create_group("x:1", "C", "#c00003")
    rk.add_to_group("x:3", c)

    def color(card_id, focus=None):
        return colors.group_color(card_id, rk, focus)

    rank_rule = {
        "no_focus": color("x:1"), "focus_a": color("x:1", a), "focus_b": color("x:1", b), "focus_c": color("x:1", c),
        "focus_unknown": color("x:1", "nope"), "x2": color("x:2"), "x3": color("x:3"),
        "x3_focus_a_not_member": color("x:3", a), "not_in_any_group": color("x:9"),
    }
    rk.delete_group(a)
    rank_rule["after_delete_a"] = {"x1": color("x:1"), "x2": color("x:2")}
    rk.delete_group(b)
    rank_rule["after_delete_b"] = color("x:1")
    rk.create_group("x:1", "D", "#d00004")
    rank_rule["after_new_d"] = color("x:1")
    rank_rule["ranks"] = [group.rank for group in rk.groups]
    # the same rule seen through the map: a focused group colours its members
    other_figure = map_module.make_figure(list(rk.cards), None, None, rk, c).to_dict() if takes_state(map_module.make_figure) else None
    if other_figure is not None and "focused_group" in inspect.signature(map_module.make_figure).parameters:
        by_name = {t.get("name"): t for t in other_figure["data"]}
        rank_rule["figure_colors_when_c_is_focused"] = dict(zip(by_name["Cards"]["customdata"], by_name["Cards"]["marker"]["color"]))
out["rank_rule"] = rank_rule
json.dump(out, sys.stdout)
