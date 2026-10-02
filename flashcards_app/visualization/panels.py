import dash_daq as daq
from dash import dcc, html

from flashcards_app import runtime
from flashcards_app.models import Flashcard
from flashcards_app.services.decks import deck_filter_options


def card_panel(card: Flashcard | None, revealed: bool = False) -> html.Div:
    if card is None:
        return html.Div(
            [
                html.P("Select a point to begin.", className="empty-state"),
            ],
            className="card-panel",
        )
    content = card.answer if revealed else card.question
    label = "Answer" if revealed else "Question"
    return html.Div(
        [
            html.Div(label, className="card-label"),
            dcc.Markdown(content, className="card-content"),
            html.Div("Click this frame to reveal or hide the answer.", className="card-hint"),
        ],
        className="card-panel",
    )


def difficulty_control(card: Flashcard | None) -> html.Div:
    is_flipped = bool(card and runtime.PROGRESS[card.id].read)
    current_value = runtime.PROGRESS[card.id].difficulty if card and card.id in runtime.PROGRESS else 1
    progress_percent = (current_value - 1) / 99 * 100
    return html.Div(
        [
            html.Label("Progress", htmlFor="difficulty-slider", className="card-label"),
            html.Div(
                dcc.Slider(
                    id="difficulty-slider",
                    min=1,
                    max=100,
                    step=1,
                    value=current_value,
                    disabled=not is_flipped,
                    marks={
                        1: {"label": "review", "style": {"color": "#ffffff"}},
                        50: {"label": "developing", "style": {"color": "#ffffff"}},
                        100: {"label": "learned", "style": {"color": "#ffffff"}},
                    },
                ),
                className="progress-slider" if is_flipped else "progress-slider disabled-progress-slider",
                style={"--progress": f"{progress_percent:.4f}%"},
            ),
        ],
        className="progress-control",
    )


def position_control(card: Flashcard | None, drag_enabled: bool = False) -> html.Div:
    position = runtime.POSITION_BY_ID.get(card.id) if card else None
    x_value = round(position.x, 3) if position else 0
    y_value = round(position.y, 3) if position else 0
    z_value = round(position.z, 3) if position else 0
    return html.Div(
        [
            html.Div("Position", className="card-label"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Button("Stop changing position" if drag_enabled else "Change", id="toggle-drag", n_clicks=0, disabled=position is None, className="tool-button"),
                            html.Button("Save", id="save-position", n_clicks=0, disabled=position is None, className="tool-button"),
                        ],
                        className="position-actions",
                    ),
                    html.Div(
                        [
                            html.Div([html.Label("X", htmlFor="drag-x"), dcc.Slider(id="drag-x", min=-1, max=1, step=0.001, value=x_value, disabled=not drag_enabled, marks={-1: {"label": "-1", "style": {"color": "#ffffff"}}, 0: {"label": "0", "style": {"color": "#ffffff"}}, 1: {"label": "1", "style": {"color": "#ffffff"}}})], className="coordinate-control"),
                            html.Div([html.Label("Y", htmlFor="drag-y"), dcc.Slider(id="drag-y", min=-1, max=1, step=0.001, value=y_value, disabled=not drag_enabled, marks={-1: {"label": "-1", "style": {"color": "#ffffff"}}, 0: {"label": "0", "style": {"color": "#ffffff"}}, 1: {"label": "1", "style": {"color": "#ffffff"}}})], className="coordinate-control"),
                            html.Div([html.Label("Z", htmlFor="drag-z"), dcc.Slider(id="drag-z", min=-1, max=1, step=0.001, value=z_value, disabled=not drag_enabled, marks={-1: {"label": "-1", "style": {"color": "#ffffff"}}, 0: {"label": "0", "style": {"color": "#ffffff"}}, 1: {"label": "1", "style": {"color": "#ffffff"}}})], className="coordinate-control"),
                        ],
                        className="position-sliders",
                    ),
                ],
                className="position-row",
            ),
        ],
        className="tool-panel",
    )


