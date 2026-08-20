from pathlib import Path

from flashcards_app.geometry import sphere_positions
from flashcards_app.parser import load_decks
from flashcards_app.state import load_positions, save_positions


ROOT = Path(__file__).resolve().parents[1]


def test_populated_decks_are_parsed():
    cards = load_decks(ROOT)
    assert len(cards) >= 20
    assert any(card.question.startswith("What is a Heuristic?") for card in cards)
    assert all(card.answer for card in cards)


def test_positions_are_deterministic_and_inside_sphere():
    ids = ["one", "two", "three"]
    first = sphere_positions(ids, seed=7)
    second = sphere_positions(ids, seed=7)
    assert first == second
    assert all(point.x**2 + point.y**2 + point.z**2 <= 1 for point in first)


def test_positions_round_trip(tmp_path):
    path = tmp_path / "positions.json"
    original = sphere_positions(["one", "two"], seed=3)
    save_positions(path, original)
    restored = load_positions(path, ["one", "two"], seed=99)
    assert restored == original


def test_app_builds_a_nonempty_3d_figure():
    from app import CARDS, make_figure

    figure = make_figure(CARDS)
    assert len(figure.data) == 1
    assert len(figure.data[0].x) == len(CARDS)
