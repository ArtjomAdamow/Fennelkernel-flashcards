"""The predefined groups of the topics view: every topic dot sorted by its mix of cards (no Dash, no state code).

The rules, the first that matches wins (the user, 2026-10-27; flashcards are stacks 1 and 4, quizzes stacks 2
and 3, see content.decks.QUIZ_STACKS):

    1. "hard quizes"      at least 1 hard or 2 medium quizzes, and no more flashcards than quizzes
    2. no group           no quizzes at all, or no flashcards at all (an empty topic too)
    3. "more flashcards"  more flashcards than quizzes
    4. "composite"        both kinds, at least as many quizzes as flashcards

On the course of 2026-10-27 (133 topics): 8 red, 15 in no group, 93 blue, 17 beige.

The groups are ordinary groups of the card state, saved with it, but their members are derived: sync sets them
to the loaded topic dots of each rule whenever the dots change (startup, a deck or topic checked or unchecked). A
deleted or edited predefined group comes back with its name, colour and rank at the next sync. Their ranks are
below every user group's, so they are always the oldest groups and colour a topic dot unless Focus unchecks them.
Their ids do not match the package's "group-<n>" ids, so new user groups keep their numbering.
"""

from typing import Iterable, List, Optional, Tuple

from project.content.topics import TopicIndex, TopicInfo
from project.models import CardGroup

QUIZES = "topic-quizes"
FLASHCARDS = "topic-flashcards"
COMPOSITE = "topic-composite"

# id, name, colour, in the rules' order; the ranks follow this order, all below the user groups' (1, 2, ...)
PREDEFINED: Tuple[Tuple[str, str, str], ...] = (
    (QUIZES, "hard quizes", "#ff5349"),
    (FLASHCARDS, "more flashcards", "#4f7fcf"),
    (COMPOSITE, "composite", "#b8956a"),
)
PREDEFINED_IDS = frozenset(group_id for group_id, _, _ in PREDEFINED)


def category(topic: TopicInfo) -> Optional[str]:
    """The predefined group of a topic by its mix of cards; None for no group."""
    if (topic.hard >= 1 or topic.medium >= 2) and topic.flashcards <= topic.quiz:
        return QUIZES
    if topic.quiz == 0 or topic.flashcards == 0:
        return None
    if topic.flashcards > topic.quiz:
        return FLASHCARDS
    return COMPOSITE


def is_predefined(group_id: Optional[str]) -> bool:
    return group_id in PREDEFINED_IDS


def sync(groups: List[CardGroup], topics: TopicIndex, loaded_ids: Iterable[str]) -> None:
    """Put the predefined groups at the front of `groups` (in place, the core's own list), with their names,
    colours and ranks, and set their members to the loaded topic dots of each rule, in load order."""
    members = {group_id: [] for group_id in PREDEFINED_IDS}
    for dot_id in loaded_ids:
        topic = topics.by_dot_id.get(dot_id)
        group_id = category(topic) if topic is not None else None
        if group_id is not None:
            members[group_id].append(dot_id)
    predefined = [
        CardGroup(group_id, name, color, members[group_id], rank)
        for rank, (group_id, name, color) in enumerate(PREDEFINED, start=-len(PREDEFINED))
    ]
    groups[:] = predefined + [group for group in groups if group.id not in PREDEFINED_IDS]
