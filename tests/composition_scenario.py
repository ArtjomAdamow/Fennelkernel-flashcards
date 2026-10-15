"""Imports the composition root (app.py) in a temporary project and records what it built.

Started by tests/test_composition.py with stand-ins for dash, plotly and flask (tests/stubs).
Do not run it inside your real project.

    python composition_scenario.py          the full scenario
    python composition_scenario.py no_data  import the hub with no data folder at all
"""

import json
import shutil
import sys
import time

SEED = [42]
time.time_ns = lambda: SEED[0]

if len(sys.argv) > 1 and sys.argv[1] == "no_data":
    shutil.move("data", "data_moved_away")
    from flashcards_app import runtime  # must not read or need anything

    json.dump({"imported": True, "names": sorted(n for n in dir(runtime) if not n.startswith("_")), "app_imported": "app" in sys.modules}, sys.stdout)
    sys.exit(0)

if len(sys.argv) > 1 and sys.argv[1] == "enabled":
    # phase 2: only the enabled decks after the start (the precedence scenario went with LEGACY_STATE_PATH)
    import app as application

    json.dump({"enabled": list(application.composition.user_state.enabled_decks)}, sys.stdout)
    sys.exit(0)

import app as application  # noqa: E402  (composes at import)
from flashcards_app import runtime  # noqa: E402

comp = application.composition
state = comp.user_state
out = {}

out["startup"] = {
    "enabled": list(state.enabled_decks),
    "cards": [c.id for c in state.cards],
    "boot_id_matches": comp.boot_id == application.SERVER_BOOT_ID,
    "app_is_the_dash_app": application.app is comp.dash_app,
    "hub_holds_the_service": comp.hub.user_state is state,
    "service_uses_the_core": state.cards is comp.core.cards,
    "callback_registered": len(comp.dash_app.callbacks) == 1,
}
out["constants"] = {
    "base_dir_holds_app_py": (application.BASE_DIR / "app.py").exists(),
    "state_path": application.STATE_PATH.relative_to(application.BASE_DIR).as_posix(),
    "cards_file": application.CARDS_FILE.relative_to(application.BASE_DIR).as_posix(),  # phase 2
    "has_legacy_state_path": hasattr(application, "LEGACY_STATE_PATH"),
    "none_deck": runtime.NONE_DECK,
}
out["runtime_names"] = sorted(n for n in dir(runtime) if not n.startswith("_"))

# F4: remove a deck, start the way main() does, restart
state.disable_deck("beta")
state.set_difficulty(state.cards[0].id, 33)
application.main()
saved = json.loads(application.STATE_PATH.read_text(encoding="utf-8"))
out["f4"] = {"decks_in_file": saved.get("decks"), "app_run_called": getattr(application.app, "ran_with", None)}
again = application.compose()  # a second composition is a restart: it reads the file that main() wrote
out["f4"]["after_restart_enabled"] = list(again.user_state.enabled_decks)
out["f4"]["after_restart_cards"] = [c.id for c in again.user_state.cards]
out["f4"]["after_restart_difficulty"] = again.user_state.progress[again.user_state.cards[0].id].difficulty
out["f4"]["two_compositions_are_independent"] = again.core is not comp.core and again.user_state.cards is not state.cards
# phase 2: the saved file is keyed by comb_id
out["f4"]["state_keys"] = sorted({key for section in ("positions", "progress") for item in saved[section] for key in item if key.endswith("_id")})
json.dump(out, sys.stdout)
