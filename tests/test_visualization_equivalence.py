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


def without_legend_title(node):
    """The recorded tree with the title of the colour legend blanked: it is a matter of taste, not of behavior."""
    if isinstance(node, list):
        return [without_legend_title(item) for item in node]
    if isinstance(node, dict):
        if isinstance(node.get("props"), dict) and node["props"].get("className") == "color-legend":
            args = [without_legend_title(a) for a in node["args"]]
            args[0] = [dict(args[0][0], args=["<legend title>"])] + args[0][1:]
            return dict(node, args=args)
        return {key: without_legend_title(value) for key, value in node.items()}
    return node


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
        self.assertGreater(len(self.result["current"]["panels"]["connection"]), 15)

    def test_figures_and_legend_match(self) -> None:
        legacy, current = self.result["legacy"]["map"], self.result["current"]["map"]
        self.assertEqual(without_legend_title(current["legend"]), without_legend_title(legacy["legend"]))
        self.assertEqual(current["figures"].keys(), legacy["figures"].keys())
        for key in legacy["figures"]:
            with self.subTest(figure=key):
                self.assertEqual(current["figures"][key], legacy["figures"][key])

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

    def test_without_a_state_the_functions_refuse_to_run_with_a_clear_message(self) -> None:
        self.assertIsNone(self.result["legacy"]["missing_state"])  # the originals take no state
        missing = self.result["current"]["missing_state"]
        self.assertEqual(len(missing), 7)
        self.assertEqual([name for name, value in missing.items() if value is not True], [])

    def test_a_group_focus_that_does_not_exist_leaves_the_connection_list_empty(self) -> None:
        self.assertIsNone(self.result["legacy"]["connection_unknown_group"])
        tree = json.dumps(self.result["current"]["connection_unknown_group"])
        self.assertIn('"options": []', tree)

    def test_swatches_of_groups_that_share_members_with_the_focused_group_glow(self) -> None:
        self.assertIsNone(self.result["legacy"]["swatches"])  # the original knows no highlight
        swatches = self.result["current"]["swatches"]
        for focus, entry in swatches.items():
            with self.subTest(focus=focus):
                self.assertEqual(entry["highlighted"], entry["expected"])
                self.assertTrue(entry["glow_is_the_group_colour"])  # box-shadow: currentColor needs the group colour as text colour
        self.assertEqual((swatches["None"]["highlighted"], swatches["nope"]["highlighted"]), ([], []))  # no focus, no glow
        self.assertTrue(any(entry["expected"] for entry in swatches.values()), "the scenario needs a group that shares a card")
        self.assertTrue(any(not entry["expected"] for key, entry in swatches.items() if key not in ("None", "nope")),
                        "and a focused group that shares none")

    def test_dialog_notes_sit_next_to_the_confirm_button(self) -> None:
        # fix F3: the right note for the right dialog, in the row of the Confirm button
        new, add, delete = "The selected card will be added to the new group.", None, "Connections of member cards will remain."
        add = "Membership and color of the previously assigned group will remain until removed from the other group."
        remove = "Settings of all deck member cards will be erased."
        legacy, current = self.result["legacy"]["notes"], self.result["current"]["notes"]
        self.assertEqual({k: v for k, v in legacy["group"].items() if v}, {})  # the original has no notes
        self.assertEqual({k: v for k, v in legacy["deck"].items() if v}, {})
        group_buttons = ["group-dialog-submit", "group-dialog-cancel"]
        # cards: 0 none, 1 in no group, 2 in two groups, 3 in one group
        expected = {}
        for card in range(4):
            expected[f"{card}:new"] = [[new, group_buttons]]
            expected[f"{card}:delete"] = [[delete, group_buttons]]
            expected[f"{card}:add"] = [[add, group_buttons]] if card in (2, 3) else []
            for dialog in (None, "remove", "focus"):
                expected[f"{card}:{dialog}"] = []
        self.assertEqual(current["group"], expected)
        deck_buttons = ["deck-dialog-submit", "deck-dialog-cancel"]
        for key, notes in current["deck"].items():
            with self.subTest(deck_dialog=key):
                self.assertEqual(notes, [[remove, deck_buttons]] if key.startswith("remove:") else [])

    def test_group_colour_rule(self) -> None:
        # fix F2: a focused group decides; otherwise the oldest existing group; deleting it passes the colour on
        self.assertIsNone(self.result["legacy"]["rank_rule"])  # the original knows no focus and no rank
        if self.result["current"]["rank_rule"] is None:
            self.skipTest("needs tranche 7b (colors.py with the focused_group parameter)")
        rule = self.result["current"]["rank_rule"]
        grey = "#7c8b99"
        self.assertEqual(rule["no_focus"], "#a00001")
        self.assertEqual((rule["focus_a"], rule["focus_b"], rule["focus_c"]), ("#a00001", "#b00002", "#c00003"))
        self.assertEqual(rule["focus_unknown"], "#a00001")
        self.assertEqual((rule["x2"], rule["x3"], rule["x3_focus_a_not_member"], rule["not_in_any_group"]), ("#a00001", "#c00003", "#c00003", grey))
        self.assertEqual(rule["after_delete_a"], {"x1": "#b00002", "x2": grey})
        self.assertEqual(rule["after_delete_b"], "#c00003")
        self.assertEqual(rule["after_new_d"], "#c00003")  # a younger group never beats an older one
        self.assertEqual(rule["ranks"], [3, 4])
        if "figure_colors_when_c_is_focused" in rule:
            self.assertEqual(rule["figure_colors_when_c_is_focused"]["x:1"], "#c00003")

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
