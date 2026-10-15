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
            + "\nCopy them unchanged from the delivered folder tranche_06a/tests/ (the stubs folder)."
        )


def make_project(base: Path, name: str, state=STATE) -> Path:
    """Copy the package and the composition root, with fixture decks and state."""
    project = base / name
    shutil.copytree(ROOT / "flashcards_app", project / "flashcards_app", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "app.py", project / "app.py")  # the composition root
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
