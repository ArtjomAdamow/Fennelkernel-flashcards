import json
from dataclasses import asdict
from pathlib import Path

from .models import CardGroup, CardLink, CardPosition, CardProgress


def load_positions(path: Path, card_ids: list[str], seed: int = 42) -> list[CardPosition]:
    from .geometry import sphere_positions

    if not path.exists():
        return sphere_positions(card_ids, seed=seed)

    payload = json.loads(path.read_text(encoding="utf-8"))
    stored = {item["card_id"]: CardPosition(**item) for item in payload.get("positions", [])}
    generated = sphere_positions(card_ids, seed=seed)
    return [stored.get(position.card_id, position) for position in generated]


def save_positions(path: Path, positions: list[CardPosition]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "positions": [asdict(position) for position in positions]}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_progress(path: Path, card_ids: list[str]) -> dict[str, CardProgress]:
    if not path.exists():
        return {card_id: CardProgress(card_id=card_id) for card_id in card_ids}

    payload = json.loads(path.read_text(encoding="utf-8"))
    stored = {
        item["card_id"]: CardProgress(**item)
        for item in payload.get("progress", [])
        if item.get("card_id") in card_ids
    }
    return {
        card_id: stored.get(card_id, CardProgress(card_id=card_id))
        for card_id in card_ids
    }


def load_groups(path: Path, card_ids: list[str]) -> list[CardGroup]:
    if not path.exists():
        return []

    valid_ids = set(card_ids)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        CardGroup(
            id=item["id"],
            name=item["name"],
            color=item["color"],
            card_ids=[card_id for card_id in item.get("card_ids", []) if card_id in valid_ids],
        )
        for item in payload.get("groups", [])
    ]


def load_links(path: Path, card_ids: list[str]) -> list[CardLink]:
    if not path.exists():
        return []

    valid_ids = set(card_ids)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        CardLink(
            source_id=item["source_id"],
            target_id=item["target_id"],
            group_id=item.get("group_id"),
        )
        for item in payload.get("links", [])
        if item.get("source_id") in valid_ids and item.get("target_id") in valid_ids
    ]


def save_state(
    path: Path,
    positions: list[CardPosition],
    progress: dict[str, CardProgress],
    groups: list[CardGroup] | None = None,
    links: list[CardLink] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 2,
        "positions": [asdict(position) for position in positions],
        "progress": [asdict(item) for item in progress.values()],
        "groups": [asdict(group) for group in groups or []],
        "links": [asdict(link) for link in links or []],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
