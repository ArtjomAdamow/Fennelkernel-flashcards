"""colors, map and panels must produce what they produced before (run from the project root).

    python -m unittest tests.test_visualization_equivalence -v

Builds two temporary projects from your flashcards_app package, one with the original visualization files
(tests/legacy/flashcards_app/visualization) and one as it is, runs tests/visualization_scenario.py in both
and compares everything the functions return. Dash and Plotly are replaced by small stand-ins
(tests/stubs) that record what is built, so the comparison needs neither library and cannot be disturbed
by their versions. What it does NOT show is how the real libraries render the result: that is what the
click-through in the tranche README is for. Your real data folder is not touched.
"""

import json
import tempfile
import unittest
from pathlib import Path

from tests.project_fixture import VISUALIZATION_TEST_FILES, check_test_files, make_project, run_script


def find_by_id(node, wanted):
    """First component in a recorded tree whose `id` property is `wanted`."""
    if isinstance(node, dict):
        if isinstance(node.get("props"), dict) and node["props"].get("id") == wanted:
            return node
        for value in node.values():
            found = find_by_id(value, wanted)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = find_by_id(value, wanted)
            if found:
                return found
    return None


class VisualizationEquivalenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        check_test_files(VISUALIZATION_TEST_FILES)
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.result = {}
        for name, legacy in (("legacy", True), ("current", False)):
            project = make_project(base, name, legacy)
            done = run_script(project, "visualization_scenario.py", stubs=True)
            if done.returncode != 0:
                raise AssertionError(f"{name} scenario failed:\n{done.stderr}")
            cls.result[name] = json.loads(done.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def assert_section_equal(self, section: str) -> None:
        legacy, current = self.result["legacy"][section], self.result["current"][section]
        self.assertEqual(legacy.keys(), current.keys())
        for key in legacy:
            with self.subTest(section=section, key=key):
                self.assertEqual(current[key], legacy[key])

    def test_colors_match(self) -> None:
        self.assert_section_equal("colors")

    def test_panels_match(self) -> None:
        self.assert_section_equal("panels")
        self.assertGreater(len(self.result["current"]["panels"]["connection"]), 20)

    def test_figures_and_legend_match(self) -> None:
        legacy, current = self.result["legacy"]["map"], self.result["current"]["map"]
        self.assertEqual(current["legend"], legacy["legend"])
        self.assertEqual(current["figures"].keys(), legacy["figures"].keys())
        for key in legacy["figures"]:
            with self.subTest(figure=key):
                self.assertEqual(current["figures"][key], legacy["figures"][key])

    def test_passing_the_state_explicitly_changes_nothing(self) -> None:
        explicit = self.result["current"]["explicit_state_matches_default"]
        self.assertNotIn(False, explicit.values(), [k for k, v in explicit.items() if v is False])
        self.assertEqual(self.result["legacy"]["explicit_state_matches_default"], {})  # the originals take no state

    def test_a_state_that_is_passed_in_is_the_one_that_gets_used(self) -> None:
        # A second state (cards x:1, x:2, one group "Z", one link) next to the shared one:
        # every function that takes `state` must show the second one and nothing of the shared one.
        foreign = self.result["current"]["foreign_state"]
        self.assertIsNone(self.result["legacy"]["foreign_state"])
        grey = "#7c8b99"
        if "progress_colors" in foreign:
            self.assertEqual(foreign["progress_colors"], ["#69c6a5", "#e76f51", grey])
        if "group_colors" in foreign:
            self.assertEqual(foreign["group_colors"], ["#123456", "#123456", grey])
        if "figure_trace_names" in foreign:
            self.assertEqual(foreign["figure_trace_names"],
                             ["AnchorBounds", "Connection", "Card progress", "Cards", "Selected progress", "Selected"])
            self.assertEqual(foreign["figure_selected_customdata"], ["x:1"])
            self.assertEqual(foreign["figure_cards_customdata"], ["x:2"])
            self.assertEqual(foreign["figure_cards_text"], ["Q2"])
            self.assertEqual(foreign["figure_marker_colors"], {
                "Card progress": ["#e76f51"], "Cards": ["#123456"], "Selected progress": "#69c6a5", "Selected": "#123456"})
        if "difficulty_control" in foreign:
            self.assertIn('"value": 100', foreign["difficulty_control"])
        if "position_control" in foreign:
            self.assertIn('"value": 0.1', foreign["position_control"])
        if "group_control" in foreign:
            self.assertIn('"Z"', foreign["group_control"])
            self.assertNotIn("No saved groups yet.", foreign["group_control"])
        if "group_control_with_groups" in foreign:
            self.assertFalse(find_by_id(foreign["group_control_with_groups"], "focus-group")["props"]["disabled"])
            self.assertTrue(find_by_id(foreign["group_control_no_groups"], "focus-group")["props"]["disabled"])
        if "connection_control" in foreign:
            self.assertIn("x:2", foreign["connection_control"])
            self.assertNotIn("alpha:", foreign["connection_control"])
            # focusing group-1 of the passed state keeps x:2; the shared group-1 has other members
            self.assertIn("x:2", foreign["connection_control_focused"])
        if "deck_control_add" in foreign:
            self.assertNotEqual(foreign["deck_control_add"], foreign["deck_control_add_default"])
            self.assertIn("gamma", foreign["deck_control_add"])
            self.assertNotEqual(foreign["deck_control_remove"], foreign["deck_control_remove_default"])
            self.assertIn('"options": []', foreign["deck_control_remove"])

    def test_links_are_drawn_only_when_both_ends_are_visible(self) -> None:
        # Focusing a deck or a group hides cards; a link to a hidden card must not be drawn.
        for project in ("legacy", "current"):
            links = self.result[project]["map"]["links_visible"]
            for key, entry in links.items():
                with self.subTest(project=project, focus=key):
                    self.assertEqual(entry["drawn"], entry["expected"])
            self.assertTrue(any(e["drawn"] and len(e["drawn"]) < e["total_links"] for e in links.values()),
                            "the scenario must contain a focus that hides one end of a link")
            self.assertTrue(any(not e["drawn"] for e in links.values()), "and one that shows no link at all")
            self.assertEqual(len(links["all|None"]["drawn"]), links["all|None"]["total_links"])

    def test_figure_keeps_what_the_camera_script_looks_for(self) -> None:
        # camera.js finds the trace named "Selected" and reads customdata[0]; the first trace pins the axis scale
        for project in ("legacy", "current"):
            figure = self.result[project]["map"]["figures"]["selected"]
            names = [trace.get("name") for trace in figure["data"]]
            with self.subTest(project=project):
                self.assertEqual(names[0], "AnchorBounds")
                self.assertIn("Selected", names)
                selected = figure["data"][names.index("Selected")]
                self.assertEqual(len(selected["customdata"]), 1)
                self.assertEqual(len(selected["x"]), 1)
            self.assertNotIn("Selected", [t.get("name") for t in self.result[project]["map"]["figures"]["all|None"]["data"]])


if __name__ == "__main__":
    unittest.main()
