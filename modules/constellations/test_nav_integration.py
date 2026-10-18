"""Headless tranche-3 integration checks for the user's merged application.

Run from repository root:
    .venv/Scripts/python.exe -m pytest modules/constellations/test_nav_integration.py -p no:cacheprovider
"""
from __future__ import annotations

import contextlib
import importlib.util
import inspect
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

MODULE_DIR = Path(__file__).resolve().parent
CHANGES_DIR = MODULE_DIR / "changes"


def load_isolated(alias: str, source: Path):
    """Load a Python file by path under a private alias, cleaning up on failure."""
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
    """Temporarily replace/remove sys.modules entries, restoring them on exit."""
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


def _walk(node):
    if node is None or isinstance(node, (str, int, float)):
        return
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk(child)
    elif children is not None:
        yield from _walk(children)


def _callback_module():
    # Load the actual tranche copies under the application import names the launcher will reroute.
    from flashcards_app.visualization import map as original_map, panels as original_panels
    changed_map = load_isolated("_constellations_tranche3_callback_map", CHANGES_DIR / "map.py")
    changed_panels = load_isolated("_constellations_tranche3_callback_panels", CHANGES_DIR / "panels.py")
    replacements = {
        "flashcards_app.visualization.map": changed_map,
        "flashcards_app.visualization.panels": changed_panels,
        "_constellations_navigation": None,
    }
    with temporary_modules(replacements):
        callbacks = load_isolated("_constellations_tranche3_callbacks", CHANGES_DIR / "callbacks.py")
    # Preserve the imported canonical modules for the surrounding suite.
    assert original_map is not changed_map and original_panels is not changed_panels
    return callbacks


class RecordingApp:
    def __init__(self):
        self.dependencies = ()

    def callback(self, *dependencies):
        self.dependencies = dependencies
        return lambda function: function


class RecordingState:
    """Small state double for navigation-only callback branches."""
    def __init__(self):
        from flashcards_app.models import Flashcard
        self.cards = [
            Flashcard(comb_id="a", deck="d", question="Question A", answer="Answer A"),
            Flashcard(comb_id="b", deck="d", question="Question B", answer="Answer B"),
        ]
        self.card_by_id = {card.id: card for card in self.cards}
        from flashcards_app.models import CardPosition, Constellation
        self.positions = [CardPosition("a", 0, 0, 0), CardPosition("b", 0.5, 0, 0)]
        self.position_by_id = {position.comb_id: position for position in self.positions}
        self.constellations = [Constellation("1", members=["a", "b"])]
        self.progress = {}
        self.groups = []
        self.links = []
        self.save_calls = 0
        self.mutations = []

    def visible_cards(self, deck=None, focused_group=None):
        return list(self.cards)

    def refresh_constellations(self, visible_cards):
        return self.constellations

    def save(self):
        self.save_calls += 1

    def mark_read(self, *args): self.mutations.append(("mark_read", args))
    def set_difficulty(self, *args): self.mutations.append(("set_difficulty", args))
    def set_position(self, *args): self.mutations.append(("set_position", args))
    def create_link(self, *args): self.mutations.append(("create_link", args))
    def disconnect_link(self, *args): self.mutations.append(("disconnect_link", args))
    def create_group(self, *args): self.mutations.append(("create_group", args))
    def add_to_group(self, *args): self.mutations.append(("add_to_group", args))
    def remove_from_group(self, *args): self.mutations.append(("remove_from_group", args))
    def delete_group(self, *args): self.mutations.append(("delete_group", args))
    def reset_all_state(self, *args): self.mutations.append(("reset_all_state", args))
    def enable_deck(self, *args): self.mutations.append(("enable_deck", args))
    def disable_deck(self, *args): self.mutations.append(("disable_deck", args))
    def reload_decks(self, *args): self.mutations.append(("reload_decks", args))


