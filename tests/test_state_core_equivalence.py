"""StateCore must behave like the old runtime/services (run from the project root).

    python -m unittest tests.test_state_core_equivalence -v

Copies your flashcards_app package into a temporary project with small fixture decks and a
fixture state file, runs the same action sequence through the old code and through StateCore
(tests/equivalence_scenario.py) and compares every step. Your real data folder is not touched.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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


class StateCoreEquivalenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        project = Path(cls._tmp.name) / "project"
        shutil.copytree(ROOT / "flashcards_app", project / "flashcards_app",
                        ignore=shutil.ignore_patterns("__pycache__"))
        cards = project / "data" / "cards"
        cards.mkdir(parents=True)
        for deck, count in (("alpha", 3), ("beta", 2), ("gamma", 2)):
            (cards / f"{deck}.md").write_text(
                "".join(DETAILS.format(q=f"Q {deck} {i}", a=f"A {deck} {i}") for i in range(1, count + 1)),
                encoding="utf-8",
            )
        (cards / "README.md").write_text("readme", encoding="utf-8")
        (cards / "None.md").write_text("dummy", encoding="utf-8")
        (project / "data" / "positions.json").write_text(json.dumps(STATE, indent=2), encoding="utf-8")

        env = dict(os.environ, PYTHONPATH=str(project))
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("equivalence_scenario.py"))],
            cwd=project, env=env, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise AssertionError(f"scenario failed:\n{result.stderr}")
        cls.output = json.loads(result.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_every_step_matches(self) -> None:
        self.assertGreaterEqual(len(self.output["records"]), 9)
        for record in self.output["records"]:
            with self.subTest(step=record["step"]):
                self.assertEqual(record["new"], record["old"])

    def test_saved_files_are_identical(self) -> None:
        self.assertEqual(self.output["files"]["new"], self.output["files"]["old"])

    def test_new_group_ids_follow_the_old_numbering_when_nothing_was_deleted(self) -> None:
        self.assertEqual(self.output["group_ids_from_core"], ["group-2", "group-3"])


if __name__ == "__main__":
    unittest.main()
