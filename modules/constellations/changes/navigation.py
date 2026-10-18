"""Pure, standard-library navigation logic for the constellations module.

This module deliberately has no dependency on Dash, Plotly, or the flashcards app.
Navigation contexts are ordinary in-memory dictionaries owned by the callback layer.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

EPS_PRIMARY = 1e-9
TOL_ANGLE = 1e-9
TOL_DIST = 1e-9
TOL_DEPTH = 1e-9
HALF_RANGE = 1.15
SCREEN_RIGHT_SIGN = +1

_DIRECTIONS = ("right", "left", "up", "down")
_OPPOSITE = {"right": "left", "left": "right", "up": "down", "down": "up"}
_AXES = ("x", "y", "z")


@dataclass(frozen=True)
class Basis:
    """Orthonormal, camera-relative forward, right, and up vectors."""

    f: tuple[float, float, float]
    r: tuple[float, float, float]
    u: tuple[float, float, float]


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _vector(value: Any) -> tuple[float, float, float] | None:
    """Return a finite 3-vector, or None when it is malformed."""
    if isinstance(value, Mapping):
        values = (value.get("x"), value.get("y"), value.get("z"))
    elif isinstance(value, (list, tuple)) and len(value) == 3:
        values = value
    else:
        return None
    if not all(_finite_number(component) for component in values):
        return None
    return tuple(float(component) for component in values)  # type: ignore[return-value]


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(vector: Sequence[float]) -> float:
    return math.sqrt(_dot(vector, vector))


def _normalize(vector: Sequence[float]) -> tuple[float, float, float] | None:
    length = _norm(vector)
    if not math.isfinite(length) or length <= EPS_PRIMARY:
        return None
    return tuple(component / length for component in vector)  # type: ignore[return-value]


def parse_command(value: Any) -> tuple[str | None, dict[str, Any] | None]:
    """Parse a legacy bare command or a JSON command object.

    Bare strings (including the empty reset value) are returned unchanged with
    ``None`` payload. JSON objects must contain a non-empty string ``cmd``;
    malformed JSON and JSON values that are not command objects are ignored.
    A valid command object is returned as the payload even when optional fields
    such as ``view`` are absent, leaving validation to the caller.
    """
    if not isinstance(value, str):
        return None, None
    stripped = value.strip()
    if not stripped:
        return value, None
    if stripped.startswith("{"):
        try:
            parsed = json.loads(stripped)
        except (TypeError, ValueError):
            return None, None
        if not isinstance(parsed, dict):
            return None, None
        command = parsed.get("cmd")
        if not isinstance(command, str) or not command:
            return None, None
        return command, parsed
    # Do not mistake other JSON values (for example, a quoted string) for the
    # legacy transport, but keep normal bare command strings unchanged.
    if stripped[0] in '["' or stripped in {"true", "false", "null"}:
        try:
            json.loads(stripped)
        except (TypeError, ValueError):
            return value, None
        return None, None
    return value, None


def camera_basis(view: Mapping[str, Any]) -> Basis | None:
    """Build a stable orthonormal camera basis, or reject a degenerate forward.

    ``f`` points from camera eye to center. The supplied up vector is projected
    off the forward direction; if it is unusable, the least-parallel canonical
    world axis is used as a deterministic fallback.
    """
    if not isinstance(view, Mapping):
        return None
    camera = view.get("camera")
    if not isinstance(camera, Mapping):
        return None
    eye = _vector(camera.get("eye"))
    center = _vector(camera.get("center"))
    if eye is None or center is None:
        return None
    forward = tuple(c - e for c, e in zip(center, eye))
    f = _normalize(forward)
    if f is None:
        return None

    supplied_up = _vector(camera.get("up"))
    up_ortho: tuple[float, float, float] | None = None
    if supplied_up is not None:
        projection = _dot(supplied_up, f)
        projected = tuple(up - projection * direction for up, direction in zip(supplied_up, f))
        up_ortho = _normalize(projected)

    if up_ortho is None:
        world_axes = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        axis = min(world_axes, key=lambda candidate: abs(_dot(candidate, f)))
        projection = _dot(axis, f)
        up_ortho = _normalize(tuple(component - projection * direction for component, direction in zip(axis, f)))
        if up_ortho is None:  # Defensive: a least-parallel axis cannot be parallel.
            return None

    right = _normalize(_cross(f, up_ortho))
    if right is None:
        return None
    up = _normalize(_cross(right, f))
    if up is None:
        return None

    sign = -1.0 if SCREEN_RIGHT_SIGN < 0 else 1.0
    if sign < 0:
        right = tuple(sign * component for component in right)
        up = tuple(sign * component for component in up)
    return Basis(f=f, r=right, u=up)


def _range_mapping(value: Any) -> dict[str, Any] | None:
    """Normalize axis ranges from mapping or x/y/z sequence representations."""
    if isinstance(value, Mapping):
        result = {}
        for axis in _AXES:
            item = value.get(axis, value.get(f"{axis}axis"))
            if isinstance(item, Mapping):
                item = item.get("range")
            result[axis] = item
        return result
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return dict(zip(_AXES, value))
    return None


def _expected_range(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(_finite_number(item) for item in value)
        and abs(float(value[0]) + HALF_RANGE) <= TOL_DIST
        and abs(float(value[1]) - HALF_RANGE) <= TOL_DIST
    )


def _anchor_matches(anchor: Any) -> bool:
    """Check the recorded AnchorBounds extents against the expected cube."""
    if isinstance(anchor, Mapping):
        # Supported forms: {x: [min,max], ...} or {min: [x,y,z], max: [...]}.
        if all(axis in anchor or f"{axis}axis" in anchor for axis in _AXES):
            return all(_expected_range(_range_mapping(anchor).get(axis)) for axis in _AXES)  # type: ignore[union-attr]
        minimum = _vector(anchor.get("min"))
        maximum = _vector(anchor.get("max"))
        return (
            minimum is not None
            and maximum is not None
            and all(abs(value + HALF_RANGE) <= TOL_DIST for value in minimum)
            and all(abs(value - HALF_RANGE) <= TOL_DIST for value in maximum)
        )
    if isinstance(anchor, (list, tuple)) and len(anchor) == 2:
        minimum, maximum = _vector(anchor[0]), _vector(anchor[1])
        return (
            minimum is not None
            and maximum is not None
            and all(abs(value + HALF_RANGE) <= TOL_DIST for value in minimum)
            and all(abs(value - HALF_RANGE) <= TOL_DIST for value in maximum)
        )
    return False


def validate_view(view: Any) -> tuple[bool, dict[str, bool]]:
    """Validate hard camera/scale requirements and report soft map assumptions.

    Invalid or missing scale components and a degenerate forward vector are hard
    failures. Non-uniform scale, unexpected axis ranges/aspect mode, and missing
    or incorrect anchor extents are soft checks: the view remains usable and the
    false flag makes the assumption visible to integration code.
    """
    checks = {
        "scale_valid": False,
        "forward_valid": False,
        "scale_uniform": False,
        "axis_ranges": False,
        "aspectmode": False,
        "anchor": False,
    }
    if not isinstance(view, Mapping):
        return False, checks

    raw_scale = view.get("dataScale")
    scale = _vector(raw_scale)
    if scale is not None and all(component != 0.0 for component in scale):
        checks["scale_valid"] = True
        magnitudes = [abs(component) for component in scale]
        spread = max(magnitudes) - min(magnitudes)
        checks["scale_uniform"] = spread <= 1e-6 * max(magnitudes)

    checks["forward_valid"] = camera_basis(view) is not None

    ranges = _range_mapping(view.get("axisRanges"))
    checks["axis_ranges"] = ranges is not None and all(_expected_range(ranges[axis]) for axis in _AXES)
    checks["aspectmode"] = view.get("aspectmode") == "cube"
    checks["anchor"] = _anchor_matches(view.get("anchor"))

    return checks["scale_valid"] and checks["forward_valid"], checks


def scaled_delta(
    p: Sequence[float] | Mapping[str, Any],
    p0: Sequence[float] | Mapping[str, Any],
    data_scale: Sequence[float],
) -> tuple[float, float, float]:
    """Return ``(p - p0)`` scaled componentwise into Plotly's camera space."""
    point, origin, scale = _vector(p), _vector(p0), _vector(data_scale)
    if point is None or origin is None or scale is None:
        raise ValueError("p, p0, and data_scale must be finite 3-vectors")
    if any(component == 0.0 for component in scale):
        raise ValueError("data_scale components must be non-zero")
    return tuple((coordinate - start) * factor for coordinate, start, factor in zip(point, origin, scale))  # type: ignore[return-value]


