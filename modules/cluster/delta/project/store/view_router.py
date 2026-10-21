"""The view router: one UserStateService-shaped object over the two states of the cluster module.

* space state: the deck cards (all decks, always loaded); the space view shows the checked decks.
* card state: the cards of the checked decks (its enabled decks); the deck view shows the checked cards of
  the entered deck (view settings, the Cards dialog).

The callback is written against one state service. The router forwards every attribute it does not define
itself to the service of the current view, so selection, navigation, connections, groups and constellations
work in both views through the same calls. The view lives here, server-side, like the rest of the state.
"""

from typing import Optional

from project.content.decks import DeckIndex
from project.models import Flashcard
from project.services.views import DECK, SPACE
from project.store.user_state_service import UserStateService
from project.store.view_settings import ViewSettings

_OWN = {"space", "cards_state", "decks", "settings", "view", "entered_deck"}


class ViewRouter:
    def __init__(self, space: UserStateService, cards: UserStateService, decks: DeckIndex, settings: ViewSettings) -> None:
        self.space = space
        self.cards_state = cards
        self.decks = decks
        self.settings = settings
        self.view = SPACE
        self.entered_deck: Optional[str] = None  # deck id

    def __getattr__(self, name):
        # Only called for names not found on the router: everything else is the active view's service
        if name in _OWN or name.startswith("__"):
            raise AttributeError(name)
        return getattr(self.active, name)

    @property
    def active(self) -> UserStateService:
        return self.cards_state if self.view == DECK else self.space

    # --- views -------------------------------------------------------------

    @property
    def entered_name(self) -> Optional[str]:
        info = self.decks.by_id.get(self.entered_deck) if self.entered_deck else None
        return info.name if info else None

    def set_view(self, view: str, entered: Optional[str] = None) -> None:
        """Switch views. A deck can only be entered while it is checked; otherwise the space view stays."""
        info = self.decks.by_id.get(entered) if entered else None
        if view == DECK and info is not None and info.name in self.cards_state.enabled_decks:
            self.view, self.entered_deck = DECK, entered
        else:
            self.view, self.entered_deck = SPACE, None

    def visible_cards(self, deck: Optional[str] = None, focused_group: Optional[str] = None) -> list[Flashcard]:
        """The dots of the current view: the checked decks, or the checked cards of the entered deck."""
        if self.view == DECK:
            name = self.entered_name
            if not name:
                return []
            shown = set(self.settings.shown(self.entered_deck))
            return [card for card in self.cards_state.visible_cards(name, focused_group) if card.id in shown]
        checked = set(self.cards_state.enabled_decks)
        return [card for card in self.space.visible_cards(None, focused_group) if card.question in checked]

    def deck_colors(self, deck_id: Optional[str]) -> list[str]:
        """The colours of the deck's groups in the space state, the oldest group (lowest rank) first."""
        groups = [group for group in self.space.groups if deck_id and deck_id in group.card_ids]
        groups.sort(key=lambda group: (group.rank is None, group.rank if group.rank is not None else 0))
        return [group.color for group in groups]

    # --- checked cards of the entered deck (the Cards dialog) ---------------

    def deck_cards(self) -> list[Flashcard]:
        """All cards of the entered deck, checked or not, in deck order."""
        name = self.entered_name if self.view == DECK else None
        return self.cards_state.visible_cards(name, None) if name else []

    def shown_cards(self) -> list[str]:
        """The checked cards of the entered deck."""
        ids = {card.id for card in self.deck_cards()}
        return [card_id for card_id in self.settings.shown(self.entered_deck) if card_id in ids] if ids else []

    def set_shown_cards(self, card_ids) -> None:
        """Check exactly these cards of the entered deck. Unchecking only hides a card: its state stays."""
        if self.view == DECK and self.entered_deck:
            ids = {card.id for card in self.deck_cards()}
            self.settings.set_shown(self.entered_deck, [card_id for card_id in card_ids if card_id in ids])

    # --- checked decks (the card state's enabled decks) ---------------------

    @property
    def enabled_decks(self) -> list[str]:
        return self.cards_state.enabled_decks

    def available_decks(self) -> list[str]:
        """All decks, in deck id order."""
        return [info.name for info in self.decks.infos]

    def enable_deck(self, deck_name: str) -> bool:
        return self.cards_state.enable_deck(deck_name)

    def disable_deck(self, deck_name: str) -> bool:
        """Uncheck a deck: its cards' state is stripped (as removing a deck always did), its checked cards are
        forgotten, and an entered deck is left."""
        changed = self.cards_state.disable_deck(deck_name)
        info = self.decks.by_name.get(deck_name)
        if changed and info is not None:
            self.settings.drop(info.deck_id)
        if changed and self.view == DECK and self.entered_name == deck_name:
            self.set_view(SPACE)
        return changed

    # --- lifecycle ---------------------------------------------------------

    def save(self) -> None:
        self.space.save()
        self.cards_state.save()
        self.settings.save()
