"""Deck catalog: which decks exist. Two catalogs:

  * DeckCatalog: the .md deck files, unchanged from the project. Stateless on purpose: the directory
    is re-read on every call, so a deck file added while the app is running shows up the next time
    the catalog is asked (live update). Switched off (phase 1) with the .md source, see
    parser.MD_SOURCE_ENABLED.
  * JsonDeckCatalog: the decks of the course file (parser.CardsFile). The names come from the parsed
    file in memory. No live update: the file is read again only by reload() (phase 2: the deck "Add" button).
"""

from pathlib import Path
from typing import Iterable

from .parser import CardsFile, require_md_source


class DeckCatalog:
    def __init__(self, cards_dir: Path, exclude: Iterable[str] = ()) -> None:
        require_md_source()
        self._cards_dir = Path(cards_dir)
        # Names are compared case-insensitively, as the deck discovery always did
        self._exclude = {name.casefold() for name in exclude}

    def available(self) -> list[str]:
        require_md_source()
        return sorted(
            path.stem
            for path in self._cards_dir.glob("*.md")
            if path.stem.casefold() not in self._exclude
        )

    def is_available(self, deck_name: str) -> bool:
        return deck_name in self.available()


class JsonDeckCatalog:
    def __init__(self, cards_file: CardsFile, exclude: Iterable[str] = ()) -> None:
        # Same exclusion rule as DeckCatalog (case-insensitive)
        self._cards_file = cards_file
        self._excluded = {name.casefold() for name in exclude}

    def available(self) -> list[str]:
        # phase 2: asked from the course file each time, so a reload() shows up. A new list: callers may change it
        return sorted(name for name in self._cards_file.deck_names if name.casefold() not in self._excluded)

    def is_available(self, deck_name: str) -> bool:
        return deck_name in self.available()

    def reload(self) -> bool:
        """phase 2: read the course file again (the deck "Add" button). False if it is invalid; the course stays."""
        return self._cards_file.reload()
