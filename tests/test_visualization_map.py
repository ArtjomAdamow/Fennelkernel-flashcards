from flashcards_app.runtime import CARDS
from flashcards_app.visualization.map import make_figure


def test_app_builds_a_nonempty_3d_figure():
    figure = make_figure(CARDS)
    marker_traces = [
        trace for trace in figure.data
        if trace.mode == "markers" and trace.name != "AnchorBounds"
    ]
    assert marker_traces
    assert len(marker_traces) == 2
    assert all(len(trace.x) == len(CARDS) for trace in marker_traces)


def test_selected_card_has_dedicated_highlight_traces():
    selected_id = CARDS[0].id
    figure = make_figure(CARDS, selected_id=selected_id)
    traces_by_name = {trace.name: trace for trace in figure.data}

    assert traces_by_name["Selected"].customdata == (selected_id,)
    assert traces_by_name["Selected progress"].customdata is None
    assert selected_id not in traces_by_name["Cards"].customdata
    assert traces_by_name["Card progress"].customdata is None


def test_figure_uses_only_cards_allowed_by_focus_filter():
    focused_cards = CARDS[:3]
    figure = make_figure(focused_cards)
    card_trace = next(trace for trace in figure.data if trace.name == "Cards")

    assert set(card_trace.customdata) == {card.id for card in focused_cards}
    assert all(len(trace.x) == len(focused_cards) for trace in figure.data if trace.name == "Card progress")
