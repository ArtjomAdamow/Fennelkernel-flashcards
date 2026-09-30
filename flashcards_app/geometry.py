import random
from typing import List

from .models import CardPosition


def sphere_positions(card_ids: List[str], seed: int = 42, radius: float = 1.0) -> List[CardPosition]:
    generator = random.Random(seed)
    positions: List[CardPosition] = []

    for card_id in card_ids:
        # Generate random point inside unit sphere using rejection sampling
        while True:
            x = generator.uniform(-1.0, 1.0)
            y = generator.uniform(-1.0, 1.0)
            z = generator.uniform(-1.0, 1.0)
            distance_squared = x * x + y * y + z * z
            # Accept point if it's inside the unit sphere (not at origin)
            if 0 < distance_squared <= 1:
                break
        
        # Scale by radius and create position object
        positions.append(
            CardPosition(
                card_id=card_id,
                x=x * radius,
                y=y * radius,
                z=z * radius,
            )
        )

    return positions
