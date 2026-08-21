from pathlib import Path
import time

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html

from flashcards_app.models import CardGroup, CardLink, CardProgress, Flashcard
from flashcards_app.geometry import sphere_positions
from flashcards_app.parser import load_decks
from flashcards_app.state import load_groups, load_links, load_positions, load_progress, save_state

BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "data" / "positions.json"
CARDS = load_decks(BASE_DIR)
POSITIONS = load_positions(STATE_PATH, [card.id for card in CARDS])
PROGRESS = load_progress(STATE_PATH, [card.id for card in CARDS])
GROUPS = load_groups(STATE_PATH, [card.id for card in CARDS])
LINKS = load_links(STATE_PATH, [card.id for card in CARDS])
CARD_BY_ID = {card.id: card for card in CARDS}
POSITION_BY_ID = {position.card_id: position for position in POSITIONS}


def progress_color(card_id: str) -> str:
    progress = PROGRESS[card_id]
    if not progress.read:
        return "#7c8b99"
    if progress.difficulty < 35:
        return "#e76f51"
    if progress.difficulty < 70:
        return "#f5b942"
    return "#69c6a5"


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


def make_figure(cards: list[Flashcard], selected_id: str | None = None, camera: dict | None = None) -> go.Figure:
    visible_ids = {card.id for card in cards}
    points = [position for position in POSITIONS if position.card_id in visible_ids]
    selected = [position for position in points if position.card_id == selected_id]
    regular = [position for position in points if position.card_id != selected_id]

    figure = go.Figure()
    position_by_id = {position.card_id: position for position in points}
    group_by_id = {group.id: group for group in GROUPS}
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
                marker={
                    "size": 7,
                    "color": [progress_color(point.card_id) for point in regular],
                    "opacity": 0.9,
                },
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


def difficulty_control(card: Flashcard | None) -> html.Div:
    is_flipped = bool(card and PROGRESS[card.id].read)
    return html.Div(
        [
            html.Label("Learning progress", htmlFor="difficulty-slider", className="card-label"),
            dcc.Slider(
                id="difficulty-slider",
                min=1,
                max=100,
                step=1,
                value=PROGRESS[card.id].difficulty if card else 1,
                disabled=not is_flipped,
                marks={
                    1: {"label": "review", "style": {"color": "#ffffff"}},
                    50: {"label": "developing", "style": {"color": "#ffffff"}},
                    100: {"label": "learned", "style": {"color": "#ffffff"}},
                },
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
                    html.Button("Stop changing position" if drag_enabled else "Change position", id="toggle-drag", n_clicks=0, disabled=position is None, className="tool-button"),
                    html.Button("Save position", id="save-position", n_clicks=0, disabled=position is None, className="tool-button"),
                ],
                className="position-actions",
            ),
            html.Div(
                [
                    html.Label("X", htmlFor="drag-x"),
                    dcc.Slider(id="drag-x", min=-1, max=1, step=0.001, value=x_value, disabled=not drag_enabled, marks={-1: {"label": "-1", "style": {"color": "#ffffff"}}, 0: {"label": "0", "style": {"color": "#ffffff"}}, 1: {"label": "1", "style": {"color": "#ffffff"}}}),
                    html.Label("Y", htmlFor="drag-y"),
                    dcc.Slider(id="drag-y", min=-1, max=1, step=0.001, value=y_value, disabled=not drag_enabled, marks={-1: {"label": "-1", "style": {"color": "#ffffff"}}, 0: {"label": "0", "style": {"color": "#ffffff"}}, 1: {"label": "1", "style": {"color": "#ffffff"}}}),
                    html.Label("Z", htmlFor="drag-z"),
                    dcc.Slider(id="drag-z", min=-1, max=1, step=0.001, value=z_value, disabled=not drag_enabled, marks={-1: {"label": "-1", "style": {"color": "#ffffff"}}, 0: {"label": "0", "style": {"color": "#ffffff"}}, 1: {"label": "1", "style": {"color": "#ffffff"}}}),
                ],
                className="drag-controls",
            ),
        ],
        className="tool-panel",
    )


