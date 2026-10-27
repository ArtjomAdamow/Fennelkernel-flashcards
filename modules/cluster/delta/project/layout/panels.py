"""Panels of the cluster module (replaces project/layout/panels.py).

Changes against the main file:
  * deck_control (Add, Remove, Focus, All, Reset) and deck_filter_options are gone: choice_control is the
    dialog of the top bar's choice button, a checkbox list: all decks (Decks, decks view), the topics of the
    entered deck (Topics, topics view) or the cards of the entered topic (Cards, cards view).
  * position_control is gone: the user no longer changes positions (the state keeps set_position for the
    model-calculated positions of the helper module).
  * deck_panel and topic_panel show a selected deck or topic (its description); overview_panel shows the
    dendrogram of the view when no dot is selected.
  * difficulty_control can be hidden (a deck or a topic has nothing to rate).
  * Connect and Disconnect open a dialog with the dropdown (as in the main project since 2026-10-22): Connect
    lists the dots not yet connected to the selected one, Disconnect only the connected ones; the dialog's state
    lives in the panel's `link-dialog` store, like the Delete dialog's.
  * The cut-off line of the dendrogram is a vertical slider of its own (cutoff_control, `cutoff-slider`) in the
    card's window, left of the card panel, shown only while no dot is selected; overview_panel draws the line
    across the dendrogram. The progress slider (difficulty_control, `difficulty-slider`) is shown for a selected
    card only (2026-10-27, roadmap step 26; until then one slider had both roles).
  * Groups panel in the topics and cards views: Focus opens a checklist of the groups plus "No group"
    (dialog-group-checklist, all checked by default), like the Cards dialog, instead of the one-group dropdown;
    the counts cover the view's dots only (ViewRouter.group_count). The decks view keeps the dropdown.
  * Connections panel in the topics view (2026-10-27, roadmap step 29): only the Navigation button, with its
    dialog to the right of it; Connect, Disconnect, Delete, the constellation list and their dialogs stay in the
    layout hidden (they are callback inputs). Every selected topic counts as a member there: the deck's topics
    are navigated as one constellation, connected or not.
"""

import dash_daq as daq
from dash import dcc, html

from project.layout.dendrogram import dendrogram_figure
from project.models import Flashcard
from project.services.views import CARDS, DECKS, TOPICS
from project.store.view_router import NO_GROUP


def _state(state):
    if state is None:
        raise TypeError("state is required: pass the UserStateService")
    return state


# Small notes next to the Confirm button of a dialog
NEW_GROUP_NOTE = "The selected card will be added to the new group."
ADD_TO_GROUP_NOTE = "Membership and color of the previously assigned group will remain until removed from the other group."
DELETE_GROUP_NOTE = "Connections of member cards will remain."
UNCHECK_DECK_NOTE = "Unchecking a deck erases the settings of all its topics and cards: progress, positions, groups and connections."
UNCHECK_TOPIC_NOTE = "Unchecking a topic hides it and its cards and drops the topic's own connections; the cards keep their settings."
UNCHECK_CARD_NOTE = "Unchecking a card only hides it: its progress, position, groups and connections stay."
FOCUS_GROUPS_NOTE = "Unchecking a group only hides its cards; a card in a checked group stays."
NO_GROUP_LABEL = "No group"
CARD_LABEL_LENGTH = 80
# phase 4: constellations
DELETE_CONSTELLATION_NOTE = "Deleting a constellation will disconnect all members"
# The link dialogs' notes; {noun} is the level of the view: deck, topic or card
CONNECT_NOTE = "Lists the {noun}s not yet connected to the selected {noun}."
DISCONNECT_NOTE = "Lists only the {noun}s connected to the selected {noun}."
NOUNS = {DECKS: "deck", TOPICS: "topic", CARDS: "card"}
CHOICE_LABELS = {DECKS: "Decks", TOPICS: "Topics", CARDS: "Cards"}
CUTOFF_HEIGHT = 320  # the vertical cut-off slider's length in px: the dendrogram figure's height (layout.dendrogram)


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
    """A selected deck of the decks view: its name and description; a click (or Enter) enters it."""
    return html.Div(
        [
            html.Div("Deck", className="card-label"),
            html.Div(deck.question, className="card-content"),
            dcc.Markdown(deck.answer, className="deck-description"),
            html.Div("Click this frame or press Enter to open the deck. Backspace unselects it.", className="card-hint"),
        ],
        className="card-panel",
    )


