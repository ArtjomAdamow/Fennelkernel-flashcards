"""The back of the card panel in the helper module: how well the difficulty model D1 does
(services.difficulty_model.DifficultyReport), shown while nothing is selected after Enter or a click on the panel.
The decks view shows the whole course; the topics view shows the entered deck's part only (its rated quizzes, out
of fold under the course-wide model, and its predicted quizzes); the cards view shows the entered topic's counts
and predictions with the deck's metrics (about two rated quizzes per topic are too few to measure).

* A table of the key scores, D1 as mean ± sd over the repeats, next to the two baselines (always "easy", and the
  similarity baseline as a classifier); it is also the table view of the numbers.
* The confusion matrix of the rated quizzes, out of fold: rows are the true level, columns the predicted one, each
  row's shares, so the diagonal is the recall of each level. One hue, dark for 0 and light for 1, on the dark panel.
* The shares of the levels: the rated quizzes (training) next to the predicted unrated quizzes (test, no labels).

Colours: the sequential ramp and the two series colours are the dataviz reference steps for a dark surface,
validated against the panel's background; the levels are named on the axes, so no colour carries them alone.
"""

from typing import Optional

import plotly.graph_objects as go
from dash import dcc, html

from project.services.difficulty_model import LEVELS, DifficultyReport

INK = "#f7f2e8"
MUTED = "#9fb3c8"
GRID = "rgba(247, 242, 232, 0.12)"
DARK_INK = "#071827"  # the numbers on the light cells of the matrix
SEQUENTIAL = [[0.0, "#0d366b"], [0.5, "#3987e5"], [1.0, "#cde2fb"]]  # blue, from near the surface to light
RATED_COLOR = "#3987e5"  # blue: the rated quizzes (training)
PREDICTED_COLOR = "#c98500"  # yellow: the predicted unrated quizzes (test)
FONT = {"color": INK, "family": "DM Mono, monospace", "size": 11}
TABLE_ROWS = (("macro_f1", "macro-F1"), ("balanced_accuracy", "balanced accuracy"), ("kappa", "weighted kappa"), ("accuracy", "accuracy"))
BACK_HINT = "Enter or a click on this frame turns it back to the dendrogram."
CELL = {"padding": "2px 10px 2px 0", "textAlign": "right"}


def _number(value: float) -> str:
    return "–" if value != value else f"{value:.2f}"  # NaN -> dash


def _spread(value: tuple[float, float]) -> str:
    mean, sd = value
    return f"{_number(mean)} ± {_number(sd)}"


def score_table(report: DifficultyReport) -> html.Table:
    """The key scores: D1 (mean ± sd) and the baselines (their means)."""
    baselines = list(report.baselines)
    header = html.Tr(
        [html.Th("", style=CELL)] + [html.Th(name, style={**CELL, "color": MUTED, "fontWeight": "normal"}) for name in ["D1"] + baselines]
    )
    rows = [
        html.Tr(
            [html.Td(label, style={**CELL, "textAlign": "left", "color": MUTED})]
            + [html.Td(_spread(report.metrics[key]), style={**CELL, "color": INK})]
            + [html.Td(_number(report.baselines[name][key][0]), style={**CELL, "color": MUTED}) for name in baselines]
        )
        for key, label in TABLE_ROWS
    ]
    return html.Table([html.Thead(header), html.Tbody(rows)], className="difficulty-scores",
                      style={"borderCollapse": "collapse", "fontFamily": FONT["family"], "fontSize": "0.8rem", "margin": "6px 0"})


def confusion_figure(report: DifficultyReport) -> go.Figure:
    """Rows: the true level, columns: the predicted level, each row's shares (the diagonal is the recall)."""
    shares = report.confusion
    figure = go.Figure(
        go.Heatmap(
            z=shares, x=list(LEVELS), y=list(LEVELS), zmin=0, zmax=1, colorscale=SEQUENTIAL, showscale=False, xgap=2, ygap=2,
            hovertemplate="true %{y}, predicted %{x}: %{z:.0%}<extra></extra>",
        )
    )
    for row, true_level in enumerate(LEVELS):
        for column, predicted_level in enumerate(LEVELS):
            value = float(shares[row][column])
            figure.add_annotation(
                x=predicted_level, y=true_level, text=f"{value:.0%}", showarrow=False,
                font={**FONT, "color": DARK_INK if value > 0.55 else INK},
            )
    figure.update_layout(
        height=210, margin={"l": 64, "r": 8, "t": 8, "b": 40}, paper_bgcolor="rgba(0, 0, 0, 0)", plot_bgcolor="rgba(0, 0, 0, 0)",
        font=FONT, dragmode=False,
        xaxis={"title": {"text": "predicted", "font": {"color": MUTED}}, "side": "bottom", "fixedrange": True},
        yaxis={"title": {"text": "true", "font": {"color": MUTED}}, "autorange": "reversed", "fixedrange": True},
    )
    return figure