def _basis_vectors(basis: Basis | Mapping[str, Any] | Any) -> tuple[tuple[float, ...], ...]:
    if isinstance(basis, Mapping):
        values = (basis.get("f"), basis.get("r"), basis.get("u"))
    else:
        values = (getattr(basis, "f", None), getattr(basis, "r", None), getattr(basis, "u", None))
    vectors = tuple(_vector(value) for value in values)
    if any(vector is None for vector in vectors):
        raise ValueError("basis must provide finite f, r, and u 3-vectors")
    return vectors  # type: ignore[return-value]


def direction_components(
    basis: Basis | Mapping[str, Any], delta: Sequence[float], direction: str
) -> tuple[float, float, float, float, float]:
    """Return oriented primary/perpendicular progress and raw h, v, depth."""
    if direction not in _DIRECTIONS:
        raise ValueError(f"unsupported direction: {direction!r}")
    vector = _vector(delta)
    if vector is None:
        raise ValueError("delta must be a finite 3-vector")
    forward, right, up = _basis_vectors(basis)
    h = _dot(vector, right)
    v = _dot(vector, up)
    depth = _dot(vector, forward)
    if direction == "right":
        primary, perpendicular = h, v
    elif direction == "left":
        primary, perpendicular = -h, v
    elif direction == "up":
        primary, perpendicular = v, h
    else:  # down
        primary, perpendicular = -v, h
    return primary, perpendicular, h, v, depth


