"""The topic model T1 of the helper module (no Dash, no state): nearest centroid on the similarity index, seeded by
the scripted topics of the course file (docs/draft/helper/concept.md, "Topic model T1").

The topics of the course file are scripted (scripts/topics.py groups the cards by the headings and sources of the
lectures), so they are the model's input, not the truth: the model takes them in and decides every card's topic for
the state. The raw scripted topics are stored nowhere else, so nothing is ever removed, only hidden from focus.

    unit rows of the cards (services.similar) ───┐   per deck: a centroid per scripted topic (the mean of its cards'
                                                 ├→  unit rows, normalised) → every card's cosine to the deck's centroids,
    scripted topics (course file, version 3) ────┘   its own topic's without itself (leave-one-out) → the nearest
                                                     centroid is the card's topic, the best cosine minus the second
                                                     best its margin

* The decision for the state: the membership is the nearest centroid; a card whose margin is below FOCUS_MARGIN is
  hidden from focus, which means left out of the shown cards at a fresh start and nothing else (it keeps its topic,
  and the Cards dialog shows it again); a topic is never removed, and an emptied one keeps its dot.
* The derived course file (write_derived_course): the raw file with every card's "topic" set by the model, the same
  decks, topic ids and names, in the cluster module's format, so its parser, TopicIndex, dialogs and state work
  unchanged (compose reads it as its course file).
* The measures: the agreement with the scripted topics (the share of cards whose nearest centroid is their scripted
  topic, one minus the lessons' Hamming loss), the coherence per topic (the share of its scripted cards nearest to
  itself), the margin table (the cards kept at a threshold and their agreement), the moved cards and the emptied
  topics; evaluate.py --part topics records them.
* T1 is deterministic (the vectoriser and the means): the derived file and the cluster module's dot ids are the same
  at every start; a changed course or vectoriser changes them, and the state starts fresh (the cluster module's rule).

Edge cases (the user's, 2026-10-25): a topic with one scripted card has no centroid under leave-one-out, so its card
goes to the nearest other topic and the topic is emptied; a card with a single centroid to compare with (its own
topic the deck's only one with other cards) takes it with the full margin; an empty topic has no centroid and no
coherence. Ties go to the topic that comes first in the file.
"""

import json
import math
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

import numpy as np

from project.content.parser import CardsFile, card_stack, comb_id
from project.services import similar
from project.services.layout import as_dense

# A card whose margin (the best cosine minus the second best) is below this is hidden from focus: at 0.05 the map
# shows 70 % of the cards at 0.77 agreement with the scripted topics (concept.md; the user's decision, 2026-10-26)
FOCUS_MARGIN = 0.05
FULL_MARGIN = 1.0  # the margin of a card with nothing to compare its topic with: it is kept
MODEL_NAME = "T1 nearest centroid"

Key = tuple[str, str]  # (deck name, topic id)


@dataclass(frozen=True)
class TopicSeed:
    """A scripted topic of the course file, the model's input: its deck (by name), its id within the deck, its
    name, whether it is the rest topic, and its scripted cards in deck order."""

    deck: str
    topic_id: str
    name: str
    rest: bool
    card_ids: tuple[str, ...]

    @property
    def key(self) -> Key:
        return (self.deck, self.topic_id)


def scripted_topics(cards_file: CardsFile) -> list[TopicSeed]:
    """The scripted topics of every deck of the course file (version 3), in deck name order and file order."""
    cards = cards_file.load_decks()
    seeds = []
    for deck in cards_file.deck_names:
        members = [card for card in cards if card.deck == deck]
        for topic in cards_file.topics(deck):
            ids = tuple(card.id for card in members if cards_file.topic_of(card.id) == topic.topic_id)
            seeds.append(TopicSeed(deck, topic.topic_id, topic.name, topic.rest, ids))
    return seeds


def unit(vector: np.ndarray) -> np.ndarray:
    """The vector scaled to length 1 (a zero vector stays zero)."""
    length = float(np.linalg.norm(vector))
    return vector / length if length > 0 else vector