def shares_figure(report: DifficultyReport) -> go.Figure:
    """The share of each level: the rated quizzes next to the predicted unrated quizzes (a series without quizzes,
    as in most decks, is left out)."""
    predicted_counts = report.predicted_counts
    total = sum(predicted_counts)
    series = []
    if report.rated:
        series.append((f"rated ({report.rated})", [count / report.rated for count in report.rated_counts], report.rated_counts, RATED_COLOR))
    if total:
        series.append((f"predicted ({total})", [count / total for count in predicted_counts], predicted_counts, PREDICTED_COLOR))
    figure = go.Figure()
    for name, values, counts, color in series:
        figure.add_trace(
            go.Bar(
                x=list(LEVELS), y=values, name=name, marker={"color": color, "cornerradius": 4},
                text=[f"{value:.0%}" for value in values], textposition="outside", textfont={"color": INK},
                customdata=list(counts), hovertemplate=f"{name}, %{{x}}: %{{y:.0%}} (%{{customdata}} quizzes)<extra></extra>",
                cliponaxis=False,
            )
        )
    figure.update_layout(
        height=190, margin={"l": 40, "r": 8, "t": 30, "b": 28}, paper_bgcolor="rgba(0, 0, 0, 0)", plot_bgcolor="rgba(0, 0, 0, 0)",
        font=FONT, dragmode=False, barmode="group", bargap=0.3, bargroupgap=0.1,
        legend={"orientation": "h", "x": 0, "y": 1.18, "font": {"color": MUTED}},
        xaxis={"fixedrange": True},
        yaxis={"tickformat": ".0%", "range": [0, 1], "gridcolor": GRID, "zeroline": False, "fixedrange": True},
    )
    return figure


def _graph(figure: go.Figure, class_name: str) -> dcc.Graph:
    return dcc.Graph(figure=figure, config={"displayModeBar": False}, className=class_name)


def _levels(report: DifficultyReport) -> str:
    easy, medium, hard = report.rated_counts
    return f"{easy} easy, {medium} medium, {hard} hard"


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}zes"


def _subtitle(report: DifficultyReport) -> str:
    run = f"{report.folds} folds × {report.repeats} repeats"
    if report.scope is None:
        return (
            f"All decks: {report.rated} rated quizzes ({_levels(report)}), measured out of fold ({run}); levels by each "
            f"deck's shares. {report.unrated} unrated quizzes predicted; plain flashcards are not rated."
        )
    if report.parent is not None:  # the cards view: the topic's counts, the deck's metrics
        deck = report.parent
        rated = f"its {_count(report.rated, 'rated quiz')} ({_levels(report)})" if report.rated else "no rated quizzes"
        unrated = (
            f"{_count(report.unrated, 'unrated quiz')} ({len(report.predictions)} predicted)" if report.unrated
            else "no unrated quizzes"
        )
        return (
            f"This topic: {rated} and {unrated}. The scores, the matrix and the baselines are the deck's: its {deck.rated} "
            f"rated quizzes ({_levels(deck)}), out of fold in the course's cross-validation ({run}), by the deck's shares; "
            f"a topic's few rated quizzes are too few to measure on their own."
        )
    predicted = f"{report.unrated} unrated quizzes of this deck predicted." if report.unrated else "No unrated quiz in this deck."
    return (
        f"This deck: its {report.rated} rated quizzes ({_levels(report)}), out of fold in the course's cross-validation "
        f"({run}), by the deck's shares. {predicted} The decks view shows all decks."
    )


def metrics_panel(report: DifficultyReport, deck: Optional[str] = None, topic=None) -> html.Div:
    """The back of the card panel: what D1 measured and predicted, for the whole course (the decks view), for the
    entered deck only (`deck`, the topics view) or for the entered topic (`topic`, a TopicInfo with `name` and
    `card_ids`, the cards view: the topic's counts and predictions with the deck's metrics); or why there is
    nothing to show."""
    part = report.for_deck(deck) if deck is not None else report
    scope = f" · {deck}" if deck is not None else " · all decks"
    if topic is not None:
        part = part.for_topic(topic.name, topic.card_ids)
        scope = f" · {deck} › {topic.name}"
    title = html.Div("Difficulty model D1" + scope, className="card-label")
    hint = html.Div(BACK_HINT, className="card-hint")
    style = {"cursor": "pointer"}
    if not part.measured:
        children = [title, html.P(part.note or "No difficulty model.", className="empty-state")]
        if part.predictions:  # a deck without rated quizzes still has its predicted ones
            children.append(_graph(shares_figure(part), "difficulty-shares"))
        return html.Div(children + [hint], className="card-panel overview-panel difficulty-panel", style=style)
    return html.Div(
        [
            title,
            html.Div(_subtitle(part), className="deck-description"),
            score_table(part),
            html.Div("With the deck shares every level keeps its true count, so macro-F1 equals the balanced accuracy.",
                     className="card-hint"),
            html.Div("Rated quizzes: true and predicted level", className="card-label", style={"marginTop": "10px"}),
            _graph(confusion_figure(part), "difficulty-confusion"),
            html.Div("Shares of the levels", className="card-label", style={"marginTop": "6px"}),
            _graph(shares_figure(part), "difficulty-shares"),
            hint,
        ],
        className="card-panel overview-panel difficulty-panel",
        style=style,
    )
