"""The 3D map of the cluster module (replaces project/layout/map.py).

Changes against the main file:
  * make_figure takes the view ("decks", "topics" or "cards"), the entered dot (the deck, or the topic) and,
    for the decks view, the card count of every deck.
  * Decks view: every deck is a small core with a glow that fades out to its border (stacked, nearly
    transparent markers) and grows with the deck's number of cards. Dots have no progress ring.
  * Topics view: the deck's centroid at the origin, in the colours of the deck's groups (grey without a group;
    several colours take turns in camera.js), and the deck's topic dots at one size; a rest topic (the cards
    that fit no other) is an open circle.
  * Cards view: the surface of the unit sphere the cards sit on, half transparent in the topic's colour (its
    oldest group; grey without one), and the cards as in the main project, sized by the card's difficulty
    (easy, medium, hard). The connections between cards bend along the sphere's surface (great-circle arcs,
    surface_arc) instead of cutting through it; the decks and topics views keep straight lines.
  * One uirevision per view and entered dot, so switching views resets the camera; the view goes into the
    figure's meta for camera.js (the globe and the axis camera in the decks view, the axis camera for a selected
    card in the cards view, the turn around the center elsewhere).
"""

import math

import plotly.graph_objects as go
from dash import html

from project.layout.colors import group_color, hex_to_rgb, progress_color
from project.models import Flashcard
from project.services.views import CARDS, DECKS, TOPICS

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
TOPIC_SIZE = 10  # the one size of the topic dots (a size by card count is the natural next step)
TOPIC_SELECTED_SIZE = 13
REST_SYMBOL = "circle-open"  # the rest topic is set apart from the other topics
SURFACE_ALPHA = 0.5  # the cards view's sphere
SURFACE_STEPS = 24  # the sphere's mesh: this many steps around and half as many from pole to pole
ARC_STEP = math.radians(5)  # a connection along the surface is sampled every 5 degrees of its arc
ARC_LIFT = 1.01  # the arcs sit a hair above the surface, clear of the mesh's facets
LINK_COLOR = "#9fb3c8"
NAVIGATION_LINK_COLOR = "#ffffff"
CENTROID_SIZE = 16
CENTROID_GLOW_SIZE = 64
CENTROID_GLOW_ALPHA = 0.8  # times the glow layer opacities: the centroid's ring fades out more than a deck's
CENTROID_CORE_ALPHA = 0.3  # the dot in the centre fades out much more
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
    """One camera per view and entered dot: cluster:decks:, cluster:topics:<deck id>, cluster:cards:<topic dot id>."""
    return f"cluster:{view}:{entered or ''}"


def _straight(source, target) -> tuple[list, list, list]:
    return [source.x, target.x], [source.y, target.y], [source.z, target.z]


def surface_arc(source, target, step: float = ARC_STEP, lift: float = ARC_LIFT) -> tuple[list, list, list]:
    """The points (x, y, z lists) of the great-circle arc between two positions on the sphere, sampled every
    `step` radians, a `lift` share above the surface (the radius runs from the source's to the target's).
    Two positions in the same direction give a straight line; opposite positions take any half circle."""
    a = (source.x, source.y, source.z)
    b = (target.x, target.y, target.z)
    radius_a = math.sqrt(sum(value * value for value in a))
    radius_b = math.sqrt(sum(value * value for value in b))
    if radius_a < 1e-9 or radius_b < 1e-9:
        return _straight(source, target)
    unit_a = tuple(value / radius_a for value in a)
    unit_b = tuple(value / radius_b for value in b)
    cosine = max(-1.0, min(1.0, sum(p * q for p, q in zip(unit_a, unit_b))))
    angle = math.acos(cosine)
    if angle < 1e-9:
        return _straight(source, target)
    if math.sin(angle) < 1e-9:
        # Antipodes: no unique great circle; turn through any direction at right angles to the source
        pivot = (0.0, 0.0, 1.0) if abs(unit_a[2]) < 0.9 else (1.0, 0.0, 0.0)
        along = sum(p * q for p, q in zip(unit_a, pivot))
        flat = tuple(p - unit_a[index] * along for index, p in enumerate(pivot))
        length = math.sqrt(sum(value * value for value in flat))
        unit_b, cosine, angle = tuple(value / length for value in flat), 0.0, math.pi / 2
        turn = 2  # two quarter turns: through the pivot to the antipode
    else:
        turn = 1
    sine = math.sin(angle)
    steps = max(1, math.ceil(turn * angle / step))
    xs, ys, zs = [], [], []
    for index in range(steps + 1):
        share = index / steps
        theta = share * turn * angle
        # The slerp of the two unit directions; past a quarter turn it continues the same great circle
        weight_a = math.cos(theta) - math.sin(theta) * cosine / sine
        weight_b = math.sin(theta) / sine
        radius = (radius_a + (radius_b - radius_a) * share) * lift
        xs.append((weight_a * unit_a[0] + weight_b * unit_b[0]) * radius)
        ys.append((weight_a * unit_a[1] + weight_b * unit_b[1]) * radius)
        zs.append((weight_a * unit_a[2] + weight_b * unit_b[2]) * radius)
    return xs, ys, zs


