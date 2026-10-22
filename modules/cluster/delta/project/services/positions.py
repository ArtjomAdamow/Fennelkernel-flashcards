"""Card positions around the sun of the deck view (the origin).

Hard rule: no card is closer to the sun than INNER_RADIUS. Generated positions respect it, and positions
stored by earlier runs (or calculated elsewhere) are pushed out to it by keep_off_the_sun.
"""

import math
import random
from typing import List

from project.models import CardPosition

# No card sits closer to the sun than this (the deck view's unit of length is the map's radius): the knob for how
# far the innermost cards keep from the sun's glow. Stored positions below it are pushed out at startup
# (keep_off_the_sun), so a change shows at the next start; the helper module scales its model positions into
# [INNER_RADIUS, 1] from scratch only at a fresh start.
INNER_RADIUS = 0.4


def shell_positions(
    card_ids: List[str], seed: int = 42, inner: float = INNER_RADIUS, radius: float = 1.0
) -> List[CardPosition]:
    """One random position per card in the shell between `inner` and `radius`, evenly spread by volume."""
    generator = random.Random(seed)
    positions: List[CardPosition] = []
    for card_id in card_ids:
        # A random direction: a normalised Gaussian vector
        while True:
            x, y, z = (generator.gauss(0.0, 1.0) for _ in range(3))
            length = math.sqrt(x * x + y * y + z * z)
            if length > 1e-9:
                break
        # The distance: uniform by volume between the two spheres
        distance = (inner**3 + generator.random() * (radius**3 - inner**3)) ** (1 / 3)
        scale = distance / length
        positions.append(CardPosition(comb_id=card_id, x=x * scale, y=y * scale, z=z * scale))
    return positions


def keep_off_the_sun(positions: List[CardPosition], inner: float = INNER_RADIUS, seed: int = 42) -> int:
    """Push every position closer to the origin than `inner` out to `inner`, along its own direction
    (a position exactly at the origin gets a random one). Changes the positions in place; returns how many moved."""
    generator = random.Random(seed)
    moved = 0
    for position in positions:
        length = math.sqrt(position.x ** 2 + position.y ** 2 + position.z ** 2)
        if length >= inner:
            continue
        if length <= 1e-9:
            x, y, z = (generator.gauss(0.0, 1.0) for _ in range(3))
            length = math.sqrt(x * x + y * y + z * z) or 1.0
            position.x, position.y, position.z = x, y, z
        scale = inner / length
        position.x, position.y, position.z = position.x * scale, position.y * scale, position.z * scale
        moved += 1
    return moved
