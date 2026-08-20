import random

from .models import CardPosition


def sphere_positions(card_ids: list[str], seed: int = 42, radius: float = 1.0) -> list[CardPosition]:
    """Return reproducible random points distributed inside a sphere."""
    generator = random.Random(seed)
    positions: list[CardPosition] = []

    for card_id in card_ids:
        while True:
            x = generator.uniform(-1.0, 1.0)
            y = generator.uniform(-1.0, 1.0)
            z = generator.uniform(-1.0, 1.0)
            distance_squared = x * x + y * y + z * z
            if 0 < distance_squared <= 1:
                break
        positions.append(
            CardPosition(
                card_id=card_id,
                x=x * radius,
                y=y * radius,
                z=z * radius,
            )
        )

    return positions
