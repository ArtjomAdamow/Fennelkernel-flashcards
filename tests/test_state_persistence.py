"""Tests for the file-level persistence in project.store.state (run from the project root).

    python -m unittest tests.test_state_persistence -v
"""

import json
import tempfile
import threading
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest import mock

from project.models import CardGroup, CardLink, CardPosition, CardProgress
from project.store import state as state_module
from project.store.state import (
    JsonStateStore,
    RawState,
    StateFileError,
    read_state_file,
    save_state,
    write_state_file,
)


def legacy_save_state(path, positions, progress, groups=None, links=None, enabled_decks=None):
    """Copy of the writer as it was before tranche 2 (non-atomic)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 2,
        "positions": [asdict(position) for position in positions],
        "progress": [asdict(item) for item in progress.values()],
        "groups": [asdict(group) for group in groups or []],
        "links": [asdict(link) for link in links or []],
    }
    if enabled_decks is not None:
        payload["decks"] = list(enabled_decks)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def sample():
    positions = [CardPosition("a:1", 0.1, 0.2, 0.3), CardPosition("a:2", -0.4, 0.5, 0.6, status="seen", related_ids=["a:1"])]
    progress = {"a:1": CardProgress("a:1", True, 40), "a:2": CardProgress("a:2")}
    groups = [CardGroup("group-1", "X", "#f5b942", ["a:1", "a:2"], 1)]
    links = [CardLink("a:1", "a:2"), CardLink("a:2", "a:1")]
    return positions, progress, groups, links


class StatePersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "data" / "state.json"

    def leftovers(self):
        return [p.name for p in self.path.parent.iterdir() if p.name.endswith(".tmp")]

    # --- writing -------------------------------------------------------

    def test_save_state_output_is_identical_to_the_legacy_writer(self) -> None:
        positions, progress, groups, links = sample()
        for decks in (None, [], ["a", "b"]):
            with self.subTest(decks=decks):
                new_path, old_path = self.dir / "new.json", self.dir / "old.json"
                save_state(new_path, positions, progress, groups, links, decks)
                legacy_save_state(old_path, positions, progress, groups, links, decks)
                self.assertEqual(new_path.read_bytes(), old_path.read_bytes())

    def test_save_state_defaults_for_optional_sections(self) -> None:
        positions, progress, _, _ = sample()
        save_state(self.dir / "new.json", positions, progress)
        legacy_save_state(self.dir / "old.json", positions, progress)
        self.assertEqual((self.dir / "new.json").read_bytes(), (self.dir / "old.json").read_bytes())
        self.assertNotIn("decks", json.loads((self.dir / "new.json").read_text(encoding="utf-8")))

    def test_parent_directory_is_created(self) -> None:
        positions, progress, groups, links = sample()
        save_state(self.path, positions, progress, groups, links)
        self.assertTrue(self.path.exists())

    def test_failed_replace_keeps_previous_file_and_cleans_up(self) -> None:
        positions, progress, groups, links = sample()
        save_state(self.path, positions, progress, groups, links, ["a"])
        before = self.path.read_bytes()
        with mock.patch("project.store.state.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                save_state(self.path, positions, progress, groups, links, ["a", "b"])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.leftovers(), [])

    def test_failed_serialisation_keeps_previous_file(self) -> None:
        positions, progress, groups, links = sample()
        save_state(self.path, positions, progress, groups, links)
        before = self.path.read_bytes()
        with mock.patch("project.store.state.json.dumps", side_effect=TypeError("boom")):
            with self.assertRaises(TypeError):
                save_state(self.path, positions, progress, groups, links)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.leftovers(), [])

    def test_concurrent_saves_leave_a_valid_file_and_no_leftovers(self) -> None:
        positions, progress, groups, links = sample()
        errors = []

        def work() -> None:
            try:
                for _ in range(25):
                    save_state(self.path, positions, progress, groups, links, ["a"])
            except Exception as error:  # pragma: no cover - only on failure
                errors.append(error)

        threads = [threading.Thread(target=work) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["version"], 2)
        self.assertEqual(self.leftovers(), [])

    # --- reading -------------------------------------------------------

    def test_missing_file_reads_as_none(self) -> None:
        self.assertIsNone(read_state_file(self.path))
        self.assertIsNone(JsonStateStore(self.path).read())

    def test_round_trip(self) -> None:
        positions, progress, groups, links = sample()
        store = JsonStateStore(self.path)
        store.write(RawState(positions, progress, groups, links, ["a", "b"]))
        self.assertEqual(store.read(), RawState(positions, progress, groups, links, ["a", "b"]))

    def test_absent_decks_key_reads_as_none_and_empty_list_stays_empty(self) -> None:
        positions, progress, groups, links = sample()
        write_state_file(self.path, RawState(positions, progress, groups, links, None))
        self.assertIsNone(read_state_file(self.path).decks)
        write_state_file(self.path, RawState(positions, progress, groups, links, []))
        self.assertEqual(read_state_file(self.path).decks, [])

    def test_reading_is_passive_and_keeps_everything(self) -> None:
        # entries for cards nobody asked about are returned as they are: no filtering, no defaults
        self.path.parent.mkdir(parents=True)
        self.path.write_text(
            json.dumps({"version": 2, "positions": [asdict(CardPosition("zzz:9", 1, 1, 1))], "progress": [], "groups": [], "links": []}),
            encoding="utf-8",
        )
        state = read_state_file(self.path)
        self.assertEqual([p.comb_id for p in state.positions], ["zzz:9"])
        self.assertEqual(state.progress, {})

    def test_unsupported_or_missing_version_is_rejected_with_a_clear_message(self) -> None:
        self.path.parent.mkdir(parents=True)
        for payload in ({"version": 1, "positions": []}, {"version": 3}, {"positions": []}, {"version": "2"}, [1, 2]):
            with self.subTest(payload=payload):
                self.path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(StateFileError) as caught:
                    read_state_file(self.path)
                self.assertIn("supported versions: [2]", str(caught.exception))

    def test_invalid_json_is_reported_as_state_file_error(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{"version": 2, "positions": [', encoding="utf-8")
        with self.assertRaises(StateFileError):
            read_state_file(self.path)

    # --- comb_id keys (phase 2) ---------------------------------------------------------------------------

    def test_positions_and_progress_are_keyed_by_comb_id(self) -> None:
        positions, progress, groups, links = sample()
        save_state(self.path, positions, progress, groups, links)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        for section in ("positions", "progress"):
            self.assertTrue(payload[section])
            self.assertTrue(all("comb_id" in item and "card_id" not in item for item in payload[section]), section)

    def test_a_version_2_file_with_card_id_is_rejected(self) -> None:
        # the layout before comb_id: same version, older key; old states are not carried over
        self.path.parent.mkdir(parents=True)
        for section in ("positions", "progress"):
            with self.subTest(section=section):
                item = {"card_id": "a:1", "x": 0, "y": 0, "z": 0} if section == "positions" else {"card_id": "a:1"}
                self.path.write_text(json.dumps({"version": 2, section: [item]}), encoding="utf-8")
                with self.assertRaises(StateFileError) as caught:
                    read_state_file(self.path)
                self.assertIn("card_id", str(caught.exception))

    def test_custom_supported_versions(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({"version": 3}), encoding="utf-8")
        self.assertEqual(read_state_file(self.path, supported_versions={3}), RawState())

    # --- layout change of tranche 7: no link group_id, a rank for every group -----------------------------

    def test_files_from_the_previous_layout_still_load(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({
            "version": 2, "positions": [], "progress": [],
            "groups": [{"id": "group-1", "name": "X", "color": "#fff", "card_ids": ["a:1"]}],
            "links": [{"source_id": "a:1", "target_id": "a:2", "group_id": "group-1"}],
        }), encoding="utf-8")
        state = read_state_file(self.path)
        self.assertEqual(state.links, [CardLink("a:1", "a:2")])  # the old key is ignored
        self.assertIsNone(state.groups[0].rank)  # StateCore.refresh_deck_state fills it

    def test_written_layout_has_ranks_and_no_link_group_id(self) -> None:
        positions, progress, groups, links = sample()
        save_state(self.path, positions, progress, groups, links)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(payload["groups"][0]["rank"], 1)
        self.assertTrue(all("group_id" not in link for link in payload["links"]))
        self.assertEqual(payload["version"], 2)  # same version: older code can still read the file

    # --- the old loaders are gone (tranche 9) ---------------------------------------------------------------

    def test_the_old_loaders_are_gone(self) -> None:
        for name in ("load_positions", "load_progress", "load_groups", "load_links", "load_enabled_decks"):
            self.assertFalse(hasattr(state_module, name), name)

    # --- the store with a fallback file name (tranche 9) --------------------------------------------------------

    def test_the_fallback_file_is_read_while_the_new_one_does_not_exist(self) -> None:
        positions, progress, groups, links = sample()
        old, new = self.dir / "positions.json", self.dir / "user_state.json"
        save_state(old, positions, progress, groups, links, ["a"])
        before = old.read_bytes()
        store = JsonStateStore(new, fallback_path=old)
        self.assertEqual(store.read(), RawState(positions, progress, groups, links, ["a"]))
        self.assertFalse(new.exists())  # reading does not create anything
        self.assertEqual(old.read_bytes(), before)

    def test_the_first_write_creates_the_new_file_and_leaves_the_old_one_alone(self) -> None:
        positions, progress, groups, links = sample()
        old, new = self.dir / "positions.json", self.dir / "user_state.json"
        save_state(old, positions, progress, groups, links, ["a"])
        before = old.read_bytes()
        store = JsonStateStore(new, fallback_path=old)
        store.write(RawState(positions, progress, groups, links, ["a", "b"]))
        self.assertEqual(old.read_bytes(), before)
        self.assertEqual(read_state_file(new).decks, ["a", "b"])
        self.assertEqual(store.read().decks, ["a", "b"])  # from now on the new file wins

    def test_the_new_file_wins_when_both_exist(self) -> None:
        positions, progress, groups, links = sample()
        old, new = self.dir / "positions.json", self.dir / "user_state.json"
        save_state(old, positions, progress, groups, links, ["old"])
        save_state(new, positions, progress, groups, links, ["new"])
        self.assertEqual(JsonStateStore(new, fallback_path=old).read().decks, ["new"])

    def test_nothing_at_all_reads_as_none_and_a_store_without_fallback_ignores_other_files(self) -> None:
        positions, progress, groups, links = sample()
        old, new = self.dir / "positions.json", self.dir / "user_state.json"
        self.assertIsNone(JsonStateStore(new, fallback_path=old).read())
        save_state(old, positions, progress, groups, links)
        self.assertIsNone(JsonStateStore(new).read())

    def test_the_fallback_file_is_checked_like_any_other(self) -> None:
        old = self.dir / "positions.json"
        old.write_text(json.dumps({"version": 1}), encoding="utf-8")
        with self.assertRaises(StateFileError):
            JsonStateStore(self.dir / "user_state.json", fallback_path=old).read()


if __name__ == "__main__":
    unittest.main()