def _position(value: Any) -> tuple[float, float, float] | None:
    """Read an xyz coordinate from a sequence, mapping, or position-like object."""
    if isinstance(value, Mapping):
        if all(axis in value for axis in _AXES):
            return _vector(value)
        if "position" in value:
            return _vector(value["position"])
        if all(axis in value for axis in ("x", "y", "z")):
            return _vector(value)
        return None
    if all(hasattr(value, axis) for axis in _AXES):
        return _vector(tuple(getattr(value, axis) for axis in _AXES))
    return _vector(value)


def _tolerance_clusters(items: list[Any], value, tolerance: float) -> list[list[Any]]:
    """Cluster sorted items by adjacent-value gaps, not non-transitive comparisons."""
    if not items:
        return []
    ordered = sorted(items, key=value)
    clusters: list[list[Any]] = [[ordered[0]]]
    previous = value(ordered[0])
    for item in ordered[1:]:
        current = value(item)
        if current - previous > tolerance:
            clusters.append([])
        clusters[-1].append(item)
        previous = current
    return clusters


def _shuffle(cluster: list[Any], rng: Any) -> None:
    if len(cluster) > 1:
        rng.shuffle(cluster)


def rank_candidates(
    origin: str,
    direction: str,
    positions: Mapping[str, Any],
    members: Iterable[str],
    view: Mapping[str, Any],
    rng: Any = None,
) -> tuple[list[str], list[str]]:
    """Rank eligible constellation members and shuffle only final exact-tie clusters.

    Tolerance grouping is hierarchical (angle, then in-plane distance, then
    absolute depth), so adjacent near-ties form a deterministic cluster even
    when the first and last members differ by more than one tolerance.
    """
    if direction not in _DIRECTIONS:
        raise ValueError(f"unsupported direction: {direction!r}")
    basis = camera_basis(view)
    scale = _vector(view.get("dataScale")) if isinstance(view, Mapping) else None
    origin_position = _position(positions.get(origin)) if isinstance(positions, Mapping) else None
    if basis is None or scale is None or any(component == 0 for component in scale) or origin_position is None:
        return [], []

    if rng is None:
        rng = random
    scored: list[dict[str, Any]] = []
    for member in members:
        if member == origin or member not in positions:
            continue
        candidate_position = _position(positions[member])
        if candidate_position is None:
            continue
        delta = scaled_delta(candidate_position, origin_position, scale)
        primary, perpendicular, h, v, depth = direction_components(basis, delta, direction)
        if not math.isfinite(primary) or primary <= EPS_PRIMARY:
            continue
        angle = math.atan2(abs(perpendicular), primary)
        distance = math.sqrt(h * h + v * v)
        abs_depth = abs(depth)
        if not all(math.isfinite(value) for value in (angle, distance, abs_depth)):
            continue
        scored.append({
            "id": member,
            "angle": angle,
            "distance": distance,
            "depth": abs_depth,
        })

    if not scored:
        return [], []

    ranked: list[str] = []
    first_tie: list[str] = []
    angle_groups = _tolerance_clusters(scored, lambda item: item["angle"], TOL_ANGLE)
    for angle_group in angle_groups:
        distance_groups = _tolerance_clusters(angle_group, lambda item: item["distance"], TOL_DIST)
        for distance_group in distance_groups:
            depth_groups = _tolerance_clusters(distance_group, lambda item: item["depth"], TOL_DEPTH)
            for depth_group in depth_groups:
                tied_ids = [item["id"] for item in depth_group]
                _shuffle(tied_ids, rng)
                if not ranked:
                    first_tie = list(tied_ids)
                ranked.extend(tied_ids)
    return ranked, first_tie


