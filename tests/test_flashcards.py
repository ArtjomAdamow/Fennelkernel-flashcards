from pathlib import Path

from flashcards_app.geometry import sphere_positions
from flashcards_app.models import CardProgress, Flashcard
from flashcards_app.parser import format_technical_terms, load_decks
from flashcards_app.state import load_positions, load_progress, save_positions, save_state


ROOT = Path(__file__).resolve().parents[1]


def test_populated_decks_are_parsed():
    cards = load_decks(ROOT)
    assert len(cards) >= 20
    assert any(card.question.startswith("What is a Heuristic?") for card in cards)
    assert all(card.answer for card in cards)


def test_technical_term_formatting_preserves_existing_code():
    formatted = format_technical_terms("Use snake_case and already `safe_name`.")

    assert formatted == "Use `snake_case` and already `safe_name`."


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
    marker_traces = [trace for trace in figure.data if trace.mode == "markers"]
    assert marker_traces
    assert sum(len(trace.x) for trace in marker_traces) == len(CARDS)


def test_progress_round_trip_is_bounded(tmp_path):
    path = tmp_path / "positions.json"
    positions = sphere_positions(["one"], seed=3)
    progress = {"one": CardProgress("one", read=True, difficulty=140)}

    save_state(path, positions, progress)

    restored = load_progress(path, ["one"])
    assert restored["one"].read is True
    assert restored["one"].difficulty == 100


def test_random_card_prefers_read_cards_and_low_difficulty():
    from app import choose_random_card

    cards = [Flashcard("new", "deck", "new", "answer"), Flashcard("review", "deck", "review", "answer")]
    progress = {
        "new": CardProgress("new", read=False, difficulty=1),
        "review": CardProgress("review", read=True, difficulty=80),
    }

    selected = choose_random_card(cards, progress, __import__("random"))

    assert selected == cards[1]
