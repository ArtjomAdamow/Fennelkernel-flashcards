"""Headless Python integration tests for the constellation navigation tranche.

Run from the repository root:
    .venv/Scripts/python.exe -m pytest modules/constellations/test_nav_integration.py -p no:cacheprovider
"""
from __future__ import annotations

import importlib.util
import json
import math
import random
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

ROOT = Path(__file__).parent
CHANGES = ROOT / "changes"


@dataclass
class Flashcard:
    comb_id: str
    deck: str = "d"
    question: str = "Question"
    answer: str = "Answer"

    @property
    def id(self):
        return self.comb_id


@dataclass
class CardPosition:
    comb_id: str
    x: float
    y: float
    z: float


@dataclass
class Link:
    source_id: str
    target_id: str


@dataclass
class Constellation:
    const_id: str
    members: list[str]

    @property
    def name(self):
        return f"constellation {self.const_id}"


def _module(name, *, package=False, **attrs):
    mod = types.ModuleType(name)
    if package:
        mod.__path__ = []
    for key, value in attrs.items():
        setattr(mod, key, value)
    sys.modules[name] = mod
    return mod


def _load(alias, path):
    spec = importlib.util.spec_from_file_location(alias, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def app_modules():
    # Minimal app-domain modules let these source files run without the private app repository.
    flashcards = _module("flashcards_app", package=True)
    services = _module("flashcards_app.services", package=True)
    cards_service = _module("flashcards_app.services.cards", 
        select_from_click=lambda click, hover: next((point.get("customdata") for point in click.get("points", []) if point.get("customdata")), None),
        choose_random_card=lambda cards, progress, rng: cards[0] if cards else None,
        adjacent_card=lambda cards, selected, direction: next((c for c in cards if c.id != selected), None))
    services.cards = cards_service
    flashcards.services = services
    models = _module("flashcards_app.models", Flashcard=Flashcard, CardPosition=CardPosition,
                     Constellation=Constellation)
    runtime = _module("flashcards_app.runtime", NONE_DECK="None")
    _module("flashcards_app.visualization", package=True)
    colors = _module("flashcards_app.visualization.colors", group_color=lambda *a: "#ff0000",
                     progress_color=lambda *a: "#00ff00")
    map_module = _load("flashcards_app.visualization.map", CHANGES / "map.py")
    panel_module = _load("flashcards_app.visualization.panels", CHANGES / "panels.py")
    sys.modules["flashcards_app.visualization"].map = map_module
    sys.modules["flashcards_app.visualization"].panels = panel_module
    callbacks = _load("_tranche_python_callbacks", CHANGES / "callbacks.py")
    yield SimpleNamespace(callbacks=callbacks, map=map_module, panels=panel_module,
                          models=models, runtime=runtime, services=services, colors=colors)
    for name in list(sys.modules):
        if name == "flashcards_app" or name.startswith("flashcards_app.") or name == "_tranche_python_callbacks":
            sys.modules.pop(name, None)


class State:
    def __init__(self, cards=None, links=None):
        self.cards = cards or [Flashcard("a", question="Question A"), Flashcard("b", question="Question B"),
                               Flashcard("c", question="Question C")]
        self.card_by_id = {c.id: c for c in self.cards}
        self.positions = [CardPosition("a", 0, 0, 0), CardPosition("b", 1, 0, 0),
                          CardPosition("c", 0, 0, -1.5)]
        self.position_by_id = {p.comb_id: p for p in self.positions}
        self.links = links if links is not None else [Link("a", "b"), Link("a", "c")]
        self.progress = {c.id: SimpleNamespace(read=False, difficulty=1) for c in self.cards}
        self.groups = []
        self.constellations = []
        self.save_calls = 0
        self.mutations = []

    def visible_cards(self, deck=None, focused_group=None):
        return list(self.cards)

    def refresh_constellations(self, cards):
        visible = {c.id for c in cards}
        adjacency = {c.id: set() for c in cards}
        for link in self.links:
            if link.source_id in visible and link.target_id in visible:
                adjacency[link.source_id].add(link.target_id)
                adjacency[link.target_id].add(link.source_id)
        found, components = set(), []
        for ident in adjacency:
            if ident in found or not adjacency[ident]:
                continue
            stack, component = [ident], set()
            while stack:
                node = stack.pop()
                if node in component:
                    continue
                component.add(node)
                stack.extend(adjacency[node] - component)
            found |= component
            components.append(component)
        self.constellations = [Constellation(str(i + 1), sorted(c)) for i, c in enumerate(components)]
        return self.constellations

    def mark_read(self, ident):
        self.mutations.append(("mark_read", ident))
        self.progress[ident].read = True

    def save(self):
        self.save_calls += 1

    def deciding_group(self, *args):
        return None


class RecordingApp:
    def __init__(self):
        self.dependencies = ()

    def callback(self, *dependencies):
        self.dependencies = dependencies
        return lambda function: function


def _call(app_modules, state, trigger, **overrides):
    callbacks = app_modules.callbacks
    update = callbacks.register_callbacks(RecordingApp(), state, "None")
    values = {name: None for name in __import__("inspect").signature(update).parameters}
    values.update({"deck": "all", "drag_enabled": False})
    values.update(overrides)
    patches = {
        "make_figure": lambda *args, **kwargs: {"args": args, "kwargs": kwargs},
        "card_panel": lambda *args, **kwargs: "card-panel",
        "difficulty_control": lambda *args, **kwargs: "difficulty",
        "position_control": lambda *args, **kwargs: "position",
        "group_control": lambda *args, **kwargs: "groups",
        "connection_control": lambda *args, **kwargs: "connections",
        "deck_control": lambda *args, **kwargs: "deck",
        "deck_filter_options": lambda *args, **kwargs: [],
    }
    with mock.patch("dash.ctx", SimpleNamespace(triggered_id=trigger)):
        with __import__("contextlib").ExitStack() as stack:
            for name, value in patches.items():
                stack.enter_context(mock.patch.object(callbacks, name, value))
            return update(*values.values())


def _view(callbacks, state, generation=1):
    return {"camera": {"eye": [0, -1.25, 0], "center": [0, 0, 0], "up": [0, 0, 1]},
            "dataScale": [1, 1, 1], "generation": generation,
            "map_token": callbacks.navigation.map_token(state.positions)}


def _command(name, seq=1, **fields):
    return json.dumps({"cmd": name, "seq": seq, **fields})


def _activate(app_modules, state, selected="a", generation=1, nav=None):
    view = _view(app_modules.callbacks, state, generation)
    result = _call(app_modules, state, "keyboard-nav", selected_id=selected, revealed=False,
                   nav_state=nav or {"mode": "constellation"}, keyboard_nav=_command("space", view=view))
    return result[18], view


def test_enter_flips_in_card_order_and_saves(app_modules):
    state = State()
    result = _call(app_modules, state, "keyboard-nav", selected_id="a", revealed=False,
                   nav_state={"mode": "card_order"}, keyboard_nav="enter")
    assert result[8] is True and result[7] == "a"
    assert state.mutations == [("mark_read", "a")] and state.save_calls == 1


def test_enter_flips_without_ending_active_navigation(app_modules):
    state = State()
    nav, _ = _activate(app_modules, state)
    result = _call(app_modules, state, "keyboard-nav", selected_id="a", revealed=False,
                   nav_state=nav, keyboard_nav="enter")
    assert result[8] is True and result[18]["context"] == nav["context"]
    assert result[18]["preview_id"] == "a" and state.save_calls == 1


def test_space_creates_snapshot_with_members_positions_adjacency_and_tokens_without_saving(app_modules):
    state = State()
    nav, view = _activate(app_modules, state)
    ctx = nav["context"]
    assert ctx["selected_id"] == "a" and ctx["view"] == view
    assert ctx["members"] == ["a", "b", "c"]
    assert ctx["adjacency"] == {"a": ["b", "c"], "b": ["a"], "c": ["a"]}
    assert ctx["links_token"] == app_modules.callbacks.navigation.links_token(state.links)
    assert nav["preview_id"] == "a" and nav["scrolled_id"] is None
    assert state.save_calls == 0 and state.mutations == []


def test_first_right_scroll_highlights_rank_one_without_moving_cross(app_modules):
    state = State()
    nav, _ = _activate(app_modules, state)
    old_preview = nav["preview_id"]
    result = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                   keyboard_nav=_command("right", generation=1))
    nav2 = result[18]
    assert nav2["scrolled_id"] == "b" and nav2["preview_id"] == old_preview
    assert nav2["scroll_pos"] == 1
    assert result[0]["kwargs"]["scrolled_id"] == "b"
    assert state.save_calls == 0


