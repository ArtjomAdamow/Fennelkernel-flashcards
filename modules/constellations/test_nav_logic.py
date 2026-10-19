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


def test_screen_components_projects_right_up_and_camera_depth():
    basis = navigation.camera_basis(example_view())
    assert basis is not None
    assert navigation.screen_components(basis, (2, 3, -4)) == pytest.approx((2, -4, 3))
    with pytest.raises(ValueError):
        navigation.screen_components(basis, (1, float("nan"), 2))


def test_rank_ring_matches_architecture_clockwise_acceptance_example():
    positions = {
        "O": (0, 0, 0),
        "N1": (1, 0, 0),
        "N2": (0, 0, -1.5),
        "N3": (-2, 0, 0),
        "N4": (0, 0, 3),
        "P": (2, 0, 1),
    }
    ring = navigation.rank_ring("O", None, positions, ["N1", "N2", "N3", "N4"], example_view(), random.Random(8))
    assert ring == ["N1", "N2", "N3", "N4"]
    assert navigation.rank_ring("N1", "O", positions, ["O", "P"], example_view(), random.Random(8)) == ["O", "P"]


def test_rank_ring_uses_only_supplied_direct_neighbors_and_skips_bad_positions():
    positions = {"o": (0, 0, 0), "near": (0.5, 0, 0), "far": (2, 0, 0), "bad": (float("nan"), 0, 0)}
    ring = navigation.rank_ring("o", None, positions, ["o", "near", "far", "missing", "bad", "near"], example_view(), random.Random(1))
    assert ring == ["near", "far"]
    assert navigation.rank_ring("o", None, positions, ["far"], example_view(dataScale=[1, 0, 1])) == []
    assert navigation.rank_ring("missing", None, positions, ["near"], example_view()) == []


def test_rank_ring_closest_ties_break_by_absolute_depth_then_shuffle_once():
    positions = {
        "o": (0, 0, 0),
        "depth-near": (1, 0.1, 0),
        "depth-far": (1, 0.8, 0),
    }
    ring = navigation.rank_ring("o", None, positions, ["depth-far", "depth-near"], example_view(), random.Random(5))
    assert ring[0] == "depth-near"

    positions = {"o": (0, 0, 0), "a": (1, 0, 0.5), "b": (1, 0, -0.5)}
    rng = CountingRandom(reverse=True)
    ring = navigation.rank_ring("o", None, positions, ["a", "b"], example_view(), rng)
    assert ring == ["b", "a"]
    assert rng.calls == 1


def test_rank_ring_previous_card_takes_rank_one_even_when_not_closest():
    positions = {"o": (0, 0, 0), "previous": (2, 0, 0), "closest": (0.25, 0, 0), "other": (0, 0, 1)}
    ring = navigation.rank_ring("o", "previous", positions, ["closest", "previous", "other"], example_view(), random.Random(2))
    assert ring[0] == "previous"
    assert set(ring) == {"previous", "closest", "other"}
    assert navigation.rank_ring("o", "not-a-neighbor", positions, ["closest", "previous"], example_view(), random.Random(2))[0] == "closest"


def test_rank_ring_plane_epsilon_marks_near_origin_candidate_angle_undefined():
    positions = {"o": (0, 0, 0), "near-origin": (0, 0, navigation.EPS_PLANE / 2), "right": (1, 0, 0)}
    ring = navigation.rank_ring("o", "near-origin", positions, ["near-origin", "right"], example_view(), random.Random(3))
    assert ring == ["near-origin", "right"]


def test_rank_ring_uses_screen_up_when_rank_one_has_no_angle():
    positions = {"o": (0, 0, 0), "along-depth": (0, 1, 0), "right": (1, 0, 0), "down": (0, 0, -1)}
    ring = navigation.rank_ring("o", None, positions, ["along-depth", "right", "down"], example_view(), random.Random(3))
    assert ring == ["along-depth", "right", "down"]


def test_rank_ring_tolerance_groups_angle_then_plane_then_depth():
    # Candidates lie on the same ray with tolerance-sized angular differences;
    # the final ordering of an exact plane/depth tie is delegated to rng.
    positions = {
        "o": (0, 0, 0),
        "first": (1, 0, 0),
        "a": (2, 0, 1),
        "b": (3, 0, 1.5),
        "c": (4, 0, 2),
    }
    ring = navigation.rank_ring("o", None, positions, ["first", "a", "b", "c"], example_view(), random.Random(9))
    assert ring[0] == "first"
    assert set(ring) == {"first", "a", "b", "c"}


def test_step_scroll_initial_direction_wrap_and_single_candidate():
    assert navigation.step_scroll(None, "right", 4) == 1
    assert navigation.step_scroll(None, "left", 4) == 4
    assert navigation.step_scroll(1, "left", 4) == 4
    assert navigation.step_scroll(4, "right", 4) == 1
    assert navigation.step_scroll(2, "right", 4) == 3
    assert navigation.step_scroll(3, "left", 4) == 2
    assert navigation.step_scroll(None, "right", 1) == 1
    assert navigation.step_scroll(1, "left", 1) == 1


def test_step_scroll_rejects_invalid_inputs_without_raising():
    for position, direction, count in [
        (None, "up", 3), (None, "right", 0), (None, "left", -1),
        (0, "right", 3), (4, "left", 3), (1.5, "right", 3),
        (True, "right", 3), (None, "right", True),
    ]:
        assert navigation.step_scroll(position, direction, count) is None


def test_links_token_is_order_and_direction_independent_and_tracks_topology():
    links = [("b", "a"), ("c", "b")]
    assert navigation.links_token(links) == navigation.links_token([("b", "c"), ("a", "b")])
    assert navigation.links_token(links) != navigation.links_token([("a", "b")])
    assert navigation.links_token([]) == navigation.links_token(None)


def test_links_token_accepts_link_records_and_mapping_endpoints():
    from types import SimpleNamespace

    records = [SimpleNamespace(source_id="a", target_id="b"), {"source": "b", "target": "c"}, {"a": "d", "b": "e"}]
    assert navigation.links_token(records) == navigation.links_token([("b", "a"), ("c", "b"), ("e", "d")])
    with pytest.raises(ValueError):
        navigation.links_token(["not-a-link"])


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