def opposite(direction: str) -> str | None:
    """Return the opposite arrow direction, or None for an unknown direction."""
    return _OPPOSITE.get(direction)


def _cache_entry(entries: Any, origin: str, direction: str) -> dict[str, Any] | None:
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get("origin") == origin and entry.get("direction") == direction:
            return entry
    return None


def _store_predefined(context: dict[str, Any], tie: Sequence[str], direction: str) -> None:
    entries = context.setdefault("predefined", [])
    for source, target in zip(tie, tie[1:]):
        existing = _cache_entry(entries, source, direction)
        if existing is None:
            entries.append({"origin": source, "direction": direction, "target": target})
        else:
            existing["target"] = target


def _push_history(context: dict[str, Any], origin: str, target: str, direction: str) -> None:
    context.setdefault("history", []).append({"from": origin, "to": target, "direction": direction})


def next_preview(
    context: dict[str, Any],
    origin: str,
    direction: str,
    positions: Mapping[str, Any],
    rng: Any = None,
) -> tuple[str | None, dict[str, Any]]:
    """Choose the next preview, updating the context's caches and history in place."""
    if direction not in _DIRECTIONS or not isinstance(context, dict):
        return None, context
    context.setdefault("orders", [])
    context.setdefault("predefined", [])
    context.setdefault("history", [])

    history = context["history"]
    reverse = opposite(direction)
    if history and isinstance(history[-1], dict):
        top = history[-1]
        if top.get("to") == origin and top.get("direction") == reverse:
            target = top.get("from")
            if target in positions:
                history.pop()
                return target, context

    predefined = _cache_entry(context["predefined"], origin, direction)
    members = context.get("members", ())
    member_set = set(members) if isinstance(members, (list, tuple, set, frozenset)) else set()
    if predefined is not None:
        target = predefined.get("target")
        if target in member_set and target in positions:
            _push_history(context, origin, target, direction)
            return target, context

    entry = _cache_entry(context["orders"], origin, direction)
    if entry is None:
        view = context.get("view")
        order, tie = rank_candidates(origin, direction, positions, member_set, view, rng)
        entry = {"origin": origin, "direction": direction, "order": list(order), "tie": list(tie)}
        context["orders"].append(entry)
        if tie:
            _store_predefined(context, tie, direction)
    order = entry.get("order", [])
    if not isinstance(order, list):
        return None, context
    target = next((candidate for candidate in order if candidate in member_set and candidate in positions), None)
    if target is None:
        return None, context
    _push_history(context, origin, target, direction)
    return target, context


def _iter_visible_positions(visible_positions: Any) -> list[tuple[str, tuple[float, float, float]]]:
    """Normalize common map-position containers into sortable ID/coordinate pairs."""
    rows: list[tuple[str, tuple[float, float, float]]] = []
    if isinstance(visible_positions, Mapping):
        source = visible_positions.items()
        for card_id, value in source:
            point = _position(value)
            if point is None:
                raise ValueError(f"invalid coordinates for visible card {card_id!r}")
            rows.append((str(card_id), point))
        return rows

    for item in visible_positions:
        if hasattr(item, "comb_id"):
            card_id = getattr(item, "comb_id")
            point = _position(item)
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            card_id, raw_point = item
            point = _position(raw_point)
        elif isinstance(item, (list, tuple)) and len(item) == 4:
            card_id, x, y, z = item
            point = _vector((x, y, z))
        else:
            raise ValueError("visible positions must include a card ID and xyz coordinates")
        if point is None:
            raise ValueError(f"invalid coordinates for visible card {card_id!r}")
        rows.append((str(card_id), point))
    return rows


def map_token(visible_positions: Any) -> str:
    """Hash sorted visible ``(comb_id, x, y, z)`` tuples rounded to 9 decimals."""
    rows = _iter_visible_positions(visible_positions)
    canonical = []
    for card_id, point in sorted(rows, key=lambda row: row[0]):
        coords = []
        for value in point:
            rounded = round(value, 9)
            coords.append(0.0 if rounded == 0 else rounded)  # normalize negative zero
        canonical.append((card_id, *coords))
    encoded = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
