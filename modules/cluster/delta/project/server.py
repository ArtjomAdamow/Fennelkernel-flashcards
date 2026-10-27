"""The Dash app and its layout for the cluster module (replaces project/server.py).

Changes against the main file:
  * top bar: "Random" (a random topic or card; hidden in the decks view) and the choice button (Decks, Topics
    or Cards, by the view), with its checkbox dialog under it;
  * window A: the card's window as a row (the vertical cut-off slider, then the card panel; 2026-10-27, roadmap
    step 26) and the progress control (the position panel is gone);
  * window B: groups and connections (the deck panel is gone); assets/style.css puts it above the map;
  * no reset confirmation and no drag store; a store for the choice dialog;
  * a module action button (services.actions) left of Random: a module on top of this one (the helper) gives it
    a label and a function; without an action the button is there but hidden, so the callback's input exists;
  * the card's frame (2026-10-27, roadmap step 31): the gold border and the background that were the card
    panel's sit on a column (`card-frame`) that holds the clickable panel (`selected-card`) and, under it, the
    quiz control (`quiz-control`: a quiz's answer options and Confirm), so a checkbox or Confirm is no click on
    the panel; the browser keeps Confirm disabled while nothing is checked (a clientside callback);
  * the image window (`image-window`) over the map inside `.map-frame`: a selected card's image in the cards
    view, served by the route /card-image/<name> from the images folder only; the `image-open` store.
"""

from __future__ import annotations

from pathlib import Path

from dash import Dash, Input, Output, dcc, html
from flask import jsonify, send_from_directory
from werkzeug.exceptions import NotFound

from project.layout.map import color_legend, make_figure
from project.layout.panels import (
    IMAGE_ROUTE, card_panel, choice_control, choice_label, connection_control, cutoff_control, difficulty_control,
    group_control, image_window, quiz_control,
)
from project.services.actions import ACTION_ID
from project.services.views import DECKS

# Confirm follows the checks in the browser: disabled while the checklist has no value (no round trip per toggle)
CONFIRM_DISABLED_JS = "function (checked) { return !(Array.isArray(checked) && checked.length > 0); }"


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

    images_folder = str(Path(state.images.folder).resolve()) if getattr(state, "images", None) is not None else None

    @app.server.route(f"{IMAGE_ROUTE}<name>")
    def card_image(name):
        # The images folder only: a name that leaves it, or a missing file, is a plain 404 (in debug mode a
        # raised NotFound would show Dash's debugger page instead)
        if images_folder is None:
            return "", 404
        try:
            return send_from_directory(images_folder, name)
        except NotFound:
            return "", 404

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
                                    # The image window: covers the graph (which stays, a callback input and
                                    # output) while a card of the cards view is selected
                                    html.Div(id="image-window", className="image-window", children=image_window(None, False)),
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
                                    # The card's frame: the clickable panel, then a quiz's options and Confirm
                                    # outside it, so a checkbox or Confirm is no click on the panel
                                    html.Div(
                                        [
                                            html.Div(id="selected-card", children=card_panel(None), n_clicks=0, className="window-a-panel"),
                                            html.Div(id="quiz-control", children=quiz_control(None)),
                                        ],
                                        className="card-frame",
                                    ),
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
            dcc.Store(id="image-open", data=False, storage_type="memory"),
            dcc.Input(id="keyboard-nav", value="", type="text", className="keyboard-nav"),
        ],
        className="app-shell",
    )

    # Confirm's disabled state follows the quiz checklist in the browser; the main callback renders it anew with
    # every quiz control, and Dash then runs this once more for the new checklist
    app.clientside_callback(CONFIRM_DISABLED_JS, Output("quiz-confirm", "disabled"), Input("quiz-options", "value"))

    return app
