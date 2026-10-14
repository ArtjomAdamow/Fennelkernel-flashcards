"""Deck catalog: which decks exist (draft replacement for flashcards_app/deck_catalog.py). Two catalogs:

  * DeckCatalog: the .md deck files, unchanged from the project. Stateless on purpose: the directory
    is re-read on every call, so a deck file added while the app is running shows up the next time
    the catalog is asked (live update).
  * JsonDeckCatalog: the decks of the course file (parser.CardsFile). The names are taken once, on
    construction, from the already parsed file; the file itself is never touched. No live update.
"""

from pathlib import Path
from typing import Iterable

from .parser import CardsFile


class DeckCatalog:
    def __init__(self, cards_dir: Path, exclude: Iterable[str] = ()) -> None:
        self._cards_dir = Path(cards_dir)
        # Names are compared case-insensitively, as the deck discovery always did
        self._exclude = {name.casefold() for name in exclude}

    def available(self) -> list[str]:
        return sorted(
            path.stem
            for path in self._cards_dir.glob("*.md")
            if path.stem.casefold() not in self._exclude
        )

    def is_available(self, deck_name: str) -> bool:
        return deck_name in self.available()


class JsonDeckCatalog:
    def __init__(self, cards_file: CardsFile, exclude: Iterable[str] = ()) -> None:
        # Same exclusion rule as DeckCatalog (case-insensitive), applied once
        excluded = {name.casefold() for name in exclude}
        self._names = sorted(name for name in cards_file.deck_names if name.casefold() not in excluded)

    def available(self) -> list[str]:
        # A copy: callers may change the list they get
        return list(self._names)

    def is_available(self, deck_name: str) -> bool:
        return deck_name in self._names
