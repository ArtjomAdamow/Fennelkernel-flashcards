"""The course model of the helper module (no Dash, no state): the pipeline fitted once on all cards, and from it
the positions and connections the cluster module shows.

* Space view: one unit vector per deck (similar.deck_vectors); the layout step (services.layout, k = 3) places
  all decks on the unit sphere at once. The positions are keyed by deck id, the dots of the space state. The
  clustering of the deck vectors (services.clustering) gives the deck connections.
* Deck view, for each deck: the distance from the sun is the card's cosine to its deck vector, scaled linearly so
  that the most central card sits at INNER_RADIUS and the least central at 1 (all equally central: halfway). The
  direction comes from the layout step on the deck's card vectors, centred on the deck (what sets a card apart),
  with the neighbours within the deck (k = 5). The clustering of the deck's card vectors gives its connections.
* The two position sources have the cluster module's signature (ids, seed) -> positions. They are deterministic
  and ignore the seed. An id the model does not know (a card that is not in the course it was fitted on) gets the
  random position of the cluster module's own source for that view, with the seed.
"""

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

import numpy as np

from project.models import CardPosition, Flashcard
from project.services import clustering, layout, similar
from project.services.geometry import sphere_positions
from project.services.positions import INNER_RADIUS, shell_positions

DECK_NEIGHBOURS = 3
CARD_NEIGHBOURS = 5
# The force layout of the 48 decks runs with a smaller step and a weaker push than the card layouts (the defaults
# of services.layout): on the course both measures of the deck layout are better that way (results.csv)
DECK_LAYOUT = {"iterations": 300, "step": 0.05, "repulsion": 0.5}
# A hair above the hard rule's radius: the cluster module checks stored positions against INNER_RADIUS at startup
# (keep_off_the_sun), and a product of floats at exactly 0.25 can come out a rounding error below it
INNER_DISTANCE = INNER_RADIUS + 1e-9
OUTER_RADIUS = 1.0

Point = tuple[float, float, float]


def sun_distances(centrality: np.ndarray, inner: float = INNER_DISTANCE, outer: float = OUTER_RADIUS) -> np.ndarray:
    """Distances from the sun: the most central card (highest cosine to the deck vector) at `inner`, the least
    central at `outer`, linear in between; all equally central cards sit halfway. Never below `inner`."""
    centrality = np.asarray(centrality, dtype=float)
    if centrality.size == 0:
        return centrality
    low, high = float(centrality.min()), float(centrality.max())
    if high - low < 1e-12:
        return np.full(centrality.shape, (inner + outer) / 2)
    return outer - (centrality - low) / (high - low) * (outer - inner)


@dataclass
class DeckLayout:
    """One deck's cards around its sun."""

    name: str
    deck_id: str
    ids: list[str]
    positions: dict[str, Point]
    links: list[tuple[str, str]]
    overlap: float  # top-5 overlap of the 3D directions with the within-deck neighbours (NaN for tiny decks)
    trustworthiness: float


class CourseModel:
    def __init__(
        self,
        cards: Sequence[Flashcard],
        deck_ids: Mapping[str, str],
        vectoriser=None,
        index: Optional[similar.SimilarityIndex] = None,
    ) -> None:
        """Fit on all cards. `deck_ids` maps deck names to the deck ids of the course file (the space state's
        dot ids); a deck without an id keeps its name as id."""
        self.index = index if index is not None else similar.SimilarityIndex.fit(cards, vectoriser)
        self.deck_ids = {name: deck_ids.get(name, name) for name in dict.fromkeys(self.index.decks)}
        names, vectors = similar.deck_vectors(self.index.decks, self.index.vectors)
        order = sorted(range(len(names)), key=lambda row: self.deck_ids[names[row]])  # deck id order
        self.deck_names: list[str] = [names[row] for row in order]
        self.deck_vectors: np.ndarray = vectors[order] if order else vectors
        points, _start = layout.sphere_layout(self.deck_vectors, DECK_NEIGHBOURS, **DECK_LAYOUT)
        self.deck_points: dict[str, Point] = {
            self.deck_ids[name]: tuple(float(value) for value in points[row]) for row, name in enumerate(self.deck_names)
        }
        self.deck_trustworthiness = layout.trustworthiness_score(self.deck_vectors, points, DECK_NEIGHBOURS)
        self.deck_overlap = layout.neighbour_overlap(self.deck_vectors, points, DECK_NEIGHBOURS)
        self.deck_links: list[tuple[str, str]] = clustering.merge_links(
            [self.deck_ids[name] for name in self.deck_names], self.deck_vectors
        )
        self.decks: dict[str, DeckLayout] = {
            name: self._lay_out(name, self.deck_vectors[row]) for row, name in enumerate(self.deck_names)
        }
        self.card_points: dict[str, Point] = {
            card_id: point for deck in self.decks.values() for card_id, point in deck.positions.items()
        }

    def _lay_out(self, name: str, deck_vector: np.ndarray) -> DeckLayout:
        rows = self.index.rows_of_deck(name)
        ids = [self.index.ids[row] for row in rows]
        vectors = layout.as_dense(self.index.vectors[rows])
        distances = sun_distances(vectors @ deck_vector)
        directions, _start = layout.sphere_layout(vectors, CARD_NEIGHBOURS)  # the start centres the vectors
        positions = {
            card_id: tuple(float(value) for value in directions[row] * distances[row]) for row, card_id in enumerate(ids)
        }
        return DeckLayout(
            name=name,
            deck_id=self.deck_ids[name],
            ids=ids,
            positions=positions,
            links=clustering.merge_links(ids, vectors),
            overlap=layout.neighbour_overlap(vectors, directions, CARD_NEIGHBOURS),
            trustworthiness=layout.trustworthiness_score(vectors, directions, CARD_NEIGHBOURS),
        )

    # --- the cluster module's position sources ------------------------------

    def deck_positions(self, ids: Sequence[str], seed: int = 42) -> list[CardPosition]:
        """PositionSource of the space state: the model's deck positions; unknown ids are placed at random."""
        return self._positions(ids, self.deck_points, sphere_positions, seed)

    def card_positions(self, ids: Sequence[str], seed: int = 42) -> list[CardPosition]:
        """PositionSource of the card state: the model's card positions; unknown ids are placed at random in
        the shell around the sun."""
        return self._positions(ids, self.card_points, shell_positions, seed)

    @staticmethod
    def _positions(ids: Sequence[str], known: Mapping[str, Point], fallback, seed: int) -> list[CardPosition]:
        unknown = [card_id for card_id in ids if card_id not in known]
        random_positions = {position.comb_id: position for position in fallback(unknown, seed)} if unknown else {}
        positions = []
        for card_id in ids:
            if card_id in known:
                x, y, z = known[card_id]
                positions.append(CardPosition(comb_id=card_id, x=x, y=y, z=z))
            else:
                positions.append(random_positions[card_id])
        return positions

    # --- connections and neighbours ----------------------------------------

    def card_links(self, deck_name: str) -> list[tuple[str, str]]:
        """The deck's connections in merge order; empty for an unknown deck."""
        deck = self.decks.get(deck_name)
        return list(deck.links) if deck else []

    def related(self, card_id: str) -> list[tuple[str, float]]:
        """The neighbours of a card across the whole course, best first."""
        return self.index.related(card_id)
