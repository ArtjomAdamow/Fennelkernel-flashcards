from dash import Input, Output, State
import importlib.util
import sys
from pathlib import Path

from flashcards_app.services import cards as cards_service
from flashcards_app.visualization.map import make_figure
from flashcards_app.visualization.panels import (
    card_panel, connection_control, deck_control, deck_filter_options, delete_constellation, difficulty_control,
    group_control, position_control,
)



def _load_navigation():
    """Load the pure helper from its module-relative path, not from sys.path."""
    source = Path(__file__).resolve().parent.parent / "navigation.py"
    alias = "_constellations_navigation"
    existing = sys.modules.get(alias)
    if existing is not None and Path(getattr(existing, "__file__", "")).resolve() == source.resolve():
        return existing
    spec = importlib.util.spec_from_file_location(alias, source)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load navigation logic from {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(alias, None)
        raise
    return module


navigation = _load_navigation()


def register_callbacks(app, state, none_deck="None"):
    """Register the card callback on `app`.

    `state` is the UserStateService the callback reads and changes; `none_deck` is the name of the
    placeholder deck that shows an empty map. Returns the callback function (for tests).
    """

    def visible_cards(deck, focused_group):
        # "all" and the empty-map deck are UI sentinels; the state only knows "one deck" or "any deck"
        if deck in {None, none_deck}:
            return []
        return state.visible_cards(None if deck == "all" else deck, focused_group)

    @app.callback(
        Output("sphere", "figure"),
        Output("selected-card", "children"),
        Output("difficulty-control", "children"),
        Output("position-control", "children"),
        Output("group-control", "children"),
        Output("connection-control", "children"),
        Output("group-status", "children"),
        Output("selected-id", "data"),
        Output("revealed", "data"),
        Output("card-count", "children"),
        Output("drag-enabled", "data"),
        Output("keyboard-nav", "value"),
        Output("reset-confirm", "displayed"),
        Output("group-dialog", "data"),
        Output("focused-group", "data"),
        Output("deck-control", "children"),
        Output("deck-dialog-state", "data"),
        Output("deck-filter", "options"),
        Output("nav-state", "data"),
        Input("sphere", "clickData"),
        Input("selected-card", "n_clicks"),
        Input("random-card", "n_clicks"),
        Input("deck-filter", "value"),
        Input("difficulty-slider", "value"),
        Input("save-position", "n_clicks"),
        Input("new-group", "n_clicks"),
        Input("create-link", "n_clicks"),
        Input("disconnect-link", "n_clicks"),
        Input("add-group", "n_clicks"),
        Input("remove-group", "n_clicks"),
        Input("delete-group", "n_clicks"),
        Input("focus-group", "n_clicks"),
        Input("all-groups", "n_clicks"),
        Input("group-dialog-submit", "n_clicks"),
        Input("group-dialog-cancel", "n_clicks"),
        Input("toggle-drag", "n_clicks"),
        Input("drag-x", "value"),
        Input("drag-y", "value"),
        Input("drag-z", "value"),
        Input("keyboard-nav", "value"),
        Input("reset-cards", "n_clicks"),
        Input("reset-confirm", "submit_n_clicks"),
        Input("add-deck", "n_clicks"),
        Input("remove-deck", "n_clicks"),
        Input("focus-deck", "n_clicks"),
        Input("all-decks", "n_clicks"),
        Input("deck-dialog-submit", "n_clicks"),
        Input("deck-dialog-cancel", "n_clicks"),
        Input("delete-constellation", "n_clicks"),
        Input("constellation-dialog-submit", "n_clicks"),
        Input("constellation-dialog-cancel", "n_clicks"),
        Input("navigation-open", "n_clicks"),
        Input("navigation-dialog-submit", "n_clicks"),
        Input("navigation-dialog-cancel", "n_clicks"),
        State("selected-id", "data"),
        State("revealed", "data"),
        State("link-target", "value"),
        State("sphere", "relayoutData"),
        State("sphere", "hoverData"),
        State("drag-enabled", "data"),
        State("group-dialog", "data"),
        State("focused-group", "data"),
        State("dialog-group-name", "value"),
        State("dialog-group-color", "value"),
        State("dialog-group-select", "value"),
        State("deck-dialog-state", "data"),
        State("deck-dialog-select", "value"),
        State("constellation-dialog", "data"),
        State("constellation-select", "value"),
        State("navigation-select", "value"),
        State("nav-state", "data"),
    )
    def update_card(
        click_data, panel_clicks, random_clicks, deck, difficulty, save_position_clicks, new_group_clicks,
        create_link_clicks, disconnect_link_clicks, add_group_clicks, remove_group_clicks,
        delete_group_clicks, focus_group_clicks, all_groups_clicks, dialog_submit_clicks, dialog_cancel_clicks,
        toggle_drag_clicks, drag_x, drag_y, drag_z, keyboard_nav, reset_clicks, reset_submit_clicks,
        add_deck_clicks, remove_deck_clicks, focus_deck_clicks, all_decks_clicks, deck_dialog_submit_clicks,
        deck_dialog_cancel_clicks, delete_constellation_clicks, constellation_submit_clicks,
        constellation_cancel_clicks, navigation_open_clicks, navigation_submit_clicks, navigation_cancel_clicks,
        selected_id, revealed, link_target, relayout_data, hover_data,
        drag_enabled, group_dialog, focused_group, dialog_group_name, dialog_group_color,
        dialog_group_select, deck_dialog_state, deck_dialog_select, constellation_dialog, constellation_select,
        navigation_select, nav_state
    ):
        from dash import ctx
        import random

        cards = visible_cards(deck, focused_group)
        trigger = ctx.triggered_id
        nav_state = dict(nav_state) if isinstance(nav_state, dict) else {
            "mode": "card_order", "dialog": None, "preview_id": None, "message": None,
            "message_selected_id": None, "context": None,
        }
        mode = nav_state.get("mode", "card_order")
        if mode not in {"card_order", "constellation"}:
            mode = "card_order"
        empty_nav_reset = (
            trigger == "keyboard-nav" and keyboard_nav == ""
            and isinstance(nav_state, dict) and nav_state.get("mode") == "constellation"
        )
        if not empty_nav_reset:
            nav_state["mode"] = mode
        selected_id_at_start = selected_id
        command, payload = navigation.parse_command(keyboard_nav)
        mode_changed = False
        navigation_only_trigger = trigger in {
            "navigation-open", "navigation-dialog-submit", "navigation-dialog-cancel"
        } or (trigger == "keyboard-nav" and mode == "constellation" and command != "space")
        reset_dialog = False
        next_group_dialog = group_dialog
        next_focused_group = focused_group
        next_deck_dialog = deck_dialog_state
        next_deck = deck
        # phase 4: constellations
        next_constellation_dialog = constellation_dialog
        deleted_links = False

        if trigger == "reset-cards":
            reset_dialog = True
        elif trigger == "reset-confirm":
            state.reset_all_state()
            selected_id = None
            revealed = False
            drag_enabled = False
            next_focused_group = None
        elif trigger == "add-deck":
            # phase 2: the course file is read again only here, so the dialog offers decks added to it
            state.reload_decks()
            next_deck_dialog = "add"
        elif trigger == "remove-deck":
            next_deck_dialog = "remove"
        elif trigger == "focus-deck":
            next_deck_dialog = "focus"
        elif trigger == "all-decks":
            next_deck = "all"
            next_deck_dialog = None
        elif trigger == "deck-dialog-cancel":
            next_deck_dialog = None
        elif trigger == "deck-dialog-submit" and deck_dialog_select and deck_dialog_state == "add":
            state.enable_deck(deck_dialog_select)
            next_deck_dialog = None
        elif trigger == "deck-dialog-submit" and deck_dialog_select and deck_dialog_state == "remove":
            if state.disable_deck(deck_dialog_select):
                if selected_id and selected_id not in {card.id for card in state.cards}:
                    selected_id = None
                    revealed = False
                if deck != "all" and deck == deck_dialog_select:
                    next_deck = none_deck
            next_deck_dialog = None
        elif trigger == "deck-dialog-submit" and deck_dialog_select and deck_dialog_state == "focus":
            if deck_dialog_select in state.enabled_decks:
                next_deck = deck_dialog_select
            next_deck_dialog = None
        elif trigger == "sphere" and click_data and click_data.get("points"):
            clicked_id = cards_service.select_from_click(click_data, hover_data)
            if clicked_id:
                selected_id = clicked_id
                revealed = False
        elif trigger == "selected-card" and selected_id:
            revealed = not revealed
            if revealed:
                state.mark_read(selected_id)
        elif trigger == "random-card" and cards:
            chosen = cards_service.choose_random_card(cards, state.progress, random)
            selected_id = chosen.id if chosen else None
            revealed = False
        elif trigger == "keyboard-nav" and keyboard_nav:
            if command == "space" and selected_id:
                revealed = not revealed
                if revealed:
                    state.mark_read(selected_id)
            elif mode == "card_order" and command in {"next", "right", "down", "previous", "prev", "left", "up"}:
                direction = 1 if command in {"next", "right", "down"} else -1
                adjacent = cards_service.adjacent_card(cards, selected_id, direction)
                selected_id = adjacent.id if adjacent else None
                revealed = False
            # In constellation mode the JSON commands are handled after the visible
            # constellation refresh. Bare commands and malformed commands are ignored.
        elif trigger == "difficulty-slider" and selected_id and difficulty is not None:
            state.set_difficulty(selected_id, difficulty)
        elif trigger == "save-position" and selected_id and None not in (drag_x, drag_y, drag_z):
            state.set_position(selected_id, drag_x, drag_y, drag_z)
            drag_enabled = False
        elif trigger == "toggle-drag" and selected_id:
            drag_enabled = not bool(drag_enabled)
        elif trigger in {"drag-x", "drag-y", "drag-z"} and selected_id and None not in (drag_x, drag_y, drag_z):
            state.set_position(selected_id, drag_x, drag_y, drag_z)
        elif trigger == "new-group" and selected_id:
            next_group_dialog = "new"
        elif trigger == "create-link" and selected_id and link_target and link_target != selected_id:
            state.create_link(selected_id, link_target)
        elif trigger == "disconnect-link" and selected_id and link_target and link_target != selected_id:
            state.disconnect_link(selected_id, link_target)
        elif trigger == "add-group" and selected_id:
            next_group_dialog = "add"
        elif trigger == "remove-group" and selected_id:
            next_group_dialog = "remove"
        elif trigger == "focus-group":
            next_group_dialog = "focus"
        elif trigger == "all-groups":
            next_focused_group = None
        elif trigger == "group-dialog-cancel":
            next_group_dialog = None
        elif trigger == "group-dialog-submit" and selected_id and group_dialog == "new" and dialog_group_name:
            group_color_value = (dialog_group_color or {}).get("hex", "#f5b942")
            state.create_group(selected_id, dialog_group_name, group_color_value)
            next_group_dialog = None
        elif trigger == "group-dialog-submit" and selected_id and group_dialog == "add" and dialog_group_select:
            state.add_to_group(selected_id, dialog_group_select)
            next_group_dialog = None
        elif trigger == "group-dialog-submit" and selected_id and group_dialog == "remove" and dialog_group_select:
            state.remove_from_group(selected_id, dialog_group_select)
            next_group_dialog = None
        elif trigger == "group-dialog-submit" and group_dialog == "delete" and dialog_group_select:
            state.delete_group(dialog_group_select)
            if next_focused_group == dialog_group_select:
                next_focused_group = None
            next_group_dialog = None
        elif trigger == "group-dialog-submit" and group_dialog == "focus" and dialog_group_select:
            next_focused_group = dialog_group_select
            next_group_dialog = None
        elif trigger == "delete-group" and selected_id:
            next_group_dialog = "delete"
        elif trigger == "delete-constellation":
            next_constellation_dialog = "delete"
        elif trigger == "constellation-dialog-cancel":
            next_constellation_dialog = None
        elif trigger == "constellation-dialog-submit" and constellation_dialog == "delete" and constellation_select:
            # Delete: the state core removes the links between the members and saves that by itself
            delete_constellation(state, constellation_select)
            deleted_links = True
            next_constellation_dialog = None
        elif trigger == "deck-filter":
            if selected_id not in {card.id for card in cards}:
                selected_id = None
            revealed = False
        elif trigger == "navigation-open":
            nav_state["dialog"] = "navigation"
        elif trigger == "navigation-dialog-cancel":
            nav_state["dialog"] = None
        elif trigger == "navigation-dialog-submit":
            new_mode = navigation_select if navigation_select in {"card_order", "constellation"} else "card_order"
            mode_changed = new_mode != mode
            mode = new_mode
            nav_state.update({"mode": mode, "dialog": None, "context": None,
                              "preview_id": None, "message": None, "message_selected_id": None})

        cards = visible_cards(next_deck, next_focused_group)
        if selected_id not in {card.id for card in cards}:
            selected_id = None
            revealed = False
        # Runtime-only constellation refresh is permitted on navigation-only triggers.
        state.refresh_constellations(cards)

        positions = [position for position in state.positions if position.comb_id in {card.id for card in cards}]
        current_token = navigation.map_token(positions)
        selected_constellation = next(
            (item for item in state.constellations if selected_id and selected_id in item.members), None
        )
        context = nav_state.get("context") if isinstance(nav_state.get("context"), dict) else None
        preview_id = nav_state.get("preview_id")
        message = nav_state.get("message")

        # Clear cached navigation whenever its selection, mode, members, token or source data changes.
        changed_data_triggers = {
            "drag-x", "drag-y", "drag-z", "save-position", "reset-confirm", "create-link",
            "disconnect-link", "constellation-dialog-submit", "deck-filter", "deck-dialog-submit",
            "deck-dialog-cancel", "focus-group", "all-groups", "group-dialog-submit", "group-dialog-cancel",
        }
        clear_context = False if empty_nav_reset else (mode_changed or selected_id != selected_id_at_start)
        if context and not empty_nav_reset:
            context_members = context.get("members", [])
            current_members = sorted(selected_constellation.members) if selected_constellation else []
            current_const_id = selected_constellation.const_id if selected_constellation else None
            view = context.get("view", {})
            clear_context = clear_context or (
                context_members != current_members
                or context.get("const_id") != current_const_id
                or view.get("map_token") != current_token
                or trigger in changed_data_triggers
            )
        if clear_context:
            context = None
            preview_id = None
            if message == "no_candidate":
                message = None
        if mode != "constellation":
            context = None
            preview_id = None
            message = None
        if not empty_nav_reset and message == "unconnected" and (
            mode != "constellation" or selected_id != nav_state.get("message_selected_id")
            or selected_constellation is not None
        ):
            message = None

        if trigger == "keyboard-nav" and mode == "constellation" and not empty_nav_reset:
            if command == "invalidate" and payload is not None:
                generation = payload.get("generation")
                view = context.get("view", {}) if context else {}
                if context and isinstance(generation, (int, float)) and generation > view.get("generation", -1):
                    context = None
                    preview_id = None
                    if message == "no_candidate":
                        message = None
            elif command == "enter" and payload is not None:
                generation = payload.get("generation")
                view = context.get("view", {}) if context else {}
                if context and generation == view.get("generation"):
                    if preview_id and preview_id != selected_id and selected_constellation and preview_id in selected_constellation.members:
                        selected_id = preview_id
                        revealed = False
                        context = None
                        preview_id = None
                        message = None
                elif context and isinstance(generation, (int, float)) and generation > view.get("generation", -1):
                    # A newer Enter means the browser view has moved on; discard this preview.
                    context = None
                    preview_id = None
                    message = None
                # Older generations and Enter without a matching context are stale no-ops.
            elif command in {"right", "left", "up", "down"} and payload is not None:
                view = payload.get("view")
                valid, checks = navigation.validate_view(view)
                if not valid:
                    print("Ignoring keyboard navigation command with invalid camera view", checks)
                elif view.get("map_token") != current_token:
                    # Stale rendered map: ignore this command and refresh the figure. Existing
                    # context invalidation above independently compares its token to current state.
                    pass
                elif selected_constellation is None:
                    context = None
                    preview_id = None
                    message = "unconnected"
                    nav_state["message_selected_id"] = selected_id
                else:
                    members = sorted(selected_constellation.members)
                    old_generation = context.get("view", {}).get("generation") if context else None
                    incoming_generation = view.get("generation")
                    stale_generation = (
                        context is not None
                        and isinstance(old_generation, (int, float))
                        and isinstance(incoming_generation, (int, float))
                        and incoming_generation < old_generation
                    )
                    reusable = bool(context) and (
                        old_generation == incoming_generation
                        and context.get("view", {}).get("map_token") == view.get("map_token")
                        and context.get("members") == members
                        and context.get("const_id") == selected_constellation.const_id
                        and context.get("selected_id") == selected_id
                    )
                    if stale_generation:
                        # A late command from an earlier settled camera cannot replace a newer context.
                        pass
                    elif not reusable:
                        context = {
                            "const_id": selected_constellation.const_id,
                            "members": members,
                            "positions": {
                                member: [state.position_by_id[member].x, state.position_by_id[member].y,
                                         state.position_by_id[member].z]
                                for member in members if member in state.position_by_id
                            },
                            "selected_id": selected_id,
                            "view": view,
                            "orders": [], "predefined": [], "history": [],
                        }
                        preview_id = None
                    if not stale_generation:
                        origin = preview_id or selected_id
                        target, context = navigation.next_preview(
                            context, origin, command, context.get("positions", {}), random
                        )
                        if target is None:
                            message = "no_candidate"
                        else:
                            preview_id = None if target == selected_id else target
                            message = None
            # The empty reset, Space, bare arrows and unparsable values are no-op here.

        if not empty_nav_reset:
            nav_state.update({
                "mode": mode,
                "context": context,
                "preview_id": preview_id,
                "message": message,
                "message_selected_id": nav_state.get("message_selected_id") if message == "unconnected" else None,
            })
        selected_card = state.card_by_id.get(selected_id)
        preview_card = state.card_by_id.get(preview_id) if preview_id else None
        context_members = context.get("members") if context else None
        if not deleted_links and not navigation_only_trigger:
            state.save()
        return (
            make_figure(
                cards, selected_id, (relayout_data or {}).get("scene.camera"), state, next_focused_group,
                preview_id=preview_id, nav_members=context_members, map_token=current_token,
            ),
            card_panel(selected_card, revealed),
            difficulty_control(selected_card, state),
            position_control(selected_card, bool(drag_enabled), state),
            group_control(selected_card, next_group_dialog, state, next_focused_group),
            connection_control(
                selected_card, cards, state, next_constellation_dialog,
                navigation={**nav_state, "preview_card": preview_card},
            ),
            "Saved" if trigger in {"save-position", "create-link", "disconnect-link", "group-dialog-submit", "delete-group", "constellation-dialog-submit"} else "",
            selected_id,
            revealed,
            f"{len(cards)} cards mapped",
            bool(drag_enabled),
            "",
            reset_dialog,
            next_group_dialog,
            next_focused_group,
            deck_control(next_deck_dialog, next_deck, state),
            next_deck_dialog,
            deck_filter_options(state),
            nav_state,
        )

    return update_card