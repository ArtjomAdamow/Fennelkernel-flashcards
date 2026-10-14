"""Composition root: reads the configuration, builds the services, the Dash app and its callbacks, starts the server."""

import uuid
from dataclasses import dataclass
from pathlib import Path

from flashcards_app.callbacks import register_callbacks
from flashcards_app.deck_catalog import DeckCatalog
from flashcards_app.geometry import sphere_positions
from flashcards_app.parser import load_decks
from flashcards_app.runtime import NONE_DECK, Runtime
from flashcards_app.server import create_app
from flashcards_app.state import JsonStateStore
from flashcards_app.state_core import STARTUP_SEED, StateCore
from flashcards_app.user_state_service import UserStateService

# Application configuration
BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "data" / "user_state.json" # all user state: positions, progress, groups, links, enabled decks
LEGACY_STATE_PATH = BASE_DIR / "data" / "positions.json" # the file name before tranche 9: read once while user_state.json does not exist
CARDS_DIR = BASE_DIR / "data" / "cards" # preprocessed examples
SERVER_BOOT_ID = uuid.uuid4().hex


@dataclass(frozen=True)
class Composition:
    boot_id: str
    catalog: DeckCatalog
    core: StateCore
    hub: Runtime
    dash_app: object

    @property
    def user_state(self) -> UserStateService:
        return self.hub.user_state


def compose(boot_id: str = SERVER_BOOT_ID) -> Composition:
    catalog = DeckCatalog(CARDS_DIR, exclude={"readme", NONE_DECK}) # cannot be loaded: dummy NONE_DECK, readme files
    core = StateCore(
        JsonStateStore(STATE_PATH, fallback_path=LEGACY_STATE_PATH),
        card_source=lambda decks: load_decks(CARDS_DIR, decks),
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
