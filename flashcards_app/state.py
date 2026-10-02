import json
from dataclasses import asdict
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


def save_state(
    path: Path,
    positions: List[CardPosition],
    progress: Dict[str, CardProgress],
    groups: Optional[List[CardGroup]] = None,
    links: Optional[List[CardLink]] = None,
    enabled_decks: Optional[List[str]] = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 2,
        "positions": [asdict(position) for position in positions],
        "progress": [asdict(item) for item in progress.values()],
        "groups": [asdict(group) for group in groups or []],
        "links": [asdict(link) for link in links or []],
    }
    
    # Include enabled decks if provided
    if enabled_decks is not None:
        payload["decks"] = list(enabled_decks)
    
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
