"""Runs one action sequence through the OLD runtime/services and through StateCore and prints both views.

Started by tests/test_state_core_equivalence.py in a temporary copy of the project; do not run it
inside your real project (it would read your real data folder).
"""

import json
import sys
import time

# Old and new code both call time.time_ns() for their random positions.
# Pinning it per step gives both sides the same seed, so coordinates can be compared exactly.
SEED = [42]
time.time_ns = lambda: SEED[0]

from flashcards_app import runtime  # noqa: E402  (old code, loads the state at import)
from flashcards_app.geometry import sphere_positions  # noqa: E402
from flashcards_app.parser import load_decks  # noqa: E402
from flashcards_app.services import cards as cards_service  # noqa: E402
from flashcards_app.services import connections as connections_service  # noqa: E402
from flashcards_app.services import decks as decks_service  # noqa: E402
from flashcards_app.services import groups as groups_service  # noqa: E402
from flashcards_app.services import positions as positions_service  # noqa: E402
from flashcards_app.services import progress as progress_service  # noqa: E402
from flashcards_app.state import JsonStateStore, save_state  # noqa: E402
from flashcards_app.state_core import STARTUP_SEED, StateCore  # noqa: E402

NEW_SAVE_PATH = runtime.STATE_PATH.with_name("new_core_state.json")
OLD_SAVE_PATH = runtime.STATE_PATH.with_name("old_runtime_state.json")


class ReadOldWriteElsewhere:
    """The core reads the same file the old code loaded, but writes to a separate one."""

    def __init__(self) -> None:
        self._source = JsonStateStore(runtime.STATE_PATH)
        self._target = JsonStateStore(NEW_SAVE_PATH)

    def read(self):
        return self._source.read()

    def write(self, state) -> None:
        self._target.write(state)


core = StateCore(
    ReadOldWriteElsewhere(),
    card_source=lambda decks: load_decks(runtime.CARDS_DIR, decks),
    position_source=sphere_positions,
)
core.load(runtime.available_decks())
core.refresh_deck_state(seed=STARTUP_SEED)


def view(enabled, cards, positions, progress, groups, links, card_by_id, position_by_id):
    return {
        "enabled": list(enabled),
        "cards": [card.id for card in cards],
        "positions": [[p.card_id, round(p.x, 9), round(p.y, 9), round(p.z, 9), p.status, p.related_ids] for p in positions],
        "progress": [[key, value.read, value.difficulty] for key, value in progress.items()],
        "groups": [[g.id, g.name, g.color, list(g.card_ids)] for g in groups],
        "links": [[l.source_id, l.target_id, l.group_id] for l in links],
        "card_by_id": sorted(card_by_id),
        "position_by_id": sorted(position_by_id),
    }


def old_view():
    return view(runtime.ENABLED_DECKS, runtime.CARDS, runtime.POSITIONS, runtime.PROGRESS, runtime.GROUPS,
                runtime.LINKS, runtime.CARD_BY_ID, runtime.POSITION_BY_ID)


def new_view():
    return view(core.enabled_decks, core.cards, core.positions, core.progress, core.groups, core.links,
                core.card_by_id, core.position_by_id)


records = []


def record(step, old=None, new=None):
    records.append({"step": step, "old": old if old is not None else old_view(), "new": new if new is not None else new_view()})


record("startup")

ids = [card.id for card in runtime.CARDS]

SEED[0] = 101
cards_service.toggle_reveal(ids[0], False)
progress_service.set_difficulty(ids[0], 40)
core.mark_read(ids[0])
core.set_difficulty(ids[0], 40)
record("reveal and difficulty")

positions_service.set_position(ids[1], 0.1, -0.2, 0.3)
core.set_position(ids[1], 0.1, -0.2, 0.3)
record("set position")

groups_service.create_group(ids[0], " A ", "#f5b942")
groups_service.create_group(ids[1], "B", "#69c6a5")
groups_service.add_to_group(ids[2], "group-3")
groups_service.add_to_group(ids[2], "group-3")
groups_service.remove_from_group(ids[1], "group-3")
new_ids = [core.create_group(ids[0], " A ", "#f5b942"), core.create_group(ids[1], "B", "#69c6a5")]
core.add_to_group(ids[2], "group-3")
core.add_to_group(ids[2], "group-3")
core.remove_from_group(ids[1], "group-3")
record("groups")

connections_service.create_link(ids[0], ids[1])
connections_service.create_link(ids[1], ids[0])
connections_service.create_link(ids[0], ids[2])
connections_service.disconnect_link(ids[2], ids[0])
core.create_link(ids[0], ids[1])
core.create_link(ids[1], ids[0])
core.create_link(ids[0], ids[2])
core.disconnect_link(ids[2], ids[0])
record("links")

groups_service.delete_group("group-2")
core.delete_group("group-2")
record("delete group")

SEED[0] = 1111
decks_service.add_enabled_deck("gamma")
core.enable_deck("gamma")
record("enable deck")

SEED[0] = 2222
decks_service.remove_enabled_deck("alpha")
core.disable_deck("alpha")
record("disable deck")

NONE_DECK = runtime.NONE_DECK
combos = [("all", None), ("beta", None), (NONE_DECK, None), (None, None), ("all", "group-1"), ("all", "nope"), ("beta", "group-1")]
visible = {"old": [], "new": []}
for deck, group in combos:
    visible["old"].append([deck, group, [c.id for c in runtime.visible_cards(deck, group)]])
    if deck in (None, NONE_DECK):
        new_cards = []
    else:
        new_cards = core.visible_cards(None if deck == "all" else deck, group)
    visible["new"].append([deck, group, [c.id for c in new_cards]])
record("visible cards", old=visible["old"], new=visible["new"])

# give reset something to clear (the previous step stripped all links)
remaining = [card.id for card in runtime.CARDS]
groups_service.add_to_group(remaining[0], "group-1")
connections_service.create_link(remaining[0], remaining[1])
core.add_to_group(remaining[0], "group-1")
core.create_link(remaining[0], remaining[1])
record("group member and link before reset")

SEED[0] = 3333
runtime.reset_all_state()
core.reset_all_state()
record("reset")

save_state(OLD_SAVE_PATH, runtime.POSITIONS, runtime.PROGRESS, runtime.GROUPS, runtime.LINKS, runtime.ENABLED_DECKS)
core.save()

json.dump(
    {
        "records": records,
        "group_ids_from_core": new_ids,
        "files": {"old": OLD_SAVE_PATH.read_text(encoding="utf-8"), "new": NEW_SAVE_PATH.read_text(encoding="utf-8")},
    },
    sys.stdout,
)
