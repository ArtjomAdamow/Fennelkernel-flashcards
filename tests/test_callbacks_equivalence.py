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

from tests.project_fixture import CALLBACKS_TEST_FILES, check_test_files, make_project, run_script


# Steps where the original behaves differently on purpose (fix F5, one focus handling): what they return is not
# compared with the original, it is checked in test_one_focus_handling. State and saved file are still compared.
# The last two only differ because the card selected in the focus stays selected now when its group is deleted.
F5_STEPS = {"all groups", "delete the focused group", "all groups (2)", "reset dialog (2)"}


def find_by_id(node, wanted):
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
                if old["step"] not in F5_STEPS:
                    self.assertEqual(new["outputs"], old["outputs"])
                self.assertEqual(new["state"], old["state"])
                self.assertEqual(new["file"], old["file"])

    def test_one_focus_handling(self) -> None:
        # fix F5: a card is visible when neither the deck focus nor the group focus hides it, decided in one place
        def step(project, name):
            return next(r for r in self.result[project]["records"] if r["step"] == name)

        def link_targets(record):  # the cards the connection list offers
            return [option["value"] for option in find_by_id(record["outputs"][5], "link-target")["props"]["options"]]

        # clicking "All groups" ends the group focus, so the connection list offers every card but the selected one
        current = step("current", "all groups")
        selected = current["outputs"][7]
        self.assertEqual(link_targets(current), [c for c in current["state"]["cards"] if c != selected])
        self.assertLess(len(link_targets(step("legacy", "all groups"))), len(link_targets(current)))  # the original kept the old group's filter

        # deleting the focused group ends the focus: every card is on the map and no empty map is left behind
        current, legacy = step("current", "delete the focused group"), step("legacy", "delete the focused group")
        self.assertIsNone(current["outputs"][14])
        self.assertEqual(current["outputs"][9], f"{len(current['state']['cards'])} cards mapped")
        self.assertEqual((legacy["outputs"][14], legacy["outputs"][9]), ("group-2", "0 cards mapped"))  # the original: empty map

    def test_the_group_swatches_glow_for_groups_that_share_members_with_the_focused_group(self) -> None:
        # tranche 9: P (#aaaaaa) and Q (#bbbbbb) share a card; the swatch of the other group glows in its own colour
        self.assertEqual(self.result["legacy"]["swatches"], {"focus_Q": [], "focus_P": [], "no_focus": []})
        swatches = self.result["current"]["swatches"]
        self.assertEqual(swatches["focus_Q"], [["P", "#aaaaaa", "#aaaaaa"]])
        self.assertEqual(swatches["focus_P"], [["Q", "#bbbbbb", "#bbbbbb"]])
        self.assertEqual(swatches["no_focus"], [])

    def test_the_glow_always_follows_the_state_and_the_focus(self) -> None:
        # in every recorded step: exactly the groups that share a member with the focused group glow
        for record in self.result["current"]["records"]:
            with self.subTest(step=record["step"]):
                groups, focus = record["state"]["groups"], record["outputs"][14]
                focused = next((g for g in groups if g[0] == focus), None) if focus else None
                expected = sorted(g[1] for g in groups if focused is not None and g is not focused and set(g[3]) & set(focused[3]))
                self.assertEqual(sorted(name for name, _, _ in record["swatches"]), expected)
        self.assertTrue(all(r["swatches"] == [] for r in self.result["legacy"]["records"]))  # the original has none

    def test_a_reset_ends_the_group_focus(self) -> None:
        for project in ("legacy", "current"):
            with self.subTest(project=project):
                self.assertIsNone(self.result[project]["focus_after_reset"])

    def test_dialog_notes_appear_in_the_callback_output(self) -> None:
        # fix F3, end to end: the note is part of what the callback returns, next to the Confirm button
        note = {
            "new": "The selected card will be added to the new group.",
            "add": "Membership and color of the previously assigned group will remain until removed from the other group.",
            "delete": "Connections of member cards will remain.",
            "remove": "Settings of all deck member cards will be erased.",
        }
        group_buttons, deck_buttons = ["group-dialog-submit", "group-dialog-cancel"], ["deck-dialog-submit", "deck-dialog-cancel"]
        expected = {
            "new group dialog": [[note["new"], group_buttons]],
            "add to group dialog": [],  # the selected card is in no group yet
            "add to group dialog (card already grouped)": [[note["add"], group_buttons]],
            "delete dialog": [[note["delete"], group_buttons]],
            "remove deck dialog": [[note["remove"], deck_buttons]],
        }
        for record in self.result["current"]["records"]:
            with self.subTest(step=record["step"]):
                self.assertEqual(record["notes"], expected.get(record["step"], []))
        self.assertTrue(all(r["notes"] == [] for r in self.result["legacy"]["records"]))  # the original has no notes

    def test_layout_title_boot_id_route_and_index_page_match(self) -> None:
        legacy, current = self.result["legacy"]["server"], self.result["current"]["server"]
        for key in legacy:
            with self.subTest(part=key):
                self.assertEqual(without_legend_title(current[key]), without_legend_title(legacy[key]))
        self.assertIn("window.__SERVER_BOOT_ID__ = \"<BOOT>\"", current["index_string"])  # reload-guard.js reads this name
        self.assertEqual(current["routes"], ["/boot-id"])

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
