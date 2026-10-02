from dash import Dash, dcc, html
from flask import jsonify

from flashcards_app.runtime import ENABLED_DECKS, GROUPS, LINKS, POSITIONS, PROGRESS, SERVER_BOOT_ID, STATE_PATH
from flashcards_app.state import save_state
from flashcards_app.visualization.map import color_legend, make_figure
from flashcards_app.visualization.panels import (
    card_panel, connection_control, deck_control, difficulty_control,
    group_control, position_control,
)

app = Dash(__name__)
app.title = "Spatial Flashcards"
app.index_string = app.index_string.replace(
    "{%app_entry%}",
    f'<script>window.__SERVER_BOOT_ID__ = "{SERVER_BOOT_ID}";</script>{{%app_entry%}}',
)


@app.server.route("/boot-id")
def boot_id():
    return jsonify({"bootId": SERVER_BOOT_ID})


app.layout = html.Main(
    [
        html.Header(
            [
                html.Div([html.P("SPATIAL STUDY", className="eyebrow"), html.H1("Arrange what you learn.")]),
                html.Div(
                    [
                        html.Button("Random card", id="random-card", className="random-button", n_clicks=0),
                    ],
                    className="topbar-actions",
                ),
            ],
            className="topbar",
        ),
        html.Section(
            [html.Div("0 cards mapped", id="card-count", className="card-count")],
            className="toolbar",
        ),
        html.Section(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.Graph(
                                    id="sphere",
                                    figure=make_figure([]),
                                    config={"displayModeBar": False, "scrollZoom": True, "doubleClick": "reset+autosize"},
                                ),
                            ],
                            className="map-frame",
                        ),
                        color_legend(),
                    ],
                    className="map-column",
                ),
                html.Div(
                    [
                        html.Div(id="selected-card", children=card_panel(None), n_clicks=0, className="window-a-card"),
                        html.Div(id="difficulty-control", children=difficulty_control(None), className="window-a-progress"),
                        html.Div(id="position-control", children=position_control(None), className="window-a-position"),
                    ],
                    className="layout-window window-a",
                ),
                html.Div(
                    [
                        html.Div(id="deck-control", children=deck_control(), className="stack-window"),
                        html.Div(id="group-control", children=group_control(None), className="stack-window"),
                        html.Div(id="connection-control", children=connection_control(None, "all", None), className="stack-window"),
                    ],
                    className="layout-window window-b",
                ),
            ],
            className="workspace",
        ),
        dcc.Store(id="selected-id"),
        dcc.Store(id="revealed", data=False),
        dcc.Store(id="drag-enabled", data=False),
        dcc.Store(id="group-dialog", data=None),
        dcc.Store(id="deck-dialog-state", data=None),
        dcc.Store(id="focused-group", data=None),
        dcc.Input(id="keyboard-nav", value="", type="text", className="keyboard-nav"),
        dcc.ConfirmDialog(
            id="reset-confirm",
            message="Reset all cards? This clears read status, difficulty, groups, connections, and positions.",
        ),
    ],
    className="app-shell",
)


def main() -> None:
    save_state(STATE_PATH, POSITIONS, PROGRESS, GROUPS, LINKS)
    app.run(debug=True)
