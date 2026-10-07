import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .models import CardGroup, CardLink, CardPosition, CardProgress


def load_positions(path: Path, card_ids: List[str], seed: int = 42) -> List[CardPosition]:

    from .geometry import sphere_positions

    if not path.exists():
        # Generate new positions if file doesn't exist
        return sphere_positions(card_ids, seed=seed)

    # Load existing positions from JSON
    payload = json.loads(path.read_text(encoding="utf-8"))
    stored = {item["card_id"]: CardPosition(**item) for item in payload.get("positions", [])}
    generated = sphere_positions(card_ids, seed=seed)
    
    # Use stored positions if available, otherwise use generated ones
    return [stored.get(position.card_id, position) for position in generated]

def load_progress(path: Path, card_ids: List[str]) -> Dict[str, CardProgress]:
    if not path.exists():
        # Create default progress if file doesn't exist
        return {card_id: CardProgress(card_id=card_id) for card_id in card_ids}

    # Load existing progress from JSON
    payload = json.loads(path.read_text(encoding="utf-8"))
    stored = {
        item["card_id"]: CardProgress(**item)
        for item in payload.get("progress", [])
        if item.get("card_id") in card_ids
    }
    
    # Return stored progress or create default for missing cards
    return {
        card_id: stored.get(card_id, CardProgress(card_id=card_id))
        for card_id in card_ids
    }


def load_groups(path: Path, card_ids: List[str]) -> List[CardGroup]:
    if not path.exists():
        return []

    valid_ids = set(card_ids)
    payload = json.loads(path.read_text(encoding="utf-8"))
    
    # Create groups with filtered card IDs
    return [
        CardGroup(
            id=item["id"],
            name=item["name"],
            color=item["color"],
            card_ids=[card_id for card_id in item.get("card_ids", []) if card_id in valid_ids],
        )
        for item in payload.get("groups", [])
    ]


def load_links(path: Path, card_ids: List[str]) -> List[CardLink]:
    if not path.exists():
        return []

    valid_ids = set(card_ids)
    payload = json.loads(path.read_text(encoding="utf-8"))
    
    # Create links only if both source and target cards exist
    return [
        CardLink(
            source_id=item["source_id"],
            target_id=item["target_id"],
            group_id=item.get("group_id"),
        )
        for item in payload.get("links", [])
        if item.get("source_id") in valid_ids and item.get("target_id") in valid_ids
    ]


def load_enabled_decks(path: Path, available_decks: List[str]) -> List[str]:
    if not path.exists():
        return list(available_decks)

    payload = json.loads(path.read_text(encoding="utf-8"))
    saved_decks = payload.get("decks")
    
    # If no saved decks, return all available decks
    if saved_decks is None:
        return list(available_decks)
    
    # Return only decks that are both saved and available
    available = set(available_decks)
    return [deck for deck in saved_decks if deck in available]


# ---------------------------------------------------------------------------
# File level access: passive reading and atomic writing of the whole state file.
# Nothing here filters by card ids, fills defaults or generates positions.
# ---------------------------------------------------------------------------

STATE_VERSION = 2  # current layout (pre-RAG). Version 1 files are no longer supported.
SUPPORTED_VERSIONS = frozenset({STATE_VERSION})

_WRITE_LOCK = threading.Lock()


class StateFileError(Exception):
    """The state file exists but cannot be used (invalid JSON or unsupported version)."""


@dataclass
class RawState:
    positions: List[CardPosition] = field(default_factory=list)
    progress: Dict[str, CardProgress] = field(default_factory=dict)
    groups: List[CardGroup] = field(default_factory=list)
    links: List[CardLink] = field(default_factory=list)
    decks: Optional[List[str]] = None  # None = the file does not store enabled decks


def read_state_file(path: Path, supported_versions=SUPPORTED_VERSIONS) -> Optional[RawState]:
    """Read the whole file once. Returns None if it does not exist."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise StateFileError(f"{path} is not valid JSON: {error}") from error

    version = payload.get("version") if isinstance(payload, dict) else None
    if not isinstance(version, int) or version not in supported_versions:
        raise StateFileError(
            f"{path} has state version {version!r}; supported versions: {sorted(supported_versions)}"
        )

    decks = payload.get("decks")
    return RawState(
        positions=[CardPosition(**item) for item in payload.get("positions", [])],
        progress={item["card_id"]: CardProgress(**item) for item in payload.get("progress", [])},
        groups=[
            CardGroup(
                id=item["id"],
                name=item["name"],
                color=item["color"],
                card_ids=list(item.get("card_ids", [])),
            )
            for item in payload.get("groups", [])
        ],
        links=[
            CardLink(
                source_id=item["source_id"],
                target_id=item["target_id"],
                group_id=item.get("group_id"),
            )
            for item in payload.get("links", [])
        ],
        decks=list(decks) if decks is not None else None,
    )


def write_state_file(path: Path, state: RawState, version: int = STATE_VERSION) -> None:
    """Write the whole file atomically: a crash or kill leaves the previous file intact."""
    payload = {
        "version": version,
        "positions": [asdict(position) for position in state.positions],
        "progress": [asdict(item) for item in state.progress.values()],
        "groups": [asdict(group) for group in state.groups],
        "links": [asdict(link) for link in state.links],
    }

    # Include enabled decks if provided
    if state.decks is not None:
        payload["decks"] = list(state.decks)

    text = json.dumps(payload, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    with _WRITE_LOCK:
        try:
            temp.write_text(text, encoding="utf-8")
            os.replace(temp, path)
        finally:
            if temp.exists():
                temp.unlink()


class JsonStateStore:
    """File-backed persistence for StateCore: read once, write atomically."""

    def __init__(self, path: Path, supported_versions=SUPPORTED_VERSIONS) -> None:
        self.path = Path(path)
        self._supported_versions = supported_versions

    def read(self) -> Optional[RawState]:
        return read_state_file(self.path, self._supported_versions)

    def write(self, state: RawState) -> None:
        write_state_file(self.path, state)


def save_state(
    path: Path,
    positions: List[CardPosition],
    progress: Dict[str, CardProgress],
    groups: Optional[List[CardGroup]] = None,
    links: Optional[List[CardLink]] = None,
    enabled_decks: Optional[List[str]] = None,
) -> None:
    write_state_file(
        path,
        RawState(
            positions=positions,
            progress=progress,
            groups=groups or [],
            links=links or [],
            decks=enabled_decks,
        ),
    )
