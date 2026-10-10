"""Drives the one Dash callback of the app through a scripted session and records everything it returns.

Started by tests/test_callbacks_equivalence.py in a temporary copy of the project, with stand-ins for dash,
plotly and flask (tests/stubs). The callback is taken from the app object after `flashcards_app.callbacks`
was imported, so it works for the original module (registers at import) and for the router (registers through
callbacks_impl). Do not run it inside your real project.
"""

import inspect
import json
import random
import sys
import time

SEED = [42]
time.time_ns = lambda: SEED[0]

import dash  # noqa: E402  (stand-in)
from dash import to_json  # noqa: E402
from flashcards_app import runtime  # noqa: E402
from flashcards_app import callbacks  # noqa: E402,F401  (registers the callback)
from flashcards_app.server import app  # noqa: E402
from flashcards_app.services import groups as groups_service  # noqa: E402

assert len(app.callbacks) == 1, app.callbacks
registration, update_card = app.callbacks[0]
specs = [(a.component_id, a.component_property) for a in registration if a.kind in ("Input", "State")]
parameter_names = list(inspect.signature(update_card).parameters)
assert len(specs) == len(parameter_names)

BASE = {f"{cid}.{prop}": (0 if prop == "n_clicks" else None) for cid, prop in specs}
BASE.update({"revealed.data": False, "drag-enabled.data": False, "deck-filter.value": runtime.NONE_DECK, "keyboard-nav.value": ""})
carried = {}


