"""The view router: one UserStateService-shaped object over the two states of the cluster module.

* decks state (the space state file): the deck cards (all decks, always loaded); the decks view shows the
  checked decks.
* card state: the cards of the checked decks (its enabled decks) and a dot per checked topic of those decks
  (content.topics); the topics view shows the entered deck's topic dots, the cards view the checked cards of the
  entered topic (view settings, the Topics and Cards dialogs).

The callback is written against one state service. The router forwards every attribute it does not define
itself to the service of the current view, so selection, navigation, connections, groups and constellations
work in the three views through the same calls. The view lives here, server-side, like the rest of the state.

The cut-off line (runtime only, one per view, entered deck and entered topic, 1 = the full tree at every start):
below 1 the router's `links` are only the connections below the line (services.dendrogram.cut_links), so the map
draws the tree's lower part, the constellations fall apart accordingly, and the dendrogram shows the sub-trees
side by side. The stored links are never touched.

The topics view has no constellations (`constellations`, `refresh_constellations`; 2026-10-27, roadmap step 29):
the callback navigates the entered deck's visible topics as one constellation, connected or not, and the map
draws no topic connections; the stored ones stay for the dendrogram, and a module on top may add them.

Focus in the topics and cards views (runtime only, all checked again whenever the view changes): a checklist of
the groups plus "No group". A dot is hidden when none of its groups is checked (a dot in no group: when "No group"
is unchecked), and it takes the colour of its oldest checked group. The groups panel counts the view's dots only
(group_count): the entered deck's cards and topic dots, or the entered topic's cards.
"""

from typing import Callable, List, Optional

from project.content.decks import DeckIndex
from project.content.topics import TopicIndex, TopicInfo
from project.models import Flashcard
from project.services.dendrogram import cut_links
from project.services.views import CARDS, DECKS, TOPICS
from project.store.user_state_service import UserStateService
from project.store.view_settings import ViewSettings

_OWN = {
    "decks_state", "cards_state", "decks", "topics", "settings", "view", "entered_deck", "entered_topic", "cutoffs",
    "unchecked_groups", "_card_source",
}
FULL_TREE = 1.0
NO_GROUP = "__no_group__"  # the Focus checklist's entry for the cards in no group


def _age(group) -> tuple:
    """Sort key of the package's deciding_group: the lowest rank is the oldest group."""
    return (group.rank is None, group.rank if group.rank is not None else 0)


