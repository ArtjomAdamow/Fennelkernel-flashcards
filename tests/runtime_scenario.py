"""Runs one action sequence through flashcards_app.runtime and the old services, prints what it sees.

Started by tests/test_runtime_router_equivalence.py in a temporary copy of the project, once with the
legacy runtime and once with the router runtime. Do not run it inside your real project.

    python runtime_scenario.py run       mutate, save like the callbacks do
    python runtime_scenario.py startup   only print the state seen right after startup
"""

import json
import sys
import time

# Both runtimes call time.time_ns() for random positions; pinning it per step makes them comparable
SEED = [42]
time.time_ns = lambda: SEED[0]

from flashcards_app import runtime  # noqa: E402
from flashcards_app.models import CardLink  # noqa: E402
from flashcards_app.services import cards as cards_service  # noqa: E402
from flashcards_app.services import connections as connections_service  # noqa: E402
from flashcards_app.services import decks as decks_service  # noqa: E402
from flashcards_app.services import groups as groups_service  # noqa: E402
from flashcards_app.services import positions as positions_service  # noqa: E402
from flashcards_app.services import progress as progress_service  # noqa: E402
from flashcards_app.state import save_state  # noqa: E402


def view():
    return {
        "enabled": list(runtime.ENABLED_DECKS),
        "available": runtime.available_decks(),
        "available_snapshot": list(runtime.AVAILABLE_DECKS),
        "cards": [card.id for card in runtime.CARDS],
        "positions": [[p.card_id, round(p.x, 9), round(p.y, 9), round(p.z, 9), p.status, p.related_ids] for p in runtime.POSITIONS],
        "progress": [[key, v.read, v.difficulty] for key, v in runtime.PROGRESS.items()],
        "groups": [[g.id, g.name, g.color, list(g.card_ids)] for g in runtime.GROUPS],
        "links": [[l.source_id, l.target_id, l.group_id] for l in runtime.LINKS],
        "card_by_id": sorted(runtime.CARD_BY_ID),
        "position_by_id": sorted(runtime.POSITION_BY_ID),
    }


def names_are_the_cores_objects():
    core = getattr(runtime, "CORE", None)
    if core is None:
        return None
    pairs = [
        (runtime.CARDS, core.cards), (runtime.POSITIONS, core.positions), (runtime.PROGRESS, core.progress),
        (runtime.GROUPS, core.groups), (runtime.LINKS, core.links), (runtime.ENABLED_DECKS, core.enabled_decks),
        (runtime.CARD_BY_ID, core.card_by_id), (runtime.POSITION_BY_ID, core.position_by_id),
    ]
    return all(a is b for a, b in pairs)


if sys.argv[1] == "startup":
    json.dump({"startup": view()}, sys.stdout)
    sys.exit(0)

records = []
containers = [runtime.CARDS, runtime.POSITIONS, runtime.PROGRESS, runtime.GROUPS, runtime.LINKS,
              runtime.ENABLED_DECKS, runtime.CARD_BY_ID, runtime.POSITION_BY_ID]


def record(step, value=None):
    records.append({"step": step, "state": value if value is not None else view()})


record("startup")
ids = [card.id for card in runtime.CARDS]

SEED[0] = 101
cards_service.toggle_reveal(ids[0], False)
progress_service.set_difficulty(ids[0], 40)
record("reveal and difficulty")

positions_service.set_position(ids[1], 0.1, -0.2, 0.3)
record("set position")

# includes the old duplicate-id case on purpose: the services still use the old numbering
groups_service.create_group(ids[0], " A ", "#f5b942")
groups_service.create_group(ids[1], "B", "#69c6a5")
groups_service.add_to_group(ids[2], "group-3")
groups_service.remove_from_group(ids[1], "group-3")
groups_service.delete_group("group-2")
groups_service.create_group(ids[2], "C", "#e76f51")
record("groups")

connections_service.create_link(ids[0], ids[1])
connections_service.create_link(ids[1], ids[0])
connections_service.create_link(ids[0], ids[2])
connections_service.disconnect_link(ids[2], ids[0])
record("links")

SEED[0] = 1111
decks_service.add_enabled_deck("gamma")
decks_service.add_enabled_deck("None")
decks_service.add_enabled_deck("does-not-exist")
record("enable deck")
record("filter options", decks_service.deck_filter_options())

SEED[0] = 2222
decks_service.remove_enabled_deck("alpha")
record("disable deck")

# direct refresh strips what points at cards that are not loaded
runtime.GROUPS[0].card_ids.append("ghost:1")
runtime.LINKS.append(CardLink("ghost:1", ids[3]))
runtime.PROGRESS["ghost:1"] = runtime.PROGRESS[next(iter(runtime.PROGRESS))].__class__("ghost:1")
SEED[0] = 4444
runtime.refresh_deck_state()
record("refresh strips")

combos = [("all", None), ("beta", None), (runtime.NONE_DECK, None), (None, None), ("all", "group-1"), ("all", "nope"), ("beta", "group-1"), ("alpha", None)]
record("visible cards", [[d, g, [c.id for c in runtime.visible_cards(d, g)]] for d, g in combos])

remaining = [card.id for card in runtime.CARDS]
groups_service.add_to_group(remaining[0], "group-1")
connections_service.create_link(remaining[0], remaining[1])
SEED[0] = 3333
runtime.reset_all_state()
record("reset")

save_state(runtime.STATE_PATH, runtime.POSITIONS, runtime.PROGRESS, runtime.GROUPS, runtime.LINKS, runtime.ENABLED_DECKS)

json.dump(
    {
        "records": records,
        "saved_file": runtime.STATE_PATH.read_text(encoding="utf-8"),
        "containers_unchanged": all(a is b for a, b in zip(containers, [
            runtime.CARDS, runtime.POSITIONS, runtime.PROGRESS, runtime.GROUPS, runtime.LINKS,
            runtime.ENABLED_DECKS, runtime.CARD_BY_ID, runtime.POSITION_BY_ID])),
        "names_are_the_cores_objects": names_are_the_cores_objects(),
    },
    sys.stdout,
)
