"""Start the flashcards app with the draft deck loading (data/cards.json, version 2). Run from anywhere:

    .venv/Scripts/python.exe modules/loader/deck_v2_launcher.py

No project file is changed; the rerouting exists only inside the launched process:
  * Before anything else of flashcards_app is imported, the deck components are loaded from this
    folder under their project module names (REROUTES). Untouched project modules (state_core, state,
    geometry, callbacks, ...) then get the draft versions through their normal imports.
  * changes/app.py (app.py with the deck wiring changed) is run as module "app", with __file__ pointing
    at the project's app.py, so BASE_DIR and with it the assets and data paths stay the project's.
  * state.JsonStateStore is replaced by DetachedStateStore: data/positions.json is neither read nor
    written. That file holds version 2 state for the old .md card ids and deck names; the draft
    starts from an empty state (all decks enabled, generated positions) and saves nothing.
  * The .md decks are not touched: no DeckCatalog, no parser.load_decks on data/cards.

The course file is read once per process (app.run(debug=True) runs the app in a reloader child
process, which reads it once more); edits to it show up after a restart only.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

DRAFT_DIR = Path(__file__).resolve().parent
CHANGES_DIR = DRAFT_DIR / "changes"
ROOT = DRAFT_DIR.parents[1]

# Run as a script, sys.path[0] is this folder: its parser.py / models.py must not be importable as
# top-level modules, only the project root is needed
if sys.path and Path(sys.path[0] or ".").resolve() == DRAFT_DIR:
    sys.path[0] = str(ROOT)
elif str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Project module -> file that replaces it. In dependency order: each one imports only those before it
# and untouched project modules.
REROUTES = {
    "flashcards_app.models": DRAFT_DIR / "models.py",
    "flashcards_app.parser": DRAFT_DIR / "parser.py",
    "flashcards_app.deck_catalog": DRAFT_DIR / "deck_catalog.py",
    "flashcards_app.user_state_service": CHANGES_DIR / "user_state_service.py",
}
APP_SOURCE = CHANGES_DIR / "app.py"


class DetachedStateStore:
    """Stands in for state.JsonStateStore (same constructor, StatePersistence protocol): no state file is used."""

    def __init__(self, path: Path, supported_versions=None) -> None:
        self.path = Path(path)

    def read(self) -> None:
        # Like a missing state file: StateCore.load enables all available decks
        return None

    def write(self, state) -> None:
        # Saving is not part of the draft
        pass


def _load(name: str, path: Path, file: Path | None = None) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    if file is not None:
        # Only what the module sees as its own path; the code is still compiled from `path`
        module.__file__ = str(file)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


def _is_from(module: ModuleType, path: Path) -> bool:
    return module.__spec__ is not None and module.__spec__.origin is not None and Path(module.__spec__.origin).resolve() == path


def reroute_deck_components() -> None:
    """Load the draft deck components under the project module names. Safe to call twice."""
    import flashcards_app  # the package itself only holds a docstring

    for name, path in REROUTES.items():
        module = sys.modules.get(name)
        if module is None:
            module = _load(name, path)
        elif not _is_from(module, path):
            raise RuntimeError(f"{name} was imported from {module.__spec__.origin} before the rerouting")
        # What a normal import would do: the submodule becomes an attribute of its package
        setattr(flashcards_app, name.rpartition(".")[2], module)


def detach_state_store() -> None:
    """Keep data/positions.json out of the launched app (read and write)."""
    import flashcards_app.state

    flashcards_app.state.JsonStateStore = DetachedStateStore


def load_app() -> ModuleType:
    """Reroute, detach the state file, then import changes/app.py as "app" (this builds the composition)."""
    reroute_deck_components()
    detach_state_store()
    module = sys.modules.get("app")
    if module is None:
        module = _load("app", APP_SOURCE, file=ROOT / "app.py")
    elif not _is_from(module, APP_SOURCE):
        raise RuntimeError(f"app was imported from {module.__spec__.origin} before the rerouting")
    return module


def main() -> None:
    load_app().main()


if __name__ == "__main__":
    main()
