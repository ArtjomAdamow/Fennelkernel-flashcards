from flashcards_app.geometry import sphere_positions
from flashcards_app.models import CardProgress
from flashcards_app.state import load_enabled_decks, load_positions, load_progress, save_state


def test_enabled_decks_default_to_all_and_can_be_filtered(tmp_path):
    path = tmp_path / "positions.json"
    available = ["alpha", "beta"]

    assert load_enabled_decks(path, available) == available
    save_state(path, [], {}, enabled_decks=["beta"])
    assert load_enabled_decks(path, available) == ["beta"]


def test_positions_round_trip(tmp_path):
    path = tmp_path / "positions.json"
    original = sphere_positions(["one", "two"], seed=3)
    save_state(path, original, {})
    restored = load_positions(path, ["one", "two"], seed=99)
    assert restored == original


def test_progress_round_trip_is_bounded(tmp_path):
    path = tmp_path / "positions.json"
    positions = sphere_positions(["one"], seed=3)
    progress = {"one": CardProgress("one", read=True, difficulty=140)}

    save_state(path, positions, progress)

    restored = load_progress(path, ["one"])
    assert restored["one"].read is True
    assert restored["one"].difficulty == 100
