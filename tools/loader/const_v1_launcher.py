"""Launch the merged flashcards app with constellation overrides:
    
    server is the tranche 1 override,
    map, panels and callbacks are tranche 3 overrides.
    
Run from the repository root with the project's interpreter:

    .venv/Scripts/python.exe tools/loader/const_v1_launcher.py

Phases 1 and 2 are merged into the main project, so only tranche 1's changed
map and server modules are loaded from modules/constellations/changes/.
The server override provides the asset overlay and navigation stores. This
launcher redirects ordinary app state to tools/loader/scratch/const_user_state.json;
runtime constellation/navigation state is not written to the project state file.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

LAUNCHER_DIR = Path(__file__).resolve().parent
ROOT = LAUNCHER_DIR.parents[1]
MODULE_DIR = ROOT / "modules" / "constellations"
CHANGES_DIR = MODULE_DIR / "changes"
SCRATCH_STATE = LAUNCHER_DIR / "scratch" / "const_user_state.json"
APP_SOURCE = ROOT / "app.py"

# Running a script sets sys.path[0] to tools/loader. Keep project imports rooted
# at the repository, never at this launcher's directory.
if sys.path and Path(sys.path[0] or ".").resolve() == LAUNCHER_DIR:
    sys.path[0] = str(ROOT)
elif str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Models are dependencies of StateCore and the user-state service. The changed
# StateCore adds persisted bulk link deletion; runtime/panels depend on the
# resulting user-state service, and callbacks depend on panels and map.
REROUTES: dict[str, Path] = {
    # Phase 1/2 copies were merged into the main project. Keep only tranche 1
    # overrides here; their dependency order is map, then server.
    "flashcards_app.visualization.map": CHANGES_DIR / "map.py",
    "flashcards_app.visualization.panels": CHANGES_DIR / "panels.py",
    "flashcards_app.callbacks": CHANGES_DIR / "callbacks.py",
    "flashcards_app.server": CHANGES_DIR / "server.py",
}

# Captured before replacing flashcards_app.state.JsonStateStore.
_JSON_STATE_STORE: type | None = None


class ScratchStateStore:
    """Use the project's JSON state implementation at the constellation path."""

    def __init__(self, path: Path, *args, **kwargs) -> None:
        if _JSON_STATE_STORE is None:
            raise RuntimeError("The original JsonStateStore has not been captured")
        self.project_path = Path(path)  # retained for diagnostics; never opened
        SCRATCH_STATE.parent.mkdir(parents=True, exist_ok=True)
        self._store = _JSON_STATE_STORE(SCRATCH_STATE, *args, **kwargs)
        self.path = self._store.path

    def read(self):
        return self._store.read()

    def write(self, state) -> None:
        self._store.write(state)


def _module_origin_is(module: ModuleType, path: Path) -> bool:
    spec = getattr(module, "__spec__", None)
    origin = getattr(spec, "origin", None)
    return bool(origin and Path(origin).resolve() == path.resolve())


def _load_module(name: str, source: Path) -> ModuleType:
    if not source.is_file():
        raise FileNotFoundError(f"Required constellation module copy not found: {source}")
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create an import spec for {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def reroute_constellations_components() -> None:
    """Install tranche 1 map/server and tranche 3 overrides map, panels and callbacks before importing the root app."""
    importlib.import_module("flashcards_app")

    missing = [source for source in REROUTES.values() if not source.is_file()]
    if missing:
        paths = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(f"Required tranche 1 module source(s) not found:\n{paths}")

    for name, source in REROUTES.items():
        # Import the containing package as a normal import would, so the module
        # is registered both in sys.modules and on its actual parent package.
        parent_name, _, child_name = name.rpartition(".")
        parent = importlib.import_module(parent_name)
        loaded = sys.modules.get(name)
        if loaded is None:
            loaded = _load_module(name, source)
        elif not _module_origin_is(loaded, source):
            origin = getattr(getattr(loaded, "__spec__", None), "origin", "unknown")
            raise RuntimeError(
                f"{name} was imported from {origin} before constellation rerouting; "
                "start the app through tools/loader/const_v1_launcher.py"
            )
        setattr(parent, child_name, loaded)


def redirect_state_store() -> None:
    """Redirect the app's ordinary persisted state to the module scratch file."""
    global _JSON_STATE_STORE
    state_module = importlib.import_module("flashcards_app.state")
    current = state_module.JsonStateStore
    if current is ScratchStateStore:
        SCRATCH_STATE.parent.mkdir(parents=True, exist_ok=True)
        return

    _JSON_STATE_STORE = current
    state_module.JsonStateStore = ScratchStateStore
    SCRATCH_STATE.parent.mkdir(parents=True, exist_ok=True)


def _load_root_app() -> ModuleType:
    """Load the unchanged project-root app.py as top-level module ``app``."""
    if not APP_SOURCE.is_file():
        raise FileNotFoundError(f"Project application entry point not found: {APP_SOURCE}")

    loaded = sys.modules.get("app")
    if loaded is not None:
        if _module_origin_is(loaded, APP_SOURCE):
            return loaded
        origin = getattr(getattr(loaded, "__spec__", None), "origin", "unknown")
        raise RuntimeError(f"A different module named 'app' was imported first: {origin}")

    spec = importlib.util.spec_from_file_location("app", APP_SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create an import spec for {APP_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["app"] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop("app", None)
        raise
    return module


def load_app() -> ModuleType:
    """Reroute dependencies and state before loading the unchanged root app."""
    reroute_constellations_components()
    redirect_state_store()
    return _load_root_app()


def main() -> None:
    load_app().main()


if __name__ == "__main__":
    main()
