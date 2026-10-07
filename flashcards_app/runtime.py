"""Application state hub (transition): a router over StateCore.

The old module-level names (CARDS, POSITIONS, PROGRESS, GROUPS, LINKS, ENABLED_DECKS,
CARD_BY_ID, POSITION_BY_ID) are kept. They are the very objects owned by CORE and are only
ever changed in place, so every module that imported them by name keeps working.
"""

from pathlib import Path
import uuid

from flashcards_app.deck_catalog import DeckCatalog
from flashcards_app.geometry import sphere_positions
from flashcards_app.models import Flashcard
from flashcards_app.parser import load_decks
from flashcards_app.state import JsonStateStore
from flashcards_app.state_core import STARTUP_SEED, StateCore

# Application configuration
BASE_DIR = Path(__file__).resolve().parent.parent
STATE_PATH = BASE_DIR / "data" / "positions.json" # single cards position - random as placeholder
CARDS_DIR = BASE_DIR / "data" / "cards" # preprocessed examples
SERVER_BOOT_ID = uuid.uuid4().hex
NONE_DECK = "None" # this is a workaround to display empty map on startup
CATALOG = DeckCatalog(CARDS_DIR, exclude={"readme", NONE_DECK}) # cannot be loaded: dummy NONE_DECK, readme files


def available_decks() -> list[str]:
    return CATALOG.available()


AVAILABLE_DECKS = available_decks()

# Startup: read the state file once, then make everything consistent with the enabled decks
CORE = StateCore(
    JsonStateStore(STATE_PATH),
    card_source=lambda decks: load_decks(CARDS_DIR, decks),
    position_source=sphere_positions,
)
CORE.load(AVAILABLE_DECKS)
CORE.refresh_deck_state(seed=STARTUP_SEED)

# Old names -> the same objects (never rebind these, only change them in place)
ENABLED_DECKS = CORE.enabled_decks
CARDS = CORE.cards
POSITIONS = CORE.positions
PROGRESS = CORE.progress
GROUPS = CORE.groups
LINKS = CORE.links
CARD_BY_ID = CORE.card_by_id
POSITION_BY_ID = CORE.position_by_id


def refresh_deck_state() -> None:
    CORE.refresh_deck_state()


def visible_cards(deck: str, focused_group: str | None) -> list[Flashcard]:
    # "all" and NONE_DECK are UI sentinels: the core only knows "one deck" or "any deck"
    if deck in {None, NONE_DECK}:
        return []
    return CORE.visible_cards(None if deck == "all" else deck, focused_group)


def reset_all_state() -> None:
    CORE.reset_all_state()
