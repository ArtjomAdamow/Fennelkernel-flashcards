"""Decks as dots of the decks view: one deck card per deck of the course, with a placeholder description.

The space state (the decks' 3D space) is an ordinary StateCore whose only deck is SPACE_DECK; its cards are the
course's decks.
A deck card's comb_id is the deck "id" of the course file, its question the deck name and its answer the
description (never flipped: a deck is entered instead).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from project.content.parser import STACK_DIFFICULTY, STACK_QUIZ, CardsFile, read_decks
from project.models import Flashcard

# The stacks of the quiz cards; the flashcards are stacks 1 and 4 (the JS quiz file's flashcards are no quizzes)
QUIZ_STACKS = (STACK_QUIZ, STACK_DIFFICULTY)

# The only deck of the space state
SPACE_DECK = "Space"


@dataclass(frozen=True)
class DeckInfo:
    deck_id: str
    name: str
    cards: int
    quiz: int
    with_difficulty: int

    def description(self) -> str:
        """Placeholder until real descriptions exist: the size and the mix of card types."""
        return f"{self.cards} cards: {self.quiz} quiz cards, {self.with_difficulty} of them with a difficulty."


class DeckIndex:
    """The decks of the course in deck id order, with their card counts; also the space state's card source."""

    def __init__(self, course_file: Path, cards_file: CardsFile, available: Iterable[str]) -> None:
        names = set(available)
        cards = cards_file.load_decks()
        infos = []
        # read_decks gives the deck ids, which CardsFile does not keep
        for raw in read_decks(course_file):
            name = raw["name"]
            if name not in names:
                continue
            members = [card for card in cards if card.deck == name]
            infos.append(
                DeckInfo(
                    deck_id=raw["id"],
                    name=name,
                    cards=len(members),
                    quiz=sum(card.stack in QUIZ_STACKS for card in members),
                    with_difficulty=sum(card.difficulty is not None for card in members),
                )
            )
        self.infos = sorted(infos, key=lambda info: info.deck_id)
        self.by_id = {info.deck_id: info for info in self.infos}
        self.by_name = {info.name: info for info in self.infos}

    def load(self, deck_names: list[str]) -> list[Flashcard]:
        """CardSource of the space state: the deck cards when SPACE_DECK is enabled."""
        if SPACE_DECK not in deck_names:
            return []
        return [
            Flashcard(comb_id=info.deck_id, deck=SPACE_DECK, question=info.name, answer=info.description())
            for info in self.infos
        ]


class SpaceCatalog:
    """Catalog of the space state: SPACE_DECK is its only deck."""

    def available(self) -> list[str]:
        return [SPACE_DECK]

    def is_available(self, deck_name: str) -> bool:
        return deck_name == SPACE_DECK

    def reload(self) -> bool:
        return True
