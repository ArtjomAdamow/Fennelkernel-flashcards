"""Standalone tests for modules/constellations/navigation.py.

Run from the repository root:
    .venv/Scripts/python.exe -m pytest modules/constellations/test_nav_logic.py -p no:cacheprovider
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import math
import random
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

NAVIGATION_PATH = Path(__file__).with_name("navigation.py")


def load_isolated(alias: str, source: Path):
    """Load a source file under a private name and remove it if execution fails."""
    spec = importlib.util.spec_from_file_location(alias, source)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(alias, None)
        raise
    return module


@contextlib.contextmanager
def temporary_modules(replacements: dict[str, types.ModuleType | None]):
    """Temporarily replace or remove sys.modules entries, restoring them on exit."""
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in replacements}
    try:
        for name, module in replacements.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        yield
    finally:
        for name, module in previous.items():
            if module is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


navigation = load_isolated("constellations_tranche2_navigation", NAVIGATION_PATH)


def example_view(**overrides):
    view = {
        "camera": {"eye": [0, -1.25, 0], "center": [0, 0, 0], "up": [0, 0, 1]},
        "dataScale": [1, 1, 1],
        "axisRanges": {axis: [-1.15, 1.15] for axis in ("x", "y", "z")},
        "aspectmode": "cube",
        "anchor": {"min": [-1.15, -1.15, -1.15], "max": [1.15, 1.15, 1.15]},
        "generation": 1,
        "map_token": "same-map",
    }
    view.update(overrides)
    return view


class CountingRandom:
    def __init__(self, reverse=False):
        self.calls = 0
        self.reverse = reverse

    def shuffle(self, values):
        self.calls += 1
        if self.reverse:
            values.reverse()


def test_navigation_imports_without_app_dash_or_plotly_dependencies():
    forbidden = {"flashcards_app", "dash", "plotly"}
    with temporary_modules({name: None for name in forbidden}):
        isolated = load_isolated("constellations_navigation_dependency_probe", NAVIGATION_PATH)
    assert isolated.HALF_RANGE == 1.15


def test_parse_command_bare_json_malformed_and_missing_view():
    assert navigation.parse_command("right") == ("right", None)
    assert navigation.parse_command("") == ("", None)
    command = {"cmd": "right", "seq": 7, "view": {"generation": 2}}
    assert navigation.parse_command(json.dumps(command)) == ("right", command)
    missing_view = {"cmd": "right", "seq": 8}
    assert navigation.parse_command(json.dumps(missing_view)) == ("right", missing_view)
    assert navigation.parse_command('{"cmd":') == (None, None)
    assert navigation.parse_command('{"seq": 1}') == (None, None)
    assert navigation.parse_command('"right"') == (None, None)
    assert navigation.parse_command(None) == (None, None)


def test_camera_basis_default_direction_is_finite_orthonormal_and_right_handed():
    basis = navigation.camera_basis({"camera": {
        "eye": [1.25, 1.25, 1.25], "center": [0, 0, 0], "up": [0, 0, 1],
    }})
    assert basis is not None
    assert basis.r == pytest.approx((-1 / math.sqrt(2), 1 / math.sqrt(2), 0), abs=1e-12)
    for vector in (basis.f, basis.r, basis.u):
        assert all(math.isfinite(value) for value in vector)
        assert math.sqrt(sum(value * value for value in vector)) == pytest.approx(1)
    assert sum(a * b for a, b in zip(basis.f, basis.r)) == pytest.approx(0, abs=1e-12)
    assert sum(a * b for a, b in zip(basis.f, basis.u)) == pytest.approx(0, abs=1e-12)
    assert sum(a * b for a, b in zip(basis.r, basis.u)) == pytest.approx(0, abs=1e-12)


def test_camera_basis_uses_least_parallel_axis_when_up_is_parallel():
    basis = navigation.camera_basis({"camera": {
        "eye": [0, 0, -1], "center": [0, 0, 0], "up": [0, 0, 5],
    }})
    assert basis is not None
    assert basis.f == pytest.approx((0, 0, 1))
    assert basis.r == pytest.approx((0, 1, 0))
    assert basis.u == pytest.approx((1, 0, 0))


def test_camera_basis_rejects_degenerate_or_non_finite_forward():
    assert navigation.camera_basis({"camera": {
        "eye": [0, 0, 0], "center": [0, 0, 0], "up": [0, 0, 1],
    }}) is None
    assert navigation.camera_basis({"camera": {
        "eye": [0, 0, float("nan")], "center": [0, 0, 1], "up": [0, 0, 1],
    }}) is None


def test_validate_view_hard_scale_and_forward_checks_with_soft_map_checks():
    ok, checks = navigation.validate_view(example_view())
    assert ok
    assert all(checks.values())

    nonuniform = example_view(dataScale=[1, 2, 3])
    ok, checks = navigation.validate_view(nonuniform)
    assert ok
    assert checks["scale_valid"] and not checks["scale_uniform"]

    soft_mismatch = example_view(
        axisRanges={"x": [-2, 2], "y": [-1, 1], "z": [-1, 1]},
        aspectmode="manual",
        anchor=None,
    )
    ok, checks = navigation.validate_view(soft_mismatch)
    assert ok
    assert not checks["axis_ranges"]
    assert not checks["aspectmode"]
    assert not checks["anchor"]

    for scale in ([1, 2], [1, 0, 1], [1, float("inf"), 1], [1, float("nan"), 1]):
        ok, checks = navigation.validate_view(example_view(dataScale=scale))
        assert not ok
        assert not checks["scale_valid"]
    bad_forward = example_view(camera={"eye": [0, 0, 0], "center": [0, 0, 0], "up": [0, 0, 1]})
    ok, checks = navigation.validate_view(bad_forward)
    assert not ok
    assert not checks["forward_valid"]


def test_scaled_delta_applies_non_uniform_scale_componentwise():
    assert navigation.scaled_delta((2, 4, 6), (1, 1, 1), (2, 3, 4)) == pytest.approx((2, 9, 20))
    with pytest.raises(ValueError):
        navigation.scaled_delta((1, 2), (0, 0, 0), (1, 1, 1))
    with pytest.raises(ValueError):
        navigation.scaled_delta((1, 2, 3), (0, 0, 0), (1, 0, 1))


def test_direction_components_reorients_left_and_down_and_uses_camera_depth():
    basis = navigation.camera_basis(example_view())
    assert basis is not None
    delta = (2, 3, -4)
    assert navigation.direction_components(basis, delta, "right") == pytest.approx((2, -4, 2, -4, 3))
    assert navigation.direction_components(basis, delta, "left") == pytest.approx((-2, -4, 2, -4, 3))
    assert navigation.direction_components(basis, delta, "up") == pytest.approx((-4, 2, 2, -4, 3))
    assert navigation.direction_components(basis, delta, "down") == pytest.approx((4, 2, 2, -4, 3))


def test_eligibility_epsilon_is_strict_and_left_down_progress_is_reoriented():
    positions = {"o": (0, 0, 0), "edge": (navigation.EPS_PRIMARY, 0, 0), "over": (1.01e-9, 0, 0)}
    order, _ = navigation.rank_candidates("o", "right", positions, positions, example_view(), random.Random(2))
    assert order == ["over"]

    horizontal = {"o": (0, 0, 0), "left": (-1, 0, 0), "right": (1, 0, 0)}
    left, _ = navigation.rank_candidates("o", "left", horizontal, horizontal, example_view(), random.Random(2))
    assert left == ["left"]
    vertical = {"o": (0, 0, 0), "up": (0, 0, 1), "down": (0, 0, -1)}
    down, _ = navigation.rank_candidates("o", "down", vertical, vertical, example_view(), random.Random(2))
    assert down == ["down"]


def test_rank_candidates_orders_angle_then_distance_then_absolute_depth():
    view = example_view()
    positions = {
        "o": (0, 0, 0),
        "wide-angle": (1, 0, 0.2),
        "straight-far": (2, 0, 0),
        "straight-near": (1, 0, 0),
        "same-plane-far-depth": (1, -0.2, 0),
        "same-plane-near-depth": (1, -0.1, 0),
    }
    order, _ = navigation.rank_candidates("o", "right", positions, positions, view, random.Random(3))
    # The two zero-angle candidates tie on angle, then the closer one wins;
    # equal screen-plane values are finally ranked by abs(camera depth).
    assert order[0] == "straight-near"
    assert order.index("wide-angle") > order.index("straight-near")
    assert order.index("same-plane-near-depth") < order.index("same-plane-far-depth")
    assert order.index("straight-far") > order.index("straight-near")


def test_hierarchical_tolerance_clusters_adjacent_near_ties():
    # Three adjacent angular gaps are <= tolerance even though the end-to-end
    # difference is > tolerance; hierarchical clustering must keep them together.
    positions = {
        "o": (0, 0, 0),
        "a": (1, 0, 0),
        "b": (1, 0, 0.75e-9),
        "c": (1, 0, 1.5e-9),
    }
    order, tie = navigation.rank_candidates("o", "right", positions, positions, example_view(), random.Random(4))
    assert set(order) == {"a", "b", "c"}
    assert set(tie) == {"a", "b", "c"}


def test_exact_ties_shuffle_once_and_order_is_repeatable_when_cached():
    view = example_view()
    positions = {"o": (0, 0, 0), "a": (1, 0, 0.5), "b": (1, 0, -0.5)}
    rng = CountingRandom(reverse=True)
    order, tie = navigation.rank_candidates("o", "right", positions, positions, view, rng)
    assert order == ["b", "a"]
    assert tie == ["b", "a"]
    assert rng.calls == 1

    context = {"view": view, "members": ["o", "a", "b"], "orders": [], "predefined": [], "history": []}
    first_rng, second_rng = CountingRandom(), CountingRandom(reverse=True)
    first, context = navigation.next_preview(context, "o", "right", positions, first_rng)
    second, context = navigation.next_preview(context, "o", "right", positions, second_rng)
    assert first in {"a", "b"}
    assert second == first
    assert first_rng.calls == 1
    assert second_rng.calls == 0


def test_next_preview_acceptance_tie_chain_backscroll_and_empty_result():
    positions = {
        "O": (0, 0, 0),
        "A": (1, 0, 0.5),
        "B": (1, 0, -0.5),
        "C": (2, 0, 1.5),
    }
    context = {"view": example_view(), "members": ["O", "A", "B", "C"]}
    rng = random.Random(15)
    origin = "O"
    calls = 0
    original_rank = navigation.rank_candidates

    def counted_rank(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_rank(*args, **kwargs)

    with mock.patch.object(navigation, "rank_candidates", side_effect=counted_rank):
        winner, context = navigation.next_preview(context, origin, "right", positions, rng)
        assert winner in {"A", "B"}
        loser, context = navigation.next_preview(context, winner, "right", positions, rng)
        assert loser in {"A", "B"} - {winner}
        target, context = navigation.next_preview(context, loser, "right", positions, rng)
        assert target == "C"
        calls_after_forward = calls
        # Reverse through the three real edges, one stack pop each; no ranking call occurs.
        back_from = "C"
        back_from, context = navigation.next_preview(context, back_from, "left", positions, rng)
        assert back_from == loser
        back_from, context = navigation.next_preview(context, back_from, "left", positions, rng)
        assert back_from == winner
        back_from, context = navigation.next_preview(context, back_from, "left", positions, rng)
        assert back_from == "O"
        assert calls == calls_after_forward

    # The cached order survives a different RNG, and back-scroll has drained history.
    same_winner, context = navigation.next_preview(context, "O", "right", positions, random.Random(999))
    assert same_winner == winner
    no_candidate, context = navigation.next_preview(context, "O", "left", positions, rng)
    assert no_candidate is None


def test_predefined_target_bypasses_directional_eligibility():
    positions = {"o": (0, 0, 0), "winner": (1, 0, 0.5), "loser": (1, 0, -0.5)}
    context = {
        "view": example_view(), "members": ["o", "winner", "loser"],
        "orders": [], "predefined": [{"origin": "winner", "direction": "right", "target": "loser"}],
        "history": [],
    }
    # From winner to loser, rightward progress is zero, but the tie chain is intentional.
    target, context = navigation.next_preview(context, "winner", "right", positions, random.Random(1))
    assert target == "loser"


def test_history_only_opposite_of_top_edge_is_popped():
    positions = {"a": (0, 0, 0), "b": (1, 0, 0), "c": (2, 0, 0)}
    context = {
        "view": example_view(), "members": ["a", "b", "c"],
        "orders": [], "predefined": [],
        "history": [{"from": "a", "to": "b", "direction": "right"}],
    }
    target, context = navigation.next_preview(context, "b", "right", positions, random.Random(1))
    assert target == "c"
    assert context["history"][-1] == {"from": "b", "to": "c", "direction": "right"}
    assert navigation.opposite("right") == "left"
    assert navigation.opposite("up") == "down"
    assert navigation.opposite("nonsense") is None


def test_map_token_is_order_independent_and_tracks_rounded_visible_positions_only():
    positions = [("b", (0.25, -0.0, 1)), ("a", (1, 2, 3))]
    reordered = [("a", (1, 2, 3)), ("b", (0.25, 0.0, 1))]
    assert navigation.map_token(positions) == navigation.map_token(reordered)
    assert navigation.map_token({"a": (1, 2, 3), "b": (0.25, 0, 1)}) == navigation.map_token(positions)
    assert navigation.map_token([("a", (1, 2, 3.000000002))]) != navigation.map_token([("a", (1, 2, 3))])
    assert navigation.map_token([("a", (1, 2, 3.0000000001))]) == navigation.map_token([("a", (1, 2, 3))])


def test_map_token_accepts_position_like_records_and_excludes_unrelated_metadata():
    from types import SimpleNamespace

    token_a = navigation.map_token([SimpleNamespace(comb_id="card", x=1, y=2, z=3, status="new")])
    token_b = navigation.map_token([SimpleNamespace(comb_id="card", x=1, y=2, z=3, status="read")])
    assert token_a == token_b
