"""The Dash app and its layout for the cluster module (replaces project/server.py).

Changes against the main file:
  * top bar: "Random" (a random topic or card; hidden in the decks view) and the choice button (Decks, Topics
    or Cards, by the view), with its checkbox dialog under it;
  * window A: the card's window as a row (the vertical cut-off slider, then the card panel; 2026-10-27, roadmap
    step 26) and the progress control (the position panel is gone);
  * window B: groups and connections (the deck panel is gone); assets/style.css puts it above the map;
  * no reset confirmation and no drag store; a store for the choice dialog;
  * a module action button (services.actions) left of Random: a module on top of this one (the helper) gives it
    a label and a function; without an action the button is there but hidden, so the callback's input exists.
"""

from __future__ import annotations

from pathlib import Path

from dash import Dash, dcc, html
from flask import jsonify

from project.layout.map import color_legend, make_figure
from project.layout.panels import (
    card_panel, choice_control, choice_label, connection_control, cutoff_control, difficulty_control, group_control,
)
from project.services.actions import ACTION_ID
from project.services.views import DECKS


def create_app(base_dir, server_boot_id, state, action=None):
    """Build Dash with the project assets and transient navigation stores.

    `state` is the ViewRouter the initial panels and the empty map are built from; `action` is a module's
    ModuleAction for the top bar button, or None.
    """
    app = Dash(__name__, assets_folder=str(Path(base_dir) / "assets"))
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
                            html.Button(
                                action.label if action else "", id=ACTION_ID, className="random-button", n_clicks=0,
                                title=action.title if action else "", style={} if action else {"display": "none"},
                            ),
                            html.Button(
                                "Random", id="random-card", className="random-button", n_clicks=0,
                                style={"display": "none"} if state.view == DECKS else {},
                            ),
                            html.Div(
                                [
                                    html.Button(choice_label(state.view), id="choice-open", className="random-button", n_clicks=0),
                                    html.Div(id="choice-control", children=choice_control(False, state)),
                                ],
                                className="choice-anchor",
                            ),
                        ],
                        className="topbar-actions",
                    ),
                ],
                className="topbar",
            ),
            html.Section(
                [html.Div(f"{len(state.visible_cards())} decks mapped", id="card-count", className="card-count")],
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
                                        figure=make_figure([], state=state, view=state.view),
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
                            html.Div(
                                [
                                    # The cut-off line's slider, outside the card panel so a move is no panel click
                                    html.Div(
                                        id="cutoff-control", className="window-a-cutoff",
                                        children=cutoff_control(state.cutoff(), hidden=not state.connected()),
                                    ),
                                    html.Div(id="selected-card", children=card_panel(None), n_clicks=0, className="window-a-panel"),
                                ],
                                className="window-a-card",
                            ),
                            html.Div(id="difficulty-control", children=difficulty_control(None, state=state), className="window-a-progress"),
                        ],
                        className="layout-window window-a",
                    ),
                    html.Div(
                        [
                            html.Div(id="group-control", children=group_control(None, state=state), className="stack-window"),
                            html.Div(id="connection-control", children=connection_control(None, state.cards), className="stack-window"),
                        ],
                        className="layout-window window-b",
                    ),
                ],
                className="workspace",
            ),
            dcc.Store(id="selected-id"),
            dcc.Store(id="revealed", data=False),
            dcc.Store(id="group-dialog", data=None),
            dcc.Store(id="choice-dialog", data=False),
            dcc.Store(id="focused-group", data=None),
            dcc.Store(id="nav-state", data=None, storage_type="memory"),
            dcc.Input(id="keyboard-nav", value="", type="text", className="keyboard-nav"),
        ],
        className="app-shell",
    )

    return app
