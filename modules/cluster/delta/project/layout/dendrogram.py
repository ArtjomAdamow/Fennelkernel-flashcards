"""Draws the dendrogram of a view (services.dendrogram) as a small 2D Plotly figure, without scipy."""

import plotly.graph_objects as go

from project.services.dendrogram import Node

TREE_GAP = 0.8  # space between two trees, in leaf widths
LABEL_LENGTH = 18
CUT_COLOR = "#e06c75"


def _short(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= LABEL_LENGTH else text[: LABEL_LENGTH - 1] + "…"


def dendrogram_figure(forest: list[Node], label_of: dict[str, str], cut: tuple[float, int] | None = None) -> go.Figure:
    """Leaves left to right in tree order, U-shaped lines at the merge heights, trees side by side. With `cut`
    (the line's height, the full tree's number of merges) a dashed cut-off line crosses the figure, and the
    height axis keeps the full tree's range, so the line stays where it is while the trees below it change."""
    line_x: list = []
    line_y: list = []
    leaf_x: list[float] = []
    leaf_ids: list[str] = []
    cursor = 0.0

    def place(node: Node) -> float:
        nonlocal cursor
        if node.leaf is not None:
            position = cursor
            cursor += 1.0
            leaf_x.append(position)
            leaf_ids.append(node.leaf)
            return position
        left, right = node.children
        left_x = place(left)
        right_x = place(right)
        line_x.extend([left_x, left_x, right_x, right_x, None])
        line_y.extend([left.height, node.height, node.height, right.height, None])
        return (left_x + right_x) / 2

    for tree in forest:
        place(tree)
        cursor += TREE_GAP

    labels = [label_of.get(dot, dot) for dot in leaf_ids]
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(x=line_x, y=line_y, mode="lines", line={"color": "#f5b942", "width": 2}, hoverinfo="skip", name="Merges")
    )
    figure.add_trace(
        go.Scatter(
            x=leaf_x,
            y=[0] * len(leaf_x),
            mode="markers",
            marker={"color": "#9fb3c8", "size": 7},
            customdata=leaf_ids,
            text=labels,
            hovertemplate="%{text}<extra></extra>",
            name="Leaves",
        )
    )
    yaxis = {"title": {"text": "merge"}, "dtick": 1, "rangemode": "tozero", "gridcolor": "rgba(247, 242, 232, 0.12)", "zeroline": False, "fixedrange": True}
    if cut is not None:
        height, top = cut
        right_edge = max(cursor - TREE_GAP, 1.0)
        figure.add_trace(
            go.Scatter(
                x=[-0.5, right_edge - 0.5],
                y=[height, height],
                mode="lines",
                line={"color": CUT_COLOR, "width": 2, "dash": "dash"},
                hoverinfo="skip",
                name="Cut-off",
            )
        )
        yaxis["range"] = [0, top + 1]
    figure.update_layout(
        height=320,
        margin={"l": 34, "r": 10, "t": 10, "b": 110},
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font={"color": "#f7f2e8", "family": "DM Mono, monospace", "size": 12},
        showlegend=False,
        dragmode=False,
        xaxis={
            "tickvals": leaf_x,
            "ticktext": [_short(label) for label in labels],
            "tickangle": -60,
            "showgrid": False,
            "zeroline": False,
            "fixedrange": True,
        },
        yaxis=yaxis,
    )
    return figure
