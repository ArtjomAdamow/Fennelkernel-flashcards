"""Shared helper for tests that need a temporary copy of the project with fixture decks and state."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

DETAILS = "<details><summary>{q}</summary>{a}</details>\n"

STATE = {
    "version": 2,
    "positions": [
        {"card_id": "alpha:1", "x": 0.5, "y": 0.4, "z": 0.3, "status": "new", "related_ids": []},
        {"card_id": "beta:1", "x": -0.5, "y": 0.2, "z": 0.1, "status": "new", "related_ids": []},
        {"card_id": "gamma:1", "x": 0.9, "y": 0.9, "z": 0.1, "status": "new", "related_ids": []},
    ],
    "progress": [
        {"card_id": "alpha:1", "read": True, "difficulty": 55},
        {"card_id": "gamma:1", "read": True, "difficulty": 80},
    ],
    "groups": [{"id": "group-1", "name": "X", "color": "#ffffff", "card_ids": ["alpha:1", "gamma:1"]}],
    "links": [
        {"source_id": "alpha:1", "target_id": "beta:1", "group_id": None},
        {"source_id": "alpha:1", "target_id": "gamma:1", "group_id": None},
    ],
    "decks": ["alpha", "beta"],
}


# Files the visualization test needs besides the code under test: relative to tests/, and a piece of text each
# must contain (None = may be empty). The legacy files must be your ORIGINAL colors/map/panels.
VISUALIZATION_TEST_FILES = {
    "stubs/dash/__init__.py": "def to_json",
    "stubs/dash_daq/__init__.py": "def ColorPicker",
    "stubs/plotly/__init__.py": None,
    "stubs/plotly/graph_objects.py": "class Figure",
    "legacy/flashcards_app/visualization/colors.py": "runtime.PROGRESS",
    "legacy/flashcards_app/visualization/map.py": "runtime.POSITIONS",
    "legacy/flashcards_app/visualization/panels.py": "runtime.PROGRESS",
}


# Same idea for the callbacks/server test. A tuple is (must contain, must NOT contain): the legacy files have to be
# the ORIGINAL ones, not the versions from tranche 7.
CALLBACKS_TEST_FILES = {
    "stubs/dash/__init__.py": "def Input",
    "stubs/dash_daq/__init__.py": "def ColorPicker",
    "stubs/plotly/__init__.py": None,
    "stubs/plotly/graph_objects.py": "class Figure",
    "stubs/flask/__init__.py": "def jsonify",
    "legacy/flashcards_app/models.py": ("group_id", "rank"),
    "legacy/flashcards_app/state.py": ("def load_positions", "RawState"),
    "legacy/flashcards_app/callbacks.py": ("@app.callback(", "register_callbacks"),
    "legacy/flashcards_app/server.py": ("app = Dash(", "create_app"),
    "legacy/flashcards_app/runtime.py": ("def available_decks", "USER_STATE"),
    "legacy/flashcards_app/visualization/colors.py": ("runtime.PROGRESS", "_state"),
    "legacy/flashcards_app/visualization/map.py": ("runtime.POSITIONS", "_state"),
    "legacy/flashcards_app/visualization/panels.py": ("runtime.PROGRESS", "_state"),
    "legacy/flashcards_app/services/cards.py": ("runtime.PROGRESS", "USER_STATE"),
    "legacy/flashcards_app/services/decks.py": ("load_decks", "USER_STATE"),
    "legacy/flashcards_app/services/groups.py": ("runtime.GROUPS", "USER_STATE"),
    "legacy/flashcards_app/services/connections.py": ("runtime.LINKS", "USER_STATE"),
    "legacy/flashcards_app/services/positions.py": ("POSITION_BY_ID", "USER_STATE"),
    "legacy/flashcards_app/services/progress.py": ("runtime.PROGRESS", "USER_STATE"),
}


def check_test_files(required: dict) -> None:
    """Fail with a readable message if a support file is missing, empty or not the expected one."""
    problems = []
    for relative, marker in required.items():
        path = HERE / relative
        if not path.exists():
            problems.append(f"missing:    tests/{relative}")
            continue
        text = path.read_text(encoding="utf-8")
        must_contain, must_lack = marker if isinstance(marker, tuple) else (marker, None)
        if must_contain and must_contain not in text:
            problems.append(f"wrong or empty (does not contain {must_contain!r}): tests/{relative}")
        elif must_lack and must_lack in text:
            problems.append(f"wrong version (contains {must_lack!r}, so it is not your original file): tests/{relative}")
    if problems:
        raise AssertionError(
            "This test needs support files that are not in your tests folder (or are not the right ones):\n  "
            + "\n  ".join(problems)
            + "\nCopy them unchanged from the delivered folder tranche_06a/tests/ (the stubs folder with its 4 files, "
            "and legacy/flashcards_app/visualization/ with your three ORIGINAL files from before tranche 6)."
        )


def make_project(base: Path, name: str, legacy: bool, state=STATE) -> Path:
    """Copy the package; with legacy=True lay tests/legacy/flashcards_app/* over it (the code before the tranches)."""
    project = base / name
    shutil.copytree(ROOT / "flashcards_app", project / "flashcards_app", ignore=shutil.ignore_patterns("__pycache__"))
    if legacy:
        shutil.copytree(HERE / "legacy" / "flashcards_app", project / "flashcards_app", dirs_exist_ok=True)
    if not legacy:
        shutil.copy(ROOT / "app.py", project / "app.py")  # the composition root (the original code has none that composes)
    cards = project / "data" / "cards"
    cards.mkdir(parents=True)
    for deck, count in (("alpha", 3), ("beta", 2), ("gamma", 2)):
        (cards / f"{deck}.md").write_text(
            "".join(DETAILS.format(q=f"Q {deck} {i}", a=f"A {deck} {i}") for i in range(1, count + 1)), encoding="utf-8")
    (cards / "README.md").write_text("readme", encoding="utf-8")
    (cards / "None.md").write_text("dummy", encoding="utf-8")
    (project / "data" / "positions.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return project


def run_script(project: Path, script: str, *args: str, stubs: bool = False) -> subprocess.CompletedProcess:
    paths = [str(project)]
    if stubs:
        paths.insert(0, str(HERE / "stubs"))  # first, so the stand-ins shadow any real dash/plotly
    return subprocess.run(
        [sys.executable, str(HERE / script), *args],
        cwd=project, env=dict(os.environ, PYTHONPATH=os.pathsep.join(paths)), capture_output=True, text=True,
    )
