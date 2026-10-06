"""Deck catalog: which deck files exist on disk.

Stateless on purpose: the directory is re-read on every call, so a deck file
added while the app is running shows up the next time the catalog is asked.
"""

from pathlib import Path
from typing import Iterable


class DeckCatalog:
    def __init__(self, cards_dir: Path, exclude: Iterable[str] = ()) -> None:
        self._cards_dir = Path(cards_dir)
        # Names are compared case-insensitively, as runtime.available_decks always did
        self._exclude = {name.casefold() for name in exclude}

    def available(self) -> list[str]:
        return sorted(
            path.stem
            for path in self._cards_dir.glob("*.md")
            if path.stem.casefold() not in self._exclude
        )

    def is_available(self, deck_name: str) -> bool:
        return deck_name in self.available()
