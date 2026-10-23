"""Difficulty groups: the course's easy, medium and hard as generated card groups of the deck view ("Quiz: easy",
"Quiz: medium", "Quiz: hard"), and the grey group of the predicted quizzes ("Quiz difficulty: predicted").

Every card with a difficulty is a member of its difficulty's group; unrated cards are in none and keep the grey of
a card without a group. A quiz that the difficulty model D1 rated (services.difficulty_model) gets two memberships:
the grey group "Quiz difficulty: predicted" and the group of its predicted level, the same groups (and colours) as the
rated cards. The groups are ordinary groups of the card state, so a card can also be in any of the user's groups.
They are always the oldest groups: every fill gives them the lowest ranks ("Quiz difficulty: predicted" first, then
easy, medium and hard) and the first places in the list. A predicted card therefore shows grey, a rated card its
difficulty colour, unless Focus unchecks them; and a group the user deleted comes back as the oldest when the
Helper button generates it again.
"""

from typing import Mapping

# difficulty -> (group name, colour); the prefix keeps a user group from being taken for one of them
DIFFICULTY_GROUPS = {
    "easy": ("Quiz: easy", "#4f7fcf"),  # blue (a Blue-Gray moved into blue, apart from the no-group grey)
    "medium": ("Quiz: medium", "#b8956a"),  # Beige-Brown
    "hard": ("Quiz: hard", "#ff5349"),  # Red-Orange
}
GROUP_NAMES = [name for name, _ in DIFFICULTY_GROUPS.values()]
# The predicted cards: the no-group grey, so a predicted card looks unrated until Focus unchecks this group
PREDICTED_GROUP = ("Quiz difficulty: predicted", "#7c8b99")
GENERATED_NAMES = [PREDICTED_GROUP[0]] + GROUP_NAMES  # the oldest first


def _age(group) -> tuple:
    return (group.rank is None, group.rank if group.rank is not None else 0)


def _named(core, name):
    return next((item for item in core.groups if item.name == name), None)


def _join(core, card_id: str, name: str, color: str) -> int:
    """Put the card into the group of this name, creating it; 1 when a membership was added."""
    group = _named(core, name)
    if group is None:
        core.create_group(card_id, name, color)
        return 1
    if card_id in group.card_ids:
        return 0
    core.add_to_group(card_id, group.id)
    return 1


def fill_difficulty_groups(core, cards) -> int:
    """Put every card with a difficulty into its difficulty group, creating a missing group, then make the
    difficulty groups the oldest. `core` is anything with a live `groups` list, `create_group` and `add_to_group`
    (a StateCore or a UserStateService). Idempotent; returns the number of memberships added."""
    added = 0
    for card in cards:
        entry = DIFFICULTY_GROUPS.get(card.difficulty)
        if entry is not None:
            added += _join(core, card.id, *entry)
    make_oldest(core)
    return added


def fill_predicted_groups(core, predictions: Mapping[str, str]) -> int:
    """Every predicted card (card id -> level) into "Quiz difficulty: predicted" and into its level's difficulty group,
    creating missing groups; a card that was predicted at another level before leaves that level's group. Then the
    generated groups are made the oldest. Idempotent; returns the number of memberships added."""
    added = 0
    for card_id, level in predictions.items():
        entry = DIFFICULTY_GROUPS.get(level)
        if entry is None:
            continue
        added += _join(core, card_id, *PREDICTED_GROUP)
        added += _join(core, card_id, *entry)
        for other, (name, _) in DIFFICULTY_GROUPS.items():
            group = _named(core, name)
            if other != level and group is not None and card_id in group.card_ids:
                core.remove_from_group(card_id, group.id)
    make_oldest(core)
    return added


def make_oldest(core) -> None:
    """The lowest ranks for the generated groups ("Quiz difficulty: predicted", then easy, medium and hard), the user's
    groups after them in their own order; the generated groups also come first in the list, the user's keep theirs."""
    generated = sorted((group for group in core.groups if group.name in GENERATED_NAMES), key=lambda group: GENERATED_NAMES.index(group.name))
    others = [group for group in core.groups if group.name not in GENERATED_NAMES]
    for rank, group in enumerate(generated + sorted(others, key=_age), start=1):
        group.rank = rank
    core.groups[:] = generated + others
