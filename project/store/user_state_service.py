"""User state service: the learner's state as the rest of the app sees it.

A facade over StateCore (the live state and its mutations) and the deck catalog (which decks exist in
the course file: JsonDeckCatalog; phase 2: the .md DeckCatalog is switched off).
It adds the one rule that needs the catalog: only decks that exist can be enabled.

The containers it exposes are the core's own live objects (same object on every access), because
panels, map, colors and callbacks read them directly and rely on in-place changes.

Constellations (runtime only, never saved): the connected groups of visible cards, derived from the links.
refresh_constellations(cards) derives them again for the cards the map shows; Connect, Disconnect and a reset
refresh them for the cards of the last refresh. Delete (delete_constellation_links) is the one action that
removes the links between all members; links to hidden cards stay; StateCore saves that change at once.
"""

from typing import Iterable, Optional, Sequence

from project.content.deck_catalog import JsonDeckCatalog
from project.models import CardGroup, CardLink, CardPosition, CardProgress, Constellation, Flashcard
from .state_core import StateCore


# phase 4: constellations (derive_components, reconcile_constellations and the constellation API below)
def derive_components(visible_ids: Iterable[str], links: Iterable[CardLink]) -> list[list[str]]:
    """Connected groups of at least two cards, over the links whose two ends are both visible.

    Hidden cards and their links are ignored, never deleted. Every group is a sorted list of card ids.
    """
    visible = set(visible_ids)
    adjacency: dict[str, set[str]] = {}
    for link in links:
        source, target = link.source_id, link.target_id
        if source != target and source in visible and target in visible:
            adjacency.setdefault(source, set()).add(target)
            adjacency.setdefault(target, set()).add(source)

    components: list[list[str]] = []
    seen: set[str] = set()
    for start in sorted(adjacency):
        if start in seen:
            continue
        seen.add(start)
        stack, members = [start], []
        while stack:
            current = stack.pop()
            members.append(current)
            for neighbour in adjacency[current]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
        components.append(sorted(members))
    return components


def reconcile_constellations(previous: Sequence[Constellation], components: Sequence[Sequence[str]]) -> list[Constellation]:
    """Give the new groups their ids, keeping the previous ids where the groups continue.

    * Every previous id follows the largest new group it shares cards with (a tie goes to the group whose card
      ids sort first). A split therefore leaves the id with the largest branch.
    * A new group that is followed by several ids (a merge) keeps the lowest; the others become free.
    * Groups without an id (the smaller branches of a split, brand new groups) get the lowest free numbers,
      the larger group first. Free numbers include the gaps of ids that disappeared.
    The result is sorted by number.
    """
    groups = sorted((list(group) for group in components), key=lambda group: (-len(group), group))
    claims: dict[int, list[int]] = {}
    for old in previous:
        old_members = set(old.members)
        best_index, best_key = None, None
        for index, group in enumerate(groups):
            overlap = len(old_members.intersection(group))
            if overlap == 0:
                continue
            key = (len(group), overlap)
            if best_key is None or key > best_key:  # strict: the first group wins a tie
                best_index, best_key = index, key
        if best_index is not None:
            claims.setdefault(best_index, []).append(int(old.const_id))

    numbers = {index: min(ids) for index, ids in claims.items()}
    used = set(numbers.values())
    result = []
    for index, group in enumerate(groups):
        number = numbers.get(index)
        if number is None:
            number = 1
            while number in used:
                number += 1
            used.add(number)
        result.append(Constellation(const_id=str(number), members=group))
    result.sort(key=lambda constellation: int(constellation.const_id))
    return result


