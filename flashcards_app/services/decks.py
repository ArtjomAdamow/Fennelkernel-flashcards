from flashcards_app import runtime
from flashcards_app.parser import load_decks


def deck_filter_options() -> list[dict[str, str]]:
    return [{"label": "None", "value": runtime.NONE_DECK}, {"label": "All decks", "value": "all"}] + [
        {"label": deck, "value": deck}
        for deck in sorted(runtime.ENABLED_DECKS)
    ]


def add_enabled_deck(deck_name: str) -> None:
    if deck_name in runtime.available_decks() and deck_name not in runtime.ENABLED_DECKS:
        runtime.ENABLED_DECKS.append(deck_name)
        runtime.ENABLED_DECKS.sort()
        runtime.CARDS[:] = load_decks(runtime.CARDS_DIR, runtime.ENABLED_DECKS)
        runtime.refresh_deck_state()


def remove_enabled_deck(deck_name: str) -> bool:
    if deck_name not in runtime.ENABLED_DECKS:
        return False
    runtime.ENABLED_DECKS.remove(deck_name)
    runtime.CARDS[:] = load_decks(runtime.CARDS_DIR, runtime.ENABLED_DECKS)
    runtime.refresh_deck_state()
    return True