def _call_update(callbacks, state, trigger, **overrides):
    update = callbacks.register_callbacks(RecordingApp(), state, "None")
    values = {name: None for name in inspect.signature(update).parameters}
    values.update({"deck": "all", "drag_enabled": False})
    values.update(overrides)
    patches = {
        "make_figure": lambda *args, **kwargs: "figure",
        "card_panel": lambda *args, **kwargs: "card-panel",
        "difficulty_control": lambda *args, **kwargs: "difficulty",
        "position_control": lambda *args, **kwargs: "position",
        "group_control": lambda *args, **kwargs: "groups",
        "connection_control": lambda *args, **kwargs: "connections",
        "deck_control": lambda *args, **kwargs: "deck",
        "deck_filter_options": lambda *args, **kwargs: [],
    }
    with mock.patch("dash.ctx", SimpleNamespace(triggered_id=trigger)), contextlib.ExitStack() as stack:
        for name, value in patches.items():
            stack.enter_context(mock.patch.object(callbacks, name, value))
        return update(*values.values())


def test_navigation_helper_is_loaded_by_module_relative_path():
    source = (CHANGES_DIR / "callbacks.py").read_text(encoding="utf-8")
    assert 'Path(__file__).resolve().parent.parent / "navigation.py"' in source
    assert "spec_from_file_location" in source
    assert "sys.path.insert" not in source and "sys.path.append" not in source


def test_panel_additions_keep_the_two_argument_server_call():
    pytest.importorskip("dash")
    panels = load_isolated("_constellations_tranche3_panels", CHANGES_DIR / "panels.py")
    panel = panels.connection_control(None, [])
    ids = {getattr(node, "id", None) for node in _walk(panel)}
    assert {
        "create-link", "disconnect-link", "delete-constellation", "constellation-select",
        "navigation-open", "navigation-select", "navigation-dialog-submit",
        "navigation-dialog-cancel", "nav-message", "nav-preview", "nav-config",
    } <= ids
    assert panels.navigation_options() == [
        {"label": "By card order", "value": "card_order"},
        {"label": "Within constellation", "value": "constellation"},
    ]
    navigation_select = next((node for node in _walk(panel) if getattr(node, "id", None) == "navigation-select"), None)
    assert navigation_select is not None and navigation_select.value == "card_order"
    assert next(node for node in _walk(panel) if getattr(node, "id", None) == "navigation-open") is not None


def test_callback_dependencies_append_five_contract_items_and_output_19():
    callbacks = _callback_module()
    app = RecordingApp()
    update = callbacks.register_callbacks(app, None)
    found = [(type(dep).__name__, dep.component_id, dep.component_property) for dep in app.dependencies]
    expected = [
        ("Input", "navigation-open", "n_clicks"),
        ("Input", "navigation-dialog-submit", "n_clicks"),
        ("Input", "navigation-dialog-cancel", "n_clicks"),
        ("State", "navigation-select", "value"),
        ("State", "nav-state", "data"),
    ]
    assert all(item in found for item in expected)
    assert not any(item[0] == "State" and item[1] == "nav-view" for item in found)
    outputs = [item for item in app.dependencies if type(item).__name__ == "Output"]
    assert len(outputs) == 19 and outputs[-1].component_id == "nav-state"
    names = list(inspect.signature(update).parameters)
    input_state_deps = [dep for dep in found if dep[0] != "Output"]
    for dep, expected_name in zip(expected, [
        "navigation_open_clicks", "navigation_submit_clicks", "navigation_cancel_clicks",
        "navigation_select", "nav_state",
    ]):
        assert names[input_state_deps.index(dep)] == expected_name


