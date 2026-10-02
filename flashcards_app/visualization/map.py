import plotly.graph_objects as go
from dash import html

from flashcards_app import runtime
from flashcards_app.models import Flashcard
from flashcards_app.visualization.colors import group_color, progress_color


def make_figure(cards: list[Flashcard], selected_id: str | None = None, camera: dict | None = None) -> go.Figure:
    visible_ids = {card.id for card in cards}
    points = [position for position in runtime.POSITIONS if position.card_id in visible_ids]
    selected = [position for position in points if position.card_id == selected_id]
    regular = [position for position in points if position.card_id != selected_id]

    figure = go.Figure()
    position_by_id = {position.card_id: position for position in points}
    group_by_id = {group.id: group for group in runtime.GROUPS}

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
    for link in runtime.LINKS:
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
                text=[runtime.CARD_BY_ID[point.card_id].question for point in regular],
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
                text=[runtime.CARD_BY_ID[point.card_id].question],
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