def topic_panel(topic: Flashcard) -> html.Div:
    """A selected topic of the topics view: its name and description; a click (or Enter) enters it."""
    return html.Div(
        [
            html.Div("Topic", className="card-label"),
            html.Div(topic.question, className="card-content"),
            dcc.Markdown(topic.answer, className="deck-description"),
            html.Div("Click this frame or press Enter to open the topic. Backspace unselects it.", className="card-hint"),
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


def cutoff_control(cutoff: float, hidden: bool = False) -> html.Div:
    """The cut-off line of the dendrogram: a vertical slider in the card's window, left of the card panel, shown
    while no dot is selected and the view's dots have connections to cut (`hidden` otherwise; it stays in the
    layout: it is a callback input). The full tree is at the top (100 %); lower the line and the tree falls
    apart below it, on the map as separate constellations. The value stands in a box between the label and the
    rail (black on white); the rail has no marks and no tooltip, and the column is left-aligned and as narrow
    as its label (the user's browser checks, 2026-10-27)."""
    value = int(round(min(1.0, max(0.0, cutoff)) * 100))
    return html.Div(
        [
            html.Label("Cut-off", htmlFor="cutoff-slider", className="card-label cutoff-label"),
            html.Div(f"{value} %", className="cutoff-value"),
            html.Div(
                dcc.Slider(
                    id="cutoff-slider",
                    min=0,
                    max=100,
                    step=1,
                    value=value,
                    vertical=True,
                    verticalHeight=CUTOFF_HEIGHT,
                    marks=None,  # an explicit None: no marks (left out, Dash generates them)
                ),
                className="cutoff-slider",
            ),
        ],
        className="cutoff-control",
        style={"display": "none"} if hidden else None,
    )


def difficulty_control(card: Flashcard | None, state=None, hidden: bool = False) -> html.Div:
    """The progress slider of the selected card, shown for a selected card only: hidden with nothing selected and
    when `hidden` (a selected deck or topic has nothing to rate). It stays in the layout: it is a callback
    input."""
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
        # The slider stays in the layout (it is a callback input); it is shown for a selected card only
        style={"display": "none"} if hidden or card is None else None,
    )


def group_control(card: Flashcard | None, dialog: str | None = None, state=None, focused_group: str | None = None) -> html.Div:
    state = _state(state)
    # Topics and cards views: Focus is a checklist of the groups (like the Cards dialog), and the counts cover the
    # view's dots
    checklist_view = getattr(state, "view", DECKS) != DECKS
    focus_checklist = checklist_view and dialog == "focus"

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
        # Always in the layout (a callback state); shown only for Focus in the topics and cards views
        dcc.Checklist(
            id="dialog-group-checklist",
            options=[{"label": group.name, "value": group.id} for group in state.groups] + [{"label": NO_GROUP_LABEL, "value": NO_GROUP}],
            value=state.checked_groups() if checklist_view else [],
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
    """The top bar's choice button: Decks, Topics or Cards, by the view."""
    return CHOICE_LABELS.get(view, CHOICE_LABELS[DECKS])


def _short_label(text: str) -> str:
    text = " ".join(text.replace("`", "").replace("**", "").split())
    return text if len(text) <= CARD_LABEL_LENGTH else text[: CARD_LABEL_LENGTH - 1] + "…"


def _card_label(card: Flashcard) -> str:
    return _short_label(card.question)


def choice_control(dialog_open: bool = False, state=None) -> html.Div:
    """The dialog of the choice button, a checkbox list; Confirm applies the changes.

    Decks view: every deck (checked = loaded and shown; all on a fresh start). Topics view: the topics of the
    entered deck (checked = loaded and shown; all on a fresh deck). Cards view: the cards of the entered topic
    (checked = shown; all on a fresh deck). It always stays in the layout, hidden while closed: its checklist is
    read by the callback.
    """
    state = _state(state)
    if state.view == CARDS:
        options = [{"label": _card_label(card), "value": card.id} for card in state.deck_cards()]
        value = state.shown_cards()
        note = UNCHECK_CARD_NOTE
    elif state.view == TOPICS:
        options = [{"label": _short_label(topic.name), "value": topic.dot_id} for topic in state.deck_topics()]
        value = state.checked_topics()
        note = UNCHECK_TOPIC_NOTE
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
    view: str = DECKS,
    link_dialog: str | None = None,
) -> html.Div:
    """Connections panel, retaining its existing positional-compatible Delete flow; `link_dialog` is None,
    "connect" or "disconnect" (the open Connect or Disconnect dialog).

    In the topics view (`view == TOPICS`) the panel is reduced to the Navigation button with its dialog to the
    right of it: Connect, Disconnect, Delete, the constellation list and their dialogs stay in the layout hidden
    (they are callback inputs), and every selected topic is a member (`data-member`), since the deck's topics
    are navigated as one constellation, connected or not."""
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
    topics_only = view == TOPICS
    is_member = bool(card and (topics_only or any(card.id in item.members for item in constellations)))
    noun = NOUNS.get(view, NOUNS[CARDS])
    options = link_options(card, candidate_cards, state, link_dialog)
    has_links = bool(card and state is not None and any(card.id in (link.source_id, link.target_id) for link in state.links))
    link_note = (DISCONNECT_NOTE if link_dialog == "disconnect" else CONNECT_NOTE).format(noun=noun)
    hidden = {"display": "none"} if topics_only else None
    navigation_dialog_box = html.Div(
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
    )
    buttons = [
        html.Button("Connect", id="create-link", n_clicks=0, disabled=card is None, className="tool-button", style=hidden),
        html.Button("Disconnect", id="disconnect-link", n_clicks=0, disabled=not has_links, className="tool-button", style=hidden),
        html.Button("Delete", id="delete-constellation", n_clicks=0, disabled=not constellations, className="tool-button", style=hidden),
        html.Button("Navigation", id="navigation-open", n_clicks=0, className="tool-button"),
    ]
    if topics_only:
        buttons.append(navigation_dialog_box)  # the dialog to the right of the button
    return html.Div(
        [
            html.Div("Connections", className="card-label"),
            html.Div(
                [html.Div(buttons, className="connection-buttons navigation-row" if topics_only else "connection-buttons")],
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
                className="group-dialog" if link_dialog and not topics_only else "group-dialog group-dialog-hidden",
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
                style=hidden,
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
                className="group-dialog" if dialog and not topics_only else "group-dialog group-dialog-hidden",
            ),
        ]
        + ([] if topics_only else [navigation_dialog_box])
        + [
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
