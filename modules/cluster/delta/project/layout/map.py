"""The 3D map of the cluster module (replaces project/layout/map.py).

Changes against the main file:
  * make_figure takes the view ("space" or "deck"), the entered deck and, for the space view, the card count
    of every deck.
  * Space view: every deck is a small core with a glow that fades out to its border (stacked, nearly
    transparent markers) and grows with the deck's number of cards. Dots have no progress ring.
  * Deck view: the sun at the origin, in the colours of the deck's groups (grey without a group; several
    colours take turns in camera.js); card sizes come from the card's difficulty (easy, medium, hard).
  * One uirevision per view, so switching views resets the camera; the view goes into the figure's meta
    (camera.js keeps the rotation around the sun in the deck view).
"""

import math

import plotly.graph_objects as go
from dash import html

from project.layout.colors import group_color, hex_to_rgb, progress_color
from project.models import Flashcard

NAV_DIM_OPACITY = 0.3
CARD_SIZE = 7
PROGRESS_RATIO = 1.4
DIFFICULTY_SCALE = {"easy": 1.2, "medium": 1.45, "hard": 1.7}
DECK_CORE_SIZE = 6
GLOW_SIZE = 16  # glow diameter of a 13-card deck; it grows with the square root of the card count
GLOW_BASE_CARDS = 13
# (share of the glow diameter, opacity): stacked from the border inwards, so the glow fades out to its border
GLOW_LAYERS = ((1.0, 0.035), (0.86, 0.045), (0.73, 0.055), (0.61, 0.065), (0.5, 0.075), (0.4, 0.085), (0.31, 0.1))
NO_GROUP_COLOR = "#7c8b99"
SUN_SIZE = 16
SUN_GLOW_SIZE = 64
SUN_GLOW_ALPHA = 0.8  # times the glow layer opacities: the sun's ring fades out more than a deck's
SUN_CORE_ALPHA = 0.3  # the dot in the centre fades out much more
DEFAULT_CAMERA = {"eye": {"x": 1.25, "y": 1.25, "z": 1.25}, "up": {"x": 0, "y": 0, "z": 1}, "center": {"x": 0, "y": 0, "z": 0}}


def _rgba(color: str, alpha: float) -> str:
    red, green, blue = hex_to_rgb(color)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def card_size(card: Flashcard | None) -> float:
    """Cards without a difficulty keep the normal size; easy, medium and hard step up."""
    return CARD_SIZE * DIFFICULTY_SCALE.get(card.difficulty if card else None, 1.0)


def glow_size(cards: int) -> float:
    return GLOW_SIZE * math.sqrt(max(cards, 1) / GLOW_BASE_CARDS)


def ui_revision(view: str, entered: str | None = None) -> str:
    return f"cluster:{view}:{entered or ''}"


