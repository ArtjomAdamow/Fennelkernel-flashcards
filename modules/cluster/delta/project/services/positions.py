"""Random dot positions and the two hard rules on stored or calculated positions.

* shell_positions: in the shell between INNER_RADIUS and 1 around the center (the origin, where the deck's
  centroid is drawn). Hard rule: no dot is closer to the center than INNER_RADIUS; keep_off_the_center pushes
  positions that break it out to it.
* surface_positions: on the surface of the unit sphere (the decks of the decks view). Hard rule: every dot sits
  exactly on the surface; keep_on_the_surface scales positions that break it onto it, along their own direction.

Both rules change positions in place and return how many moved, so a position source that places dots elsewhere
(stored positions of an earlier run, the helper's model positions) is corrected at startup.
"""

import math
import random
from typing import List

from project.models import CardPosition

SURFACE_RADIUS = 1.0
# Positions this close to the surface count as on it (a scaled float can come out a rounding error off)
SURFACE_TOLERANCE = 1e-9

# No card sits closer to the center than this (the cards view's unit of length is the map's radius): the knob for
# how far the innermost cards keep from the centroid's glow. Stored positions below it are pushed out at startup
# (keep_off_the_center), so a change shows at the next start; the helper module scales its model positions into
# [INNER_RADIUS, 1] from scratch only at a fresh start.
INNER_RADIUS = 0.4


def _direction(generator: random.Random) -> tuple:
    """A random direction, evenly spread: a normalised Gaussian vector."""
    while True:
        x, y, z = (generator.gauss(0.0, 1.0) for _ in range(3))
        length = math.sqrt(x * x + y * y + z * z)
        if length > 1e-9:
            return x / length, y / length, z / length


def shell_positions(
    card_ids: List[str], seed: int = 42, inner: float = INNER_RADIUS, radius: float = 1.0
) -> List[CardPosition]:
    """One random position per card in the shell between `inner` and `radius`, evenly spread by volume."""
    generator = random.Random(seed)
    positions: List[CardPosition] = []
    for card_id in card_ids:
        x, y, z = _direction(generator)
        # The distance: uniform by volume between the two spheres
        distance = (inner**3 + generator.random() * (radius**3 - inner**3)) ** (1 / 3)
        positions.append(CardPosition(comb_id=card_id, x=x * distance, y=y * distance, z=z * distance))
    return positions


def surface_positions(card_ids: List[str], seed: int = 42, radius: float = SURFACE_RADIUS) -> List[CardPosition]:
    """One random position per card on the surface of the sphere with this radius (a random direction, the length
    exactly the radius)."""
    generator = random.Random(seed)
    positions: List[CardPosition] = []
    for card_id in card_ids:
        x, y, z = _direction(generator)
        positions.append(CardPosition(comb_id=card_id, x=x * radius, y=y * radius, z=z * radius))
    return positions


def keep_on_the_surface(positions: List[CardPosition], radius: float = SURFACE_RADIUS, seed: int = 42) -> int:
    """Scale every position that is not on the surface onto it, along its own direction (a position at the origin
    gets a random one). Changes the positions in place; returns how many moved."""
    generator = random.Random(seed)
    moved = 0
    for position in positions:
        length = math.sqrt(position.x ** 2 + position.y ** 2 + position.z ** 2)
        if abs(length - radius) <= SURFACE_TOLERANCE:
            continue
        if length <= 1e-9:
            position.x, position.y, position.z = _direction(generator)
            length = 1.0
        scale = radius / length
        position.x, position.y, position.z = position.x * scale, position.y * scale, position.z * scale
        moved += 1
    return moved


def keep_off_the_center(positions: List[CardPosition], inner: float = INNER_RADIUS, seed: int = 42) -> int:
    """Push every position closer to the origin than `inner` out to `inner`, along its own direction
    (a position exactly at the origin gets a random one). Changes the positions in place; returns how many moved."""
    generator = random.Random(seed)
    moved = 0
    for position in positions:
        length = math.sqrt(position.x ** 2 + position.y ** 2 + position.z ** 2)
        if length >= inner:
            continue
        if length <= 1e-9:
            position.x, position.y, position.z = _direction(generator)
            length = 1.0
        scale = inner / length
        position.x, position.y, position.z = position.x * scale, position.y * scale, position.z * scale
        moved += 1
    return moved