def test_left_starts_at_lowest_rank_and_right_wraps(app_modules):
    state = State()
    nav, _ = _activate(app_modules, state)
    left = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                 keyboard_nav=_command("left", generation=1))[18]
    assert left["scrolled_id"] == "c" and left["scroll_pos"] == 2
    right1 = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=left,
                   keyboard_nav=_command("right", seq=2, generation=1))[18]
    assert right1["scrolled_id"] == "b" and right1["scroll_pos"] == 1


def test_space_completes_step_and_next_ring_places_previous_card_first(app_modules):
    state = State()
    nav, view = _activate(app_modules, state)
    nav = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                keyboard_nav=_command("right", generation=1))[18]
    result = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                   keyboard_nav=_command("space", seq=3, view=view))
    nav = result[18]
    assert nav["preview_id"] == "b" and nav["previous_id"] == "a"
    assert nav["scrolled_id"] is None and nav["scroll_pos"] is None
    assert result[0]["kwargs"]["preview_id"] == "b"
    assert result[0]["kwargs"]["scrolled_id"] is None
    nav = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                keyboard_nav=_command("right", seq=4, generation=1))[18]
    assert nav["scrolled_id"] == "a"


def test_space_without_highlight_selects_current_preview_and_exits_from_initial_trigger(app_modules):
    state = State()
    nav, view = _activate(app_modules, state)
    result = _call(app_modules, state, "keyboard-nav", selected_id="a", revealed=True,
                   nav_state=nav, keyboard_nav=_command("space", seq=2, view=view))
    assert result[7] == "a" and result[18]["context"] is None
    assert result[18]["preview_id"] is None and result[8] is False
    assert state.save_calls == 1


