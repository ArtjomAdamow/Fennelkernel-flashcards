import json
from dataclasses import asdict
from pathlib import Path

from .models import CardPosition


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
