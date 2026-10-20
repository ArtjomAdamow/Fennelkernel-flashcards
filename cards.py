"""Composition root: reads the configuration, builds the services, the Dash app and its callbacks, starts the server."""

import uuid
from dataclasses import dataclass
from pathlib import Path

from project.callbacks import register_callbacks
from project.content.deck_catalog import JsonDeckCatalog
from project.services.geometry import sphere_positions
from project.content.parser import CardsFile
from project.runtime import NONE_DECK, Runtime
from project.server import create_app
from project.store.state import JsonStateStore
from project.store.state_core import STARTUP_SEED, StateCore
from project.store.user_state_service import UserStateService

# Application configuration
BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "data" / "user_state.json" # all user state: positions, progress, groups, links, enabled decks
CARDS_FILE = BASE_DIR / "data" / "cards.json" # course file, read once at startup
SERVER_BOOT_ID = uuid.uuid4().hex


@dataclass(frozen=True)
class Composition:
    boot_id: str
    catalog: JsonDeckCatalog
    core: StateCore
    hub: Runtime
    dash_app: object

    @property
    def user_state(self) -> UserStateService:
        return self.hub.user_state


def compose(boot_id: str = SERVER_BOOT_ID) -> Composition:
    cards_file = CardsFile(CARDS_FILE) # the only read of the course file
    catalog = JsonDeckCatalog(cards_file, exclude={"readme", NONE_DECK}) # cannot be loaded: dummy NONE_DECK, readme deck
    core = StateCore(
        JsonStateStore(STATE_PATH), # phase 1: no fallback to positions.json, the state starts fresh with comb_id keys
        card_source=cards_file.load_decks,
        position_source=sphere_positions,
    )
    # Startup: read the state file once, then make everything consistent with the enabled decks
    core.load(catalog.available())
    core.refresh_deck_state(seed=STARTUP_SEED)

    hub = Runtime(user_state=UserStateService(core, catalog))
    dash_app = create_app(BASE_DIR, boot_id, hub.user_state)
    register_callbacks(dash_app, hub.user_state, NONE_DECK)
    return Composition(boot_id=boot_id, catalog=catalog, core=core, hub=hub, dash_app=dash_app)


composition = compose()
app = composition.dash_app


def main() -> None:
    # The startup save writes everything, including the enabled decks (fix F4)
    composition.user_state.save()
    app.run(debug=True)


if __name__ == "__main__":
    main()
