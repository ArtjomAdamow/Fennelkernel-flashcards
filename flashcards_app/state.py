import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .models import CardGroup, CardLink, CardPosition, CardProgress


# ---------------------------------------------------------------------------
# File level access: passive reading and atomic writing of the whole state file.
# Nothing here filters by card ids, fills defaults or generates positions.
# ---------------------------------------------------------------------------

STATE_VERSION = 2  # current layout (pre-RAG). Version 1 files are no longer supported.
SUPPORTED_VERSIONS = frozenset({STATE_VERSION})

_WRITE_LOCK = threading.Lock()


class StateFileError(Exception):
    """The state file exists but cannot be used (invalid JSON, unsupported version, or card_id keys instead of comb_id)."""


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

    # phase 1: positions and progress are keyed by comb_id. A version 2 file written before that has card_id
    # keys and is incompatible; it is refused instead of failing somewhere in the constructors below.
    for section in ("positions", "progress"):
        for item in payload.get(section, []):
            if not isinstance(item, dict) or "comb_id" not in item:
                raise StateFileError(
                    f"{path} is incompatible: {section} entries need a 'comb_id' key"
                    + (" (it has 'card_id', the key before comb_id)" if isinstance(item, dict) and "card_id" in item else "")
                )

    decks = payload.get("decks")
    return RawState(
        positions=[CardPosition(**item) for item in payload.get("positions", [])],
        progress={item["comb_id"]: CardProgress(**item) for item in payload.get("progress", [])},
        groups=[
            CardGroup(
                id=item["id"],
                name=item["name"],
                color=item["color"],
                card_ids=list(item.get("card_ids", [])),
                rank=item.get("rank"),
            )
            for item in payload.get("groups", [])
        ],
        links=[
            CardLink(
                source_id=item["source_id"],
                target_id=item["target_id"],
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
    """File-backed persistence for StateCore: read once, write atomically.

    `fallback_path` is an older file name: it is read when `path` does not exist yet, and never written.
    The first save then creates `path`, and the older file stays as it was.
    """

    def __init__(self, path: Path, supported_versions=SUPPORTED_VERSIONS, fallback_path: Optional[Path] = None) -> None:
        self.path = Path(path)
        self._supported_versions = supported_versions
        self._fallback_path = Path(fallback_path) if fallback_path is not None else None

    def read(self) -> Optional[RawState]:
        if not self.path.exists() and self._fallback_path is not None and self._fallback_path.exists():
            return read_state_file(self._fallback_path, self._supported_versions)
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