# phase 1: positions are addressed by their comb_id (was card_id)
def make_figure(
    cards: list[Flashcard],
    selected_id: str | None = None,
    camera: dict | None = None,
    state=None,
    focused_group: str | None = None,
    *,
    preview_id: str | None = None,
    scrolled_id: str | None = None,
    nav_members: set[str] | list[str] | tuple[str, ...] | None = None,
    map_token: str | None = None,
    view: str = "space",
    entered: str | None = None,
    deck_counts: dict[str, int] | None = None,
    sun_colors: list[str] | None = None,
) -> go.Figure:
    if state is None:
        raise TypeError("state is required: pass the UserStateService")
    visible_ids = {card.id for card in cards}
    points = [position for position in state.positions if position.comb_id in visible_ids]
    selected = [position for position in points if position.comb_id == selected_id]
    regular = [position for position in points if position.comb_id != selected_id]
    deck_counts = deck_counts or {}

    # With nav_members omitted, retain the original trace composition and properties.
    if nav_members is None:
        member_regular = regular
        nonmember_regular = []
    else:
        members = set(nav_members)
        member_regular = [point for point in regular if point.comb_id in members]
        nonmember_regular = [point for point in regular if point.comb_id not in members]

    figure = go.Figure()
    position_by_id = {position.comb_id: position for position in points}

    # Invisible corner anchors: pins Plotly's internal camera data-scale to the fixed axis range,
    # so camera.js's centering math stays correct regardless of how many cards are filtered/visible.
    figure.add_trace(
        go.Scatter3d(
            x=[-1.15, 1.15],
            y=[-1.15, 1.15],
            z=[-1.15, 1.15],
            mode="markers",
            marker={"size": 0.001, "opacity": 0},
            hoverinfo="skip",
            showlegend=False,
            name="AnchorBounds",
        )
    )

    # The sun of the deck view: the deck's centroid at the origin, neither selectable nor hoverable. Its colour
    # is the deck's group colour (the oldest group first); meta.colors lets camera.js cycle through several.
    if view == "deck":
        colors = list(sun_colors or []) or [NO_GROUP_COLOR]
        for share, alpha in GLOW_LAYERS:
            layer = [_rgba(color, alpha * SUN_GLOW_ALPHA) for color in colors]
            figure.add_trace(
                go.Scatter3d(
                    x=[0], y=[0], z=[0], mode="markers",
                    marker={"size": SUN_GLOW_SIZE * share, "color": layer[0], "line": {"width": 0}},
                    hoverinfo="skip", showlegend=False, name="Sun glow", meta={"colors": layer},
                )
            )
        core = [_rgba(color, SUN_CORE_ALPHA) for color in colors]
        figure.add_trace(
            go.Scatter3d(
                x=[0], y=[0], z=[0], mode="markers",
                marker={"size": SUN_SIZE, "color": core[0], "line": {"width": 0}},
                hoverinfo="skip", showlegend=False, name="Sun", meta={"colors": core},
            )
        )

    # Draw connection lines between cards
    for link in state.links:
        source = position_by_id.get(link.source_id)
        target = position_by_id.get(link.target_id)
        if source is None or target is None:
            continue
        color = "#9fb3c8"  # links carried a group_id for a group colour that nothing ever set
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

    # A separate overlay emphasizes only the currently scrolled direct link.
    linked = bool(preview_id and scrolled_id) and any(
        {link.source_id, link.target_id} == {preview_id, scrolled_id} for link in state.links
    )
    if linked and preview_id in position_by_id and scrolled_id in position_by_id:
        origin = position_by_id[preview_id]
        target = position_by_id[scrolled_id]
        figure.add_trace(
            go.Scatter3d(
                x=[origin.x, target.x, None],
                y=[origin.y, target.y, None],
                z=[origin.z, target.z, None],
                mode="lines",
                line={"color": "#ffffff", "width": 7},
                hoverinfo="skip",
                showlegend=False,
                name="Navigation link",
            )
        )

    def add_glow(glow_points) -> None:
        # Behind the cores; the glow carries the deck id, so a click on it selects the deck too
        for share, alpha in GLOW_LAYERS:
            figure.add_trace(
                go.Scatter3d(
                    x=[point.x for point in glow_points],
                    y=[point.y for point in glow_points],
                    z=[point.z for point in glow_points],
                    mode="markers",
                    customdata=[point.comb_id for point in glow_points],
                    marker={
                        "size": [glow_size(deck_counts.get(point.comb_id, 1)) * share for point in glow_points],
                        "color": [_rgba(group_color(point.comb_id, state, focused_group), alpha) for point in glow_points],
                        "line": {"width": 0},
                    },
                    hoverinfo="skip",
                    showlegend=False,
                    name="Deck glow",
                )
            )

    def add_regular_traces(regular_points, *, dimmed: bool = False) -> None:
        if not regular_points:
            return
        suffix = " (dimmed)" if dimmed else ""
        if view == "space":
            add_glow(regular_points)
            card_marker = {
                "size": DECK_CORE_SIZE,
                "color": [group_color(point.comb_id, state, focused_group) for point in regular_points],
            }
        else:
            sizes = [card_size(state.card_by_id.get(point.comb_id)) for point in regular_points]
            progress_marker = {
                "size": [size * PROGRESS_RATIO for size in sizes],
                "color": [progress_color(point.comb_id, state) for point in regular_points],
            }
            card_marker = {
                "size": sizes,
                "color": [group_color(point.comb_id, state, focused_group) for point in regular_points],
            }
            if dimmed:
                progress_marker["opacity"] = NAV_DIM_OPACITY
            figure.add_trace(
                go.Scatter3d(
                    x=[point.x for point in regular_points],
                    y=[point.y for point in regular_points],
                    z=[point.z for point in regular_points],
                    mode="markers",
                    marker=progress_marker,
                    hoverinfo="skip",
                    showlegend=False,
                    name=f"Card progress{suffix}",
                )
            )
        if dimmed:
            card_marker["opacity"] = NAV_DIM_OPACITY
        figure.add_trace(
            go.Scatter3d(
                x=[point.x for point in regular_points],
                y=[point.y for point in regular_points],
                z=[point.z for point in regular_points],
                mode="markers",
                customdata=[point.comb_id for point in regular_points],
                text=[state.card_by_id[point.comb_id].question for point in regular_points],
                hovertemplate="%{text}<extra></extra>",
                marker=card_marker,
                name=f"{'Decks' if view == 'space' else 'Cards'}{suffix}",
            )
        )

    add_regular_traces(member_regular)
    add_regular_traces(nonmember_regular, dimmed=True)

    # Draw selected card with highlight
    if selected:
        point = selected[0]
        if view == "space":
            add_glow([point])
            ring = {"size": 15, "color": "rgba(255, 255, 255, 0.55)"}
            core_size = 11
        else:
            size = card_size(state.card_by_id.get(point.comb_id))
            ring = {"size": max(13, size) * PROGRESS_RATIO, "color": progress_color(point.comb_id, state)}
            core_size = max(13, size)
        figure.add_trace(
            go.Scatter3d(
                x=[point.x],
                y=[point.y],
                z=[point.z],
                mode="markers",
                marker=ring,
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
                customdata=[point.comb_id],
                text=[state.card_by_id[point.comb_id].question],
                hovertemplate="%{text}<extra></extra>",
                marker={"size": core_size, "color": group_color(point.comb_id, state, focused_group)},
                name="Selected",
            )
        )

    if preview_id and preview_id in position_by_id:
        preview = position_by_id[preview_id]
        figure.add_trace(
            go.Scatter3d(
                x=[preview.x],
                y=[preview.y],
                z=[preview.z],
                mode="markers",
                marker={"symbol": "cross", "size": 18, "color": "#ffffff"},
                hoverinfo="skip",
                showlegend=False,
                name="Navigation preview",
            )
        )

    figure.update_layout(
        uirevision=ui_revision(view, entered),
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
        meta={"view": view, "map_token": map_token},
    )
    if camera:
        figure.update_layout(scene_camera=camera)
    return figure


def color_legend() -> html.Div:
    return html.Div(
        [
            html.Div("Card's ring colors", className="card-label"),
            html.Div([html.Span(className="legend-swatch unread"), html.Span("unopened")], className="legend-item"),
            html.Div([html.Span(className="legend-swatch review"), html.Span("review")], className="legend-item"),
            html.Div([html.Span(className="legend-swatch developing"), html.Span("developing")], className="legend-item"),
            html.Div([html.Span(className="legend-swatch learned"), html.Span("learned")], className="legend-item"),
        ],
        className="color-legend",
    )