def group_control(card: Flashcard | None, dialog: str | None = None) -> html.Div:
    selected_groups = [group.id for group in runtime.GROUPS if card and card.id in group.card_ids]
    dialog_options = [
        {"label": group.name, "value": group.id}
        for group in runtime.GROUPS
        if dialog != "remove" or card is None or card.id in group.card_ids
    ]
    dialog_title = {"new": "New group", "add": "Add to group", "remove": "Remove from group", "delete": "Delete group", "focus": "Focus group"}.get(dialog)
    dialog_body = [
        dcc.Input(id="dialog-group-name", type="text", placeholder="Group name", style={"display": "block" if dialog == "new" else "none"}),
        daq.ColorPicker(id="dialog-group-color", value={"hex": "#f5b942"}, size=140, style={"display": "block" if dialog == "new" else "none"}),
        dcc.Dropdown(
            id="dialog-group-select",
            className="closed-dropdown",
            options=dialog_options,
            value=selected_groups[0] if selected_groups else None,
            placeholder="Select a saved group",
            clearable=True,
            style={"display": "block" if dialog in {"add", "remove", "delete", "focus"} else "none"},
        ),
    ]
    return html.Div(
        [
            html.Div("Groups", className="card-label"),
            html.Div(
                [
                    html.Button("New", id="new-group", n_clicks=0, disabled=card is None, className="tool-button"),
                    html.Button("Delete", id="delete-group", n_clicks=0, disabled=card is None, className="tool-button"),
                    html.Button("Add", id="add-group", n_clicks=0, disabled=card is None, className="tool-button"),
                    html.Button("Remove", id="remove-group", n_clicks=0, disabled=card is None, className="tool-button"),
                    html.Button("Focus", id="focus-group", n_clicks=0, disabled=not runtime.GROUPS, className="tool-button"),
                    html.Button("All", id="all-groups", n_clicks=0, className="tool-button"),
                ],
                className="tool-row control-actions",
            ),
            html.Div(
                [
                    html.Div(
                        [html.Span(className="group-color-swatch", style={"backgroundColor": group.color}), html.Span(group.name), html.Span(f"{len(group.card_ids)} cards", className="group-member-count")],
                        className="group-list-item",
                    )
                    for group in runtime.GROUPS
                ] or [html.Div("No saved groups yet.", className="tool-status")],
                className="group-list",
            ),
            html.Div(
                [
                    html.Div(dialog_title, className="dialog-title"),
                    html.Div(dialog_body, className="dialog-fields"),
                    html.Div(
                        [
                            html.Button("Confirm", id="group-dialog-submit", n_clicks=0, className="tool-button"),
                            html.Button("Cancel", id="group-dialog-cancel", n_clicks=0, className="tool-button"),
                        ],
                        className="tool-row",
                    ),
                ],
                className="group-dialog" if dialog else "group-dialog group-dialog-hidden",
            ),
            html.Div(id="group-status", className="tool-status"),
        ],
        className="tool-panel",
    )


def deck_control(dialog: str | None = None, selected_deck: str | None = runtime.NONE_DECK) -> html.Div:
    current_decks = runtime.available_decks()
    dialog_options = [
        {"label": deck, "value": deck}
        for deck in current_decks
        if (dialog == "add" and deck not in runtime.ENABLED_DECKS)
        or (dialog in {"remove", "focus"} and deck in runtime.ENABLED_DECKS)
    ]
    dialog_title = {"add": "Add deck", "remove": "Remove deck", "focus": "Focus deck"}.get(dialog)
    return html.Div(
        [
            html.Div("Deck", className="card-label"),
            html.Div(
                [
                    html.Button("Add", id="add-deck", n_clicks=0, className="tool-button"),
                    html.Button("Remove", id="remove-deck", n_clicks=0, className="tool-button"),
                    html.Button("Focus", id="focus-deck", n_clicks=0, className="tool-button"),
                    html.Button("All", id="all-decks", n_clicks=0, className="tool-button"),
                    html.Button("Reset", id="reset-cards", n_clicks=0, className="reset-button"),
                ],
                className="tool-row control-actions",
            ),
            dcc.Dropdown(
                id="deck-filter",
                className="closed-dropdown",
                options=deck_filter_options(),
                value=selected_deck,
                clearable=False,
                style={"display": "none"},
            ),
            html.Div(
                [
                    html.Div(dialog_title, className="dialog-title"),
                    dcc.Dropdown(
                        id="deck-dialog-select",
                        className="closed-dropdown",
                        options=dialog_options,
                        placeholder="Select a deck",
                        clearable=True,
                    ),
                    html.Div(
                        [
                            html.Button("Confirm", id="deck-dialog-submit", n_clicks=0, className="tool-button"),
                            html.Button("Cancel", id="deck-dialog-cancel", n_clicks=0, className="tool-button"),
                        ],
                        className="tool-row",
                    ),
                ],
                className="group-dialog" if dialog else "group-dialog group-dialog-hidden",
            ),
        ],
        className="tool-panel compact-panel deck-panel",
    )


def connection_control(card: Flashcard | None, deck: str = "all", focused_group: str | None = None) -> html.Div:
    candidate_cards = [entry for entry in runtime.CARDS if deck == "all" or entry.deck == deck]
    if focused_group:
        group = next((item for item in runtime.GROUPS if item.id == focused_group), None)
        if group:
            candidate_cards = [entry for entry in candidate_cards if entry.id in group.card_ids]
    options = [
        {"label": other.question[:55], "value": other.id}
        for other in candidate_cards
        if other.id != (card.id if card else "")
    ]
    return html.Div(
        [
            html.Div("Connections", className="card-label"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Button("Connect", id="create-link", n_clicks=0, disabled=card is None, className="tool-button"),
                            html.Button("Disconnect", id="disconnect-link", n_clicks=0, disabled=card is None, className="tool-button"),
                        ],
                        className="connection-buttons",
                    ),
                    dcc.Dropdown(
                        id="link-target",
                        className="closed-dropdown",
                        options=options,
                        placeholder="Select a card",
                        disabled=card is None,
                        clearable=True,
                    ),
                ],
                className="connection-actions",
            ),
        ],
        className="tool-panel compact-panel",
    )
