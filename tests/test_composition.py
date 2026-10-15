"""The composition root (app.py) and the hub (runtime.py) (run from the project root).

    python -m unittest tests.test_composition -v

Imports app.py in a temporary project (fixture decks and state, stand-ins for dash/plotly/flask) and checks what it
builds, that the startup save keeps the enabled decks (fix F4), and, by reading the source files, that nothing in the
package still uses what tranche 8 removed. Your real data folder is not touched.
"""

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.project_fixture import ROOT, STATE, check_test_files, make_project, run_script

PACKAGE = ROOT / "flashcards_app"

REMOVED_FILES = [
    "callbacks_impl.py", "server_impl.py",
    "services/positions.py", "services/progress.py", "services/groups.py", "services/connections.py", "services/decks.py",
]
REMOVED_RUNTIME_NAMES = [
    "CARDS", "POSITIONS", "PROGRESS", "GROUPS", "LINKS", "ENABLED_DECKS", "CARD_BY_ID", "POSITION_BY_ID", "USER_STATE", "CORE",
    "CATALOG", "STATE_PATH", "CARDS_DIR", "BASE_DIR", "SERVER_BOOT_ID", "AVAILABLE_DECKS",
    "available_decks", "visible_cards", "refresh_deck_state", "reset_all_state",
]
ALLOWED_RUNTIME_NAMES = {"NONE_DECK", "Runtime"}


def package_sources():
    return {path: path.read_text(encoding="utf-8") for path in PACKAGE.rglob("*.py")}


class CompositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        check_test_files({"stubs/dash/__init__.py": "def Input", "stubs/flask/__init__.py": "def jsonify",
                          "stubs/dash_daq/__init__.py": "def ColorPicker", "stubs/plotly/graph_objects.py": "class Figure"})
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        done = run_script(make_project(base, "full"), "composition_scenario.py", stubs=True)
        if done.returncode != 0:
            raise AssertionError(f"scenario failed:\n{done.stderr}")
        cls.result = json.loads(done.stdout)
        no_data = run_script(make_project(base, "no_data"), "composition_scenario.py", "no_data", stubs=True)
        if no_data.returncode != 0:
            raise AssertionError(f"importing the hub without a data folder failed:\n{no_data.stderr}")
        cls.no_data = json.loads(no_data.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    # --- what app.py builds ----------------------------------------------------------------------

    def test_startup_builds_one_connected_set_of_objects(self) -> None:
        startup = self.result["startup"]
        self.assertEqual(startup["enabled"], ["alpha", "beta"])  # from the fixture state file
        self.assertEqual(len(startup["cards"]), 5)
        self.assertTrue(all(value is True for key, value in startup.items() if key not in ("enabled", "cards")), startup)

    def test_configuration_lives_in_app_py(self) -> None:
        constants = self.result["constants"]
        self.assertTrue(constants["base_dir_holds_app_py"])
        # phase 2: the course file instead of the cards folder, no positions.json fallback
        self.assertEqual((constants["state_path"], constants["cards_file"]), ("data/user_state.json", "data/cards.json"))
        self.assertFalse(constants["has_legacy_state_path"])
        self.assertEqual(constants["none_deck"], "None")

    # --- the hub -----------------------------------------------------------------------------------

    def test_the_hub_keeps_no_state_and_none_of_the_old_names(self) -> None:
        names = set(self.result["runtime_names"])
        self.assertEqual(names & set(REMOVED_RUNTIME_NAMES), set())
        self.assertTrue(ALLOWED_RUNTIME_NAMES <= names)

    def test_importing_the_hub_needs_no_data_and_composes_nothing(self) -> None:
        self.assertTrue(self.no_data["imported"])
        self.assertFalse(self.no_data["app_imported"])

    # --- F4 ------------------------------------------------------------------------------------------

    def test_the_startup_save_keeps_the_enabled_decks(self) -> None:
        f4 = self.result["f4"]
        self.assertEqual(f4["decks_in_file"], ["alpha"])  # beta was disabled before main() saved
        self.assertEqual(f4["app_run_called"], {"debug": True})
        self.assertEqual(f4["after_restart_enabled"], ["alpha"])  # before the fix every available deck came back
        self.assertTrue(all(card_id.startswith("101") for card_id in f4["after_restart_cards"]))  # phase 2: alpha's comb_ids
        self.assertEqual(f4["after_restart_difficulty"], 33)
        self.assertTrue(f4["two_compositions_are_independent"])

    # --- user_state.json keyed by comb_id (phase 2: the O5 fallback to positions.json is gone) --------------------

    def test_the_restart_reads_the_new_file(self) -> None:
        # the F4 scenario restarts after main() saved: the state came back from user_state.json (decks, progress)
        self.assertEqual(self.result["f4"]["after_restart_enabled"], ["alpha"])
        self.assertEqual(self.result["f4"]["after_restart_difficulty"], 33)

    def test_the_saved_file_is_keyed_by_comb_id(self) -> None:
        self.assertEqual(self.result["f4"]["state_keys"], ["comb_id"])

    def test_positions_json_is_not_read_any_more(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = make_project(Path(tmp), "legacy", state=dict(STATE, decks=["alpha"]), state_file="positions.json")
            done = run_script(project, "composition_scenario.py", "enabled", stubs=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotEqual(json.loads(done.stdout)["enabled"], ["alpha"])  # positions.json is ignored, the start is fresh

    # --- the cut-over, checked in the source files ---------------------------------------------------

    def test_removed_files_are_gone(self) -> None:
        still_there = [name for name in REMOVED_FILES if (PACKAGE / name).exists()]
        self.assertEqual(still_there, [], "delete these files (tranche 8a): " + ", ".join(still_there))

    def test_nothing_imports_what_was_removed(self) -> None:
        pattern = re.compile(r"callbacks_impl|server_impl|services(?:\.|\s+import\s+)(?:positions|progress|groups|connections|decks)\b")
        offenders = [str(path.relative_to(ROOT)) for path, text in package_sources().items() if pattern.search(text)]
        offenders += [str(path.relative_to(ROOT)) for path in [ROOT / "app.py"] if pattern.search(path.read_text(encoding="utf-8"))]
        self.assertEqual(offenders, [])

    def test_the_package_only_takes_the_hub_constants_from_runtime(self) -> None:
        used = {}
        for path, text in package_sources().items():
            if path.name == "runtime.py":
                continue
            for name in re.findall(r"\bruntime\.([A-Za-z_]\w*)", text):
                used.setdefault(name, []).append(path.name)
            for block in re.findall(r"from flashcards_app\.runtime import \(([^)]*)\)|from flashcards_app\.runtime import ([^\n(]+)", text):
                for name in re.split(r"[,\s]+", "".join(block).replace("\r", "")):
                    if name and not name.startswith("#"):
                        used.setdefault(name, []).append(path.name)
        self.assertEqual({k: v for k, v in used.items() if k not in ALLOWED_RUNTIME_NAMES}, {})

    def test_the_old_loaders_are_not_in_state_py_any_more(self) -> None:
        text = (PACKAGE / "state.py").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"def (load_\w+)\(", text), [])

    def test_the_services_folder_only_has_the_pure_card_helpers(self) -> None:
        text = (PACKAGE / "services" / "cards.py").read_text(encoding="utf-8")
        self.assertNotIn("runtime", text)
        for name in ("choose_random_card", "adjacent_card", "select_from_click"):
            self.assertIn(f"def {name}(", text)


if __name__ == "__main__":
    unittest.main()
