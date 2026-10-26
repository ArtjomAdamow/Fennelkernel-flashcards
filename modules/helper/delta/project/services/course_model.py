"""The course model of the helper module (no Dash, no state): the pipeline fitted once on all cards, and from it the
topics of the state and the positions and connections the cluster module shows.

* Decks view: one unit vector per deck (similar.deck_vectors); the layout step (services.layout, k = 3) places all
  decks on the unit sphere at once. The positions are keyed by deck id, the dots of the decks state. The clustering
  of the deck vectors (services.clustering) gives the deck connections, which the Helper button adds on request
  (a fresh start writes none).
* Topics: the topic model T1 (services.topic_model) takes the scripted topics of the course file as its input and
  decides every card's topic and margin; the derived course file it writes is what the cluster module reads, so the
  topic dots are the cluster module's own (random in the shell; the model places none).
* Cards view, for each topic of the model: the layout step on the topic's card vectors, centred on the topic's mean
  (the start's own centring), with the neighbours within the topic (k = min(5, n - 1)), gives one unit direction per
  card, and that direction is the position: every card sits on the surface of its topic's sphere (radius 1), as the
  cluster module's hard rule wants it. The clustering of the topic's card vectors gives its connections (n - 1). A
  topic with fewer than two cards gets no layout and no connections.
* The two position sources have the cluster module's signature (ids, seed) -> positions. They are deterministic and
  ignore the seed. An id the model does not know (a card of a one-card topic, a card that is not in the course it
  was fitted on) gets the cluster module's random position on the surface (services.positions.surface_positions),
  with the seed.
"""

import math
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

import numpy as np

from project.models import CardPosition, Flashcard
from project.services import clustering, layout, similar
from project.services.positions import surface_positions
from project.services.topic_model import FOCUS_MARGIN, TopicModel, TopicSeed

DECK_NEIGHBOURS = 3
CARD_NEIGHBOURS = 5
# The force layout of the decks runs with a smaller step and a weaker push than the card layouts (the defaults of
# services.layout): on the course both measures of the deck layout are better that way (results.csv)
DECK_LAYOUT = {"iterations": 300, "step": 0.05, "repulsion": 0.5}

Point = tuple[float, float, float]
Key = tuple[str, str]  # (deck id, topic id)


@dataclass
class TopicLayout:
    """One topic's cards (the model's membership) on the surface of the topic's sphere."""

    deck: str  # the deck name
    deck_id: str
    topic_id: str
    name: str
    ids: list[str]
    positions: dict[str, Point]  # unit directions; empty below two cards
    links: list[tuple[str, str]]  # n - 1 connections in merge order; empty below two cards
    overlap: float  # top-k overlap of the 3D directions with the within-topic neighbours (NaN below two cards)
    trustworthiness: float


class CourseModel:
    def __init__(
        self,
        cards: Sequence[Flashcard],
        deck_ids: Mapping[str, str],
        topics: Sequence[TopicSeed],
        vectoriser=None,
        index: Optional[similar.SimilarityIndex] = None,
        margin: float = FOCUS_MARGIN,
    ) -> None:
        """Fit on all cards. `deck_ids` maps deck names to the deck ids of the course file (the decks state's dot
        ids); a deck without an id keeps its name as id. `topics` are the scripted topics (topic_model.scripted_topics),
        the input of T1."""
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
        self.topic_model = TopicModel(self.index, topics, margin)
        self._row_of = {card_id: row for row, card_id in enumerate(self.index.ids)}
        self.topics: dict[Key, TopicLayout] = {}
        for seed in self.topic_model.seeds:
            placed = self._lay_out(seed)
            self.topics[(placed.deck_id, placed.topic_id)] = placed
        self.card_points: dict[str, Point] = {
            card_id: point for placed in self.topics.values() for card_id, point in placed.positions.items()
        }

    def _lay_out(self, seed: TopicSeed) -> TopicLayout:
        ids = list(self.topic_model.members.get(seed.key, []))
        deck_id = self.deck_ids.get(seed.deck, seed.deck)
        if len(ids) < 2:  # no layout and no connections below two cards (the user's edge case)
            return TopicLayout(seed.deck, deck_id, seed.topic_id, seed.name, ids, {}, [], math.nan, math.nan)
        vectors = layout.as_dense(self.index.vectors[[self._row_of[card_id] for card_id in ids]])
        k = min(CARD_NEIGHBOURS, len(ids) - 1)
        directions, _start = layout.sphere_layout(vectors, k)  # the start centres the vectors on the topic's mean
        positions = {card_id: tuple(float(value) for value in directions[row]) for row, card_id in enumerate(ids)}
        return TopicLayout(
            deck=seed.deck,
            deck_id=deck_id,
            topic_id=seed.topic_id,
            name=seed.name,
            ids=ids,
            positions=positions,
            links=clustering.merge_links(ids, vectors),
            overlap=layout.neighbour_overlap(vectors, directions, k),
            trustworthiness=layout.trustworthiness_score(vectors, directions, k),
        )

    # --- the cluster module's position sources ------------------------------

    def deck_positions(self, ids: Sequence[str], seed: int = 42) -> list[CardPosition]:
        """PositionSource of the decks state: the model's deck positions; unknown ids are placed at random on the
        surface."""
        return self._positions(ids, self.deck_points, seed)

    def card_positions(self, ids: Sequence[str], seed: int = 42) -> list[CardPosition]:
        """PositionSource of the card state's cards: the model's directions (radius 1); unknown ids, and the cards
        of a one-card topic, are placed at random on the surface."""
        return self._positions(ids, self.card_points, seed)

    @staticmethod
    def _positions(ids: Sequence[str], known: Mapping[str, Point], seed: int) -> list[CardPosition]:
        unknown = [card_id for card_id in ids if card_id not in known]
        random_positions = {position.comb_id: position for position in surface_positions(unknown, seed)} if unknown else {}
        positions = []
        for card_id in ids:
            if card_id in known:
                x, y, z = known[card_id]
                positions.append(CardPosition(comb_id=card_id, x=x, y=y, z=z))
            else:
                positions.append(random_positions[card_id])
        return positions

    # --- the topics, connections and neighbours ------------------------------

    @property
    def hidden(self) -> set[str]:
        """The cards T1 hides from focus (a margin below the threshold)."""
        return self.topic_model.hidden

    def topics_of_deck(self, deck_id: str) -> list[TopicLayout]:
        """The deck's topics in file order."""
        return [placed for placed in self.topics.values() if placed.deck_id == deck_id]

    def card_links(self, deck_id: str, topic_id: str) -> list[tuple[str, str]]:
        """The topic's connections in merge order; empty for an unknown topic or one with fewer than two cards."""
        placed = self.topics.get((deck_id, topic_id))
        return list(placed.links) if placed else []

    def related(self, card_id: str) -> list[tuple[str, float]]:
        """The neighbours of a card across the whole course, best first."""
        return self.index.related(card_id)
