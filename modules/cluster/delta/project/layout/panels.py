"""Panels of the cluster module (replaces project/layout/panels.py).

Changes against the main file:
  * deck_control (Add, Remove, Focus, All, Reset) and deck_filter_options are gone: choice_control is the
    dialog of the top bar's choice button, a checkbox list: all decks (Decks, space view) or the cards of the
    entered deck (Cards, deck view).
  * position_control is gone: the user no longer changes positions (the state keeps set_position for the
    model-calculated positions of the helper module).
  * deck_panel shows a selected deck (its description); overview_panel shows the dendrogram of the view
    when no dot is selected.
  * difficulty_control can be hidden (the space view has nothing to rate).
  * Connect and Disconnect open a dialog with the dropdown (as in the main project since 2026-10-22): Connect
    lists the dots not yet connected to the selected one, Disconnect only the connected ones; the dialog's state
    lives in the panel's `link-dialog` store, like the Delete dialog's.
  * With no dot selected the progress slider becomes the cut-off line of the dendrogram (cutoff_control), and
    overview_panel draws that line across the dendrogram.
  * Groups panel in the deck view: Focus opens a checklist of the groups plus "No group" (dialog-group-checklist,
    all checked by default), like the Cards dialog, instead of the one-group dropdown; the counts cover the
    entered deck's cards only (ViewRouter.group_count). The space view keeps the dropdown.
"""

import dash_daq as daq
from dash import dcc, html

from project.layout.dendrogram import dendrogram_figure
from project.models import Flashcard
from project.store.view_router import NO_GROUP


def _state(state):
    if state is None:
        raise TypeError("state is required: pass the UserStateService")
    return state


# Small notes next to the Confirm button of a dialog
NEW_GROUP_NOTE = "The selected card will be added to the new group."
ADD_TO_GROUP_NOTE = "Membership and color of the previously assigned group will remain until removed from the other group."
DELETE_GROUP_NOTE = "Connections of member cards will remain."
UNCHECK_DECK_NOTE = "Unchecking a deck erases the settings of all its cards: progress, positions, groups and connections."
UNCHECK_CARD_NOTE = "Unchecking a card only hides it: its progress, position, groups and connections stay."
FOCUS_GROUPS_NOTE = "Unchecking a group only hides its cards; a card in a checked group stays."
NO_GROUP_LABEL = "No group"
CARD_LABEL_LENGTH = 80
# phase 4: constellations
DELETE_CONSTELLATION_NOTE = "Deleting a constellation will disconnect all members"
# The link dialogs' notes; {noun} is "deck" in the space view and "card" in the deck view
CONNECT_NOTE = "Lists the {noun}s not yet connected to the selected {noun}."
DISCONNECT_NOTE = "Lists only the {noun}s connected to the selected {noun}."


def _dialog_note(text):
    return [html.Span(text, className="dialog-note")] if text else []


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


def deck_panel(deck: Flashcard) -> html.Div:
    """A selected deck of the space view: its name and description; a click (or Enter) enters it."""
    return html.Div(
        [
            html.Div("Deck", className="card-label"),
            html.Div(deck.question, className="card-content"),
            dcc.Markdown(deck.answer, className="deck-description"),
            html.Div("Click this frame or press Enter to open the deck. Backspace unselects it.", className="card-hint"),
        ],
        className="card-panel",
    )


def overview_panel(
    title: str, forest, label_of: dict[str, str], hint: str, subtitle: str | None = None, cut: tuple[float, int] | None = None
) -> html.Div:
    """No dot selected: the dendrogram of the view's connections (empty without connections). `cut` is the
    cut-off line (its height, the full tree's merges): drawn across the dendrogram, even when the line has cut
    every connection away."""
    if forest or cut:
        body = dcc.Graph(
            figure=dendrogram_figure(forest, label_of, cut),
            config={"displayModeBar": False},
            className="dendrogram-graph",
        )
    else:
        body = html.P("No connections yet: connected dots grow the dendrogram.", className="empty-state")
    return html.Div(
        [html.Div(title, className="card-label")]
        + ([html.Div(subtitle, className="deck-description")] if subtitle else [])
        + [body, html.Div(hint, className="card-hint")],
        className="card-panel overview-panel",
    )


def cutoff_control(cutoff: float) -> html.Div:
    """The slider as the cut-off line of the dendrogram while no dot is selected (the same slider id: it is a
    callback input). 100 % is the full tree; lower it and the tree falls apart below the line, on the map as
    separate constellations. The value shows in the slider's box as a percentage."""
    value = int(round(min(1.0, max(0.0, cutoff)) * 100))
    return html.Div(
        [
            html.Label("Cut-off line", htmlFor="difficulty-slider", className="card-label"),
            html.Div(
                dcc.Slider(
                    id="difficulty-slider",
                    min=0,
                    max=100,
                    step=1,
                    value=value,
                    disabled=False,
                    marks={
                        0: {"label": "0 %", "style": {"color": "#ffffff"}},
                        50: {"label": "50 %", "style": {"color": "#ffffff"}},
                        100: {"label": "full tree", "style": {"color": "#ffffff"}},
                    },
                    tooltip={"placement": "bottom", "always_visible": True, "template": "{value} %"},
                ),
                className="progress-slider",
                style={"--progress": f"{value}%"},
            ),
        ],
        className="progress-control",
    )


