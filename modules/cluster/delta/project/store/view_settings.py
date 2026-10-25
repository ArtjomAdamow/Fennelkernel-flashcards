"""What the topics and cards views show: the checked topics and the checked cards of each deck (the Topics and
Cards dialogs), kept in their own small file.

The file lives next to the card state, named after it (view_state_path: cluster_state.json ->
cluster_view_state.json; a module on top of this one, such as the helper, gets its own name the same way).

File version 2:
  * shown_cards: deck id -> the checked card ids. A deck without an entry shows all its cards (the default of a
    freshly checked deck); an entry lists the checked cards, an empty list none. A checked card stays checked
    whichever topic it is in.
  * checked_topics: deck id -> the checked topic ids with a signature of the deck's assignment (every card's
    topic, content.topics.deck_signature). An entry whose signature no longer matches the course is stale: the
    deck gets all its topics checked and the entry is dropped at startup (drop_stale_topics).
A version 1 file holds shown_cards only: its entries are kept, and every deck's topics are checked.

Unchecking a deck drops both entries, together with its card state.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

VIEW_STATE_NAME = "cluster_view_state.json"  # the name next to a card state not named <name>_state.json
VERSION = 2


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
        self._shown: Dict[str, List[str]] = {}
        self._topics: Dict[str, Tuple[str, List[str]]] = {}  # deck id -> (signature, checked topic ids)
        self._read()

    def _read(self) -> None:
        if not self.path.exists():
            return
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return
        shown = payload.get("shown_cards", {})
        if isinstance(shown, dict):
            self._shown = {str(deck): [str(card) for card in cards] for deck, cards in shown.items() if isinstance(cards, list)}
        topics = payload.get("checked_topics", {})
        if isinstance(topics, dict):
            for deck, entry in topics.items():
                if isinstance(entry, dict) and isinstance(entry.get("topics"), list):
                    self._topics[str(deck)] = (str(entry.get("signature", "")), [str(topic) for topic in entry["topics"]])

    # --- the checked cards (the Cards dialog) --------------------------------

    def shown(self, deck_id: str) -> Optional[List[str]]:
        """The checked cards of a deck, in the order they were stored; None without an entry (all cards)."""
        cards = self._shown.get(deck_id)
        return None if cards is None else list(cards)

    def set_shown(self, deck_id: str, card_ids: Iterable[str]) -> None:
        self._shown[deck_id] = list(card_ids)

    # --- the checked topics (the Topics dialog) ------------------------------

    def checked_topics(self, deck_id: str, signature: str) -> Optional[List[str]]:
        """The checked topic ids of a deck, if its entry was made for this assignment (signature); None without
        an entry or with a stale one (all topics)."""
        entry = self._topics.get(deck_id)
        if entry is None or entry[0] != signature:
            return None
        return list(entry[1])

    def set_checked_topics(self, deck_id: str, signature: str, topic_ids: Iterable[str]) -> None:
        self._topics[deck_id] = (signature, list(topic_ids))

    def drop_stale_topics(self, signatures: Mapping[str, str]) -> List[str]:
        """Forget the topic entries of decks that are gone or whose assignment changed (their topics are all
        checked again). Returns the deck ids dropped."""
        stale = [deck for deck, (signature, _topics) in self._topics.items() if signatures.get(deck) != signature]
        for deck in stale:
            del self._topics[deck]
        return stale

    # --- both ----------------------------------------------------------------

    def drop(self, deck_id: str) -> None:
        self._shown.pop(deck_id, None)
        self._topics.pop(deck_id, None)

    def keep_only(self, deck_ids: Iterable[str]) -> None:
        """Forget the entries of decks that are no longer checked (their card state is gone)."""
        keep = set(deck_ids)
        for deck_id in [deck for deck in self._shown if deck not in keep]:
            del self._shown[deck_id]
        for deck_id in [deck for deck in self._topics if deck not in keep]:
            del self._topics[deck_id]

    def save(self) -> None:
        """Write the whole file atomically, like the state files."""
        payload = {
            "version": VERSION,
            "shown_cards": self._shown,
            "checked_topics": {deck: {"signature": signature, "topics": topics} for deck, (signature, topics) in self._topics.items()},
        }
        text = json.dumps(payload, indent=2)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(f"{self.path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temp.write_text(text, encoding="utf-8")
            os.replace(temp, self.path)
        finally:
            if temp.exists():
                temp.unlink()
