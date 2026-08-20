from dataclasses import dataclass, field


@dataclass(frozen=True)
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
    related_ids: list[str] = field(default_factory=list)