def group_control(card: Flashcard | None, dialog: str | None = None) -> html.Div:
    group_options = [{"label": group.name, "value": group.id} for group in GROUPS]
    selected_groups = [group.id for group in GROUPS if card and card.id in group.card_ids]
    dialog_options = [
        {"label": group.name, "value": group.id}
        for group in GROUPS
        if dialog != "remove" or card is None or card.id in group.card_ids
    ]
    dialog_title = {"new": "New group", "add": "Add to group", "remove": "Remove from group", "delete": "Delete group", "focus": "Focus group"}.get(dialog)
    dialog_body = [
        dcc.Input(id="dialog-group-name", type="text", placeholder="Group name", style={"display": "block" if dialog == "new" else "none"}),
        dcc.Input(id="dialog-group-color", type="color", value="#f5b942", style={"display": "block" if dialog == "new" else "none"}),
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
            html.Div("Groups and connections", className="card-label"),
            html.Div(
                [
                    html.Button("New", id="new-group", n_clicks=0, disabled=card is None, className="tool-button"),
                    html.Button("Add", id="add-group", n_clicks=0, disabled=card is None, className="tool-button"),
                    html.Button("Remove", id="remove-group", n_clicks=0, disabled=card is None, className="tool-button"),
                ],
                className="tool-row",
            ),
            html.Div(
                [
                    html.Button("Delete", id="delete-group", n_clicks=0, disabled=card is None, className="tool-button"),
                    html.Button("Focus", id="focus-group", n_clicks=0, disabled=not GROUPS, className="tool-button"),
                    html.Button("All", id="all-groups", n_clicks=0, className="tool-button"),
                ],
                className="tool-row",
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
            html.Div(
                [
                    dcc.Dropdown(
                        id="link-target",
                        className="closed-dropdown",
                        options=[{"label": other.question[:55], "value": other.id} for other in CARDS if not card or other.id != card.id],
                        placeholder="Connect selected card to...",
                        disabled=card is None,
                        clearable=True,
                    ),
                    html.Button("Connect", id="create-link", n_clicks=0, disabled=card is None, className="tool-button"),
                ],
                className="tool-row",
            ),
            html.Div(id="group-status", className="tool-status"),
        ],
        className="tool-panel",
    )


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
app.layout = html.Main(
    [
        html.Header(
            [
                html.Div([html.P("SPATIAL STUDY", className="eyebrow"), html.H1("Arrange what you learn.")]),
                html.Div(
                    [
                        html.Button("Random card", id="random-card", className="random-button", n_clicks=0),
                        html.Button("Reset cards", id="reset-cards", className="reset-button", n_clicks=0),
                    ],
                    className="topbar-actions",
                ),
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
                            className="closed-dropdown",
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
                html.Div(
                    [
                        dcc.Graph(id="sphere", figure=make_figure(CARDS), config={"displayModeBar": False, "scrollZoom": True, "doubleClick": "reset+autosize"}),
                        color_legend(),
                    ],
                    className="map-column",
                ),
                html.Div(
                    [
                        html.Div(id="selected-card", children=card_panel(None), n_clicks=0),
                        html.Div(id="difficulty-control", children=difficulty_control(None)),
                        html.Div(id="position-control", children=position_control(None)),
                        html.Div(id="group-control", children=group_control(None)),
                    ],
                    className="card-column",
                ),
            ],
            className="workspace",
        ),
        dcc.Store(id="selected-id"),
        dcc.Store(id="revealed", data=False),
        dcc.Store(id="drag-enabled", data=False),
        dcc.Store(id="group-dialog", data=None),
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
    Output("group-status", "children"),
    Output("selected-id", "data"),
    Output("revealed", "data"),
    Output("card-count", "children"),
    Output("drag-enabled", "data"),
    Output("keyboard-nav", "value"),
    Output("reset-confirm", "displayed"),
    Output("group-dialog", "data"),
    Output("focused-group", "data"),
    Input("sphere", "clickData"),
    Input("selected-card", "n_clicks"),
    Input("random-card", "n_clicks"),
    Input("deck-filter", "value"),
    Input("difficulty-slider", "value"),
    Input("save-position", "n_clicks"),
    Input("new-group", "n_clicks"),
    Input("create-link", "n_clicks"),
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
    State("selected-id", "data"),
    State("revealed", "data"),
    State("link-target", "value"),
    State("sphere", "relayoutData"),
    State("drag-enabled", "data"),
    State("group-dialog", "data"),
    State("focused-group", "data"),
    State("dialog-group-name", "value"),
    State("dialog-group-color", "value"),
    State("dialog-group-select", "value"),
)
def update_card(click_data, panel_clicks, random_clicks, deck, difficulty, save_position_clicks, new_group_clicks, create_link_clicks, add_group_clicks, remove_group_clicks, delete_group_clicks, focus_group_clicks, all_groups_clicks, dialog_submit_clicks, dialog_cancel_clicks, toggle_drag_clicks, drag_x, drag_y, drag_z, keyboard_nav, reset_clicks, reset_submit_clicks, selected_id, revealed, link_target, relayout_data, drag_enabled, group_dialog, focused_group, dialog_group_name, dialog_group_color, dialog_group_select):
    from dash import ctx
    import random

    cards = [card for card in CARDS if deck == "all" or card.deck == deck]
    if focused_group:
        group = next((item for item in GROUPS if item.id == focused_group), None)
        focused_ids = set(group.card_ids) if group else set()
        cards = [card for card in cards if card.id in focused_ids]
    trigger = ctx.triggered_id
    reset_dialog = False
    next_group_dialog = group_dialog
    next_focused_group = focused_group
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
    elif trigger == "sphere" and click_data and click_data.get("points"):
        selected_id = click_data["points"][0].get("customdata")
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
        LINKS.append(CardLink(selected_id, link_target))
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
        GROUPS.append(CardGroup(group_id, dialog_group_name.strip(), dialog_group_color or "#f5b942", [selected_id]))
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

    if next_focused_group:
        focused_group = next((group for group in GROUPS if group.id == next_focused_group), None)
        focused_ids = set(focused_group.card_ids) if focused_group else set()
        cards = [card for card in cards if card.id in focused_ids]
        if selected_id not in {card.id for card in cards}:
            selected_id = None

    selected_card = CARD_BY_ID.get(selected_id)
    save_state(STATE_PATH, POSITIONS, PROGRESS, GROUPS, LINKS)
    return (
        make_figure(cards, selected_id, (relayout_data or {}).get("scene.camera")),
        card_panel(selected_card, revealed),
        difficulty_control(selected_card),
        position_control(selected_card, bool(drag_enabled)),
        group_control(selected_card, next_group_dialog),
        "Saved" if trigger in {"save-position", "create-link", "group-dialog-submit", "delete-group"} else "",
        selected_id,
        revealed,
        f"{len(cards)} cards mapped",
        bool(drag_enabled),
        "",
        reset_dialog,
        next_group_dialog,
        next_focused_group,
    )


if __name__ == "__main__":
    save_state(STATE_PATH, POSITIONS, PROGRESS, GROUPS, LINKS)
    app.run(debug=False)