class ViewRouter:
    def __init__(
        self,
        decks_state: UserStateService,
        cards: UserStateService,
        decks: DeckIndex,
        settings: ViewSettings,
        topics: TopicIndex,
        card_source: Callable[[List[str]], List[Flashcard]],
    ) -> None:
        self.decks_state = decks_state
        self.cards_state = cards
        self.decks = decks
        self.topics = topics
        self.settings = settings
        self._card_source = card_source  # the card state's source, for the reload after a topic check
        self.view = DECKS
        self.entered_deck: Optional[str] = None  # deck id
        self.entered_topic: Optional[str] = None  # topic dot id
        self.cutoffs: dict[str, float] = {}  # view key -> the cut-off line (a share of the tree's height)
        self.unchecked_groups: set[str] = set()  # Focus: group ids (and NO_GROUP) unchecked

    def __getattr__(self, name):
        # Only called for names not found on the router: everything else is the active view's service
        if name in _OWN or name.startswith("__"):
            raise AttributeError(name)
        return getattr(self.active, name)

    @property
    def active(self) -> UserStateService:
        return self.decks_state if self.view == DECKS else self.cards_state

    # --- views -------------------------------------------------------------

    @property
    def entered_name(self) -> Optional[str]:
        info = self.decks.by_id.get(self.entered_deck) if self.entered_deck else None
        return info.name if info else None

    @property
    def entered_topic_info(self) -> Optional[TopicInfo]:
        return self.topics.by_dot_id.get(self.entered_topic) if self.entered_topic else None

    def set_view(self, view: str, entered: Optional[str] = None, entered_topic: Optional[str] = None) -> None:
        """Switch views. A deck can only be entered while it is checked, a topic only while its deck is checked
        and its dot is loaded (checked); otherwise the view stays one level up, or at the decks."""
        before = (self.view, self.entered_deck, self.entered_topic)
        info = self.decks.by_id.get(entered) if entered else None
        checked = info is not None and info.name in self.cards_state.enabled_decks
        topic = self.topics.by_dot_id.get(entered_topic) if entered_topic else None
        loaded = topic is not None and topic.deck_id == entered and entered_topic in self.cards_state.card_by_id
        if view == CARDS and checked and loaded:
            self.view, self.entered_deck, self.entered_topic = CARDS, entered, entered_topic
        elif view in (TOPICS, CARDS) and checked:
            self.view, self.entered_deck, self.entered_topic = TOPICS, entered, None
        else:
            self.view, self.entered_deck, self.entered_topic = DECKS, None, None
        if (self.view, self.entered_deck, self.entered_topic) != before:
            self.unchecked_groups = set()  # a new view starts with every group checked

    def is_topic(self, dot_id: Optional[str]) -> bool:
        return bool(dot_id) and self.topics.is_dot(dot_id)

    def is_rest(self, dot_id: Optional[str]) -> bool:
        topic = self.topics.by_dot_id.get(dot_id) if dot_id else None
        return bool(topic and topic.rest)

    def _deck_dots(self, name: str, focused_group: Optional[str] = None) -> list[Flashcard]:
        """Everything of the entered deck in the card state: its cards, then its loaded topic dots."""
        return self.cards_state.visible_cards(name, focused_group)

    def visible_cards(self, deck: Optional[str] = None, focused_group: Optional[str] = None) -> list[Flashcard]:
        """The dots of the current view: the checked decks; the entered deck's checked topics; the entered topic's
        checked cards. In the topics and cards views only the dots Focus keeps (in a checked group, or in none
        while "No group" is checked)."""
        if self.view == DECKS:
            checked = set(self.cards_state.enabled_decks)
            return [card for card in self.decks_state.visible_cards(None, focused_group) if card.question in checked]
        name = self.entered_name
        if not name:
            return []
        if self.view == TOPICS:
            dots = [card for card in self._deck_dots(name, focused_group) if self.is_topic(card.id)]
        else:
            shown = set(self.shown_cards())
            dots = [card for card in self._deck_dots(name, focused_group) if card.id in shown]
        return [card for card in dots if self._focused(card.id)] if self.unchecked_groups else dots

    # --- Focus in the topics and cards views -----------------------------------

    def _focused(self, card_id: str) -> bool:
        memberships = [group.id for group in self.cards_state.groups if card_id in group.card_ids]
        if not memberships:
            return NO_GROUP not in self.unchecked_groups
        return any(group_id not in self.unchecked_groups for group_id in memberships)

    def checked_groups(self) -> list[str]:
        """The Focus checklist's checked entries: the groups in list order, then NO_GROUP."""
        return [item for item in [group.id for group in self.groups] + [NO_GROUP] if item not in self.unchecked_groups]

    def set_checked_groups(self, checked=None) -> None:
        """Focus's Confirm in the topics and cards views; None (the All button) checks everything again."""
        if checked is None:
            self.unchecked_groups = set()
            return
        keep = set(checked)
        self.unchecked_groups = {item for item in [group.id for group in self.groups] + [NO_GROUP] if item not in keep}

    def deciding_group(self, card_id: str, focused_group: Optional[str] = None):
        """The group that colours a dot: in the topics and cards views its oldest checked group; otherwise the
        package's rule (the focused group if the dot is a member, else its oldest group)."""
        if self.view != DECKS and self.unchecked_groups:
            checked = [group for group in self.cards_state.groups if card_id in group.card_ids and group.id not in self.unchecked_groups]
            if checked:
                return min(checked, key=_age)
        return self.active.deciding_group(card_id, focused_group)

    def scope_ids(self) -> Optional[set[str]]:
        """The dots a groups panel counts: None for every member (the decks view); the entered deck's cards and
        topic dots (the topics view); the entered topic's cards (the cards view)."""
        if self.view == DECKS:
            return None
        if self.view == TOPICS:
            return {card.id for card in self._deck_dots(self.entered_name)} if self.entered_name else set()
        return {card.id for card in self.deck_cards()}

    def group_count(self, group) -> int:
        """The members a groups panel counts, within the view's scope (scope_ids)."""
        scope = self.scope_ids()
        if scope is None:
            return len(group.card_ids)
        return sum(card_id in scope for card_id in group.card_ids)

    def deck_colors(self, deck_id: Optional[str]) -> list[str]:
        """The colours of the deck's groups in the decks state, the oldest group (lowest rank) first."""
        groups = [group for group in self.decks_state.groups if deck_id and deck_id in group.card_ids]
        groups.sort(key=_age)
        return [group.color for group in groups]

    def topic_color(self, dot_id: Optional[str]) -> Optional[str]:
        """The colour of a topic dot's oldest group in the card state; None without a group."""
        group = self.cards_state.deciding_group(dot_id) if dot_id else None
        return group.color if group is not None else None

    # --- the cut-off line ---------------------------------------------------

    def view_key(self) -> str:
        """The decks view, the entered deck or the entered topic: each keeps its own cut-off line."""
        if self.view == CARDS:
            return f"{CARDS}:{self.entered_topic}"
        if self.view == TOPICS:
            return f"{TOPICS}:{self.entered_deck}"
        return DECKS

    def cutoff(self) -> float:
        """The view's cut-off line as a share of the tree's height; 1 is the full tree."""
        return self.cutoffs.get(self.view_key(), FULL_TREE)

    def set_cutoff(self, value: float) -> None:
        self.cutoffs[self.view_key()] = min(FULL_TREE, max(0.0, float(value)))

    def connected(self) -> bool:
        """Whether the view's dots have stored connections at all (the full tree, whatever the cut-off line):
        without any there is nothing to cut, and the cut-off slider is hidden (2026-10-27, the user)."""
        visible = {card.id for card in self.visible_cards()}
        return any(link.source_id in visible and link.target_id in visible for link in self.active.links)

    @property
    def links(self) -> list:
        """The active view's connections below the cut-off line; at the full tree the stored list itself."""
        stored = self.active.links
        cutoff = self.cutoff()
        if cutoff >= FULL_TREE:
            return stored
        return cut_links([card.id for card in self.visible_cards()], stored, cutoff)

    @property
    def constellations(self) -> list:
        """The active view's constellations; none in the topics view (2026-10-27, roadmap step 29), where the
        entered deck's topics are navigated as one constellation, connected or not, and nothing creates
        constellations. The topics' stored connections stay for the dendrogram."""
        if self.view == TOPICS:
            return []
        return self.active.constellations

    def refresh_constellations(self, visible_cards) -> list:
        """The active view's constellations over the connections below the cut-off line (the package's
        refresh_constellations takes the links to consider); nothing in the topics view."""
        if self.view == TOPICS:
            return []
        if self.cutoff() >= FULL_TREE:
            return self.active.refresh_constellations(visible_cards)
        return self.active.refresh_constellations(visible_cards, links=self.links)

    # --- the checked topics of the entered deck (the Topics dialog) -----------

    def deck_topics(self) -> list[TopicInfo]:
        """All topics of the entered deck, checked or not, in file order."""
        return list(self.topics.topics(self.entered_deck)) if self.view != DECKS else []

    def checked_topics(self) -> list[str]:
        """The dot ids of the entered deck's checked topics (the ones loaded in the card state), in file order."""
        return [topic.dot_id for topic in self.deck_topics() if topic.dot_id in self.cards_state.card_by_id]

    def set_checked_topics(self, dot_ids) -> None:
        """Check exactly these topics of the entered deck: the settings are written, the card state's dots are
        reloaded through the core's public containers (an unchecked topic's dot goes with its connections; its
        cards keep their state and are only not shown), and an unchecked entered topic returns to the topics
        view."""
        if self.view == DECKS or not self.entered_deck:
            return
        wanted = set(dot_ids)
        topic_ids = [topic.topic_id for topic in self.deck_topics() if topic.dot_id in wanted]
        self.settings.set_checked_topics(self.entered_deck, self.topics.signature(self.entered_deck), topic_ids)
        self.reload_dots()
        if self.view == CARDS and self.entered_topic not in self.cards_state.card_by_id:
            self.set_view(TOPICS, self.entered_deck)

    def reload_dots(self) -> None:
        """The core's own reload, through its public containers: the source again, then the refresh that strips
        whatever the source no longer gives and places what is new."""
        self.cards_state.cards[:] = self._card_source(list(self.cards_state.enabled_decks))
        self.cards_state.refresh_deck_state()

    # --- the checked cards of the entered topic (the Cards dialog) -------------

    def deck_cards(self) -> list[Flashcard]:
        """The dots the view's choice dialog lists: the entered deck's loaded topic dots (the topics view), or
        all cards of the entered topic, checked or not, in deck order (the cards view)."""
        name = self.entered_name
        if not name or self.view == DECKS:
            return []
        if self.view == TOPICS:
            return [card for card in self._deck_dots(name) if self.is_topic(card.id)]
        topic = self.entered_topic_info
        members = set(topic.card_ids) if topic else set()
        return [card for card in self._deck_dots(name) if card.id in members]

    def _deck_card_ids(self, name: str) -> list[str]:
        """All cards of a deck (no dots), in deck order."""
        return [card.id for card in self._deck_dots(name) if not self.is_topic(card.id)]

    def shown_cards(self) -> list[str]:
        """The checked cards of the entered topic, in deck order (all of them without an entry)."""
        if self.view != CARDS:
            return []
        ids = [card.id for card in self.deck_cards()]
        stored = self.settings.shown(self.entered_deck)
        if stored is None:
            return ids
        checked = set(stored)
        return [card_id for card_id in ids if card_id in checked]

    def set_shown_cards(self, card_ids) -> None:
        """Check exactly these cards of the entered topic; the deck's other cards keep their checks (a deck
        without an entry gets its first one from all cards checked). Unchecking only hides a card: its state
        stays."""
        if self.view != CARDS or not self.entered_deck or not self.entered_name:
            return
        topic_ids = {card.id for card in self.deck_cards()}
        wanted = set(card_ids) & topic_ids
        stored = self.settings.shown(self.entered_deck)
        kept = set(self._deck_card_ids(self.entered_name)) if stored is None else set(stored)
        self.settings.set_shown(
            self.entered_deck,
            [card_id for card_id in self._deck_card_ids(self.entered_name)
             if ((card_id in wanted) if card_id in topic_ids else (card_id in kept))],
        )

    # --- checked decks (the card state's enabled decks) ---------------------

    @property
    def enabled_decks(self) -> list[str]:
        return self.cards_state.enabled_decks

    def available_decks(self) -> list[str]:
        """All decks, in deck id order."""
        return [info.name for info in self.decks.infos]

    def enable_deck(self, deck_name: str) -> bool:
        """Check a deck: its cards and the dots of its topics (all, on a fresh deck) are loaded."""
        return self.cards_state.enable_deck(deck_name)

    def disable_deck(self, deck_name: str) -> bool:
        """Uncheck a deck: its cards' and topics' state is stripped (as removing a deck always did), its checked
        topics and cards are forgotten, and an entered deck is left."""
        changed = self.cards_state.disable_deck(deck_name)
        info = self.decks.by_name.get(deck_name)
        if changed and info is not None:
            self.settings.drop(info.deck_id)
        if changed and self.view != DECKS and self.entered_name == deck_name:
            self.set_view(DECKS)
        return changed

    # --- lifecycle ---------------------------------------------------------

    def save(self) -> None:
        self.decks_state.save()
        self.cards_state.save()
        self.settings.save()
