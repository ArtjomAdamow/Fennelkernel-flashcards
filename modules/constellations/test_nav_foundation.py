"""Foundation tests for the isolated constellations navigation layer.

Run from the repository root with:
    .venv/Scripts/python.exe -m pytest modules/constellations/test_nav_foundation.py -p no:cacheprovider
"""

from __future__ import annotations

import contextlib
import importlib.metadata
import importlib.util
import json
import shutil
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

MODULE_DIR = Path(__file__).resolve().parent
ROOT = MODULE_DIR.parents[1]
CHANGES_DIR = MODULE_DIR / "changes"
# Dash 4.4.1 declares Plotly.py >=5.0.0. The old 4.4.1 Plotly pin in the
# planning notes conflicts with that requirement, so test the supported minimum
# and the Scatter3d features instead of demanding the incompatible old pin.
EXPECTED_VERSIONS = {
    "dash": "4.4.1",
    "flask": "3.1.3",
    "dash-daq": "0.6.0",
}
PLOTLY_MIN_VERSION = "5.0.0"
PACKAGES_TO_REPORT = ("plotly", *EXPECTED_VERSIONS)


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


def _versions() -> dict[str, str]:
    result = {}
    for package in PACKAGES_TO_REPORT:
        try:
            result[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            result[package] = "<not installed>"
    return result


def test_runtime_versions_and_plotly_marker_contract(capsys):
    """Report runtime versions and fail visibly on either package or API mismatch."""
    versions = _versions()
    print("Navigation runtime versions: " + json.dumps(versions, sort_keys=True))
    try:
        import plotly.graph_objects as go

        marker_trace = go.Scatter3d(
            x=[0], y=[0], z=[0], mode="markers",
            marker={"symbol": "cross", "opacity": 0.5},
        )
        marker_json = marker_trace.to_plotly_json()["marker"]
        assert marker_json["symbol"] == "cross"
        assert marker_json["opacity"] == 0.5
    except Exception as error:
        pytest.fail(f"Installed Plotly cannot construct the required Scatter3d marker: {error!r}")

    from packaging.version import Version

    assert Version(versions["plotly"]) >= Version(PLOTLY_MIN_VERSION), (
        "Plotly.py is older than Dash 4.4.1's supported minimum. "
        f"Installed={versions['plotly']}; required>={PLOTLY_MIN_VERSION}."
    )
    assert {name: versions[name] for name in EXPECTED_VERSIONS} == EXPECTED_VERSIONS, (
        "Installed Dash/Flask/dash-daq versions differ from the documented set. "
        f"Installed={versions}; expected={EXPECTED_VERSIONS}."
    )


def _map_modules():
    changed = load_isolated("_const_nav_foundation_changed_map", CHANGES_DIR / "map.py")
    reference = load_isolated("_const_nav_foundation_reference_map", ROOT / "flashcards_app" / "visualization" / "map.py")
    return changed, reference


@pytest.fixture(scope="module")
def map_modules():
    changed, reference = _map_modules()
    try:
        yield changed, reference
    finally:
        sys.modules.pop("_const_nav_foundation_changed_map", None)
        sys.modules.pop("_const_nav_foundation_reference_map", None)


def _map_state():
    from flashcards_app.models import CardLink, CardPosition, Flashcard

    cards = [
        Flashcard("a", "deck", "Question A", "Answer A"),
        Flashcard("b", "deck", "Question B", "Answer B"),
        Flashcard("c", "deck", "Question C", "Answer C"),
    ]
    positions = [
        CardPosition("a", 0.1, 0.2, 0.3),
        CardPosition("b", -0.2, 0.4, 0.1),
        CardPosition("c", 0.7, -0.5, 0.25),
    ]
    state = SimpleNamespace(
        positions=positions,
        links=[CardLink("a", "b")],
        card_by_id={card.id: card for card in cards},
        progress={},
        deciding_group=lambda card_id, focused_group=None: None,
    )
    return cards, state


def test_map_without_navigation_arguments_matches_reference(map_modules):
    changed, reference = map_modules
    cards, state = _map_state()
    actual = changed.make_figure(cards, "a", state=state)
    expected = reference.make_figure(cards, "a", state=state)
    assert actual.to_plotly_json() == expected.to_plotly_json()


def test_map_dims_nonmembers_and_preserves_member_selected_anchor_and_links(map_modules):
    changed, _ = map_modules
    cards, state = _map_state()
    figure = changed.make_figure(cards, "a", state=state, nav_members={"a", "b"})
    traces = {trace.name: trace for trace in figure.data}

    assert traces["Cards (dimmed)"].marker.opacity == 0.3
    assert traces["Card progress (dimmed)"].marker.opacity == 0.3
    assert list(traces["Cards (dimmed)"].customdata) == ["c"]
    assert "opacity" not in traces["Cards"].marker.to_plotly_json()
    assert "opacity" not in traces["Card progress"].marker.to_plotly_json()
    assert "opacity" not in traces["Selected"].marker.to_plotly_json()
    assert "opacity" not in traces["Selected progress"].marker.to_plotly_json()
    assert traces["AnchorBounds"].to_plotly_json() == changed.make_figure(cards, "a", state=state).data[0].to_plotly_json()
    assert traces["Connection"].to_plotly_json() == changed.make_figure(cards, "a", state=state).data[1].to_plotly_json()

    all_members = changed.make_figure(cards, "a", state=state, nav_members={"a", "b", "c"})
    assert not any(trace.name.endswith("(dimmed)") for trace in all_members.data)


def test_navigation_preview_cross_is_visible_for_visible_card_including_selected(map_modules):
    changed, _ = map_modules
    cards, state = _map_state()
    nav_members = {"a", "b"}

    previewed = changed.make_figure(cards, "a", state=state, preview_id="b", nav_members=nav_members)
    cross = next(trace for trace in previewed.data if trace.name == "Navigation preview")
    assert (list(cross.x), list(cross.y), list(cross.z)) == ([-0.2], [0.4], [0.1])
    assert cross.marker.symbol == "cross"
    assert cross.hoverinfo == "skip"

    # Navigation activation also marks the currently selected card. Only absent
    # and non-visible preview IDs should omit the cross.
    selected_preview = changed.make_figure(cards, "a", state=state, preview_id="a", nav_members=nav_members)
    selected_cross = next(trace for trace in selected_preview.data if trace.name == "Navigation preview")
    assert (list(selected_cross.x), list(selected_cross.y), list(selected_cross.z)) == ([0.1], [0.2], [0.3])
    assert selected_cross.marker.symbol == "cross"
    assert selected_cross.hoverinfo == "skip"

    for preview_id in (None, "not-visible"):
        figure = changed.make_figure(cards, "a", state=state, preview_id=preview_id, nav_members=nav_members)
        assert not any(trace.name == "Navigation preview" for trace in figure.data)


def test_click_on_dimmed_point_still_uses_real_select_from_click(map_modules):
    changed, _ = map_modules
    from flashcards_app.services.cards import select_from_click

    cards, state = _map_state()
    figure = changed.make_figure(cards, "a", state=state, nav_members={"a", "b"})
    dimmed = next(trace for trace in figure.data if trace.name == "Cards (dimmed)")
    click_data = {"points": [{"customdata": dimmed.customdata[0]}]}
    assert select_from_click(click_data, None) == "c"


def _plain_tree(component):
    """Serialize a Dash component tree to ordinary dict/list values."""
    if isinstance(component, (list, tuple)):
        return [_plain_tree(child) for child in component]
    if hasattr(component, "to_plotly_json"):
        return _plain_tree(component.to_plotly_json())
    if isinstance(component, dict):
        return {key: _plain_tree(value) for key, value in component.items()}
    return component


def _without_navigation_stores(tree):
    if isinstance(tree, list):
        return [item for item in (_without_navigation_stores(value) for value in tree) if item is not None]
    if isinstance(tree, dict):
        props = tree.get("props", {})
        if props.get("id") in {"nav-state", "nav-view"}:
            return None
        return {key: _without_navigation_stores(value) for key, value in tree.items()}
    return tree


def _patch_server_for_layout(server_module, monkeypatch):
    from dash import dcc, html
    import plotly.graph_objects as go

    monkeypatch.setattr(server_module, "make_figure", lambda *args, **kwargs: go.Figure())
    monkeypatch.setattr(server_module, "color_legend", lambda: html.Div(id="stub-legend"))
    for name in ("card_panel", "connection_control", "deck_control", "difficulty_control", "group_control", "position_control"):
        monkeypatch.setattr(server_module, name, lambda *args, **kwargs: html.Div(id="stub-" + name))


def test_server_layout_matches_reference_plus_two_memory_stores(tmp_path, monkeypatch):
    changed_path = CHANGES_DIR / "server.py"
    reference_path = ROOT / "flashcards_app" / "server.py"
    empty_assets = tmp_path / "no-module-assets"
    empty_assets.mkdir()

    with temporary_modules({"_const_nav_foundation_changed_server": None, "_const_nav_foundation_reference_server": None}):
        changed = load_isolated("_const_nav_foundation_changed_server", changed_path)
        reference = load_isolated("_const_nav_foundation_reference_server", reference_path)
        monkeypatch.setattr(changed, "MODULE_ASSETS_DIR", empty_assets)
        _patch_server_for_layout(changed, monkeypatch)
        _patch_server_for_layout(reference, monkeypatch)
        state = SimpleNamespace(cards=[])
        actual_app = changed.create_app(tmp_path, "boot", state)
        expected_app = reference.create_app(tmp_path, "boot", state)
        actual_layout = _plain_tree(actual_app.layout)
        expected_layout = _plain_tree(expected_app.layout)

        stores = {node.get("props", {}).get("id"): node for node in actual_layout["props"]["children"] if isinstance(node, dict)}
        assert stores["nav-state"]["type"] == "Store"
        assert stores["nav-view"]["type"] == "Store"
        assert stores["nav-state"]["props"]["storage_type"] == "memory"
        assert stores["nav-view"]["props"]["storage_type"] == "memory"
        assert _without_navigation_stores(actual_layout) == expected_layout


def test_server_asset_overlay_is_idempotent_overlays_module_assets_and_keeps_root_untouched(tmp_path):
    changed = load_isolated("_const_nav_foundation_overlay_server", CHANGES_DIR / "server.py")
    root_assets = tmp_path / "assets"
    module_assets = tmp_path / "module-assets"
    root_assets.mkdir()
    module_assets.mkdir()
    root_files = {
        "keyboard.js": "root keyboard",
        "orientation.js": "root orientation",
        "reload-guard.js": "root reload guard",
        "untouched.txt": "root-only asset",
    }
    module_files = {
        "keyboard.js": "module keyboard",
        "camera.js": "module camera",
        "style.css": "module styles",
    }
    for name, content in root_files.items():
        (root_assets / name).write_text(content, encoding="utf-8")
    for name, content in module_files.items():
        (module_assets / name).write_text(content, encoding="utf-8")

    overlay = changed.build_assets_overlay(tmp_path, module_assets)
    first = {str(path.relative_to(overlay)): path.read_bytes() for path in overlay.rglob("*") if path.is_file()}
    assert (overlay / "keyboard.js").read_text(encoding="utf-8") == "module keyboard"
    assert (overlay / "camera.js").read_text(encoding="utf-8") == "module camera"
    assert (overlay / "style.css").read_text(encoding="utf-8") == "module styles"
    assert (overlay / "orientation.js").read_text(encoding="utf-8") == "root orientation"
    assert (overlay / "reload-guard.js").read_text(encoding="utf-8") == "root reload guard"
    assert (overlay / "untouched.txt").read_text(encoding="utf-8") == "root-only asset"

    second_overlay = changed.build_assets_overlay(tmp_path, module_assets)
    second = {str(path.relative_to(second_overlay)): path.read_bytes() for path in second_overlay.rglob("*") if path.is_file()}
    assert second == first
    assert {name: (root_assets / name).read_text(encoding="utf-8") for name in root_files} == root_files

    sys.modules.pop("_const_nav_foundation_overlay_server", None)


def test_launcher_reroutes_tranche_three_overrides_and_server_after_phases_one_and_two_were_merged():
    launcher_path = ROOT / "tools" / "loader" / "const_v1_launcher.py"
    launcher = load_isolated("_const_nav_foundation_launcher_contract", launcher_path)
    try:
        assert list(launcher.REROUTES.items()) == [
            ("flashcards_app.visualization.map", CHANGES_DIR / "map.py"),
            ("flashcards_app.visualization.panels", CHANGES_DIR / "panels.py"),
            ("flashcards_app.callbacks", CHANGES_DIR / "callbacks.py"),
            ("flashcards_app.server", CHANGES_DIR / "server.py"),
        ]
        assert launcher.SCRATCH_STATE == ROOT / "tools" / "loader" / "scratch" / "const_user_state.json"
        assert launcher.APP_SOURCE == ROOT / "app.py"
    finally:
        sys.modules.pop("_const_nav_foundation_launcher_contract", None)
