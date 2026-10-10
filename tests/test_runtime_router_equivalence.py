"""The router runtime must behave like the legacy runtime (run from the project root).

    python -m unittest tests.test_runtime_router_equivalence -v

Builds two temporary projects from your flashcards_app package: one with tests/legacy/flashcards_app/*
laid over it (the runtime as it was before tranche 4) and one as it is. Both get the same fixture decks
and state file and run tests/runtime_scenario.py: a sequence through the old services, a save like the
callbacks do, and a fresh start that reads the saved file. Your real data folder is not touched.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
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


def make_project(base: Path, name: str, legacy: bool, state=STATE) -> Path:
    project = base / name
    shutil.copytree(ROOT / "flashcards_app", project / "flashcards_app", ignore=shutil.ignore_patterns("__pycache__"))
    if legacy:
        shutil.copytree(HERE / "legacy" / "flashcards_app", project / "flashcards_app", dirs_exist_ok=True)
    cards = project / "data" / "cards"
    cards.mkdir(parents=True)
    for deck, count in (("alpha", 3), ("beta", 2), ("gamma", 2)):
        (cards / f"{deck}.md").write_text(
            "".join(DETAILS.format(q=f"Q {deck} {i}", a=f"A {deck} {i}") for i in range(1, count + 1)), encoding="utf-8")
    (cards / "README.md").write_text("readme", encoding="utf-8")
    (cards / "None.md").write_text("dummy", encoding="utf-8")
    (project / "data" / "positions.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return project


def run(project: Path, mode: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HERE / "runtime_scenario.py"), mode],
        cwd=project, env=dict(os.environ, PYTHONPATH=str(project)), capture_output=True, text=True,
    )


def normalized(saved_file: str) -> dict:
    """The saved file without what tranche 7 changed on purpose: no link group_id any more, a rank for every group."""
    data = json.loads(saved_file)
    for group in data["groups"]:
        group.pop("rank", None)
    for link in data["links"]:
        link.pop("group_id", None)
    return data


class RuntimeRouterEquivalenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.result = {}
        for name, legacy in (("legacy", True), ("router", False)):
            project = make_project(base, name, legacy)
            first = run(project, "run")
            if first.returncode != 0:
                raise AssertionError(f"{name} run failed:\n{first.stderr}")
            second = run(project, "startup")  # fresh interpreter reading the file saved by the first run
            if second.returncode != 0:
                raise AssertionError(f"{name} restart failed:\n{second.stderr}")
            cls.result[name] = {"run": json.loads(first.stdout), "restart": json.loads(second.stdout)}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_every_step_matches(self) -> None:
        legacy, router = self.result["legacy"]["run"]["records"], self.result["router"]["run"]["records"]
        self.assertGreaterEqual(len(legacy), 11)
        self.assertEqual([r["step"] for r in router], [r["step"] for r in legacy])
        for old, new in zip(legacy, router):
            with self.subTest(step=old["step"]):
                self.assertEqual(new["state"], old["state"])

    def test_saved_file_is_identical(self) -> None:
        router, legacy = self.result["router"]["run"]["saved_file"], self.result["legacy"]["run"]["saved_file"]
        self.assertEqual(normalized(router), normalized(legacy))

    def test_saved_file_has_the_new_layout(self) -> None:
        router = json.loads(self.result["router"]["run"]["saved_file"])
        self.assertTrue(all("group_id" not in link for link in router["links"]))
        self.assertEqual([group["rank"] for group in router["groups"]], list(range(1, len(router["groups"]) + 1)))
        self.assertEqual(router["version"], 2)

    def test_state_after_a_restart_is_identical(self) -> None:
        self.assertEqual(self.result["router"]["restart"], self.result["legacy"]["restart"])

    def test_old_names_stay_the_cores_objects_and_are_never_rebound(self) -> None:
        run_result = self.result["router"]["run"]
        self.assertTrue(run_result["names_are_the_cores_objects"])
        self.assertTrue(run_result["containers_unchanged"])
        self.assertTrue(self.result["legacy"]["run"]["containers_unchanged"])
        self.assertIsNone(self.result["legacy"]["run"]["names_are_the_cores_objects"])

    def test_unsupported_state_version_stops_the_start_with_a_clear_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp), "router", legacy=False, state={"version": 1, "positions": []})
            result = run(project, "startup")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("StateFileError", result.stderr)
        self.assertIn("supported versions: [2]", result.stderr)


if __name__ == "__main__":
    unittest.main()