def sphere_surface(color: str, radius: float = 1.0, steps: int = SURFACE_STEPS) -> go.Surface:
    """The surface of the sphere the cards sit on, half transparent in one colour, neither selectable nor
    hoverable."""
    rings = max(2, steps // 2)
    x, y, z = [], [], []
    for row in range(rings + 1):
        polar = math.pi * row / rings
        x.append([radius * math.sin(polar) * math.cos(2 * math.pi * column / steps) for column in range(steps + 1)])
        y.append([radius * math.sin(polar) * math.sin(2 * math.pi * column / steps) for column in range(steps + 1)])
        z.append([radius * math.cos(polar)] * (steps + 1))
    return go.Surface(
        x=x, y=y, z=z,
        surfacecolor=[[0] * (steps + 1) for _ in range(rings + 1)],
        colorscale=[[0, color], [1, color]], cmin=0, cmax=1, showscale=False,
        opacity=SURFACE_ALPHA, hoverinfo="skip", showlegend=False, name="Surface",
        contours={"x": {"highlight": False}, "y": {"highlight": False}, "z": {"highlight": False}},
    )


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
    view: str = DECKS,
    entered: str | None = None,
    deck_counts: dict[str, int] | None = None,
    centroid_colors: list[str] | None = None,
    topic_color: str | None = None,
    rest_ids: set[str] | None = None,
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

    # The centroid of the topics view: the deck's place among its topics, at the origin, neither selectable nor
    # hoverable. Its colour is the deck's group colour (the oldest group first); meta.colors lets camera.js cycle
    # through several.
    if view == TOPICS:
        colors = list(centroid_colors or []) or [NO_GROUP_COLOR]
        for share, alpha in GLOW_LAYERS:
            layer = [_rgba(color, alpha * CENTROID_GLOW_ALPHA) for color in colors]
            figure.add_trace(
                go.Scatter3d(
                    x=[0], y=[0], z=[0], mode="markers",
                    marker={"size": CENTROID_GLOW_SIZE * share, "color": layer[0], "line": {"width": 0}},
                    hoverinfo="skip", showlegend=False, name="Centroid glow", meta={"colors": layer},
                )
            )
        core = [_rgba(color, CENTROID_CORE_ALPHA) for color in colors]
        figure.add_trace(
            go.Scatter3d(
                x=[0], y=[0], z=[0], mode="markers",
                marker={"size": CENTROID_SIZE, "color": core[0], "line": {"width": 0}},
                hoverinfo="skip", showlegend=False, name="Centroid", meta={"colors": core},
            )
        )

    # The cards view: the sphere the cards sit on, in the entered topic's colour
    if view == CARDS:
        figure.add_trace(sphere_surface(topic_color or NO_GROUP_COLOR))

    # A connection's line: along the sphere's surface between two cards, straight between decks or topics
    def link_line(source, target) -> tuple[list, list, list]:
        xs, ys, zs = surface_arc(source, target) if view == CARDS else _straight(source, target)
        return xs + [None], ys + [None], zs + [None]

    # Draw connection lines between the dots
    for link in state.links:
        source = position_by_id.get(link.source_id)
        target = position_by_id.get(link.target_id)
        if source is None or target is None:
            continue
        xs, ys, zs = link_line(source, target)
        figure.add_trace(
            go.Scatter3d(
                x=xs, y=ys, z=zs, mode="lines",
                line={"color": LINK_COLOR, "width": 4},  # links carried a group_id for a colour nothing ever set
                hoverinfo="skip", showlegend=False, name="Connection",
            )
        )

    # A separate overlay emphasizes only the currently scrolled direct link.
    linked = bool(preview_id and scrolled_id) and any(
        {link.source_id, link.target_id} == {preview_id, scrolled_id} for link in state.links
    )
    if linked and preview_id in position_by_id and scrolled_id in position_by_id:
        xs, ys, zs = link_line(position_by_id[preview_id], position_by_id[scrolled_id])
        figure.add_trace(
            go.Scatter3d(
                x=xs, y=ys, z=zs, mode="lines",
                line={"color": NAVIGATION_LINK_COLOR, "width": 7},
                hoverinfo="skip", showlegend=False, name="Navigation link",
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

    rest = set(rest_ids or ())
    trace_names = {DECKS: "Decks", TOPICS: "Topics", CARDS: "Cards"}

    def add_regular_traces(regular_points, *, dimmed: bool = False) -> None:
        if not regular_points:
            return
        suffix = " (dimmed)" if dimmed else ""
        if view == DECKS:
            add_glow(regular_points)
            card_marker = {
                "size": DECK_CORE_SIZE,
                "color": [group_color(point.comb_id, state, focused_group) for point in regular_points],
            }
        elif view == TOPICS:
            # One size for every topic; the rest topic is an open circle. No progress ring.
            card_marker = {
                "size": TOPIC_SIZE,
                "color": [group_color(point.comb_id, state, focused_group) for point in regular_points],
                "symbol": [REST_SYMBOL if point.comb_id in rest else "circle" for point in regular_points],
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
                name=f"{trace_names.get(view, 'Cards')}{suffix}",
            )
        )

    add_regular_traces(member_regular)
    add_regular_traces(nonmember_regular, dimmed=True)

    # Draw selected card with highlight
    if selected:
        point = selected[0]
        if view == DECKS:
            add_glow([point])
            ring = {"size": 15, "color": "rgba(255, 255, 255, 0.55)"}
            core_size = 11
        elif view == TOPICS:
            ring = {"size": 18, "color": "rgba(255, 255, 255, 0.55)"}
            core_size = TOPIC_SELECTED_SIZE
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
                marker={
                    "size": core_size, "color": group_color(point.comb_id, state, focused_group),
                    "symbol": REST_SYMBOL if point.comb_id in rest else "circle",
                },
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
        # The view for camera.js, which starts the view's motion from it
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
