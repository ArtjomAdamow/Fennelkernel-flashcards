from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Flashcard:
    # Global card id: stack + deck "id" + "card_id" of the JSON source (see parser.comb_id)
    comb_id: str
    deck: str
    question: str
    answer: str
    # 1 = plain card, 2 = quiz, 3 = quiz with difficulty (see parser.card_stack)
    stack: int = 1
    # Authored level of the card ("easy" / "medium" / "hard"), only in stack 3.
    # Not to be confused with CardProgress.difficulty, the learner's 1..100 rating.
    difficulty: Optional[str] = None
    explain: Optional[str] = None
    weblink: Optional[str] = None

    @property
    def id(self) -> str:
        # Read-only alias: the app addresses cards as card.id (state_core, panels, map, callbacks)
        return self.comb_id

@dataclass
class CardPosition:
    card_id: str
    x: float
    y: float
    z: float
    status: str = "new"
    related_ids: List[str] = field(default_factory=list)

@dataclass
class CardProgress:
    card_id: str
    read: bool = False
    difficulty: int = 1
    def __post_init__(self) -> None:
        object.__setattr__(self, "difficulty", max(1, min(100, int(self.difficulty))))

@dataclass
class CardGroup:
    id: str
    name: str
    color: str
    card_ids: List[str] = field(default_factory=list)
    rank: Optional[int] = None  # age order of groups: lower = older (see StateCore.deciding_group)

@dataclass
class CardLink:
    source_id: str
    target_id: str