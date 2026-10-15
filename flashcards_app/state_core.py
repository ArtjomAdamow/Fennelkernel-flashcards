"""State core: the live card state of one learner (or, later, of one RAG run).

Holds cards, positions, progress, groups, links and the enabled decks, and offers
the mutations on them. It knows nothing about files, Dash or where cards come from:
persistence, card source and position source are injected.

Rules that keep the data flow one-directional:
  * load() is passive: it only reads. No defaults, no position generation, nothing stripped.
  * refresh_deck_state() is the only place that derives or strips state (as before).
  * save() is the only place that writes. Nothing here calls save() by itself.

The containers (cards, positions, progress, groups, links, enabled_decks, card_by_id,
position_by_id) are created once and only ever changed in place, because consumers
hold references to them.
"""

import re
import time
from typing import Callable, Optional, Protocol

from .models import CardGroup, CardLink, CardPosition, CardProgress, Flashcard
from .state import RawState

# Positions for cards without a stored one were generated with this seed at startup
# (state.load_positions did so). Passing it keeps the first-run layout reproducible.
STARTUP_SEED = 42

_GROUP_ID = re.compile(r"^group-(\d+)$")


class StatePersistence(Protocol):
    """Where the state lives. state.JsonStateStore is the file-backed implementation."""

    def read(self) -> Optional[RawState]: ...

    def write(self, state: RawState) -> None: ...


# Enabled deck names -> cards (e.g. lambda decks: parser.load_decks(cards_dir, decks))
CardSource = Callable[[list[str]], list[Flashcard]]

# Card ids, seed -> one position per card (e.g. geometry.sphere_positions)
PositionSource = Callable[[list[str], int], list[CardPosition]]


