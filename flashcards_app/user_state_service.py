"""User state service: the learner's state as the rest of the app sees it.

A facade over StateCore (the live state and its mutations) and the deck catalog (which decks exist in
the course file: JsonDeckCatalog; phase 2: the .md DeckCatalog is switched off).
It adds the one rule that needs the catalog: only decks that exist can be enabled.

The containers it exposes are the core's own live objects (same object on every access), because
panels, map, colors and callbacks read them directly and rely on in-place changes.
"""

from typing import Optional

from .deck_catalog import JsonDeckCatalog
from .models import CardGroup, CardLink, CardPosition, CardProgress, Flashcard
from .state_core import StateCore


class UserStateService:
    def __init__(self, core: StateCore, catalog: JsonDeckCatalog) -> None:
        self._core = core
        self._catalog = catalog

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

    def disconnect_link(self, source_id: str, target_id: str) -> None:
        self._core.disconnect_link(source_id, target_id)

    # --- lifecycle ---------------------------------------------------------

    def refresh_deck_state(self, seed: Optional[int] = None) -> None:
        self._core.refresh_deck_state(seed)

    def reset_all_state(self, seed: Optional[int] = None) -> None:
        self._core.reset_all_state(seed)

    def save(self) -> None:
        self._core.save()
