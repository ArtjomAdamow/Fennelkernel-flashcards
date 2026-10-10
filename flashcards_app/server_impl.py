from dash import Dash, dcc, html
from flask import jsonify

from flashcards_app.visualization.map import color_legend, make_figure
from flashcards_app.visualization.panels import (
    card_panel, connection_control, deck_control, difficulty_control,
    group_control, position_control,
)


def create_app(base_dir, server_boot_id, state):
    """Build the Dash app: layout, assets folder and the boot-id route that reload-guard.js polls.

    `state` is the UserStateService the initial panels and the empty map are built from.
    """
    app = Dash(__name__, assets_folder=str(base_dir / "assets"))
    app.title = "Spatial Flashcards"
    app.index_string = app.index_string.replace(
        "{%app_entry%}",
        f'<script>window.__SERVER_BOOT_ID__ = "{server_boot_id}";</script>{{%app_entry%}}',
    )


    @app.server.route("/boot-id")
    def boot_id():
        return jsonify({"bootId": server_boot_id})


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
                                        figure=make_figure([], state=state),
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
                            html.Div(id="difficulty-control", children=difficulty_control(None, state=state), className="window-a-progress"),
                            html.Div(id="position-control", children=position_control(None, state=state), className="window-a-position"),
                        ],
                        className="layout-window window-a",
                    ),
                    html.Div(
                        [
                            html.Div(id="deck-control", children=deck_control(state=state), className="stack-window"),
                            html.Div(id="group-control", children=group_control(None, state=state), className="stack-window"),
                            html.Div(id="connection-control", children=connection_control(None, "all", None, state=state), className="stack-window"),
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

    return app
