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
from world import load_world  # noqa: E402  (tests/world.py: the original app or the one app.py composes)
from flashcards_app.visualization import colors, panels  # noqa: E402
from flashcards_app.visualization import map as map_module  # noqa: E402

W = load_world()
kw = W.state_kw()  # {"state": ...} for the current code; the original functions take none

# --- build a state with: read cards of different difficulty, a card in two groups, links, a second deck ------
ids = [card.id for card in W.cards]
W.reveal(ids[2])
W.set_difficulty(ids[2], 20)
W.reveal(ids[3])
W.set_difficulty(ids[3], 90)
W.create_group(ids[0], "A", "#aaaaaa")  # group-2; ids[0] is also in group-1 (fixture): two groups
W.add_to_group(ids[1], "group-2")
W.create_group(ids[4], "B", "#bbbbbb")  # group-3
W.create_link(ids[1], ids[3])
W.create_link(ids[0], ids[2])
W.create_link(ids[3], ids[4])
W.create_link(ids[0], ids[1])  # both are members of group-2: focusing that group still shows it
SEED[0] = 1111
W.add_enabled_deck("gamma")
ids = [card.id for card in W.cards]
W.create_link(ids[0], ids[5])
W.set_position(ids[1], 0.1, 0.2, 0.3)

all_ids = ids + ["unknown:1"]
state = W.user_state


def takes_state(func):
    return "state" in inspect.signature(func).parameters


def with_explicit(name, func, *args):
    """Call func(*args), handing over the state when the code under test takes one (the name is only a label)."""
    return func(*args, **kw)


out = {}

# --- colors ---------------------------------------------------------------------------------------------
out["colors"] = {
    "progress_by_card": {cid: with_explicit(f"progress_color:{cid}", colors.progress_color, cid) for cid in all_ids},
    "progress_by_value": {str(v): colors.progress_color(v, **kw) for v in (1, 17, 34, 35, 50, 69, 70, 100, 150, -3)},
    "group_by_card": {cid: with_explicit(f"group_color:{cid}", colors.group_color, cid) for cid in all_ids},
}

# --- map ------------------------------------------------------------------------------------------------
camera = {"eye": {"x": 1.0, "y": 2.0, "z": 3.0}, "up": {"x": 0, "y": 0, "z": 1}, "center": {"x": 0, "y": 0, "z": 0}}
combos = [("all", None), ("alpha", None), ("beta", None), ("gamma", None), ("all", "group-1"), ("all", "group-2"),
          ("all", "group-3"), ("alpha", "group-2"), ("beta", "group-2"), (W.none_deck, None), ("all", "nope")]
figures = {"empty": map_module.make_figure([], **kw).to_dict()}
links_visible = {}
for deck, group in combos:
    visible = W.visible_cards(deck, group)
    visible_ids = {card.id for card in visible}
    key = f"{deck}|{group}"
    figure = with_explicit(f"make_figure:{key}", map_module.make_figure, visible, None, None)
    figures[key] = figure.to_dict()
    drawn = [[round(c, 9) for c in (trace["x"][0], trace["y"][0], trace["z"][0], trace["x"][1], trace["y"][1], trace["z"][1])]
             for trace in figure.to_dict()["data"] if trace.get("name") == "Connection"]
    expected = []
    for link in W.links:
        if link.source_id in visible_ids and link.target_id in visible_ids:
            a, b = W.position_by_id[link.source_id], W.position_by_id[link.target_id]
            expected.append([round(c, 9) for c in (a.x, a.y, a.z, b.x, b.y, b.z)])
    links_visible[key] = {"drawn": drawn, "expected": expected, "total_links": len(W.links)}
all_cards = list(W.cards)
figures["selected"] = map_module.make_figure(all_cards, ids[1], **kw).to_dict()
figures["selected_with_camera"] = map_module.make_figure(all_cards, ids[1], camera, **kw).to_dict()
figures["selected_not_visible"] = map_module.make_figure(W.visible_cards("beta", None), ids[0], **kw).to_dict()
out["map"] = {"figures": figures, "links_visible": links_visible, "legend": to_json(map_module.color_legend())}

# --- panels ---------------------------------------------------------------------------------------------
unread, read_card, two_groups = W.card_by_id[ids[4]], W.card_by_id[ids[2]], W.card_by_id[ids[0]]

def is_note(x):
    return isinstance(x, dict) and isinstance(x.get("props"), dict) and x["props"].get("className") == "dialog-note"


def is_swatch(x):
    return isinstance(x, dict) and isinstance(x.get("props"), dict) and str(x["props"].get("className", "")).startswith("group-color-swatch")


def strip_notes(x):
    """The recorded tree without what the original does not have (the dialog notes and the highlight of group swatches:
    a class and an inline colour), so that the rest can be compared with the original."""
    if isinstance(x, list):
        return [strip_notes(i) for i in x if not is_note(i)]
    if is_swatch(x):
        style = {"backgroundColor": x["props"]["style"]["backgroundColor"]}
        return dict(x, props=dict(x["props"], className="group-color-swatch", style=style))
    if isinstance(x, dict):
        return {k: strip_notes(v) for k, v in x.items()}
    return x


