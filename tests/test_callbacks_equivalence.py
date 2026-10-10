"""The callback and the server must do what the original ones did (run from the project root).

    python -m unittest tests.test_callbacks_equivalence -v

Builds two temporary projects from your flashcards_app package, one with the original files of the whole app
(tests/legacy/flashcards_app/*) and one as it is, and drives the one Dash callback through a scripted session
(tests/callbacks_scenario.py): every kind of click, dialog, deck and group action, reset, keyboard navigation.
After every call it compares the 18 values the callback returns (figure, panels, stores, texts), the state and the
saved file. It also compares the layout, the title, the boot-id route and the index page the server builds.
Dash, Plotly and Flask are replaced by small stand-ins (tests/stubs) that record what is built.
Your real data folder is not touched. What it cannot show is how the real libraries render the result.
"""

import json
import tempfile
import unittest
from pathlib import Path

from tests.project_fixture import CALLBACKS_TEST_FILES, ROOT, check_test_files, make_project, run_script

# Tranche 7c adds these two files; the checks that need them are skipped until then.
TRANCHE_7C_INSERTED = (ROOT / "flashcards_app" / "callbacks_impl.py").exists() and (ROOT / "flashcards_app" / "server_impl.py").exists()


class CallbacksEquivalenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        check_test_files(CALLBACKS_TEST_FILES)
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.result = {}
        for name, legacy in (("legacy", True), ("current", False)):
            project = make_project(base, name, legacy)
            done = run_script(project, "callbacks_scenario.py", stubs=True)
            if done.returncode != 0:
                raise AssertionError(f"{name} scenario failed:\n{done.stderr}")
            cls.result[name] = json.loads(done.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_callback_is_registered_with_the_same_outputs_inputs_and_states(self) -> None:
        self.assertEqual(self.result["current"]["registration"], self.result["legacy"]["registration"])
        kinds = [entry[0] for entry in self.result["current"]["registration"]]
        self.assertEqual((kinds.count("Output"), kinds.count("Input"), kinds.count("State")), (18, 29, 13))

    def test_every_step_matches(self) -> None:
        legacy, current = self.result["legacy"]["records"], self.result["current"]["records"]
        self.assertGreaterEqual(len(legacy), 45)
        self.assertEqual([r["step"] for r in current], [r["step"] for r in legacy])
        for old, new in zip(legacy, current):
            with self.subTest(step=old["step"]):
                self.assertEqual(new["outputs"], old["outputs"])
                self.assertEqual(new["state"], old["state"])
                self.assertEqual(new["file"], old["file"])

    def test_layout_title_boot_id_route_and_index_page_match(self) -> None:
        legacy, current = self.result["legacy"]["server"], self.result["current"]["server"]
        for key in legacy:
            with self.subTest(part=key):
                self.assertEqual(current[key], legacy[key])
        self.assertIn("window.__SERVER_BOOT_ID__ = \"<BOOT>\"", current["index_string"])  # reload-guard.js reads this name
        self.assertEqual(current["routes"], ["/boot-id"])

    @unittest.skipUnless(TRANCHE_7C_INSERTED, "needs tranche 7c (callbacks_impl.py, server_impl.py)")
    def test_group_colour_follows_the_focused_group(self) -> None:
        # fix F2: card 0 is in the older group P (#aaaaaa) and the younger group Q (#bbbbbb)
        for project, expected_when_focused in (("legacy", "#aaaaaa"), ("current", "#bbbbbb")):
            f2 = self.result[project]["f2"]
            first, second = f2["ids"]
            with self.subTest(project=project):
                self.assertEqual(f2["focused_on_younger_group"][first], expected_when_focused)
                self.assertEqual(f2["focused_on_younger_group"][second], "#bbbbbb")
                self.assertEqual(f2["nothing_focused"][first], "#aaaaaa")  # without focus the oldest group still wins
                self.assertEqual(f2["nothing_focused"][second], "#bbbbbb")

    @unittest.skipUnless(TRANCHE_7C_INSERTED, "needs tranche 7c (callbacks_impl.py, server_impl.py)")
    def test_the_callback_uses_only_the_state_it_was_given(self) -> None:
        self.assertIsNone(self.result["legacy"]["foreign"])
        foreign = self.result["current"]["foreign"]
        self.assertEqual(foreign["count_text"], "2 cards mapped")
        self.assertEqual(foreign["map_card_ids"], ["x:1", "x:2"])
        self.assertEqual(foreign["selected"], "x:1")
        # every panel the callback returns was built from the given state, not from the shared one
        self.assertIn('"value": 1', foreign["difficulty"])
        self.assertIn('"value": 0.1', foreign["position"])
        self.assertIn("No saved groups yet.", foreign["groups"])
        self.assertIn("x:2", foreign["connections"])
        self.assertNotIn("alpha:", foreign["connections"])
        self.assertIn('"value": "x"', foreign["deck_control"])
        self.assertEqual(foreign["filter_option_values"], ["None", "all", "x"])
        self.assertTrue(foreign["shared_cards_unchanged"])
        self.assertTrue(foreign["shared_file_unchanged"])

    @unittest.skipUnless(TRANCHE_7C_INSERTED, "needs tranche 7c (callbacks_impl.py, server_impl.py)")
    def test_the_server_builds_its_first_page_from_the_state_and_boot_id_it_is_given(self) -> None:
        server = self.result["current"]["foreign"]["server"]
        self.assertTrue(server["layout_has_foreign_cards"])
        self.assertFalse(server["layout_has_shared_cards"])
        self.assertTrue(server["layout_deck_options_are_the_foreign_ones"])
        self.assertTrue(server["layout_group_list_is_the_foreign_one"])
        self.assertTrue(server["boot_id_in_index_page"])
        self.assertEqual(server["boot_id_route"], {"bootId": "BOOT-X"})


if __name__ == "__main__":
    unittest.main()