class UserStateService:
    def __init__(self, core: StateCore, catalog: JsonDeckCatalog) -> None:
        self._core = core
        self._catalog = catalog
        # phase 4: runtime only, never part of the state file. Ids may differ from session to session.
        self._constellations: list[Constellation] = []
        self._visible_ids: list[str] = []

    # --- live containers ---------------------------------------------------

    @property
    def cards(self) -> list[Flashcard]:
        return self._core.cards

    @property
    def positions(self) -> list[CardPosition]:
        return self._core.positions

    @property
    def progress(self) -> dict[str, CardProgress]:
        return self._core.progress

    @property
    def groups(self) -> list[CardGroup]:
        return self._core.groups

    @property
    def links(self) -> list[CardLink]:
        return self._core.links

    @property
    def enabled_decks(self) -> list[str]:
        return self._core.enabled_decks

    @property
    def card_by_id(self) -> dict[str, Flashcard]:
        return self._core.card_by_id

    @property
    def position_by_id(self) -> dict[str, CardPosition]:
        return self._core.position_by_id

    # --- deck scope --------------------------------------------------------

    def available_decks(self) -> list[str]:
        return self._catalog.available()

    def reload_decks(self) -> bool:
        """phase 2: read the course file again, so decks added to it can be enabled. The cards of the enabled
        decks follow at the next deck change. False if the file is invalid now; the current decks are kept."""
        return self._catalog.reload()

    def enable_deck(self, deck_name: str) -> bool:
        """Enable a deck the catalog lists. False if it does not exist or is already enabled."""
        if not self._catalog.is_available(deck_name):
            return False
        return self._core.enable_deck(deck_name)

    def disable_deck(self, deck_name: str) -> bool:
        return self._core.disable_deck(deck_name)

    # --- queries -----------------------------------------------------------

    def visible_cards(self, deck: Optional[str] = None, focused_group: Optional[str] = None) -> list[Flashcard]:
        return self._core.visible_cards(deck, focused_group)

    def get_card_by_id(self, card_id: str) -> Optional[Flashcard]:
        return self._core.get_card_by_id(card_id)

    def get_position_by_id(self, card_id: str) -> Optional[CardPosition]:
        return self._core.get_position_by_id(card_id)

    def deciding_group(self, card_id: str, focused_group: Optional[str] = None) -> Optional[CardGroup]:
        return self._core.deciding_group(card_id, focused_group)

    # --- constellations (runtime only) -------------------------------------

    @property
    def constellations(self) -> list[Constellation]:
        """The constellations of the last refresh (copies; reading never recalculates)."""
        return [Constellation(item.const_id, item.name, list(item.members)) for item in self._constellations]

    def refresh_constellations(
        self, visible_cards: Iterable[Flashcard], links: Optional[Iterable[CardLink]] = None
    ) -> list[Constellation]:
        """Derive the constellations again for the cards the map shows (deck and group focus already applied).
        `links` restricts the connections considered (the cluster module's cut-off line); by default all stored links."""
        self._derive([card.id for card in visible_cards], links)
        return self.constellations

    def delete_constellation_links(self, const_id: str) -> int:
        """Delete: remove the stored links between the members of the constellation and save at once.

        The members are the visible cards of the current runtime constellation; links to hidden cards stay.
        Returns the number of links removed (0 for an unknown id: nothing is changed or written).
        """
        constellation = next((item for item in self._constellations if item.const_id == str(const_id)), None)
        if constellation is None:
            return 0
        removed = self._core.delete_links_for_members(constellation.members)
        self._derive(self._visible_ids)
        return removed

    # --- mutations ---------------------------------------------------------

    def set_position(self, card_id: str, x: float, y: float, z: float) -> None:
        self._core.set_position(card_id, x, y, z)

    def set_difficulty(self, card_id: str, difficulty: int) -> None:
        self._core.set_difficulty(card_id, difficulty)

    def mark_read(self, card_id: str) -> None:
        self._core.mark_read(card_id)

    def create_group(self, card_id: str, name: str, color: str) -> str:
        return self._core.create_group(card_id, name, color)

    def add_to_group(self, card_id: str, group_id: str) -> None:
        self._core.add_to_group(card_id, group_id)

    def remove_from_group(self, card_id: str, group_id: str) -> None:
        self._core.remove_from_group(card_id, group_id)

    def delete_group(self, group_id: str) -> None:
        self._core.delete_group(group_id)

    def create_link(self, source_id: str, target_id: str) -> None:
        self._core.create_link(source_id, target_id)
        self._derive(self._visible_ids)

    def disconnect_link(self, source_id: str, target_id: str) -> None:
        self._core.disconnect_link(source_id, target_id)
        self._derive(self._visible_ids)

    # --- lifecycle ---------------------------------------------------------

    def refresh_deck_state(self, seed: Optional[int] = None) -> None:
        self._core.refresh_deck_state(seed)

    def reset_all_state(self, seed: Optional[int] = None) -> None:
        self._core.reset_all_state(seed)
        self._derive(self._visible_ids)

    def save(self) -> None:
        self._core.save()

    # --- internals ---------------------------------------------------------

    def _derive(self, visible_ids: list[str], links: Optional[Iterable[CardLink]] = None) -> None:
        self._visible_ids = list(visible_ids)
        components = derive_components(self._visible_ids, self._core.links if links is None else links)
        self._constellations = reconcile_constellations(self._constellations, components)