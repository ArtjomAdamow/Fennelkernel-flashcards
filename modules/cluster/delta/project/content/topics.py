"""The topics of the course as dots between the decks and the cards (no Dash, no state code).

A topic (course file version 3, CardsFile.topics) becomes a dot of the card state: a Flashcard with the topic's
name as its question and a short description as its answer, next to the deck's cards. Its id carries the deck id,
the topic id and a short hash of the topic's card ids ("0203" plus 4 hex characters): a topic whose cards changed
(a new run of scripts/topics.py, another topic source) is a new dot, so it never carries a dot's connections over
to other cards, and an unchanged topic keeps its position and connections. The 8 characters stay apart from the
6-digit card ids.

The card state's source (card_source) gives, for every enabled (checked) deck, all its cards and a dot per
checked topic (the view settings; a deck without an entry, or with a stale signature, has all topics checked), so
the package's refresh_deck_state strips exactly the cards and dots of an unchecked deck and the dot of an
unchecked topic. A card's state never hangs on its topic: topic_of only says which view shows the card.

The position source by kind (position_source) places topic dots in the shell around the deck's centroid and
cards on the surface of their topic's sphere.
"""

import hashlib
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from project.content.decks import QUIZ_STACKS, DeckIndex
from project.content.parser import CardsFile
from project.models import CardPosition, Flashcard
from project.services.positions import shell_positions, surface_positions

DOT_HASH_LENGTH = 4
SIGNATURE_LENGTH = 8


def card_hash(card_ids: Iterable[str]) -> str:
    """The short hash of a topic's card ids (order-free)."""
    return hashlib.sha1("\n".join(sorted(card_ids)).encode("utf-8")).hexdigest()[:DOT_HASH_LENGTH]


def deck_signature(assignment: Iterable[Tuple[str, str]]) -> str:
    """The hash of a deck's whole assignment: every (comb_id, topic id) pair, order-free."""
    lines = sorted(f"{comb_id}:{topic_id}" for comb_id, topic_id in assignment)
    return hashlib.sha1("\n".join(lines).encode("utf-8")).hexdigest()[:SIGNATURE_LENGTH]


@dataclass(frozen=True)
class TopicInfo:
    dot_id: str
    deck_id: str
    deck_name: str
    topic_id: str
    name: str
    rest: bool
    card_ids: Tuple[str, ...]  # in deck order
    quiz: int  # cards on the quiz stacks
    hard: int = 0  # quizzes with the authored difficulty "hard" (stack 3)
    medium: int = 0  # quizzes with the authored difficulty "medium" (stack 3)

    @property
    def cards(self) -> int:
        return len(self.card_ids)

    @property
    def flashcards(self) -> int:
        return self.cards - self.quiz

    def description(self) -> str:
        """Placeholder until real descriptions exist: the size and the mix of card types."""
        text = f"{self.cards} cards: {self.flashcards} flashcards, {self.quiz} quiz cards."
        return f"The deck's cards that fit no other topic. {text}" if self.rest else text

    def dot(self) -> Flashcard:
        """The topic as a dot of the card state (never flipped: a topic is entered instead)."""
        return Flashcard(comb_id=self.dot_id, deck=self.deck_name, question=self.name, answer=self.description())


class TopicIndex:
    """The topics of every deck in file order, with their cards, dot ids and the decks' assignment signatures."""

    def __init__(self, cards_file: CardsFile, decks: DeckIndex) -> None:
        self._by_deck: Dict[str, Tuple[TopicInfo, ...]] = {}
        self.by_dot_id: Dict[str, TopicInfo] = {}
        self._topic_of_card: Dict[str, TopicInfo] = {}
        self._signatures: Dict[str, str] = {}
        cards = cards_file.load_decks()
        for info in decks.infos:
            members = [card for card in cards if card.deck == info.name]
            assignment = [(card.comb_id, cards_file.topic_of(card.comb_id) or "") for card in members]
            topics = []
            for topic in cards_file.topics(info.name):
                own = [card for card in members if cards_file.topic_of(card.comb_id) == topic.topic_id]
                ids = tuple(card.comb_id for card in own)
                topics.append(
                    TopicInfo(
                        dot_id=f"{info.deck_id}{topic.topic_id}{card_hash(ids)}",
                        deck_id=info.deck_id,
                        deck_name=info.name,
                        topic_id=topic.topic_id,
                        name=topic.name,
                        rest=topic.rest,
                        card_ids=ids,
                        quiz=sum(card.stack in QUIZ_STACKS for card in own),
                        hard=sum(card.difficulty == "hard" for card in own),
                        medium=sum(card.difficulty == "medium" for card in own),
                    )
                )
            self._by_deck[info.deck_id] = tuple(topics)
            self._signatures[info.deck_id] = deck_signature(assignment)
            for topic in topics:
                self.by_dot_id[topic.dot_id] = topic
                for comb_id in topic.card_ids:
                    self._topic_of_card[comb_id] = topic

    def topics(self, deck_id: Optional[str]) -> Tuple[TopicInfo, ...]:
        """The deck's topics in file order; none for an unknown deck."""
        return self._by_deck.get(deck_id, ()) if deck_id else ()

    def topic_of(self, comb_id: str) -> Optional[TopicInfo]:
        """The topic of a card; None for an unknown card or a dot."""
        return self._topic_of_card.get(comb_id)

    def is_dot(self, dot_id: str) -> bool:
        return dot_id in self.by_dot_id

    def signature(self, deck_id: str) -> str:
        return self._signatures.get(deck_id, "")

    def signatures(self) -> Dict[str, str]:
        return dict(self._signatures)

    # --- the card state's sources -------------------------------------------

    def card_source(self, cards_file: CardsFile, decks: DeckIndex, settings) -> Callable[[List[str]], List[Flashcard]]:
        """The card state's source: for the enabled decks all their cards (as the package's source gives them),
        then a dot per checked topic (the view settings), in deck id order and file order."""

        def source(deck_names: List[str]) -> List[Flashcard]:
            names = set(deck_names)
            dots = []
            for info in decks.infos:
                if info.name not in names:
                    continue
                checked = settings.checked_topics(info.deck_id, self.signature(info.deck_id))
                for topic in self.topics(info.deck_id):
                    if checked is None or topic.topic_id in checked:
                        dots.append(topic.dot())
            return cards_file.load_decks(deck_names) + dots

        return source

    def position_source(self, card_positions=surface_positions, topic_positions=shell_positions):
        """A position source that places a dot by its kind: topic dots with `topic_positions` (the random shell
        around the centroid by default), cards with `card_positions` (the sphere's surface by default). Both are
        hooks of compose for a module on top (the helper's model positions). The hard rules of services.positions
        apply to stored and given positions at startup."""

        def source(ids: List[str], seed: int = 42) -> List[CardPosition]:
            dot_ids = [item for item in ids if self.is_dot(item)]
            card_ids = [item for item in ids if not self.is_dot(item)]
            generated = {position.comb_id: position for position in card_positions(card_ids, seed)}
            generated.update({position.comb_id: position for position in topic_positions(dot_ids, seed + 1)})
            return [generated[item] for item in ids]

        return source
