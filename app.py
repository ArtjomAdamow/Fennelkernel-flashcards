from pathlib import Path
import time
import uuid

import numpy as np
import dash_daq as daq
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html
from flask import jsonify

from flashcards_app.models import CardGroup, CardLink, CardProgress, Flashcard
from flashcards_app.geometry import sphere_positions
from flashcards_app.parser import load_decks
from flashcards_app.state import load_enabled_decks, load_groups, load_links, load_positions, load_progress, save_state

# Application configuration
BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "data" / "positions.json" # single cards position - random as placeholder
CARDS_DIR = BASE_DIR / "data" / "cards" # preprocessed examples
SERVER_BOOT_ID = uuid.uuid4().hex
NONE_DECK = "None" # this is a workaround to display empty map on startup


def available_decks() -> list[str]:
    return sorted(
        path.stem
        for path in CARDS_DIR.glob("*.md")
        if path.stem.casefold() not in {"readme", NONE_DECK.casefold()} # cannot be loaded: dummy NONE_DECK, readme files
    )


AVAILABLE_DECKS = available_decks()
ENABLED_DECKS = [
    deck
    for deck in load_enabled_decks(STATE_PATH, AVAILABLE_DECKS)
# DELETE?   if deck.casefold() != "readme" # cannot be loaded
]
CARDS = load_decks(CARDS_DIR, ENABLED_DECKS)
POSITIONS = load_positions(STATE_PATH, [card.id for card in CARDS])
PROGRESS = load_progress(STATE_PATH, [card.id for card in CARDS])
GROUPS = load_groups(STATE_PATH, [card.id for card in CARDS])
LINKS = load_links(STATE_PATH, [card.id for card in CARDS])
CARD_BY_ID = {card.id: card for card in CARDS}
POSITION_BY_ID = {position.card_id: position for position in POSITIONS}


def refresh_deck_state() -> None:
    card_ids = [card.id for card in CARDS]
    stored_positions = {position.card_id: position for position in POSITIONS}
    generated_positions = sphere_positions(card_ids, seed=time.time_ns())
    POSITIONS[:] = [stored_positions.get(position.card_id, position) for position in generated_positions]

    stored_progress = dict(PROGRESS)
    PROGRESS.clear()
    PROGRESS.update({card_id: stored_progress.get(card_id, CardProgress(card_id)) for card_id in card_ids})

    valid_ids = set(card_ids)
    for group in GROUPS:
        group.card_ids = [card_id for card_id in group.card_ids if card_id in valid_ids]
    LINKS[:] = [
        link for link in LINKS
        if link.source_id in valid_ids and link.target_id in valid_ids
    ]
    CARD_BY_ID.clear()
    CARD_BY_ID.update({card.id: card for card in CARDS})
    POSITION_BY_ID.clear()
    POSITION_BY_ID.update({position.card_id: position for position in POSITIONS})


def visible_cards(deck: str, focused_group: str | None) -> list[Flashcard]:
    cards = [] if deck in {None, NONE_DECK} else [card for card in CARDS if deck == "all" or card.deck == deck]
    if focused_group:
        group = next((item for item in GROUPS if item.id == focused_group), None)
        focused_ids = set(group.card_ids) if group else set()
        cards = [card for card in cards if card.id in focused_ids]
    return cards


def deck_filter_options() -> list[dict[str, str]]:
    return [{"label": "None", "value": NONE_DECK}, {"label": "All decks", "value": "all"}] + [
        {"label": deck, "value": deck}
        for deck in sorted(ENABLED_DECKS)
    ]

# TO_DO: in this section are some visual finctions, move to frontend_file
def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02x}" for channel in rgb)


def interpolate_color(start: str, end: str, progress: float) -> str:
    start_rgb = hex_to_rgb(start)
    end_rgb = hex_to_rgb(end)
    ratio = max(0.0, min(1.0, progress))
    mixed = tuple(
        round(start_channel + (end_channel - start_channel) * ratio)
        for start_channel, end_channel in zip(start_rgb, end_rgb)
    )
    return rgb_to_hex(mixed)

def progress_color(value_or_card_id: str | int) -> str:
    if isinstance(value_or_card_id, str):
        progress = PROGRESS.get(value_or_card_id)
        if progress is None or not progress.read:
            return "#7c8b99"
        value = progress.difficulty
    else:
        value = int(value_or_card_id)
    value = max(1, min(100, value))
    if value < 35:
        return interpolate_color("#e76f51", "#f5b942", (value - 1) / 34)
    if value < 70:
        return interpolate_color("#f5b942", "#69c6a5", (value - 35) / 35)
    return "#69c6a5"


