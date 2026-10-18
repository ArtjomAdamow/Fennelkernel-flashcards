"""Start the flashcards app with its state kept out of data/. Run from anywhere:

    .venv/Scripts/python.exe tools/loader/deck_v2_launcher.py

    This launcher redirects the state file (it emulates a multi-user setup):
  * state.JsonStateStore is replaced by ScratchStateStore before app is imported. The state is read from
    and saved to SCRATCH_STATE in this folder, never to data/user_state.json.
  * On startup, if user_state.json exists, the user is asked whether to back it up. If confirmed, the
    existing file is renamed to user_state.json_01.bak (or the next available number if that already
    exists) and a fresh state is used.
  * Everything else is the project's own code: app.py, data/cards.json (read only; read again when the
    deck "Add" button is clicked) and the assets.

app.run(debug=True) runs the app in a reloader child process, which reads cards.json once more.
"""

import os
import sys
from pathlib import Path
from types import ModuleType

LAUNCHER_DIR = Path(__file__).resolve().parent
ROOT = LAUNCHER_DIR.parents[1]

# The launcher's own state file. Read when the store is built, so it can be changed before load_app().
SCRATCH_STATE = LAUNCHER_DIR / "scratch" / "user_state.json"

# Run as a script, sys.path[0] is this folder; only the project root is needed
if sys.path and Path(sys.path[0] or ".").resolve() == LAUNCHER_DIR:
    sys.path[0] = str(ROOT)
elif str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The project's state.JsonStateStore, set by redirect_state_store()
_JSON_STATE_STORE = None


class ScratchStateStore:
    """Stands in for state.JsonStateStore (same constructor, StatePersistence protocol): the path the app
    passes (data/user_state.json) is replaced by SCRATCH_STATE. Reading and writing are the real store's."""

    def __init__(self, path: Path, *args, **kwargs) -> None:
        self.project_path = Path(path)  # never opened
        self._store = _JSON_STATE_STORE(SCRATCH_STATE, *args, **kwargs)
        self.path = self._store.path

    def read(self):
        return self._store.read()

    def write(self, state) -> None:
        self._store.write(state)


def redirect_state_store() -> None:
    """Keep data/ out of the state handling: the app's store reads and writes SCRATCH_STATE."""
    global _JSON_STATE_STORE
    import flashcards_app.state

    if flashcards_app.state.JsonStateStore is not ScratchStateStore:
        _JSON_STATE_STORE = flashcards_app.state.JsonStateStore
        flashcards_app.state.JsonStateStore = ScratchStateStore


def load_app() -> ModuleType:
    """Redirect the state file, then import the project's app.py (this builds the composition)."""
    if "app" in sys.modules:
        # app.py binds JsonStateStore on import; imported before the redirect, it would save to data/
        raise RuntimeError("app was imported before the state file was redirected")
    redirect_state_store()
    import app

    return app


def _find_unique_backup_path() -> Path:
    """Return the next available backup path: user_state.json_01.bak, _02.bak, ..."""
    scratch_dir = SCRATCH_STATE.parent
    for i in range(1, 100):
        candidate = scratch_dir / f"user_state.json_{i:02d}.bak"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not find a free backup name (100 existing backups)")


def prepare_scratch_state() -> None:
    """Check if user_state.json exists and ask for backup before starting fresh."""
    if not SCRATCH_STATE.exists():
        print("No existing state file found.")
        return

    print(f"Found existing state file: {SCRATCH_STATE}")
    try:
        response = input("Backup existing user_state.json? (y/n): ").strip().lower()
    except EOFError:
        # Non-interactive environment (e.g. piped input): keep the existing file.
        print("No input available; keeping existing state file.")
        return

    if response in ('y', 'yes'):
        backup_path = _find_unique_backup_path()
        SCRATCH_STATE.rename(backup_path)
        print(f"Backed up existing state to: {backup_path}")
    else:
        print("Keeping existing state file.")
        return
    print("Starting with a fresh user_state.json.")


#def main() -> None:
#    prepare_scratch_state()
#    load_app().main()

def main() -> None:
    # app.run(debug=True) runs this script again in a reloader child (WERKZEUG_RUN_MAIN=true): ask only once
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        prepare_scratch_state()
    load_app().main()



if __name__ == "__main__":
    main()