def test_space_without_highlight_selects_returned_card_and_exits(app_modules):
    state = State()
    nav, view = _activate(app_modules, state)
    nav = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                keyboard_nav=_command("right", generation=1))[18]
    nav = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                keyboard_nav=_command("space", seq=3, view=view))[18]
    nav = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                keyboard_nav=_command("right", seq=4, generation=1))[18]
    assert nav["scrolled_id"] == "a"
    nav = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                keyboard_nav=_command("space", seq=5, view=view))[18]
    result = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                   keyboard_nav=_command("space", seq=6, view=view))
    assert result[7] == "a" and result[18]["context"] is None
    assert state.save_calls == 1


def test_enter_is_not_navigation_commit(app_modules):
    state = State()
    nav, _ = _activate(app_modules, state)
    result = _call(app_modules, state, "keyboard-nav", selected_id="a", revealed=False,
                   nav_state=nav, keyboard_nav=_command("enter", generation=1))
    assert result[7] == "a" and result[18]["context"] == nav["context"]


def test_messages_for_unconnected_and_arrows_before_start(app_modules):
    state = State(links=[])
    state.refresh_constellations(state.cards)
    result = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state={"mode": "constellation"},
                   keyboard_nav=_command("space", view=_view(app_modules.callbacks, state)))
    assert result[18]["message"] == "unconnected" and result[18]["context"] is None
    assert result[18]["message_selected_id"] == "a"

    connected = State()
    result = _call(app_modules, connected, "keyboard-nav", selected_id="a", nav_state={"mode": "constellation"},
                   keyboard_nav=_command("right", generation=1))
    assert result[18]["message"] == "hit_space" and result[18]["message_selected_id"] == "a"


def test_message_lifecycle_and_panel_copy(app_modules):
    panel = app_modules.panels.connection_control(None, [], navigation={"mode": "constellation", "message": "hit_space"})
    texts = []
    def walk(node):
        if isinstance(node, str):
            texts.append(node)
        else:
            children = getattr(node, "children", None)
            if isinstance(children, (list, tuple)):
                for child in children: walk(child)
            elif children is not None: walk(children)
    walk(panel)
    assert "Hit Space key to start navigation" in texts
    unconnected = app_modules.panels.connection_control(None, [], navigation={"message": "unconnected"})
    texts.clear(); walk(unconnected)
    assert "Navigation with arrow keys within constellations toggled on." in texts


def test_up_down_do_nothing_with_active_context(app_modules):
    state = State()
    nav, _ = _activate(app_modules, state)
    for direction in ("up", "down"):
        result = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                       keyboard_nav=_command(direction, generation=1))
        assert result[18] == nav
        assert state.save_calls == 0