def norm(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(k): norm(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [norm(v) for v in value]
    return to_json(value)


def find_by_id(node, wanted):
    if isinstance(node, dict):
        if isinstance(node.get("props"), dict) and node["props"].get("id") == wanted:
            return node
        for v in node.values():
            found = find_by_id(v, wanted)
            if found:
                return found
    elif isinstance(node, list):
        for v in node:
            found = find_by_id(v, wanted)
            if found:
                return found
    return None


def saved_file():
    data = json.loads(runtime.STATE_PATH.read_text(encoding="utf-8"))
    for group in data["groups"]:
        group.pop("rank", None)
    for link in data["links"]:
        link.pop("group_id", None)
    return data


def view():
    return {
        "enabled": list(runtime.ENABLED_DECKS),
        "cards": [c.id for c in runtime.CARDS],
        "positions": [[p.card_id, round(p.x, 9), round(p.y, 9), round(p.z, 9)] for p in runtime.POSITIONS],
        "progress": [[k, v.read, v.difficulty] for k, v in runtime.PROGRESS.items()],
        "groups": [[g.id, g.name, g.color, list(g.card_ids)] for g in runtime.GROUPS],
        "links": [[l.source_id, l.target_id] for l in runtime.LINKS],
    }


records = []


def call(label, trigger, values=None, record=True):
    SEED[0] = 1000 + len(records)
    random.seed(7)
    dash.ctx.triggered_id = trigger
    inputs = dict(BASE)
    inputs.update(carried)
    inputs.update(values or {})
    out = update_card(**dict(zip(parameter_names, [inputs[f"{cid}.{prop}"] for cid, prop in specs])))
    assert len(out) == 18
    normalized = norm(out)
    carried.update({
        "selected-id.data": out[7], "revealed.data": out[8], "drag-enabled.data": out[10],
        "group-dialog.data": out[13], "focused-group.data": out[14], "deck-dialog-state.data": out[16],
        "deck-filter.value": find_by_id(normalized[15], "deck-filter")["props"]["value"],
    })
    if record:
        records.append({"step": label, "trigger": trigger, "outputs": normalized, "state": view(), "file": saved_file()})
    return normalized


def key(value):
    return {"keyboard-nav.value": value}


call("initial load", None)
call("deck: all", "all-decks")
ids = [c.id for c in runtime.CARDS]
call("next card", "keyboard-nav", key("next"))
call("next card again", "keyboard-nav", key("next"))
call("reveal", "selected-card", {"selected-card.n_clicks": 1})
call("hide", "selected-card", {"selected-card.n_clicks": 2})
call("reveal again", "selected-card", {"selected-card.n_clicks": 3})
call("difficulty", "difficulty-slider", {"difficulty-slider.value": 40})
call("new group dialog", "new-group")
call("create group", "group-dialog-submit", {"dialog-group-name.value": "G1", "dialog-group-color.value": {"hex": "#112233"}})
call("third card", "keyboard-nav", key("next"))  # not a member of the older fixture group: no card is in two groups here
call("add to group dialog", "add-group")
call("add to group", "group-dialog-submit", {"dialog-group-select.value": "group-2"})
call("cancel group dialog", "group-dialog-cancel")
call("focus group dialog", "focus-group")
call("focus group", "group-dialog-submit", {"dialog-group-select.value": "group-2"})
call("next card inside the focus", "keyboard-nav", key("next"))
call("previous card inside the focus", "keyboard-nav", key("previous"))
call("all groups", "all-groups")
call("link", "create-link", {"link-target.value": ids[3]})
call("unlink", "disconnect-link", {"link-target.value": ids[3]})
call("link again", "create-link", {"link-target.value": ids[3]})
call("toggle drag", "toggle-drag")
drag = {"drag-x.value": 0.25, "drag-y.value": 0.1, "drag-z.value": -0.2}
call("drag", "drag-x", drag)
call("save position", "save-position", drag)
call("random card", "random-card")
call("click on the map", "sphere", {"sphere.clickData": {"points": [{"customdata": ids[3]}]}})
call("click with hover", "sphere", {"sphere.clickData": {"points": [{"customdata": ids[3]}]}, "sphere.hoverData": {"points": [{"customdata": ids[0]}]}})
call("add deck dialog", "add-deck")
call("add deck", "deck-dialog-submit", {"deck-dialog-select.value": "gamma"})
call("focus deck dialog", "focus-deck")
call("focus deck", "deck-dialog-submit", {"deck-dialog-select.value": "gamma"})
call("remove deck dialog", "remove-deck")
call("remove the focused deck", "deck-dialog-submit", {"deck-dialog-select.value": "gamma"})
call("cancel deck dialog", "deck-dialog-cancel")
call("deck: all again", "all-decks")
call("deck filter", "deck-filter", {"deck-filter.value": "beta"})
call("deck: all (3)", "all-decks")
call("focus group (to delete it)", "focus-group")
call("focus group submit", "group-dialog-submit", {"dialog-group-select.value": "group-2"})
call("delete dialog", "delete-group")
call("delete the focused group", "group-dialog-submit", {"dialog-group-select.value": "group-2"})
call("all groups (2)", "all-groups")
call("reset dialog", "reset-cards")
call("reset", "reset-confirm", {"reset-confirm.submit_n_clicks": 1})
call("reveal without a selection", "selected-card", {"selected-card.n_clicks": 4})

out = {
    "registration": [[a.kind, a.component_id, a.component_property] for a in registration],
    "records": records,
}

# --- the layout, the title, the boot-id route and the index page --------------------------------------------
boot = runtime.SERVER_BOOT_ID
out["server"] = {
    "title": app.title,
    "layout": json.loads(json.dumps(to_json(app.layout)).replace(boot, "<BOOT>")),
    "index_string": app.index_string.replace(boot, "<BOOT>"),
    "routes": sorted(app.server.routes),
    "boot_id_route": json.loads(json.dumps(app.server.routes["/boot-id"]()).replace(boot, "<BOOT>")),
    "assets_folder": str(app.assets_folder).replace(str(runtime.BASE_DIR), "<BASE>"),
}

# --- fix F2 through the callback: a card in two groups, one of them focused -------------------------------
ids = [c.id for c in runtime.CARDS]
groups_service.create_group(ids[0], "P", "#aaaaaa")  # group-1, the older group
groups_service.create_group(ids[1], "Q", "#bbbbbb")  # group-2, the younger group
groups_service.add_to_group(ids[0], "group-2")  # ids[0] is a member of both


def card_colors(outputs):
    traces = {t.get("name"): t for t in outputs[0]["data"]}
    return dict(zip(traces["Cards"]["customdata"], traces["Cards"]["marker"]["color"])) if "Cards" in traces else {}


call("F2 focus dialog", "focus-group", record=False)
focused = call("F2 focus Q", "group-dialog-submit", {"dialog-group-select.value": "group-2"}, record=False)
call("F2 all groups", "all-groups", record=False)
unfocused = call("F2 deck all", "all-decks", record=False)
out["f2"] = {"ids": ids[:2], "focused_on_younger_group": card_colors(focused), "nothing_focused": card_colors(unfocused)}

# --- the injected state is the one that gets used (current code only) ------------------------------------------
foreign = None
register_callbacks = None
if hasattr(runtime, "USER_STATE"):  # the original runtime has none
    try:
        from flashcards_app.callbacks_impl import register_callbacks
    except ImportError:  # tranche 7c is not inserted yet
        register_callbacks = None
if register_callbacks is not None:
    from flashcards_app.models import CardPosition, Flashcard
    from flashcards_app.state_core import StateCore
    from flashcards_app.user_state_service import UserStateService

    class NothingStored:
        def read(self):
            return None

        def write(self, state):
            pass

    core = StateCore(
        NothingStored(),
        lambda decks: [Flashcard(f"x:{i}", "x", f"Q{i}", f"A{i}") for i in (1, 2)],
        lambda card_ids, seed: [CardPosition(cid, 0.1 * (i + 1), 0.2, 0.3) for i, cid in enumerate(card_ids)],
    )
    core.load(["x"])
    core.refresh_deck_state(seed=1)
    other = UserStateService(core, runtime.CATALOG)
    other_callback = register_callbacks(dash.Dash(), other, runtime.NONE_DECK)
    file_before = runtime.STATE_PATH.read_text(encoding="utf-8")
    shared_cards_before = [c.id for c in runtime.CARDS]

    def call_other(trigger, **changes):
        dash.ctx.triggered_id = trigger
        values = dict(BASE, **changes)
        return norm(other_callback(**dict(zip(parameter_names, [values[f"{c}.{p}"] for c, p in specs]))))

    first = call_other("all-decks", **{"deck-filter.value": runtime.NONE_DECK})
    second = call_other("keyboard-nav", **{"deck-filter.value": "all", "keyboard-nav.value": "next"})
    foreign = {
        "count_text": first[9],
        "map_card_ids": sorted(card_colors(first)),
        "selected": second[7],
        "difficulty": json.dumps(second[2]),
        "position": json.dumps(second[3]),
        "groups": json.dumps(second[4]),
        "connections": json.dumps(second[5]),
        "deck_control": json.dumps(second[15]),
        "filter_option_values": [o["value"] for o in second[17]],
        "shared_cards_unchanged": [c.id for c in runtime.CARDS] == shared_cards_before,
        "shared_file_unchanged": runtime.STATE_PATH.read_text(encoding="utf-8") == file_before,
    }
    # the server builds its first page from the state it is given
    from flashcards_app.server_impl import create_app
    built = create_app(runtime.BASE_DIR, "BOOT-X", other)
    layout = json.dumps(to_json(built.layout))
    foreign["server"] = {
        "layout_has_foreign_cards": "x:1" in layout,
        "layout_has_shared_cards": "alpha:" in layout or "beta:" in layout,
        "layout_deck_options_are_the_foreign_ones": '"value": "x"' in layout and '"value": "alpha"' not in layout,
        "layout_group_list_is_the_foreign_one": "No saved groups yet." in layout,
        "boot_id_in_index_page": 'window.__SERVER_BOOT_ID__ = "BOOT-X"' in built.index_string,
        "boot_id_route": built.server.routes["/boot-id"](),
    }
out["foreign"] = foreign
json.dump(out, sys.stdout)
