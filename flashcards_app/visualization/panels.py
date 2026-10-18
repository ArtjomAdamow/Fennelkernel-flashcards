import dash_daq as daq
from dash import dcc, html

from flashcards_app import runtime
from flashcards_app.models import Flashcard


def _state(state):
    if state is None:
        raise TypeError("state is required: pass the UserStateService")
    return state


# Small notes next to the Confirm button of a dialog
NEW_GROUP_NOTE = "The selected card will be added to the new group."
ADD_TO_GROUP_NOTE = "Membership and color of the previously assigned group will remain until removed from the other group."
DELETE_GROUP_NOTE = "Connections of member cards will remain."
REMOVE_DECK_NOTE = "Settings of all deck member cards will be erased."
# phase 4: constellations
DELETE_CONSTELLATION_NOTE = "Deleting a constellation will disconnect all members"


def _dialog_note(text):
    return [html.Span(text, className="dialog-note")] if text else []


def deck_filter_options(state=None) -> list[dict[str, str]]:
    return [{"label": "None", "value": runtime.NONE_DECK}, {"label": "All decks", "value": "all"}] + [
        {"label": deck, "value": deck}
        for deck in sorted(_state(state).enabled_decks)
    ]


def constellation_options(state=None) -> list[dict[str, str]]:
    """Dropdown options of the Delete dialog: the runtime constellations, valued by const_id."""
    return [{"label": item.name, "value": item.const_id} for item in _state(state).constellations]


def delete_constellation(state, const_id: str) -> int:
    """The Delete action of the Connections panel: disconnect all members of the constellation from each other.

    The members are the visible cards of the runtime constellation `const_id`; the service removes the stored links
    between them (links to hidden cards stay) and the state core saves that at once. Returns the number of links
    removed. Ordinary Disconnect is something else: it removes only the one selected link.
    """
    return _state(state).delete_constellation_links(const_id)


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


def difficulty_control(card: Flashcard | None, state=None) -> html.Div:
    state = _state(state)
    is_flipped = bool(card and state.progress[card.id].read)
    current_value = state.progress[card.id].difficulty if card and card.id in state.progress else 1
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


def position_control(card: Flashcard | None, drag_enabled: bool = False, state=None) -> html.Div:
    position = _state(state).position_by_id.get(card.id) if card else None
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


def group_control(card: Flashcard | None, dialog: str | None = None, state=None, focused_group: str | None = None) -> html.Div:
    state = _state(state)
    # The swatches of the selected card's groups glow, except the group that gives the card its colour on the map
    deciding = state.deciding_group(card.id, focused_group) if card else None
    shares_members = {
        id(group) for group in state.groups
        if card and card.id in group.card_ids and group is not deciding
    }
    selected_groups = [group.id for group in state.groups if card and card.id in group.card_ids]
    dialog_options = [
        {"label": group.name, "value": group.id}
        for group in state.groups
        if dialog != "remove" or card is None or card.id in group.card_ids
    ]
    dialog_title = {"new": "New group", "add": "Add to group", "remove": "Remove from group", "delete": "Delete group", "focus": "Focus group"}.get(dialog)
    note = {"new": NEW_GROUP_NOTE, "delete": DELETE_GROUP_NOTE}.get(dialog)
    if dialog == "add" and card is not None and any(card.id in group.card_ids for group in state.groups):
        note = ADD_TO_GROUP_NOTE
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
                    html.Button("Focus", id="focus-group", n_clicks=0, disabled=not state.groups, className="tool-button"),
                    html.Button("All", id="all-groups", n_clicks=0, className="tool-button"),
                ],
                className="tool-row control-actions",
            ),
            html.Div(
                [
                    html.Div(
                        [html.Span(className="group-color-swatch group-color-swatch-shared" if id(group) in shares_members else "group-color-swatch", style={"backgroundColor": group.color, "color": group.color}), html.Span(group.name), html.Span(f"{len(group.card_ids)} cards", className="group-member-count")],
                        className="group-list-item",
                    )
                    for group in state.groups
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
                        ] + _dialog_note(note),
                        className="tool-row",
                    ),
                ],
                className="group-dialog" if dialog else "group-dialog group-dialog-hidden",
            ),
            html.Div(id="group-status", className="tool-status"),
        ],
        className="tool-panel",
    )


def deck_control(dialog: str | None = None, selected_deck: str | None = runtime.NONE_DECK, state=None) -> html.Div:
    state = _state(state)
    current_decks = state.available_decks()
    dialog_options = [
        {"label": deck, "value": deck}
        for deck in current_decks
        if (dialog == "add" and deck not in state.enabled_decks)
        or (dialog in {"remove", "focus"} and deck in state.enabled_decks)
    ]
    dialog_title = {"add": "Add deck", "remove": "Remove deck", "focus": "Focus deck"}.get(dialog)
    note = REMOVE_DECK_NOTE if dialog == "remove" else None
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
                options=deck_filter_options(state),
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
                        ] + _dialog_note(note),
                        className="tool-row",
                    ),
                ],
                className="group-dialog" if dialog else "group-dialog group-dialog-hidden",
            ),
        ],
        className="tool-panel compact-panel deck-panel",
    )


def connection_control(card: Flashcard | None, candidate_cards: list[Flashcard], state=None, dialog: str | None = None) -> html.Div:
    """`candidate_cards` are the cards the map shows: the deck focus and the group focus are already applied.

    `state` supplies the runtime constellations (the first layout is built without it: empty list, Delete
    disabled); `dialog` is "delete" while the Delete dialog is open. The dialog state is kept in a store inside this
    panel, because the layout of the server has no store for it.
    """
    constellations = state.constellations if state is not None else []
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
                            html.Button("Delete", id="delete-constellation", n_clicks=0, disabled=not constellations, className="tool-button"),
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
            html.Div(
                [
                    html.Div(
                        [html.Span(item.name), html.Span(f"{len(item.members)} cards", className="group-member-count")],
                        className="group-list-item",
                    )
                    for item in constellations
                ] or [html.Div("No visible constellations.", className="tool-status")],
                className="group-list",
            ),
            html.Div(
                [
                    html.Div("Delete constellation", className="dialog-title"),
                    dcc.Dropdown(
                        id="constellation-select",
                        className="closed-dropdown",
                        options=constellation_options(state) if state is not None else [],
                        placeholder="Select a constellation",
                        clearable=True,
                    ),
                    html.Div(
                        [
                            html.Button("Confirm", id="constellation-dialog-submit", n_clicks=0, className="tool-button"),
                            html.Button("Cancel", id="constellation-dialog-cancel", n_clicks=0, className="tool-button"),
                        ] + _dialog_note(DELETE_CONSTELLATION_NOTE),
                        className="tool-row",
                    ),
                ],
                className="group-dialog" if dialog else "group-dialog group-dialog-hidden",
            ),
            dcc.Store(id="constellation-dialog", data=dialog),
        ],
        className="tool-panel compact-panel",
    )