def test_new_generation_arrow_clears_context_and_sets_hit_space(app_modules):
    state = State()
    nav, _ = _activate(app_modules, state)
    result = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                   keyboard_nav=_command("right", generation=2))
    assert result[18]["context"] is None and result[18]["message"] == "hit_space"
    assert result[18]["preview_id"] is None


def test_late_arrow_and_invalidate_do_not_clear_newer_context(app_modules):
    state = State()
    nav, view = _activate(app_modules, state, generation=3)
    late = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                 keyboard_nav=_command("right", generation=2))[18]
    assert late["context"] == nav["context"]
    late_inv = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                     keyboard_nav=_command("invalidate", generation=2))[18]
    assert late_inv["context"] == nav["context"]
    newer = _call(app_modules, state, "keyboard-nav", selected_id="a", nav_state=nav,
                  keyboard_nav=_command("invalidate", generation=4))[18]
    assert newer["context"] is None and newer["preview_id"] is None


def test_links_and_positions_invalidate_context(app_modules):
    state = State()
    nav, _ = _activate(app_modules, state)
    state.links.append(Link("b", "c"))
    result = _call(app_modules, state, "selected-card", selected_id="a", nav_state=nav)
    assert result[18]["context"] is None
    nav, _ = _activate(app_modules, state)
    state.position_by_id["c"].z = -0.8
    result = _call(app_modules, state, "selected-card", selected_id="a", nav_state=nav)
    assert result[18]["context"] is None


def test_selected_card_change_and_mode_change_clear_every_derived_field(app_modules):
    state = State()
    nav, _ = _activate(app_modules, state)
    nav["scroll_pos"] = 1; nav["scrolled_id"] = "b"; nav["previous_id"] = "c"
    with mock.patch.object(app_modules.services.cards, "select_from_click", return_value="c"):
        changed = _call(app_modules, state, "sphere", selected_id="a", nav_state=nav,
                        click_data={"points": [{"customdata": "c"}]})[18]
    assert changed["context"] is None and changed["preview_id"] is None
    assert changed["scroll_pos"] is None and changed["scrolled_id"] is None
    mode_changed = _call(app_modules, state, "navigation-dialog-submit", selected_id="a", nav_state=nav,
                         navigation_select="card_order")[18]
    assert mode_changed["context"] is None and mode_changed["preview_id"] is None
    assert mode_changed["previous_id"] is None and mode_changed["scrolled_id"] is None


def test_preview_readout_hidden_on_selected_card(app_modules):
    panel = app_modules.panels.connection_control(Flashcard("a"), [], navigation={
        "mode": "constellation", "preview_id": "a", "preview_card": Flashcard("a", question="A")})
    def find(node, ident):
        if getattr(node, "id", None) == ident: return node
        children = getattr(node, "children", None)
        if isinstance(children, (tuple, list)):
            for child in children:
                found = find(child, ident)
                if found is not None: return found
        elif children is not None:
            return find(children, ident)
        return None
    readout = find(panel, "nav-preview")
    assert readout is not None and "nav-preview-hidden" in readout.className


def test_map_draws_03_nonmember_dimming_cross_on_selected_and_only_one_highlight(app_modules):
    state = State()
    state.refresh_constellations(state.cards)
    fig = app_modules.map.make_figure(state.cards, "a", state=state, nav_members={"a", "b"},
                                      preview_id="a", scrolled_id="b")
    traces = {trace.name: trace for trace in fig.data}
    assert traces["Cards (dimmed)"].marker.opacity == 0.3
    assert traces["Card progress (dimmed)"].marker.opacity == 0.3
    assert list(traces["Navigation preview"].x) == [0]
    nav_links = [trace for trace in fig.data if trace.name == "Navigation link"]
    assert len(nav_links) == 1 and list(nav_links[0].x[:2]) == [0, 1]
    assert traces["Cards"].marker.opacity is None
    assert traces["Selected"].marker.opacity is None


def test_map_cross_moves_to_preview_even_when_preview_is_selected(app_modules):
    state = State()
    fig = app_modules.map.make_figure(state.cards, "a", state=state, nav_members={"a", "b", "c"},
                                      preview_id="b")
    trace = next(trace for trace in fig.data if trace.name == "Navigation preview")
    assert list(trace.x) == [1]


