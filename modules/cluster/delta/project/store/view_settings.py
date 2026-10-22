"""What the deck view shows: the checked cards of each deck (the Cards dialog), kept in their own small file.

The file lives next to the card state, named after it (view_state_path: cluster_state.json ->
cluster_view_state.json; a module on top of this one, such as the helper, gets its own name the same way).
A deck without an entry shows no card: a freshly checked deck starts with all its cards unchecked. Unchecking a
deck drops its entry, together with its card state.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Iterable

VIEW_STATE_NAME = "cluster_view_state.json"  # the name next to a card state not named <name>_state.json
VERSION = 1


def view_state_path(card_state_path: Path) -> Path:
    """The view state file next to a card state file: <name>_state.json -> <name>_view_state.json.
    A card state with another name gets VIEW_STATE_NAME next to it."""
    card_state_path = Path(card_state_path)
    suffix = "_state.json"
    if card_state_path.name.endswith(suffix) and len(card_state_path.name) > len(suffix):
        return card_state_path.with_name(card_state_path.name[: -len(suffix)] + "_view_state.json")
    return card_state_path.with_name(VIEW_STATE_NAME)


class ViewSettings:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._shown: dict[str, list[str]] = self._read()

    def _read(self) -> dict[str, list[str]]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        shown = payload.get("shown_cards", {}) if isinstance(payload, dict) else {}
        return {str(deck): [str(card) for card in cards] for deck, cards in shown.items() if isinstance(cards, list)}

    def shown(self, deck_id: str) -> list[str]:
        """The checked cards of a deck, in the order they were stored."""
        return list(self._shown.get(deck_id, []))

    def set_shown(self, deck_id: str, card_ids: Iterable[str]) -> None:
        self._shown[deck_id] = list(card_ids)

    def drop(self, deck_id: str) -> None:
        self._shown.pop(deck_id, None)

    def keep_only(self, deck_ids: Iterable[str]) -> None:
        """Forget the entries of decks that are no longer checked (their card state is gone)."""
        keep = set(deck_ids)
        for deck_id in [deck for deck in self._shown if deck not in keep]:
            del self._shown[deck_id]

    def save(self) -> None:
        """Write the whole file atomically, like the state files."""
        text = json.dumps({"version": VERSION, "shown_cards": self._shown}, indent=2)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(f"{self.path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temp.write_text(text, encoding="utf-8")
            os.replace(temp, self.path)
        finally:
            if temp.exists():
                temp.unlink()
