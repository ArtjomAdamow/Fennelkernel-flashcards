"""The view router: one UserStateService-shaped object over the two states of the cluster module.

* space state: the deck cards (all decks, always loaded); the space view shows the checked decks.
* card state: the cards of the checked decks (its enabled decks); the deck view shows the checked cards of
  the entered deck (view settings, the Cards dialog).

The callback is written against one state service. The router forwards every attribute it does not define
itself to the service of the current view, so selection, navigation, connections, groups and constellations
work in both views through the same calls. The view lives here, server-side, like the rest of the state.

The cut-off line (runtime only, one per view and entered deck, 1 = the full tree at every start): below 1 the
router's `links` are only the connections below the line (services.dendrogram.cut_links), so the map draws the
tree's lower part, the constellations fall apart accordingly, and the dendrogram shows the sub-trees side by
side. The stored links are never touched.

Focus in the deck view (runtime only, all checked again whenever the view changes): a checklist of the groups
plus "No group". A card is hidden when none of its groups is checked (a card in no group: when "No group" is
unchecked), and it takes the colour of its oldest checked group. The groups panel counts the entered deck's
cards only (group_count).
"""

from typing import Optional

from project.content.decks import DeckIndex
from project.models import Flashcard
from project.services.dendrogram import cut_links
from project.services.views import DECK, SPACE
from project.store.user_state_service import UserStateService
from project.store.view_settings import ViewSettings

_OWN = {"space", "cards_state", "decks", "settings", "view", "entered_deck", "cutoffs", "unchecked_groups"}
FULL_TREE = 1.0
NO_GROUP = "__no_group__"  # the Focus checklist's entry for the cards in no group


def _age(group) -> tuple:
    """Sort key of the package's deciding_group: the lowest rank is the oldest group."""
    return (group.rank is None, group.rank if group.rank is not None else 0)


class ViewRouter:
    def __init__(self, space: UserStateService, cards: UserStateService, decks: DeckIndex, settings: ViewSettings) -> None:
        self.space = space
        self.cards_state = cards
        self.decks = decks
        self.settings = settings
        self.view = SPACE
        self.entered_deck: Optional[str] = None  # deck id
        self.cutoffs: dict[str, float] = {}  # view key -> the cut-off line (a share of the tree's height)
        self.unchecked_groups: set[str] = set()  # the deck view's Focus: group ids (and NO_GROUP) unchecked

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
        before = (self.view, self.entered_deck)
        info = self.decks.by_id.get(entered) if entered else None
        if view == DECK and info is not None and info.name in self.cards_state.enabled_decks:
            self.view, self.entered_deck = DECK, entered
        else:
            self.view, self.entered_deck = SPACE, None
        if (self.view, self.entered_deck) != before:
            self.unchecked_groups = set()  # a new view starts with every group checked

    def visible_cards(self, deck: Optional[str] = None, focused_group: Optional[str] = None) -> list[Flashcard]:
        """The dots of the current view: the checked decks, or the checked cards of the entered deck that Focus
        keeps (in a checked group, or in none while "No group" is checked)."""
        if self.view == DECK:
            name = self.entered_name
            if not name:
                return []
            shown = set(self.settings.shown(self.entered_deck))
            cards = [card for card in self.cards_state.visible_cards(name, focused_group) if card.id in shown]
            return [card for card in cards if self._focused(card.id)] if self.unchecked_groups else cards
        checked = set(self.cards_state.enabled_decks)
        return [card for card in self.space.visible_cards(None, focused_group) if card.question in checked]

    # --- Focus in the deck view ---------------------------------------------

    def _focused(self, card_id: str) -> bool:
        memberships = [group.id for group in self.cards_state.groups if card_id in group.card_ids]
        if not memberships:
            return NO_GROUP not in self.unchecked_groups
        return any(group_id not in self.unchecked_groups for group_id in memberships)

    def checked_groups(self) -> list[str]:
        """The Focus checklist's checked entries: the groups in list order, then NO_GROUP."""
        return [item for item in [group.id for group in self.groups] + [NO_GROUP] if item not in self.unchecked_groups]

    def set_checked_groups(self, checked=None) -> None:
        """Focus's Confirm in the deck view; None (the All button) checks everything again."""
        if checked is None:
            self.unchecked_groups = set()
            return
        keep = set(checked)
        self.unchecked_groups = {item for item in [group.id for group in self.groups] + [NO_GROUP] if item not in keep}

    def deciding_group(self, card_id: str, focused_group: Optional[str] = None):
        """The group that colours a card: in the deck view its oldest checked group; otherwise the package's rule
        (the focused group if the card is a member, else its oldest group)."""
        if self.view == DECK and self.unchecked_groups:
            checked = [group for group in self.cards_state.groups if card_id in group.card_ids and group.id not in self.unchecked_groups]
            if checked:
                return min(checked, key=_age)
        return self.active.deciding_group(card_id, focused_group)

    def group_count(self, group) -> int:
        """The members a groups panel counts: in the deck view only the entered deck's cards."""
        if self.view != DECK:
            return len(group.card_ids)
        ids = {card.id for card in self.deck_cards()}
        return sum(card_id in ids for card_id in group.card_ids)

    def deck_colors(self, deck_id: Optional[str]) -> list[str]:
        """The colours of the deck's groups in the space state, the oldest group (lowest rank) first."""
        groups = [group for group in self.space.groups if deck_id and deck_id in group.card_ids]
        groups.sort(key=_age)
        return [group.color for group in groups]

    # --- the cut-off line ---------------------------------------------------

    def view_key(self) -> str:
        """The space view, or the entered deck: each keeps its own cut-off line."""
        return f"{DECK}:{self.entered_deck}" if self.view == DECK else SPACE

    def cutoff(self) -> float:
        """The view's cut-off line as a share of the tree's height; 1 is the full tree."""
        return self.cutoffs.get(self.view_key(), FULL_TREE)

    def set_cutoff(self, value: float) -> None:
        self.cutoffs[self.view_key()] = min(FULL_TREE, max(0.0, float(value)))

    @property
    def links(self) -> list:
        """The active view's connections below the cut-off line; at the full tree the stored list itself."""
        stored = self.active.links
        cutoff = self.cutoff()
        if cutoff >= FULL_TREE:
            return stored
        return cut_links([card.id for card in self.visible_cards()], stored, cutoff)

    def refresh_constellations(self, visible_cards) -> list:
        """The active view's constellations over the connections below the cut-off line (the package's
        refresh_constellations takes the links to consider)."""
        if self.cutoff() >= FULL_TREE:
            return self.active.refresh_constellations(visible_cards)
        return self.active.refresh_constellations(visible_cards, links=self.links)

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