class StateCore:
    def __init__(
        self,
        persistence: StatePersistence,
        card_source: CardSource,
        position_source: PositionSource,
    ) -> None:
        self._persistence = persistence
        self._card_source = card_source
        self._position_source = position_source

        self.enabled_decks: list[str] = []
        self.cards: list[Flashcard] = []
        self.positions: list[CardPosition] = []
        self.progress: dict[str, CardProgress] = {}
        self.groups: list[CardGroup] = []
        self.links: list[CardLink] = []
        self.card_by_id: dict[str, Flashcard] = {}
        self.position_by_id: dict[str, CardPosition] = {}

    # --- lifecycle ---------------------------------------------------------

    def load(self, available_decks: list[str]) -> None:
        """Read the persisted state once. Call refresh_deck_state() afterwards."""
        raw = self._persistence.read() or RawState()
        available = set(available_decks)
        if raw.decks is None:
            decks = list(available_decks)
        else:
            decks = [deck for deck in raw.decks if deck in available]

        self.enabled_decks[:] = decks
        self.cards[:] = self._card_source(list(self.enabled_decks))
        self.positions[:] = raw.positions
        self.progress.clear()
        self.progress.update(raw.progress)
        self.groups[:] = raw.groups
        self.links[:] = raw.links
        self._rebuild_indexes()

    def refresh_deck_state(self, seed: Optional[int] = None) -> None:
        """Make everything consistent with the current cards.

        Positions and progress are generated for cards that have none; entries of cards
        that are no longer loaded are dropped from progress, positions, related_ids, groups and links.
        """
        card_ids = [card.id for card in self.cards]
        stored_positions = {position.comb_id: position for position in self.positions}
        generated = self._position_source(card_ids, self._seed(seed))
        self.positions[:] = [stored_positions.get(position.comb_id, position) for position in generated]

        stored_progress = dict(self.progress)
        self.progress.clear()
        self.progress.update({card_id: stored_progress.get(card_id, CardProgress(card_id)) for card_id in card_ids})

        valid_ids = set(card_ids)
        for group in self.groups:
            group.card_ids = [card_id for card_id in group.card_ids if card_id in valid_ids]
        # phase 1: related_ids hold comb_ids too and get the same filter as group members and links
        for position in self.positions:
            position.related_ids = [related_id for related_id in position.related_ids if related_id in valid_ids]
        self._fill_missing_ranks()
        self.links[:] = [
            link for link in self.links
            if link.source_id in valid_ids and link.target_id in valid_ids
        ]
        self._rebuild_indexes()

    def save(self) -> None:
        self._persistence.write(
            RawState(
                positions=self.positions,
                progress=self.progress,
                groups=self.groups,
                links=self.links,
                decks=self.enabled_decks,
            )
        )

    def reset_all_state(self, seed: Optional[int] = None) -> None:
        generated = self._position_source([card.id for card in self.cards], self._seed(seed))
        for position, replacement in zip(self.positions, generated):
            position.x, position.y, position.z = replacement.x, replacement.y, replacement.z
        for progress in self.progress.values():
            progress.read = False
            progress.difficulty = 1
        self.groups.clear()
        self.links.clear()

    # --- deck scope --------------------------------------------------------

    def enable_deck(self, deck_name: str) -> bool:
        """Enable a deck and reload cards. The caller checks that the deck exists."""
        if deck_name in self.enabled_decks:
            return False
        self.enabled_decks.append(deck_name)
        self.enabled_decks.sort()
        self._reload_cards()
        return True

    def disable_deck(self, deck_name: str) -> bool:
        if deck_name not in self.enabled_decks:
            return False
        self.enabled_decks.remove(deck_name)
        self._reload_cards()
        return True

    # --- queries -----------------------------------------------------------

    def get_card_by_id(self, card_id: str) -> Optional[Flashcard]:
        return self.card_by_id.get(card_id)

    def get_position_by_id(self, card_id: str) -> Optional[CardPosition]:
        return self.position_by_id.get(card_id)

    def visible_cards(self, deck: Optional[str] = None, focused_group: Optional[str] = None) -> list[Flashcard]:
        """Cards of one deck (None = all decks), optionally only members of a group.

        UI sentinels such as "all" or the empty-map deck are the caller's business.
        """
        cards = [card for card in self.cards if deck is None or card.deck == deck]
        if focused_group:
            group = next((item for item in self.groups if item.id == focused_group), None)
            focused_ids = set(group.card_ids) if group else set()
            cards = [card for card in cards if card.id in focused_ids]
        return cards

    def deciding_group(self, card_id: str, focused_group: Optional[str] = None) -> Optional[CardGroup]:
        """The group that decides how a card is shown (its colour).

        1. A group is focused and the card is a member: that group.
        2. Otherwise the oldest existing group the card is a member of (lowest rank; a tie goes to the
           group that comes first in the list). When that group is deleted, the next oldest takes over.
        """
        members = [group for group in self.groups if card_id in group.card_ids]
        if focused_group:
            for group in members:
                if group.id == focused_group:
                    return group
        if not members:
            return None
        return min(members, key=lambda group: (group.rank is None, group.rank if group.rank is not None else 0))

    # --- mutations ---------------------------------------------------------

    def set_position(self, card_id: str, x: float, y: float, z: float) -> None:
        position = self.position_by_id[card_id]
        position.x = float(x)
        position.y = float(y)
        position.z = float(z)

    def set_difficulty(self, card_id: str, difficulty: int) -> None:
        # same bounds CardProgress enforces on construction
        self.progress[card_id].difficulty = max(1, min(100, int(difficulty)))

    def mark_read(self, card_id: str) -> None:
        progress = self.progress.get(card_id)
        if progress is not None:
            progress.read = True

    def create_group(self, card_id: str, name: str, color: str) -> str:
        self._fill_missing_ranks()
        group_id = self._next_group_id()
        rank = max((group.rank for group in self.groups), default=0) + 1
        self.groups.append(CardGroup(group_id, name.strip(), color, [card_id], rank))
        return group_id

    def add_to_group(self, card_id: str, group_id: str) -> None:
        group = self._group(group_id)
        if group and card_id not in group.card_ids:
            group.card_ids.append(card_id)

    def remove_from_group(self, card_id: str, group_id: str) -> None:
        group = self._group(group_id)
        if group:
            group.card_ids = [member for member in group.card_ids if member != card_id]

    def delete_group(self, group_id: str) -> None:
        # Links are never touched: the members stay on the map (unlike removing a deck)
        self.groups[:] = [group for group in self.groups if group.id != group_id]

    def create_link(self, source_id: str, target_id: str) -> None:
        exists = any(
            (link.source_id == source_id and link.target_id == target_id)
            or (link.source_id == target_id and link.target_id == source_id)
            for link in self.links
        )
        if not exists:
            self.links.append(CardLink(source_id, target_id))

    def disconnect_link(self, source_id: str, target_id: str) -> None:
        self.links[:] = [
            link for link in self.links
            if not (
                (link.source_id == source_id and link.target_id == target_id)
                or (link.source_id == target_id and link.target_id == source_id)
            )
        ]

    # --- internals ---------------------------------------------------------

    @staticmethod
    def _seed(seed: Optional[int]) -> int:
        return time.time_ns() if seed is None else seed

    def _reload_cards(self) -> None:
        self.cards[:] = self._card_source(list(self.enabled_decks))
        self.refresh_deck_state()

    def _rebuild_indexes(self) -> None:
        self.card_by_id.clear()
        self.card_by_id.update({card.id: card for card in self.cards})
        self.position_by_id.clear()
        self.position_by_id.update({position.comb_id: position for position in self.positions})

    def _group(self, group_id: str) -> Optional[CardGroup]:
        return next((item for item in self.groups if item.id == group_id), None)

    def _fill_missing_ranks(self) -> None:
        """Groups from files written before ranks existed get one in list order, after the existing ranks."""
        highest = max((group.rank for group in self.groups if group.rank is not None), default=0)
        for group in self.groups:
            if group.rank is None:
                highest += 1
                group.rank = highest

    def _next_group_id(self) -> str:
        # The old "group-<count+1>" produced duplicates after a group was deleted.
        # With contiguous ids (no deletions) both give the same result.
        used = {group.id for group in self.groups}
        numbers = [int(match.group(1)) for group_id in used if (match := _GROUP_ID.match(group_id))]
        number = max(numbers, default=0) + 1
        while f"group-{number}" in used:
            number += 1
        return f"group-{number}"
