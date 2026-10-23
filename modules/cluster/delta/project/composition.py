"""Builds the cluster module's services, the Dash app and its callback (used by delta/cards.py and the tests).

* card state: the cards of the checked decks, random positions in a shell around the sun. A fresh state
  starts with no deck checked (the main app enables all decks). Stored positions too close to the sun are
  pushed out (the hard rule of services.positions).
* space state: one deck card per deck, always all decks, random positions in the ball.
* view settings: the checked cards of each deck, in their own file next to the card state, named after it
  (store.view_settings.view_state_path).
* the ViewRouter over both, handed to the server and the callback.
* hooks for a module on top (the helper): the two position sources are parameters of compose, defaulting to
  the random ones (deck_positions for the space state, card_positions for the card state), an optional
  module action (services.actions.ModuleAction): a button in the top bar that runs a function on the router, and
  an optional back of the card panel (overview_back): with nothing selected, Enter or a click on the panel flips
  between the dendrogram and what the function draws from the router.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from project.callbacks import register_callbacks
from project.content.deck_catalog import JsonDeckCatalog
from project.content.decks import SPACE_DECK, DeckIndex, SpaceCatalog
from project.content.parser import CardsFile
from project.runtime import NONE_DECK, Runtime
from project.server import create_app
from project.services.actions import ModuleAction
from project.services.geometry import sphere_positions
from project.services.positions import keep_off_the_sun, shell_positions
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
    hub: Runtime
    dash_app: object

    @property
    def user_state(self) -> ViewRouter:
        return self.hub.user_state


def compose(
    base_dir: Path,
    boot_id: str,
    cards_path: Path,
    state_path: Path,
    space_state_path: Path,
    deck_positions: PositionSource = sphere_positions,
    card_positions: PositionSource = shell_positions,
    action: Optional[ModuleAction] = None,
    overview_back: Optional[Callable[[ViewRouter], object]] = None,
) -> Composition:
    """Build the whole app from explicit paths. The position sources place the dots that have no stored
    position: decks in the space state, cards in the card state (random by default). The action, if any, is
    a module's button in the top bar; overview_back, if any, draws the back of the card panel while nothing is
    selected (a function of the router that returns a Dash component)."""
    cards_file = CardsFile(cards_path)  # the course file, read here and once more by DeckIndex for the deck ids
    catalog = JsonDeckCatalog(cards_file, exclude={"readme", NONE_DECK})
    decks = DeckIndex(cards_path, cards_file, catalog.available())

    card_store = JsonStateStore(state_path)
    fresh = card_store.read() is None
    core = StateCore(card_store, card_source=cards_file.load_decks, position_source=card_positions)
    # A fresh state starts with no deck checked: no available decks to enable on the first load
    core.load([] if fresh else catalog.available())
    core.refresh_deck_state(seed=STARTUP_SEED)
    keep_off_the_sun(core.positions)

    space_core = StateCore(JsonStateStore(space_state_path), card_source=decks.load, position_source=deck_positions)
    space_core.load([SPACE_DECK])
    space_core.refresh_deck_state(seed=STARTUP_SEED)

    # The checked cards of decks that are no longer checked are gone with their card state
    settings = ViewSettings(view_state_path(card_store.path))
    settings.keep_only(decks.by_name[name].deck_id for name in core.enabled_decks if name in decks.by_name)

    router = ViewRouter(
        space=UserStateService(space_core, SpaceCatalog()),
        cards=UserStateService(core, catalog),
        decks=decks,
        settings=settings,
    )
    hub = Runtime(user_state=router)
    dash_app = create_app(base_dir, boot_id, router, action)
    register_callbacks(dash_app, router, action=action, overview_back=overview_back)
    return Composition(boot_id=boot_id, catalog=catalog, core=core, space_core=space_core, hub=hub, dash_app=dash_app)
