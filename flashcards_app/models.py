from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Flashcard:
    id: str
    deck: str
    question: str
    answer: str

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

@dataclass
class CardLink:
    source_id: str
    target_id: str
    group_id: Optional[str] = None