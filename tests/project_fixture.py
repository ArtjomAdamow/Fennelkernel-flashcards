"""Shared helper for tests that need a temporary copy of the project with fixture decks and state."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# phase 2: the fixture course is a cards.json; deck ids 01..05, all cards stack 1 (no "quiz"), so the comb_ids are
# "1" + deck id + card_id: alpha 101001..101003, beta 102001..102002, gamma 103001..103002
DECKS = (("01", "alpha", 3), ("02", "beta", 2), ("03", "gamma", 2), ("04", "README", 0), ("05", "None", 0))
ALPHA_1, BETA_1, GAMMA_1 = "101001", "102001", "103001"

STATE = {
    "version": 2,
    "positions": [
        {"comb_id": ALPHA_1, "x": 0.5, "y": 0.4, "z": 0.3, "status": "new", "related_ids": []},
        {"comb_id": BETA_1, "x": -0.5, "y": 0.2, "z": 0.1, "status": "new", "related_ids": []},
        {"comb_id": GAMMA_1, "x": 0.9, "y": 0.9, "z": 0.1, "status": "new", "related_ids": []},
    ],
    "progress": [
        {"comb_id": ALPHA_1, "read": True, "difficulty": 55},
        {"comb_id": GAMMA_1, "read": True, "difficulty": 80},
    ],
    "groups": [{"id": "group-1", "name": "X", "color": "#ffffff", "card_ids": [ALPHA_1, GAMMA_1]}],
    "links": [
        {"source_id": ALPHA_1, "target_id": BETA_1, "group_id": None},
        {"source_id": ALPHA_1, "target_id": GAMMA_1, "group_id": None},
    ],
    "decks": ["alpha", "beta"],
}


def course() -> dict:
    return {"courseName": "fixture", "version": 2, "decks": [
        {"id": deck_id, "name": name, "cards": [
            {"card_id": f"{i:03d}", "question": f"Q {name} {i}", "feedback": f"A {name} {i}"} for i in range(1, count + 1)]}
        for deck_id, name, count in DECKS]}


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


def make_project(base: Path, name: str, state=STATE, state_file: str = "user_state.json") -> Path:
    """Copy the package and the composition root, with the fixture course and state (phase 2: cards.json, user_state.json)."""
    project = base / name
    shutil.copytree(ROOT / "project", project / "project", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "cards.py", project / "cards.py")  # the composition root
    (project / "data").mkdir()
    (project / "data" / "cards.json").write_text(json.dumps(course(), indent=2), encoding="utf-8")
    (project / "data" / state_file).write_text(json.dumps(state, indent=2), encoding="utf-8")
    return project


def run_script(project: Path, script: str, *args: str, stubs: bool = False) -> subprocess.CompletedProcess:
    paths = [str(project)]
    if stubs:
        paths.insert(0, str(HERE / "stubs"))  # first, so the stand-ins shadow any real dash/plotly
    return subprocess.run(
        [sys.executable, str(HERE / script), *args],
        cwd=project, env=dict(os.environ, PYTHONPATH=os.pathsep.join(paths)), capture_output=True, text=True,
    )
