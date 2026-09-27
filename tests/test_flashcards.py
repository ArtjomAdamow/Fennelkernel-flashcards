from pathlib import Path

from flashcards_app.geometry import sphere_positions
from flashcards_app.models import CardProgress, Flashcard
from flashcards_app.parser import format_technical_terms, load_decks
from flashcards_app.state import load_enabled_decks, load_positions, load_progress, save_positions, save_state


ROOT = Path(__file__).resolve().parents[1]


def test_populated_decks_are_parsed():
    cards = load_decks(ROOT / "data" / "cards")
    assert len(cards) >= 20
    assert any(card.question.startswith("What is a Heuristic?") for card in cards)
    assert all(card.answer for card in cards)


def test_enabled_decks_default_to_all_and_can_be_filtered(tmp_path):
    path = tmp_path / "positions.json"
    available = ["alpha", "beta"]

    assert load_enabled_decks(path, available) == available
    save_state(path, [], {}, enabled_decks=["beta"])
    assert load_enabled_decks(path, available) == ["beta"]


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
    assert len(marker_traces) == 2
    assert all(len(trace.x) == len(CARDS) for trace in marker_traces)


def test_selected_card_has_dedicated_highlight_traces():
    from app import CARDS, make_figure

    selected_id = CARDS[0].id
    figure = make_figure(CARDS, selected_id=selected_id)
    traces_by_name = {trace.name: trace for trace in figure.data}

    assert traces_by_name["Selected"].customdata == (selected_id,)
    assert traces_by_name["Selected progress"].customdata is None
    assert selected_id not in traces_by_name["Cards"].customdata
    assert traces_by_name["Card progress"].customdata is None


def test_figure_uses_only_cards_allowed_by_focus_filter():
    from app import CARDS, make_figure

    focused_cards = CARDS[:3]
    figure = make_figure(focused_cards)
    card_trace = next(trace for trace in figure.data if trace.name == "Cards")

    assert set(card_trace.customdata) == {card.id for card in focused_cards}
    assert all(len(trace.x) == len(focused_cards) for trace in figure.data if trace.name == "Card progress")


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


def test_deck_and_group_actions_are_single_rows():
    from app import deck_control, group_control

    def nodes(component):
        node = component.to_plotly_json()
        yield node
        children = node.get("props", {}).get("children", [])
        if not isinstance(children, list):
            children = [children]
        for child in children:
            if hasattr(child, "to_plotly_json"):
                yield from nodes(child)

    deck_nodes = list(nodes(deck_control()))
    group_nodes = list(nodes(group_control(None)))
    deck_ids = {node.get("props", {}).get("id") for node in deck_nodes}
    group_ids = {node.get("props", {}).get("id") for node in group_nodes}

    def action_ids(component_nodes):
        action_row = next(
            node
            for node in component_nodes
            if node.get("props", {}).get("className") == "tool-row control-actions"
        )
        return [
            child.to_plotly_json()["props"]["id"]
            for child in action_row["props"]["children"]
        ]

    assert sum(node.get("props", {}).get("className") == "tool-row control-actions" for node in deck_nodes) == 1
    assert sum(node.get("props", {}).get("className") == "tool-row control-actions" for node in group_nodes) == 1
    assert action_ids(deck_nodes) == ["add-deck", "remove-deck", "focus-deck", "all-decks", "reset-cards"]
    assert action_ids(group_nodes) == ["new-group", "delete-group", "add-group", "remove-group", "focus-group", "all-groups"]
    assert {"add-deck", "remove-deck", "focus-deck", "all-decks", "reset-cards"} <= deck_ids
    assert {"new-group", "add-group", "remove-group", "delete-group", "focus-group", "all-groups"} <= group_ids