def test_navigation_only_triggers_never_mutate_or_save_and_empty_reset_is_noop():
    pytest.importorskip("dash")
    callbacks = _callback_module()
    state = RecordingState()
    nav = {"mode": "constellation", "dialog": None, "preview_id": None,
           "message": None, "message_selected_id": None, "context": None}
    navigation = callbacks.navigation
    valid_view = {
        "camera": {"eye": [0, -1, 0], "center": [0, 0, 0], "up": [0, 0, 1]},
        "dataScale": [1, 1, 1], "generation": 4,
        "map_token": navigation.map_token(state.positions),
    }
    commands = [
        ('{"cmd":"right","seq":1,"view":' + __import__("json").dumps(valid_view) + '}', "keyboard-nav"),
        ('{"cmd":"enter","seq":2,"generation":4}', "keyboard-nav"),
        ('{"cmd":"invalidate","seq":3,"generation":5}', "keyboard-nav"),
        ("", "keyboard-nav"),
    ]
    # Space retains the existing mark-read and save path even in constellation mode.
    _call_update(callbacks, state, "keyboard-nav", selected_id="a", nav_state=nav,
                 keyboard_nav="space", revealed=False)
    assert state.mutations == [("mark_read", ("a",))]
    assert state.save_calls == 1
    state.mutations.clear()
    state.save_calls = 0

    previous = nav
    for command, trigger in commands:
        before_command = previous
        result = _call_update(callbacks, state, trigger, selected_id="a", nav_state=before_command,
                              keyboard_nav=command)
        previous = result[18]
        if command.startswith('{"cmd":"right"'):
            assert previous["preview_id"] == "b"
            assert previous["context"]["const_id"] == "1"
        if command == "":
            assert previous == before_command
        assert state.mutations == []
        assert state.save_calls == 0
    _call_update(callbacks, state, "navigation-open", selected_id="a", nav_state=nav)
    assert state.mutations == []
    assert state.save_calls == 0


def test_navigation_dialog_confirm_and_cancel_keep_mode_contract():
    pytest.importorskip("dash")
    callbacks = _callback_module()
    state = RecordingState()
    from flashcards_app.models import Constellation
    state.constellations = [Constellation("1", members=["a", "b"])]
    nav = {"mode": "constellation", "dialog": "navigation", "preview_id": "b",
           "message": "no_candidate", "message_selected_id": None,
           "context": {"const_id": "1", "members": ["a", "b"], "view": {
               "map_token": callbacks.navigation.map_token(state.positions), "generation": 1
           }}}
    cancelled = _call_update(callbacks, state, "navigation-dialog-cancel", selected_id="a", nav_state=nav)[18]
    assert cancelled["mode"] == "constellation"
    assert cancelled["dialog"] is None
    assert cancelled["preview_id"] == "b" and cancelled["context"] == nav["context"]
    confirmed = _call_update(callbacks, state, "navigation-dialog-submit", selected_id="a",
                             nav_state=nav, navigation_select="card_order")[18]
    assert confirmed == {"mode": "card_order", "dialog": None, "preview_id": None,
                         "message": None, "message_selected_id": None, "context": None}
    assert state.save_calls == 0 and state.mutations == []


def test_map_token_metadata_is_optional_and_added_by_keyword_only():
    pytest.importorskip("plotly")
    pytest.importorskip("dash")
    from flashcards_app.models import CardPosition
    changed_map = load_isolated("_constellations_tranche3_map", CHANGES_DIR / "map.py")
    state = SimpleNamespace(positions=[CardPosition("a", 0.1, 0.2, 0.3)], links=[], card_by_id={},
                            progress={}, deciding_group=lambda *args: None)
    original = changed_map.make_figure([], state=state)
    tokenized = changed_map.make_figure([], state=state, map_token="token")
    assert original.layout.meta is None
    assert tokenized.layout.meta == {"map_token": "token"}
    assert "map_token" in inspect.signature(changed_map.make_figure).parameters


def test_source_preserves_existing_callback_branches_and_skips_only_named_nav_saves():
    source = (CHANGES_DIR / "callbacks.py").read_text(encoding="utf-8")
    for retained in (
        'trigger == "reset-confirm"', 'trigger == "selected-card"', 'trigger == "random-card"',
        'trigger == "difficulty-slider"', 'trigger == "save-position"',
        'trigger == "create-link"', 'trigger == "disconnect-link"',
        'trigger == "constellation-dialog-submit"', 'state.refresh_constellations(cards)',
    ):
        assert retained in source
    assert "if not deleted_links and not navigation_only_trigger:" in source
    assert 'trigger == "keyboard-nav" and mode == "constellation" and command != "space"' in source