def highlighted_in(x, found=None):
    """[[group name, swatch colour, glow colour]] for every highlighted group swatch in a recorded tree."""
    found = [] if found is None else found
    if isinstance(x, list):
        for index, item in enumerate(x):
            if is_swatch(item) and "group-color-swatch-shared" in item["props"]["className"]:
                style = item["props"]["style"]
                found.append([x[index + 1]["args"][0], style.get("backgroundColor"), style.get("color")])
        for item in x:
            highlighted_in(item, found)
    elif isinstance(x, dict):
        for value in x.values():
            highlighted_in(value, found)
    return found


def notes_in(x, found=None):
    """[(text, ids of the buttons in the same row)] for every dialog note in a recorded tree."""
    found = [] if found is None else found
    if isinstance(x, list):
        notes = [i for i in x if is_note(i)]
        if notes:
            buttons = [i["props"].get("id") for i in x if isinstance(i, dict) and i.get("type") == "html.Button"]
            found.extend([n["args"][0], buttons] for n in notes)
        for i in x:
            notes_in(i, found)
    elif isinstance(x, dict):
        for v in x.values():
            notes_in(v, found)
    return found

group_dialogs = (None, "new", "add", "remove", "delete", "focus")
group_trees = [(i, dialog, to_json(with_explicit(f"group:{i}:{dialog}", panels.group_control, c, dialog)))
               for i, c in enumerate((None, read_card, two_groups, unread)) for dialog in group_dialogs]
deck_trees = [(dialog, selected, to_json(with_explicit(f"deck:{dialog}:{selected}", panels.deck_control, dialog, selected)))
              for dialog in (None, "add", "remove", "focus") for selected in (W.none_deck, "all", "alpha")]
out["panels"] = {
    "card_panel": [to_json(panels.card_panel(c, r)) for c in (None, read_card) for r in (False, True)],
    "difficulty": [to_json(with_explicit(f"difficulty:{i}", panels.difficulty_control, c)) for i, c in enumerate((None, read_card, unread, two_groups))],
    "position": [to_json(with_explicit(f"position:{i}:{d}", panels.position_control, c, d)) for i, c in enumerate((None, read_card)) for d in (False, True)],
    "group": [strip_notes(tree) for _, _, tree in group_trees],
    "deck": [strip_notes(tree) for _, _, tree in deck_trees],
    "connection": [to_json(W.connection_control(c, deck, fg))
                   for c in (None, read_card) for deck in ("all", "alpha", "beta") for fg in (None, "group-1", "group-2")],
}

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
        return UserStateService(core, W.catalog)

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
    if W.current:  # the connection list is built from the cards it is given, not from a state
        foreign["connection_control"] = json.dumps(to_json(panels.connection_control(x1, other.visible_cards(None, None))))
        foreign["connection_control_focused"] = json.dumps(to_json(panels.connection_control(x1, other.visible_cards(None, "group-1"))))
    if takes_state(panels.deck_control):
        foreign["deck_control_add"] = json.dumps(to_json(panels.deck_control("add", W.none_deck, state=other)))
        foreign["deck_control_add_default"] = json.dumps(to_json(panels.deck_control("add", W.none_deck, state=state)))
        foreign["deck_control_remove"] = json.dumps(to_json(panels.deck_control("remove", W.none_deck, state=other)))
        foreign["deck_control_remove_default"] = json.dumps(to_json(panels.deck_control("remove", W.none_deck, state=state)))
out["foreign_state"] = foreign

# group swatches: the groups that share member cards with the focused group glow (tranche 9)
swatches = None
if W.current:
    def expected_glow(focus_id):
        focused = next((g for g in W.groups if g.id == focus_id), None)
        if focused is None:
            return []
        return sorted(g.name for g in W.groups if g is not focused and set(g.card_ids) & set(focused.card_ids))

    swatches = {}
    for focus in [None] + [g.id for g in W.groups] + ["nope"]:
        found = highlighted_in(to_json(panels.group_control(None, None, focused_group=focus, **kw)))
        swatches[str(focus)] = {
            "highlighted": sorted(name for name, _, _ in found),
            "glow_is_the_group_colour": all(background == glow for _, background, glow in found),
            "expected": expected_glow(focus),
        }
out["swatches"] = swatches

# the dialog notes: which text next to which buttons, for every card and dialog (fix F3)
out["notes"] = {
    "group": {f"{i}:{dialog}": notes_in(tree) for i, dialog, tree in group_trees},
    "deck": {f"{dialog}:{selected}": notes_in(tree) for dialog, selected, tree in deck_trees},
}

# --- without a state the current functions refuse to run (they used to fall back to a shared one) ----------
missing_state = None
if W.current:
    def refuses(func, *args):
        try:
            func(*args)
        except TypeError as error:
            return "state is required" in str(error)
        except Exception as error:  # a different failure is not the clear message
            return f"other: {type(error).__name__}"
        return False

    some_card = W.card_by_id[ids[2]]
    missing_state = {
        "progress_color": refuses(colors.progress_color, ids[2]),
        "group_color": refuses(colors.group_color, ids[2]),
        "make_figure": refuses(map_module.make_figure, []),
        "difficulty_control": refuses(panels.difficulty_control, some_card),
        "position_control": refuses(panels.position_control, some_card),
        "group_control": refuses(panels.group_control, some_card),
        "deck_control": refuses(panels.deck_control, None),
    }
out["missing_state"] = missing_state
# a group focus that does not exist shows no cards, so the connection list is empty too (the original listed all)
out["connection_unknown_group"] = to_json(W.connection_control(W.card_by_id[ids[2]], "all", "nope")) if W.current else None

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
    rk = UserStateService(rule_core, W.catalog)
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
