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
            "mode": "card_order", "dialog": None, "preview_id": None, "previous_id": None,
            "scroll_pos": None, "scrolled_id": None, "message": None,
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
        } or (
            trigger == "keyboard-nav" and mode == "constellation"
            and not (command == "enter" and payload is None)
        )
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
            if command == "enter" and payload is None and selected_id:
                revealed = not revealed
                if revealed:
                    state.mark_read(selected_id)
            elif mode == "card_order" and payload is None and command in {"next", "right", "down", "previous", "prev", "left", "up"}:
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
                              "preview_id": None, "previous_id": None, "scroll_pos": None,
                              "scrolled_id": None, "message": None, "message_selected_id": None})

        cards = visible_cards(next_deck, next_focused_group)
        if selected_id not in {card.id for card in cards}:
            selected_id = None
            revealed = False
        # Constellations are runtime-derived from current visible cards and links.
        state.refresh_constellations(cards)

        visible_ids = {card.id for card in cards}
        positions = [position for position in state.positions if position.comb_id in visible_ids]
        position_by_id = {
            position.comb_id: (position.x, position.y, position.z) for position in positions
        }
        current_token = navigation.map_token(positions)
        visible_links = [
            link for link in state.links
            if link.source_id in visible_ids and link.target_id in visible_ids
        ]
        current_links_token = navigation.links_token(visible_links)
        selected_constellation = next(
            (item for item in state.constellations if selected_id and selected_id in item.members), None
        )
        context = nav_state.get("context") if isinstance(nav_state.get("context"), dict) else None
        preview_id = nav_state.get("preview_id")
        previous_id = nav_state.get("previous_id")
        scroll_pos = nav_state.get("scroll_pos")
        scrolled_id = nav_state.get("scrolled_id")
        message = nav_state.get("message")
        message_selected_id = nav_state.get("message_selected_id")

        changed_data_triggers = {
            "drag-x", "drag-y", "drag-z", "save-position", "reset-confirm", "create-link",
            "disconnect-link", "constellation-dialog-submit", "deck-filter", "deck-dialog-submit",
            "deck-dialog-cancel", "focus-group", "all-groups", "group-dialog-submit",
            "group-dialog-cancel", "all-decks", "reset-confirm",
        }
        clear_context = not empty_nav_reset and (mode_changed or selected_id != selected_id_at_start)
        if context and not empty_nav_reset:
            current_members = sorted(selected_constellation.members) if selected_constellation else []
            current_const_id = selected_constellation.const_id if selected_constellation else None
            context_view = context.get("view", {})
            clear_context = clear_context or (
                context.get("members") != current_members
                or context.get("const_id") != current_const_id
                or context_view.get("map_token") != current_token
                or context.get("links_token") != current_links_token
                or trigger in changed_data_triggers
            )
        if clear_context:
            context = None
            preview_id = previous_id = scroll_pos = scrolled_id = None
        if mode != "constellation":
            context = None
            preview_id = previous_id = scroll_pos = scrolled_id = None
            message = message_selected_id = None

        if not empty_nav_reset:
            if selected_id != nav_state.get("message_selected_id"):
                message = message_selected_id = None
            if message == "unconnected" and selected_constellation is not None:
                message = message_selected_id = None
            if message == "hit_space" and selected_constellation is None:
                message = message_selected_id = None

        if trigger == "keyboard-nav" and mode == "constellation" and not empty_nav_reset:
            if command == "invalidate" and payload is not None:
                generation = payload.get("generation")
                context_view = context.get("view", {}) if context else {}
                current_generation = context_view.get("generation")
                if (context and isinstance(generation, int) and not isinstance(generation, bool)
                        and isinstance(current_generation, int) and generation > current_generation):
                    context = None
                    preview_id = previous_id = scroll_pos = scrolled_id = None
            elif command == "space" and payload is not None:
                view = payload.get("view")
                valid, checks = navigation.validate_view(view)
                generation = view.get("generation") if isinstance(view, dict) else None
                if not valid or not isinstance(generation, int) or isinstance(generation, bool):
                    print("Ignoring keyboard navigation command with invalid camera view", checks)
                elif view.get("map_token") != current_token:
                    # The rendered map is stale; refresh it without accepting the key.
                    pass
                elif selected_constellation is None:
                    context = None
                    preview_id = previous_id = scroll_pos = scrolled_id = None
                    message = "unconnected"
                    message_selected_id = selected_id
                else:
                    members = sorted(selected_constellation.members)
                    old_view = context.get("view", {}) if context else {}
                    old_generation = old_view.get("generation")
                    if (context and isinstance(old_generation, int) and generation < old_generation):
                        # Ignore a late Space captured against an earlier camera view.
                        pass
                    else:
                        current_const_id = selected_constellation.const_id
                        reusable = bool(context) and (
                            old_generation == generation
                            and old_view.get("map_token") == view.get("map_token")
                            and context.get("members") == members
                            and context.get("const_id") == current_const_id
                            and context.get("links_token") == current_links_token
                            and context.get("selected_id") == selected_id
                        )
                        if not reusable:
                            adjacency = {member: set() for member in members}
                            for link in visible_links:
                                left, right = link.source_id, link.target_id
                                if left in adjacency and right in adjacency and left != right:
                                    adjacency[left].add(right)
                                    adjacency[right].add(left)
                            context = {
                                "const_id": current_const_id,
                                "members": members,
                                "positions": {
                                    member: list(position_by_id[member])
                                    for member in members if member in position_by_id
                                },
                                "adjacency": {member: sorted(adjacency[member]) for member in members},
                                "links_token": current_links_token,
                                "selected_id": selected_id,
                                "view": view,
                                "rings": [],
                            }
                            preview_id = selected_id
                            previous_id = scroll_pos = scrolled_id = None
                            message = message_selected_id = None
                        elif scrolled_id is not None:
                            previous_id = preview_id
                            preview_id = scrolled_id
                            scroll_pos = scrolled_id = None
                            message = message_selected_id = None
                        else:
                            # Space with no highlighted connection selects the current navigated card.
                            selection = cards_service.select_from_click(
                                {"points": [{"customdata": preview_id}]}, None
                            )
                            if selection:
                                selected_id = selection
                            revealed = False
                            context = None
                            preview_id = previous_id = scroll_pos = scrolled_id = None
                            message = message_selected_id = None
                            navigation_only_trigger = False
            elif command in {"left", "right", "up", "down"} and payload is not None:
                generation = payload.get("generation")
                if not isinstance(generation, int) or isinstance(generation, bool):
                    pass
                elif selected_constellation is None:
                    context = None
                    preview_id = previous_id = scroll_pos = scrolled_id = None
                    message = "unconnected"
                    message_selected_id = selected_id
                else:
                    context_view = context.get("view", {}) if context else {}
                    context_generation = context_view.get("generation")
                    if (context and isinstance(context_generation, int) and generation < context_generation):
                        # A delayed key from an earlier camera state is harmless.
                        pass
                    elif (context is None or generation > context_generation):
                        context = None
                        preview_id = previous_id = scroll_pos = scrolled_id = None
                        message = "hit_space"
                        message_selected_id = selected_id
                    elif command in {"left", "right"}:
                        origin = preview_id
                        if origin is not None:
                            ring_entry = next((entry for entry in context.get("rings", [])
                                               if entry.get("origin") == origin
                                               and entry.get("previous") == previous_id), None)
                            if ring_entry is None:
                                order = navigation.rank_ring(
                                    origin, previous_id, context.get("positions", {}),
                                    context.get("adjacency", {}).get(origin, []),
                                    context.get("view", {}), random,
                                )
                                ring_entry = {"origin": origin, "previous": previous_id, "order": order}
                                context.setdefault("rings", []).append(ring_entry)
                            order = ring_entry.get("order", [])
                            next_position = navigation.step_scroll(scroll_pos, command, len(order))
                            if next_position is not None:
                                scroll_pos = next_position
                                scrolled_id = order[next_position - 1]
                    # Up and Down do nothing while a valid navigation context is active.
            # JSON Enter is intentionally ignored. Bare Enter was handled above as the flip action.

        if not empty_nav_reset:
            nav_state.update({
                "mode": mode,
                "context": context,
                "preview_id": preview_id,
                "previous_id": previous_id,
                "scroll_pos": scroll_pos,
                "scrolled_id": scrolled_id,
                "message": message,
                "message_selected_id": message_selected_id,
            })
        selected_card = state.card_by_id.get(selected_id)
        preview_card = (
            state.card_by_id.get(preview_id)
            if preview_id and preview_id != selected_id else None
        )
        context_members = context.get("members") if context else None
        if not deleted_links and not navigation_only_trigger:
            state.save()
        return (
            make_figure(
                cards, selected_id, (relayout_data or {}).get("scene.camera"), state, next_focused_group,
                preview_id=preview_id if context else None,
                scrolled_id=scrolled_id if context else None,
                nav_members=context_members, map_token=current_token,
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