def test_dialog_contract_is_transient_and_has_expected_navigation_options(app_modules):
    options = app_modules.panels.navigation_options()
    assert options == [{"label": "By card order", "value": "card_order"},
                       {"label": "Within constellation", "value": "constellation"}]


def _walk_components(node):
    if node is None or isinstance(node, (str, int, float)):
        return
    yield node
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk_components(child)
    elif children is not None:
        yield from _walk_components(children)


def test_navigation_helper_loader_uses_module_relative_path(app_modules):
    source = (CHANGES / "callbacks.py").read_text(encoding="utf-8")
    assert 'Path(__file__).resolve().parent.parent / "navigation.py"' in source
    assert "spec_from_file_location" in source
    assert "sys.path.insert" not in source and "sys.path.append" not in source


def test_callback_contract_keeps_19_outputs_and_five_navigation_dependencies(app_modules):
    app = RecordingApp()
    update = app_modules.callbacks.register_callbacks(app, State(), "None")
    deps = [(type(dep).__name__, dep.component_id, dep.component_property) for dep in app.dependencies]
    expected = [
        ("Input", "navigation-open", "n_clicks"),
        ("Input", "navigation-dialog-submit", "n_clicks"),
        ("Input", "navigation-dialog-cancel", "n_clicks"),
        ("State", "navigation-select", "value"),
        ("State", "nav-state", "data"),
    ]
    assert all(item in deps for item in expected)
    assert not any(dep[0] == "State" and dep[1] == "nav-view" for dep in deps)
    outputs = [dep for dep in app.dependencies if type(dep).__name__ == "Output"]
    assert len(outputs) == 19 and outputs[-1].component_id == "nav-state"


def test_panel_keeps_existing_two_argument_call_and_navigation_controls(app_modules):
    panel = app_modules.panels.connection_control(None, [])
    ids = {getattr(node, "id", None) for node in _walk_components(panel)}
    assert {"create-link", "disconnect-link", "delete-constellation", "constellation-select",
            "navigation-open", "navigation-select", "navigation-dialog-submit",
            "navigation-dialog-cancel", "nav-message", "nav-preview", "nav-config"} <= ids
    assert app_modules.panels.navigation_options() == [
        {"label": "By card order", "value": "card_order"},
        {"label": "Within constellation", "value": "constellation"},
    ]


def test_map_token_metadata_is_optional_and_keyword_only(app_modules):
    state = State(cards=[], links=[])
    original = app_modules.map.make_figure([], state=state)
    tokenized = app_modules.map.make_figure([], state=state, map_token="token")
    assert original.layout.meta is None
    assert tokenized.layout.meta == {"map_token": "token"}
    import inspect
    assert "map_token" in inspect.signature(app_modules.map.make_figure).parameters


def test_existing_callback_branches_remain_and_only_named_nav_paths_skip_save(app_modules):
    source = (CHANGES / "callbacks.py").read_text(encoding="utf-8")
    for retained in (
        'trigger == "reset-confirm"', 'trigger == "selected-card"', 'trigger == "random-card"',
        'trigger == "difficulty-slider"', 'trigger == "save-position"',
        'trigger == "create-link"', 'trigger == "disconnect-link"',
        'trigger == "constellation-dialog-submit"', 'state.refresh_constellations(cards)',
    ):
        assert retained in source
    assert "if not deleted_links and not navigation_only_trigger:" in source


def test_navigation_dialog_is_transient_and_confirm_clears_derived_state(app_modules):
    state = State()
    nav, _ = _activate(app_modules, state)
    cancelled = _call(app_modules, state, "navigation-dialog-cancel", selected_id="a",
                      nav_state={**nav, "dialog": "navigation"})[18]
    assert cancelled["mode"] == "constellation" and cancelled["dialog"] is None
    assert cancelled["context"] == nav["context"]
    confirmed = _call(app_modules, state, "navigation-dialog-submit", selected_id="a", nav_state=nav,
                      navigation_select="card_order")[18]
    assert confirmed == {"mode": "card_order", "dialog": None, "context": None,
                         "preview_id": None, "previous_id": None, "scroll_pos": None,
                         "scrolled_id": None, "message": None, "message_selected_id": None}
    assert state.save_calls == 0 and state.mutations == []
