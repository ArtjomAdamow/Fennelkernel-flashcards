from flashcards_app import runtime


def deck_filter_options() -> list[dict[str, str]]:
    return [{"label": "None", "value": runtime.NONE_DECK}, {"label": "All decks", "value": "all"}] + [
        {"label": deck, "value": deck}
        for deck in sorted(runtime.USER_STATE.enabled_decks)
    ]


def add_enabled_deck(deck_name: str) -> None:
    runtime.USER_STATE.enable_deck(deck_name)


def remove_enabled_deck(deck_name: str) -> bool:
    return runtime.USER_STATE.disable_deck(deck_name)
