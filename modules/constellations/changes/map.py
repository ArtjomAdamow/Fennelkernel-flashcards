import plotly.graph_objects as go
from dash import html

from flashcards_app.models import Flashcard
from flashcards_app.visualization.colors import group_color, progress_color


# phase 1: positions are addressed by their comb_id (was card_id)
def make_figure(
    cards: list[Flashcard],
    selected_id: str | None = None,
    camera: dict | None = None,
    state=None,
    focused_group: str | None = None,
    *,
    preview_id: str | None = None,
    nav_members: set[str] | list[str] | tuple[str, ...] | None = None,
    map_token: str | None = None,
) -> go.Figure:
    if state is None:
        raise TypeError("state is required: pass the UserStateService")
    visible_ids = {card.id for card in cards}
    points = [position for position in state.positions if position.comb_id in visible_ids]
    selected = [position for position in points if position.comb_id == selected_id]
    regular = [position for position in points if position.comb_id != selected_id]

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

    def add_regular_traces(regular_points, *, dimmed: bool = False) -> None:
        if not regular_points:
            return
        progress_marker = {
            "size": 7 * 1.4,
            "color": [progress_color(point.comb_id, state) for point in regular_points],
        }
        card_marker = {
            "size": 7,
            "color": [group_color(point.comb_id, state, focused_group) for point in regular_points],
        }
        if dimmed:
            progress_marker["opacity"] = 0.5
            card_marker["opacity"] = 0.5
        suffix = " (dimmed)" if dimmed else ""
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
                name=f"Cards{suffix}",
            )
        )

    add_regular_traces(member_regular)
    add_regular_traces(nonmember_regular, dimmed=True)

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
                    "color": progress_color(point.comb_id, state),
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
                customdata=[point.comb_id],
                text=[state.card_by_id[point.comb_id].question],
                hovertemplate="%{text}<extra></extra>",
                marker={"size": 13, "color": group_color(point.comb_id, state, focused_group)},
                name="Selected",
            )
        )

    if preview_id and preview_id != selected_id and preview_id in position_by_id:
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
    if map_token is not None:
        figure.update_layout(meta={"map_token": map_token})
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
