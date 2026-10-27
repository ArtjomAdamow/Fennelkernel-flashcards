"""Builds the cluster module's services, the Dash app and its callback (used by delta/cards.py and the tests).

* card state: the cards of the checked decks and a dot per checked topic of those decks (content.topics). A
  fresh state starts with every deck checked, as the main app does (the user, 2026-10-25; until then with none).
  Positions by kind: topic dots in the shell around the center, cards on the surface of their topic's sphere;
  stored positions that break the hard rules of services.positions are corrected at startup (dots too close to
  the center pushed out, cards scaled onto the surface).
* space state (the decks' 3D space): one deck card per deck, always all decks, random positions on the surface of
  the unit sphere. Stored positions off the surface (an earlier run's, a model's) are scaled onto it.
* view settings: the checked topics and the checked cards of each deck, in their own file next to the card
  state, named after it (store.view_settings.view_state_path). Read before the card state, whose source reads
  them; stale topic entries (a changed assignment) are dropped first.
* the ViewRouter over both, handed to the server and the callback. It sorts the loaded topic dots into the
  predefined groups of the topics view (content.topic_groups) before the app is built.
* hooks for a module on top (the helper): the three position sources are parameters of compose, defaulting to
  the random ones (deck_positions for the space state, card_positions for the cards and topic_positions for the
  topic dots of the card state), an optional module action (services.actions.ModuleAction): a button in the top
  bar that runs a function on the router, and an optional back of the card panel (overview_back): with nothing
  selected, Enter or a click on the panel flips between the dendrogram and what the function draws from the
  router. The topic_positions hook (the user, 2026-10-25) is for the helper's model positions of the topics and
  can go once the merge of this module into the main project is decided.
* the cards' images (content.images): the folder `images_dir` (data/images by default) is indexed once, by
  comb_id, and handed to the router with the course's answer options (CardsFile.quiz); files that match no card
  are reported, not refused (2026-10-27, roadmap step 31).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from project.callbacks import register_callbacks
from project.content.deck_catalog import JsonDeckCatalog
from project.content.decks import SPACE_DECK, DeckIndex, SpaceCatalog
from project.content.images import ImageIndex, image_index
from project.content.parser import CardsFile
from project.content.topics import TopicIndex
from project.runtime import NONE_DECK, Runtime
from project.server import create_app
from project.services.actions import ModuleAction
from project.services.positions import keep_off_the_center, keep_on_the_surface, shell_positions, surface_positions
from project.store.state import JsonStateStore
from project.store.state_core import STARTUP_SEED, PositionSource, StateCore
from project.store.user_state_service import UserStateService
from project.store.view_router import ViewRouter
from project.store.view_settings import ViewSettings, view_state_path


@dataclass(frozen=True)
class Composition:
    boot_id: str
    catalog: JsonDeckCatalog
    core: StateCore
    space_core: StateCore
    topics: TopicIndex
    hub: Runtime
    dash_app: object
    images: ImageIndex

    @property
    def user_state(self) -> ViewRouter:
        return self.hub.user_state


def compose(
    base_dir: Path,
    boot_id: str,
    cards_path: Path,
    state_path: Path,
    space_state_path: Path,
    deck_positions: PositionSource = surface_positions,
    card_positions: PositionSource = surface_positions,
    topic_positions: PositionSource = shell_positions,
    action: Optional[ModuleAction] = None,
    overview_back: Optional[Callable[[ViewRouter], object]] = None,
    images_dir: Optional[Path] = None,
) -> Composition:
    """Build the whole app from explicit paths. The position sources place the dots that have no stored
    position: decks in the space state (on the sphere's surface), cards (on the surface too) and topic dots (in
    the shell around the center) in the card state, random by default; the hard rules then correct every stored
    or given position. The action, if any, is a module's button in the top bar; overview_back, if any, draws the
    back of the card panel while nothing is selected (a function of the router that returns a Dash component);
    images_dir is the folder of the cards' images (base_dir/data/images by default; a missing folder has none)."""
    cards_file = CardsFile(cards_path)  # the course file, read here and once more by DeckIndex for the deck ids
    catalog = JsonDeckCatalog(cards_file, exclude={"readme", NONE_DECK})
    decks = DeckIndex(cards_path, cards_file, catalog.available())
    topics = TopicIndex(cards_file, decks)
    images = image_index(
        Path(images_dir) if images_dir is not None else Path(base_dir) / "data" / "images",
        (card.comb_id for card in cards_file.load_decks()),
    )
    if images.unmatched:
        shown = ", ".join(images.unmatched[:5]) + (", ..." if len(images.unmatched) > 5 else "")
        print(f"{len(images.unmatched)} image file(s) in {images.folder} match no card: {shown}")

    card_store = JsonStateStore(state_path)
    # The settings come first: the card state's source reads the checked topics; a changed assignment resets them
    settings = ViewSettings(view_state_path(card_store.path))
    settings.drop_stale_topics(topics.signatures())
    card_source = topics.card_source(cards_file, decks, settings)
    core = StateCore(
        card_store, card_source=card_source, position_source=topics.position_source(card_positions, topic_positions)
    )
    # A fresh state (no stored decks) starts with every available deck checked, as the main app does
    core.load(catalog.available())
    core.refresh_deck_state(seed=STARTUP_SEED)
    keep_off_the_center([position for position in core.positions if topics.is_dot(position.comb_id)])
    keep_on_the_surface([position for position in core.positions if not topics.is_dot(position.comb_id)])

    space_core = StateCore(JsonStateStore(space_state_path), card_source=decks.load, position_source=deck_positions)
    space_core.load([SPACE_DECK])
    space_core.refresh_deck_state(seed=STARTUP_SEED)
    keep_on_the_surface(space_core.positions)

    # The checked topics and cards of decks that are no longer checked are gone with their card state
    settings.keep_only(decks.by_name[name].deck_id for name in core.enabled_decks if name in decks.by_name)

    router = ViewRouter(
        decks_state=UserStateService(space_core, SpaceCatalog()),
        cards=UserStateService(core, catalog),
        decks=decks,
        settings=settings,
        topics=topics,
        card_source=card_source,
        quiz_of=cards_file.quiz,
        images=images,
    )
    router.sync_topic_groups()
    hub = Runtime(user_state=router)
    dash_app = create_app(base_dir, boot_id, router, action)
    register_callbacks(dash_app, router, action=action, overview_back=overview_back)
    return Composition(
        boot_id=boot_id, catalog=catalog, core=core, space_core=space_core, topics=topics, hub=hub, dash_app=dash_app,
        images=images,
    )
