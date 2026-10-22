"""Offline measures of the helper's models (no Dash, no state): how good the neighbours are, judged by an
independent label (the deck a card belongs to), and the random floor the map shows without a model.

* same_deck_precision: of a card's top-5 neighbours, how many come from the card's own deck, over all cards.
  Empty slots (fewer than 5 neighbours above the minimum score) count as misses. Random neighbours score about 2 %.
* kept_precision: the same over the kept neighbours only (what the user would actually see).
* coverage: the share of cards with at least one neighbour, and the number of different cards that appear as a
  neighbour at all (hub cards show up everywhere; a low number means they do).
* random_floor (B0): the same-deck precision of the k nearest cards at random positions, as the map placed them.
"""

from typing import Callable, Mapping, Sequence

import numpy as np

from project.services.geometry import sphere_positions
from project.services.layout import nearest_in_3d
from project.services.similar import TOP_K


def _card_id(item) -> str:
    return item[0] if isinstance(item, tuple) else item


def same_deck_precision(neighbours: Mapping[str, Sequence], deck_of: Mapping[str, str], k: int = TOP_K) -> float:
    """Mean over all cards of (same-deck neighbours among the first k) / k. NaN without cards."""
    if not neighbours:
        return float("nan")
    hits = [
        sum(deck_of.get(_card_id(item)) == deck_of.get(card_id) for item in list(items)[:k]) / k
        for card_id, items in neighbours.items()
    ]
    return float(np.mean(hits))


def kept_precision(neighbours: Mapping[str, Sequence], deck_of: Mapping[str, str], k: int = TOP_K) -> float:
    """The share of the kept neighbour slots (up to k per card) that are same-deck. NaN without neighbours."""
    kept = [(card_id, _card_id(item)) for card_id, items in neighbours.items() for item in list(items)[:k]]
    if not kept:
        return float("nan")
    return float(np.mean([deck_of.get(other) == deck_of.get(card_id) for card_id, other in kept]))


def coverage(neighbours: Mapping[str, Sequence]) -> tuple[float, int]:
    """(share of cards with at least one neighbour, number of distinct cards that are someone's neighbour)."""
    if not neighbours:
        return float("nan"), 0
    with_neighbour = float(np.mean([len(items) > 0 for items in neighbours.values()]))
    distinct = {_card_id(item) for items in neighbours.values() for item in items}
    return with_neighbour, len(distinct)


def nearest_by_position(ids: Sequence[str], points: np.ndarray, k: int = TOP_K) -> dict[str, list[str]]:
    """Every card's k nearest cards on a map (euclidean), as the map shows them."""
    nearest = nearest_in_3d(np.asarray(points, dtype=float), k)
    return {card_id: [ids[column] for column in nearest[row]] for row, card_id in enumerate(ids)}


def random_floor(
    ids: Sequence[str],
    deck_of: Mapping[str, str],
    seed: int,
    k: int = TOP_K,
    source: Callable = sphere_positions,
) -> float:
    """B0: the same-deck precision of the k nearest cards when all cards sit at random positions."""
    positions = source(list(ids), seed)
    points = np.array([[position.x, position.y, position.z] for position in positions])
    return same_deck_precision(nearest_by_position(list(ids), points, k), deck_of, k)
