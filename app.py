from pathlib import Path

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html

from flashcards_app.models import Flashcard
from flashcards_app.parser import load_decks
from flashcards_app.state import load_positions, save_positions

BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "data" / "positions.json"
CARDS = load_decks(BASE_DIR)
POSITIONS = load_positions(STATE_PATH, [card.id for card in CARDS])
CARD_BY_ID = {card.id: card for card in CARDS}
POSITION_BY_ID = {position.card_id: position for position in POSITIONS}


def make_figure(cards: list[Flashcard], selected_id: str | None = None) -> go.Figure:
    visible_ids = {card.id for card in cards}
    points = [position for position in POSITIONS if position.card_id in visible_ids]
    selected = [position for position in points if position.card_id == selected_id]
    regular = [position for position in points if position.card_id != selected_id]

    figure = go.Figure()
    if regular:
        figure.add_trace(
            go.Scatter3d(
                x=[point.x for point in regular],
                y=[point.y for point in regular],
                z=[point.z for point in regular],
                mode="markers",
                customdata=[point.card_id for point in regular],
                text=[CARD_BY_ID[point.card_id].question for point in regular],
                hovertemplate="%{text}<extra></extra>",
                marker={"size": 7, "color": "#f5b942", "opacity": 0.82},
                name="Cards",
            )
        )
    if selected:
        point = selected[0]
        figure.add_trace(
            go.Scatter3d(
                x=[point.x],
                y=[point.y],
                z=[point.z],
                mode="markers",
                customdata=[point.card_id],
                text=[CARD_BY_ID[point.card_id].question],
                hovertemplate="%{text}<extra></extra>",
                marker={"size": 13, "color": "#e76f51", "line": {"width": 2, "color": "#fff3d6"}},
                name="Selected",
            )
        )

    figure.update_layout(
        paper_bgcolor="#102a43",
        plot_bgcolor="#102a43",
        font={"color": "#f7f2e8", "family": "Georgia"},
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        showlegend=False,
        scene={
            "aspectmode": "cube",
            "xaxis": {"visible": False, "range": [-1.15, 1.15]},
            "yaxis": {"visible": False, "range": [-1.15, 1.15]},
            "zaxis": {"visible": False, "range": [-1.15, 1.15]},
            "bgcolor": "#102a43",
        },
    )
    return figure


def card_panel(card: Flashcard | None, revealed: bool = False) -> html.Div:
    if card is None:
        return html.Div([html.P("Select a point to begin.", className="empty-state")], className="card-panel")
    content = card.answer if revealed else card.question
    label = "Answer" if revealed else "Question"
    return html.Div(
        [
            html.Div(label, className="card-label"),
            html.Div(content, className="card-content"),
            html.Div("Click this frame to reveal or hide the answer.", className="card-hint"),
        ],
        className="card-panel",
    )


app = Dash(__name__)
app.title = "Spatial Flashcards"
app.layout = html.Main(
    [
        html.Header(
            [
                html.Div([html.P("SPATIAL STUDY", className="eyebrow"), html.H1("Arrange what you learn.")]),
                html.Button("Random card", id="random-card", className="random-button", n_clicks=0),
            ],
            className="topbar",
        ),
        html.Section(
            [
                html.Div(
                    [
                        html.Label("Deck", htmlFor="deck-filter"),
                        dcc.Dropdown(
                            id="deck-filter",
                            options=[{"label": "All decks", "value": "all"}] + [
                                {"label": deck, "value": deck}
                                for deck in sorted({card.deck for card in CARDS})
                            ],
                            value="all",
                            clearable=False,
                        ),
                    ],
                    className="filter-control",
                ),
                html.Div(f"{len(CARDS)} cards mapped", id="card-count", className="card-count"),
            ],
            className="toolbar",
        ),
        html.Section(
            [
                dcc.Graph(id="sphere", figure=make_figure(CARDS), config={"displayModeBar": False}),
                html.Div(id="selected-card", children=card_panel(None), n_clicks=0),
            ],
            className="workspace",
        ),
        dcc.Store(id="selected-id"),
        dcc.Store(id="revealed", data=False),
    ],
    className="app-shell",
)


@app.callback(
    Output("sphere", "figure"),
    Output("selected-card", "children"),
    Output("selected-id", "data"),
    Output("revealed", "data"),
    Input("sphere", "clickData"),
    Input("selected-card", "n_clicks"),
    Input("random-card", "n_clicks"),
    Input("deck-filter", "value"),
    State("selected-id", "data"),
    State("revealed", "data"),
)
def update_card(click_data, panel_clicks, random_clicks, deck, selected_id, revealed):
    from dash import ctx
    import random

    cards = [card for card in CARDS if deck == "all" or card.deck == deck]
    trigger = ctx.triggered_id
    if trigger == "sphere" and click_data and click_data.get("points"):
        selected_id = click_data["points"][0].get("customdata")
        revealed = False
    elif trigger == "selected-card" and selected_id:
        revealed = not revealed
    elif trigger == "random-card" and cards:
        selected_id = random.choice(cards).id
        revealed = False
    elif trigger == "deck-filter":
        if selected_id not in {card.id for card in cards}:
            selected_id = None
        revealed = False

    selected_card = CARD_BY_ID.get(selected_id)
    return make_figure(cards, selected_id), card_panel(selected_card, revealed), selected_id, revealed


if __name__ == "__main__":
    save_positions(STATE_PATH, POSITIONS)
    app.run(debug=True)