def difficulty_control(card: Flashcard | None, state=None, hidden: bool = False, cutoff: float | None = None) -> html.Div:
    """The progress slider of the selected card; with no card and a `cutoff`, the cut-off line slider instead."""
    state = _state(state)
    if card is None and cutoff is not None and not hidden:
        return cutoff_control(cutoff)
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
        # The slider stays in the layout (it is a callback input); the space view just does not show it
        style={"display": "none"} if hidden else None,
    )


def group_control(card: Flashcard | None, dialog: str | None = None, state=None, focused_group: str | None = None) -> html.Div:
    state = _state(state)
    # Deck view: Focus is a checklist of the groups (like the Cards dialog), and the counts cover the deck's cards
    deck_view = getattr(state, "view", None) == "deck"
    focus_checklist = deck_view and dialog == "focus"

    def count(group) -> int:
        return state.group_count(group) if hasattr(state, "group_count") else len(group.card_ids)

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
    if focus_checklist:
        dialog_title, note = "Focus groups", FOCUS_GROUPS_NOTE
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
            style={"display": "block" if dialog in {"add", "remove", "delete", "focus"} and not focus_checklist else "none"},
        ),
        # Always in the layout (a callback state); shown only for Focus in the deck view
        dcc.Checklist(
            id="dialog-group-checklist",
            options=[{"label": group.name, "value": group.id} for group in state.groups] + [{"label": NO_GROUP_LABEL, "value": NO_GROUP}],
            value=state.checked_groups() if deck_view else [],
            className="choice-checklist",
            inputClassName="choice-checkbox",
            labelClassName="choice-option",
            style={"display": "block" if focus_checklist else "none"},
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
                        [html.Span(className="group-color-swatch group-color-swatch-shared" if id(group) in shares_members else "group-color-swatch", style={"backgroundColor": group.color, "color": group.color}), html.Span(group.name), html.Span(f"{count(group)} cards", className="group-member-count")],
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


def choice_label(view: str) -> str:
    """The top bar's choice button: Decks in the space view, Cards in the deck view."""
    return "Cards" if view == "deck" else "Decks"


def _card_label(card: Flashcard) -> str:
    text = " ".join(card.question.replace("`", "").replace("**", "").split())
    return text if len(text) <= CARD_LABEL_LENGTH else text[: CARD_LABEL_LENGTH - 1] + "…"


def choice_control(dialog_open: bool = False, state=None) -> html.Div:
    """The dialog of the choice button, a checkbox list; Confirm applies the changes.

    Space view: every deck (checked = loaded and shown). Deck view: the cards of the entered deck (checked =
    shown). Nothing is checked on a fresh start. It always stays in the layout, hidden while closed: its
    checklist is read by the callback.
    """
    state = _state(state)
    if state.view == "deck":
        options = [{"label": _card_label(card), "value": card.id} for card in state.deck_cards()]
        value = state.shown_cards()
        note = UNCHECK_CARD_NOTE
    else:
        options = [{"label": name, "value": name} for name in state.available_decks()]
        value = [name for name in state.available_decks() if name in state.enabled_decks]
        note = UNCHECK_DECK_NOTE
    return html.Div(
        [
            html.Div(choice_label(state.view), className="dialog-title"),
            dcc.Checklist(
                id="choice-checklist",
                options=options,
                value=value,
                className="choice-checklist",
                inputClassName="choice-checkbox",
                labelClassName="choice-option",
            ),
            html.Div(
                [
                    html.Button("Confirm", id="choice-dialog-submit", n_clicks=0, className="tool-button"),
                    html.Button("Cancel", id="choice-dialog-cancel", n_clicks=0, className="tool-button"),
                ] + _dialog_note(note),
                className="tool-row",
            ),
        ],
        className="choice-dialog" if dialog_open else "choice-dialog choice-dialog-hidden",
    )


def navigation_options() -> list[dict[str, str]]:
    """Modes available in the Navigation dialog."""
    return [
        {"label": "By card order", "value": "card_order"},
        {"label": "Within constellation", "value": "constellation"},
    ]


def navigation_readout(card: Flashcard | None = None) -> html.Div:
    """Preview question and id; hidden when no card is being previewed."""
    if card is None:
        return html.Div(id="nav-preview", className="nav-preview nav-preview-hidden")
    return html.Div(
        [
            html.Div("Keyboard preview", className="card-label"),
            dcc.Markdown(card.question, className="nav-preview-question"),
            html.Div(card.id, className="nav-preview-id"),
        ],
        id="nav-preview",
        className="nav-preview",
    )


def link_options(card, candidate_cards, state, link_dialog):
    """Connect: the visible dots not connected to the selected one. Disconnect: the ones connected to it."""
    if card is None or state is None or link_dialog not in {"connect", "disconnect"}:
        return []
    connected = {
        link.target_id if link.source_id == card.id else link.source_id
        for link in state.links
        if card.id in (link.source_id, link.target_id)
    }
    return [
        {"label": other.question[:55], "value": other.id}
        for other in candidate_cards
        if other.id != card.id and ((other.id in connected) == (link_dialog == "disconnect"))
    ]


def connection_control(
    card: Flashcard | None,
    candidate_cards: list[Flashcard],
    state=None,
    dialog: str | None = None,
    navigation=None,
    view: str = "space",
    link_dialog: str | None = None,
) -> html.Div:
    """Connections panel, retaining its existing positional-compatible Delete flow; `link_dialog` is None,
    "connect" or "disconnect" (the open Connect or Disconnect dialog)."""
    constellations = state.constellations if state is not None else []
    navigation = navigation if isinstance(navigation, dict) else {}
    mode = navigation.get("mode", "card_order")
    navigation_dialog = navigation.get("dialog") == "navigation"
    message = navigation.get("message")
    message_text = {
        "unconnected": "Navigation with arrow keys within constellations toggled on.",
        "hit_space": "Hit Space key to start navigation",
    }.get(message, "")
    preview_card = navigation.get("preview_card")
    if navigation.get("preview_id") == (card.id if card else None):
        preview_card = None
    is_member = bool(card and any(card.id in item.members for item in constellations))
    noun = "deck" if view == "space" else "card"
    options = link_options(card, candidate_cards, state, link_dialog)
    has_links = bool(card and state is not None and any(card.id in (link.source_id, link.target_id) for link in state.links))
    link_note = (DISCONNECT_NOTE if link_dialog == "disconnect" else CONNECT_NOTE).format(noun=noun)
    return html.Div(
        [
            html.Div("Connections", className="card-label"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Button("Connect", id="create-link", n_clicks=0, disabled=card is None, className="tool-button"),
                            html.Button("Disconnect", id="disconnect-link", n_clicks=0, disabled=not has_links, className="tool-button"),
                            html.Button("Delete", id="delete-constellation", n_clicks=0, disabled=not constellations, className="tool-button"),
                            html.Button("Navigation", id="navigation-open", n_clicks=0, className="tool-button"),
                        ],
                        className="connection-buttons",
                    ),
                ],
                className="connection-actions",
            ),
            html.Div(
                [
                    html.Div(f"Disconnect from a {noun}" if link_dialog == "disconnect" else f"Connect to a {noun}", className="dialog-title"),
                    dcc.Dropdown(
                        id="link-target",
                        className="closed-dropdown",
                        options=options,
                        placeholder=f"Select a {noun}",
                        clearable=True,
                    ),
                    html.Div(
                        [
                            html.Button("Confirm", id="link-dialog-submit", n_clicks=0, className="tool-button"),
                            html.Button("Cancel", id="link-dialog-cancel", n_clicks=0, className="tool-button"),
                        ] + _dialog_note(link_note),
                        className="tool-row",
                    ),
                ],
                className="group-dialog" if link_dialog else "group-dialog group-dialog-hidden",
            ),
            html.Div(
                [
                    html.Div(
                        [html.Span(item.name), html.Span(f"{len(item.members)} {noun}s", className="group-member-count")],
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
            html.Div(
                [
                    html.Div("Navigation", className="dialog-title"),
                    dcc.Dropdown(
                        id="navigation-select",
                        className="closed-dropdown",
                        options=navigation_options(),
                        value=mode,
                        clearable=False,
                    ),
                    html.Div(
                        [
                            html.Button("Confirm", id="navigation-dialog-submit", n_clicks=0, className="tool-button"),
                            html.Button("Cancel", id="navigation-dialog-cancel", n_clicks=0, className="tool-button"),
                        ],
                        className="tool-row",
                    ),
                ],
                className="group-dialog" if navigation_dialog else "group-dialog group-dialog-hidden",
            ),
            html.Div(message_text, id="nav-message", className="tool-status nav-message"),
            navigation_readout(preview_card),
            html.Div(
                id="nav-config",
                hidden=True,
                **{
                    "data-mode": mode,
                    "data-preview": "1" if preview_card is not None else "",
                    "data-selected": "1" if card is not None else "",
                    "data-member": "1" if is_member else "",
                    "data-view": view,
                },
            ),
            dcc.Store(id="constellation-dialog", data=dialog),
            dcc.Store(id="link-dialog", data=link_dialog),
        ],
        className="tool-panel compact-panel",
    )