def group_color(card_id: str) -> str:
    for group in GROUPS:
        if card_id in group.card_ids:
            return group.color
    return "#7c8b99"

# end of frontend block

def choose_random_card(cards: list[Flashcard], progress: dict, rng) -> Flashcard | None:
    if not cards:
        return None

    read_cards = [card for card in cards if progress.get(card.id) and progress[card.id].read]
    candidates = read_cards or cards
    weights = [101 - progress.get(card.id, CardProgress(card.id)).difficulty for card in candidates]
    return rng.choices(candidates, weights=weights, k=1)[0]


def adjacent_card(cards: list[Flashcard], selected_id: str | None, direction: int) -> Flashcard | None:
    if not cards:
        return None
    if selected_id not in {card.id for card in cards}:
        return cards[0 if direction > 0 else -1]
    index = next(index for index, card in enumerate(cards) if card.id == selected_id)
    return cards[(index + direction) % len(cards)]

#more frontend parts

def make_figure(cards: list[Flashcard], selected_id: str | None = None, camera: dict | None = None) -> go.Figure:
    visible_ids = {card.id for card in cards}
    points = [position for position in POSITIONS if position.card_id in visible_ids]
    selected = [position for position in points if position.card_id == selected_id]
    regular = [position for position in points if position.card_id != selected_id]

    figure = go.Figure()
    position_by_id = {position.card_id: position for position in points}
    group_by_id = {group.id: group for group in GROUPS}
    
    # Draw connection lines between cards
    for link in LINKS:
        source = position_by_id.get(link.source_id)
        target = position_by_id.get(link.target_id)
        if source is None or target is None:
            continue
        color = group_by_id.get(link.group_id).color if link.group_id in group_by_id else "#9fb3c8"
        figure.add_trace(
            go.Scatter3d(
                x=[source.x, target.x, None],
                y=[source.y, target.y, None],
                z=[source.z, target.z, None],
                mode="lines",
                line={"color": color, "width": 4},
                hoverinfo="skip",
                showlegend=False,
                name="Connection",
            )
        )
    
    # Draw regular cards
    if regular:
        figure.add_trace(
            go.Scatter3d(
                x=[point.x for point in regular],
                y=[point.y for point in regular],
                z=[point.z for point in regular],
                mode="markers",
                marker={
                    "size": 7 * 1.4,
                    "color": [progress_color(point.card_id) for point in regular],
                },
                hoverinfo="skip",
                showlegend=False,
                name="Card progress",
            )
        )
        figure.add_trace(
            go.Scatter3d(
                x=[point.x for point in regular],
                y=[point.y for point in regular],
                z=[point.z for point in regular],
                mode="markers",
                customdata=[point.card_id for point in regular],
                text=[CARD_BY_ID[point.card_id].question for point in regular],
                hovertemplate="%{text}<extra></extra>",
                marker={
                    "size": 7,
                    "color": [group_color(point.card_id) for point in regular],
                },
                name="Cards",
            )
        )
    
    # Draw selected card with highlight
    if selected:
        point = selected[0]
        figure.add_trace(
            go.Scatter3d(
                x=[point.x],
                y=[point.y],
                z=[point.z],
                mode="markers",
                marker={
                    "size": 13 * 1.4,
                    "color": progress_color(point.card_id),
                },
                hoverinfo="skip",
                showlegend=False,
                name="Selected progress",
            )
        )
        figure.add_trace(
            go.Scatter3d(
                x=[point.x],
                y=[point.y],
                z=[point.z],
                mode="markers",
                customdata=[point.card_id],
                text=[CARD_BY_ID[point.card_id].question],
                hovertemplate="%{text}<extra></extra>",
                marker={"size": 13, "color": group_color(point.card_id)},
                name="Selected",
            )
        )

    figure.update_layout(
        uirevision="spatial-flashcards",
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
    if camera:
        figure.update_layout(scene_camera=camera)
    return figure


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

# end of more frontend parts
# here start control features

def difficulty_control(card: Flashcard | None) -> html.Div:
    is_flipped = bool(card and PROGRESS[card.id].read)
    current_value = PROGRESS[card.id].difficulty if card and card.id in PROGRESS else 1
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
    position = POSITION_BY_ID.get(card.id) if card else None
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
    selected_groups = [group.id for group in GROUPS if card and card.id in group.card_ids]
    dialog_options = [
        {"label": group.name, "value": group.id}
        for group in GROUPS
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
                    html.Button("Focus", id="focus-group", n_clicks=0, disabled=not GROUPS, className="tool-button"),
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
                    for group in GROUPS
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


def deck_control(dialog: str | None = None, selected_deck: str | None = NONE_DECK) -> html.Div:
    current_decks = available_decks()
    dialog_options = [
        {"label": deck, "value": deck}
        for deck in current_decks
        if (dialog == "add" and deck not in ENABLED_DECKS)
        or (dialog in {"remove", "focus"} and deck in ENABLED_DECKS)
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
    candidate_cards = [entry for entry in CARDS if deck == "all" or entry.deck == deck]
    if focused_group:
        group = next((item for item in GROUPS if item.id == focused_group), None)
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


# more frontend

def color_legend() -> html.Div:
    return html.Div(
        [
            html.Div("Card colors", className="card-label"),
            html.Div([html.Span(className="legend-swatch unread"), html.Span("unopened")], className="legend-item"),
            html.Div([html.Span(className="legend-swatch review"), html.Span("review")], className="legend-item"),
            html.Div([html.Span(className="legend-swatch developing"), html.Span("developing")], className="legend-item"),
            html.Div([html.Span(className="legend-swatch learned"), html.Span("learned")], className="legend-item"),
        ],
        className="color-legend",
    )


app = Dash(__name__)
app.title = "Spatial Flashcards"
app.index_string = app.index_string.replace(
    "{%app_entry%}",
    f'<script>window.__SERVER_BOOT_ID__ = "{SERVER_BOOT_ID}";</script>{{%app_entry%}}',
)

# end of frontend

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


@app.callback(
    Output("sphere", "figure"),
    Output("selected-card", "children"),
    Output("difficulty-control", "children"),
    Output("position-control", "children"),
    Output("group-control", "children"),
    Output("connection-control", "children"),
    Output("group-status", "children"),
    Output("selected-id", "data"),
    Output("revealed", "data"),
    Output("card-count", "children"),
    Output("drag-enabled", "data"),
    Output("keyboard-nav", "value"),
    Output("reset-confirm", "displayed"),
    Output("group-dialog", "data"),
    Output("focused-group", "data"),
    Output("deck-control", "children"),
    Output("deck-dialog-state", "data"),
    Output("deck-filter", "options"),
    Input("sphere", "clickData"),
    Input("selected-card", "n_clicks"),
    Input("random-card", "n_clicks"),
    Input("deck-filter", "value"),
    Input("difficulty-slider", "value"),
    Input("save-position", "n_clicks"),
    Input("new-group", "n_clicks"),
    Input("create-link", "n_clicks"),
    Input("disconnect-link", "n_clicks"),
    Input("add-group", "n_clicks"),
    Input("remove-group", "n_clicks"),
    Input("delete-group", "n_clicks"),
    Input("focus-group", "n_clicks"),
    Input("all-groups", "n_clicks"),
    Input("group-dialog-submit", "n_clicks"),
    Input("group-dialog-cancel", "n_clicks"),
    Input("toggle-drag", "n_clicks"),
    Input("drag-x", "value"),
    Input("drag-y", "value"),
    Input("drag-z", "value"),
    Input("keyboard-nav", "value"),
    Input("reset-cards", "n_clicks"),
    Input("reset-confirm", "submit_n_clicks"),
    Input("add-deck", "n_clicks"),
    Input("remove-deck", "n_clicks"),
    Input("focus-deck", "n_clicks"),
    Input("all-decks", "n_clicks"),
    Input("deck-dialog-submit", "n_clicks"),
    Input("deck-dialog-cancel", "n_clicks"),
    State("selected-id", "data"),
    State("revealed", "data"),
    State("link-target", "value"),
    State("sphere", "relayoutData"),
    State("sphere", "hoverData"),
    State("drag-enabled", "data"),
    State("group-dialog", "data"),
    State("focused-group", "data"),
    State("dialog-group-name", "value"),
    State("dialog-group-color", "value"),
    State("dialog-group-select", "value"),
    State("deck-dialog-state", "data"),
    State("deck-dialog-select", "value"),
)
def update_card(
    click_data, panel_clicks, random_clicks, deck, difficulty, save_position_clicks, new_group_clicks,
    create_link_clicks, disconnect_link_clicks, add_group_clicks, remove_group_clicks,
    delete_group_clicks, focus_group_clicks, all_groups_clicks, dialog_submit_clicks, dialog_cancel_clicks,
    toggle_drag_clicks, drag_x, drag_y, drag_z, keyboard_nav, reset_clicks, reset_submit_clicks,
    add_deck_clicks, remove_deck_clicks, focus_deck_clicks, all_decks_clicks, deck_dialog_submit_clicks,
    deck_dialog_cancel_clicks, selected_id, revealed, link_target, relayout_data, hover_data,
    drag_enabled, group_dialog, focused_group, dialog_group_name, dialog_group_color,
    dialog_group_select, deck_dialog_state, deck_dialog_select
):
    from dash import ctx
    import random

    cards = visible_cards(deck, focused_group)
    trigger = ctx.triggered_id
    reset_dialog = False
    next_group_dialog = group_dialog
    next_focused_group = focused_group
    next_deck_dialog = deck_dialog_state
    next_deck = deck
    
    if trigger == "reset-cards":
        reset_dialog = True
    elif trigger == "reset-confirm":
        generated = sphere_positions([card.id for card in CARDS], seed=time.time_ns())
        for position, replacement in zip(POSITIONS, generated):
            position.x, position.y, position.z = replacement.x, replacement.y, replacement.z
        for progress in PROGRESS.values():
            progress.read = False
            progress.difficulty = 1
        GROUPS.clear()
        LINKS.clear()
        selected_id = None
        revealed = False
        drag_enabled = False
        next_focused_group = None
    elif trigger == "add-deck":
        next_deck_dialog = "add"
    elif trigger == "remove-deck":
        next_deck_dialog = "remove"
    elif trigger == "focus-deck":
        next_deck_dialog = "focus"
    elif trigger == "all-decks":
        next_deck = "all"
        next_deck_dialog = None
    elif trigger == "deck-dialog-cancel":
        next_deck_dialog = None
    elif trigger == "deck-dialog-submit" and deck_dialog_select and deck_dialog_state == "add":
        if deck_dialog_select in available_decks() and deck_dialog_select not in ENABLED_DECKS:
            ENABLED_DECKS.append(deck_dialog_select)
            ENABLED_DECKS.sort()
            CARDS[:] = load_decks(CARDS_DIR, ENABLED_DECKS)
            refresh_deck_state()
        next_deck_dialog = None
    elif trigger == "deck-dialog-submit" and deck_dialog_select and deck_dialog_state == "remove":
        if deck_dialog_select in ENABLED_DECKS:
            ENABLED_DECKS.remove(deck_dialog_select)
            CARDS[:] = load_decks(CARDS_DIR, ENABLED_DECKS)
            refresh_deck_state()
            if selected_id and selected_id not in {card.id for card in CARDS}:
                selected_id = None
                revealed = False
            if deck != "all" and deck == deck_dialog_select:
                next_deck = NONE_DECK
        next_deck_dialog = None
    elif trigger == "deck-dialog-submit" and deck_dialog_select and deck_dialog_state == "focus":
        if deck_dialog_select in ENABLED_DECKS:
            next_deck = deck_dialog_select
        next_deck_dialog = None
    elif trigger == "sphere" and click_data and click_data.get("points"):
        hovered_points = (hover_data or {}).get("points", [])
        hovered_id = hovered_points[0].get("customdata") if hovered_points else None
        clicked_id = hovered_id or click_data["points"][0].get("customdata")
        if clicked_id:
            selected_id = clicked_id
            revealed = False
    elif trigger == "selected-card" and selected_id:
        revealed = not revealed
        if revealed and selected_id in PROGRESS:
            PROGRESS[selected_id].read = True
    elif trigger == "random-card" and cards:
        selected = choose_random_card(cards, PROGRESS, random)
        selected_id = selected.id if selected else None
        revealed = False
    elif trigger == "keyboard-nav" and keyboard_nav:
        direction = 1 if keyboard_nav == "next" else -1
        selected = adjacent_card(cards, selected_id, direction)
        selected_id = selected.id if selected else None
        revealed = False
    elif trigger == "difficulty-slider" and selected_id and difficulty is not None:
        PROGRESS[selected_id].difficulty = difficulty
    elif trigger == "save-position" and selected_id and None not in (drag_x, drag_y, drag_z):
        position = POSITION_BY_ID[selected_id]
        position.x = float(drag_x)
        position.y = float(drag_y)
        position.z = float(drag_z)
        drag_enabled = False
    elif trigger == "toggle-drag" and selected_id:
        drag_enabled = not bool(drag_enabled)
    elif trigger in {"drag-x", "drag-y", "drag-z"} and selected_id and None not in (drag_x, drag_y, drag_z):
        position = POSITION_BY_ID[selected_id]
        position.x = float(drag_x)
        position.y = float(drag_y)
        position.z = float(drag_z)
    elif trigger == "new-group" and selected_id:
        next_group_dialog = "new"
    elif trigger == "create-link" and selected_id and link_target and link_target != selected_id:
        exists = any(
            (link.source_id == selected_id and link.target_id == link_target)
            or (link.source_id == link_target and link.target_id == selected_id)
            for link in LINKS
        )
        if not exists:
            LINKS.append(CardLink(selected_id, link_target))
    elif trigger == "disconnect-link" and selected_id and link_target and link_target != selected_id:
        LINKS[:] = [
            link for link in LINKS
            if not (
                (link.source_id == selected_id and link.target_id == link_target)
                or (link.source_id == link_target and link.target_id == selected_id)
            )
        ]
    elif trigger == "add-group" and selected_id:
        next_group_dialog = "add"
    elif trigger == "remove-group" and selected_id:
        next_group_dialog = "remove"
    elif trigger == "focus-group":
        next_group_dialog = "focus"
    elif trigger == "all-groups":
        next_focused_group = None
    elif trigger == "group-dialog-cancel":
        next_group_dialog = None
    elif trigger == "group-dialog-submit" and selected_id and group_dialog == "new" and dialog_group_name:
        group_id = f"group-{len(GROUPS) + 1}"
        group_color_value = (dialog_group_color or {}).get("hex", "#f5b942")
        GROUPS.append(CardGroup(group_id, dialog_group_name.strip(), group_color_value, [selected_id]))
        next_group_dialog = None
    elif trigger == "group-dialog-submit" and selected_id and group_dialog == "add" and dialog_group_select:
        group = next((item for item in GROUPS if item.id == dialog_group_select), None)
        if group and selected_id not in group.card_ids:
            group.card_ids.append(selected_id)
        next_group_dialog = None
    elif trigger == "group-dialog-submit" and selected_id and group_dialog == "remove" and dialog_group_select:
        group = next((item for item in GROUPS if item.id == dialog_group_select), None)
        if group:
            group.card_ids = [card_id for card_id in group.card_ids if card_id != selected_id]
        next_group_dialog = None
    elif trigger == "group-dialog-submit" and group_dialog == "delete" and dialog_group_select:
        GROUPS[:] = [group for group in GROUPS if group.id != dialog_group_select]
        LINKS[:] = [link for link in LINKS if link.group_id != dialog_group_select]
        next_group_dialog = None
    elif trigger == "group-dialog-submit" and group_dialog == "focus" and dialog_group_select:
        next_focused_group = dialog_group_select
        next_group_dialog = None
    elif trigger == "delete-group" and selected_id:
        next_group_dialog = "delete"
    elif trigger == "group-dialog-submit" and group_dialog == "delete" and dialog_group_select:
        GROUPS[:] = [group for group in GROUPS if group.id != dialog_group_select]
        LINKS[:] = [link for link in LINKS if link.group_id != dialog_group_select]
        next_group_dialog = None
    elif trigger == "deck-filter":
        if selected_id not in {card.id for card in cards}:
            selected_id = None
        revealed = False

    cards = visible_cards(next_deck, next_focused_group)
    if next_focused_group:
        focused_group = next((group for group in GROUPS if group.id == next_focused_group), None)
        focused_ids = set(focused_group.card_ids) if focused_group else set()
        cards = [card for card in cards if card.id in focused_ids]
    if selected_id not in {card.id for card in cards}:
        selected_id = None
        revealed = False

    selected_card = CARD_BY_ID.get(selected_id)
    save_state(STATE_PATH, POSITIONS, PROGRESS, GROUPS, LINKS, ENABLED_DECKS)
    return (
        make_figure(cards, selected_id, (relayout_data or {}).get("scene.camera")),
        card_panel(selected_card, revealed),
        difficulty_control(selected_card),
        position_control(selected_card, bool(drag_enabled)),
        group_control(selected_card, next_group_dialog),
        connection_control(selected_card, next_deck or "all", next_focused_group or focused_group),
        "Saved" if trigger in {"save-position", "create-link", "disconnect-link", "group-dialog-submit", "delete-group"} else "",
        selected_id,
        revealed,
        f"{len(cards)} cards mapped",
        bool(drag_enabled),
        "",
        reset_dialog,
        next_group_dialog,
        next_focused_group,
        deck_control(next_deck_dialog, next_deck),
        next_deck_dialog,
        deck_filter_options(),
    )


if __name__ == "__main__":
    save_state(STATE_PATH, POSITIONS, PROGRESS, GROUPS, LINKS)
    app.run(debug=True)
