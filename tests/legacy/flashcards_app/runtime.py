"""Mutable application state: bootstrapped once at import time, mutated in place by services."""

from pathlib import Path
import time
import uuid

from flashcards_app.geometry import sphere_positions
from flashcards_app.models import CardProgress, Flashcard
from flashcards_app.parser import load_decks
from flashcards_app.state import load_enabled_decks, load_groups, load_links, load_positions, load_progress

# Application configuration
BASE_DIR = Path(__file__).resolve().parent.parent
STATE_PATH = BASE_DIR / "data" / "positions.json" # single cards position - random as placeholder
CARDS_DIR = BASE_DIR / "data" / "cards" # preprocessed examples
SERVER_BOOT_ID = uuid.uuid4().hex
NONE_DECK = "None" # this is a workaround to display empty map on startup


def available_decks() -> list[str]:
    return sorted(
        path.stem
        for path in CARDS_DIR.glob("*.md")
        if path.stem.casefold() not in {"readme", NONE_DECK.casefold()} # cannot be loaded: dummy NONE_DECK, readme files
    )


AVAILABLE_DECKS = available_decks()
ENABLED_DECKS = [
    deck
    for deck in load_enabled_decks(STATE_PATH, AVAILABLE_DECKS)
# DELETE?   if deck.casefold() != "readme" # cannot be loaded
]
CARDS = load_decks(CARDS_DIR, ENABLED_DECKS)
POSITIONS = load_positions(STATE_PATH, [card.id for card in CARDS])
PROGRESS = load_progress(STATE_PATH, [card.id for card in CARDS])
GROUPS = load_groups(STATE_PATH, [card.id for card in CARDS])
LINKS = load_links(STATE_PATH, [card.id for card in CARDS])
CARD_BY_ID = {card.id: card for card in CARDS}
POSITION_BY_ID = {position.card_id: position for position in POSITIONS}


def refresh_deck_state() -> None:
    card_ids = [card.id for card in CARDS]
    stored_positions = {position.card_id: position for position in POSITIONS}
    generated_positions = sphere_positions(card_ids, seed=time.time_ns())
    POSITIONS[:] = [stored_positions.get(position.card_id, position) for position in generated_positions]

    stored_progress = dict(PROGRESS)
    PROGRESS.clear()
    PROGRESS.update({card_id: stored_progress.get(card_id, CardProgress(card_id)) for card_id in card_ids})

    valid_ids = set(card_ids)
    for group in GROUPS:
        group.card_ids = [card_id for card_id in group.card_ids if card_id in valid_ids]
    LINKS[:] = [
        link for link in LINKS
        if link.source_id in valid_ids and link.target_id in valid_ids
    ]
    CARD_BY_ID.clear()
    CARD_BY_ID.update({card.id: card for card in CARDS})
    POSITION_BY_ID.clear()
    POSITION_BY_ID.update({position.card_id: position for position in POSITIONS})


def visible_cards(deck: str, focused_group: str | None) -> list[Flashcard]:
    cards = [] if deck in {None, NONE_DECK} else [card for card in CARDS if deck == "all" or card.deck == deck]
    if focused_group:
        group = next((item for item in GROUPS if item.id == focused_group), None)
        focused_ids = set(group.card_ids) if group else set()
        cards = [card for card in cards if card.id in focused_ids]
    return cards


def reset_all_state() -> None:
    generated = sphere_positions([card.id for card in CARDS], seed=time.time_ns())
    for position, replacement in zip(POSITIONS, generated):
        position.x, position.y, position.z = replacement.x, replacement.y, replacement.z
    for progress in PROGRESS.values():
        progress.read = False
        progress.difficulty = 1
    GROUPS.clear()
    LINKS.clear()