class TopicModel:
    """T1 fitted on the index: every card's topic and margin, the model's membership per topic, the coherence per
    scripted topic, and the measures against the scripted topics."""

    def __init__(self, index: similar.SimilarityIndex, seeds: Sequence[TopicSeed], margin: float = FOCUS_MARGIN) -> None:
        self.seeds: list[TopicSeed] = list(seeds)
        self.margin = margin
        self.scripted_of: dict[str, str] = {card_id: seed.topic_id for seed in self.seeds for card_id in seed.card_ids}
        self.topic_of: dict[str, str] = {}  # card id -> the model's topic id (within the card's deck)
        self.margin_of: dict[str, float] = {}  # card id -> the best cosine minus the second best
        self.members: dict[Key, list[str]] = {seed.key: [] for seed in self.seeds}  # the model's membership, deck order
        self.coherence: dict[Key, float] = {}  # the share of a topic's scripted cards nearest to itself (NaN: no cards)
        self._fit(index)

    def _fit(self, index: similar.SimilarityIndex) -> None:
        by_deck: dict[str, list[TopicSeed]] = {}
        for seed in self.seeds:
            by_deck.setdefault(seed.deck, []).append(seed)
        for deck, seeds in by_deck.items():
            rows = index.rows_of_deck(deck)
            ids = [index.ids[row] for row in rows]
            position = {card_id: place for place, card_id in enumerate(ids)}
            vectors = as_dense(index.vectors[rows]) if rows else np.zeros((0, 0))
            sums: dict[str, np.ndarray] = {}
            counts: dict[str, int] = {}
            for seed in seeds:
                own = [position[card_id] for card_id in seed.card_ids if card_id in position]
                sums[seed.topic_id] = vectors[own].sum(axis=0) if own else np.zeros(vectors.shape[1] if rows else 0)
                counts[seed.topic_id] = len(own)
            for place, card_id in enumerate(ids):
                own_topic = self.scripted_of.get(card_id)
                scores = []
                for seed in seeds:
                    total, count = sums[seed.topic_id], counts[seed.topic_id]
                    if seed.topic_id == own_topic:
                        total, count = total - vectors[place], count - 1  # leave-one-out: never its own vote
                    if count <= 0:
                        continue
                    scores.append((float(vectors[place] @ unit(total)), seed.topic_id))
                if not scores:
                    if own_topic is None:
                        continue  # not a card of this model: no topic to keep
                    topic, margin = own_topic, FULL_MARGIN
                elif len(scores) == 1:
                    topic, margin = scores[0][1], FULL_MARGIN
                else:
                    ordered = sorted(scores, key=lambda item: -item[0])  # a stable sort: ties keep the file order
                    topic, margin = ordered[0][1], ordered[0][0] - ordered[1][0]
                self.topic_of[card_id] = topic
                self.margin_of[card_id] = margin
                self.members[(deck, topic)].append(card_id)
            for seed in seeds:
                judged = [card_id for card_id in seed.card_ids if card_id in self.topic_of]
                self.coherence[seed.key] = (
                    sum(self.topic_of[card_id] == seed.topic_id for card_id in judged) / len(judged) if judged else math.nan
                )

    # --- the decision for the state ------------------------------------------

    @property
    def hidden(self) -> set[str]:
        """The cards hidden from focus: a margin below the threshold (between two topics)."""
        return {card_id for card_id, margin in self.margin_of.items() if margin < self.margin}

    def topics_of_deck(self, deck: str) -> list[TopicSeed]:
        return [seed for seed in self.seeds if seed.deck == deck]

    # --- the measures against the scripted topics ----------------------------

    def agreement_of(self, card_ids: Iterable[str]) -> float:
        """The share of these cards whose model topic is their scripted one (NaN without cards)."""
        judged = [card_id for card_id in card_ids if card_id in self.topic_of and card_id in self.scripted_of]
        if not judged:
            return math.nan
        return sum(self.topic_of[card_id] == self.scripted_of[card_id] for card_id in judged) / len(judged)

    @property
    def agreement(self) -> float:
        return self.agreement_of(self.topic_of)

    def kept(self, threshold: float) -> tuple[float, float]:
        """The margin table's row: (the share of the cards with a margin of at least `threshold`, their agreement)."""
        if not self.topic_of:
            return math.nan, math.nan
        kept = [card_id for card_id, margin in self.margin_of.items() if margin >= threshold]
        return len(kept) / len(self.topic_of), self.agreement_of(kept)

    @property
    def moved(self) -> int:
        """The cards whose model topic is not their scripted one."""
        return sum(self.topic_of[card_id] != self.scripted_of.get(card_id) for card_id in self.topic_of)

    @property
    def emptied(self) -> list[Key]:
        """The topics that had scripted cards and keep none under the model (they keep their dots)."""
        return [seed.key for seed in self.seeds if seed.card_ids and not self.members[seed.key]]


# --- the derived course file ---------------------------------------------------


def write_derived_course(source: Path, target: Path, topic_of: Mapping[str, str], hidden: Optional[int] = None) -> Path:
    """Write the course file again with every card's "topic" set by the model: the same decks, topics (ids and
    names), cards and ids, so the cluster module's parser reads it as it reads the raw file. A card the model does
    not know (skipped by the parser for its empty question) keeps its topic. A "helper" entry names the model, the
    source file and what changed; the file is written atomically. Returns `target`."""
    source, target = Path(source), Path(target)
    data = json.loads(source.read_text(encoding="utf-8"))
    moved = 0
    for deck in data["decks"]:
        for card in deck["cards"]:
            topic = topic_of.get(comb_id(card_stack(card), deck["id"], card["card_id"]))
            if topic is not None and topic != card.get("topic"):
                card["topic"] = topic
                moved += 1
    data["helper"] = {"model": MODEL_NAME, "source": source.name, "moved": moved, **({} if hidden is None else {"hidden": hidden})}
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
    return target
