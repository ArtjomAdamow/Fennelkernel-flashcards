"""The card callback of the cluster module (replaces project/callbacks.py).

Changes against the main file:
  * `state` is the ViewRouter: the same calls reach the space state (decks) or the card state (cards).
  * Enter (key) or a click on the panel enters a selected deck in the space view; in the deck view it flips the
    card as before. The bare "back" command (Backspace, assets/keyboard.js) follows services.views.back.
  * The choice dialog (choice-open, choice-dialog-submit/cancel, choice-checklist) replaces the deck panel
    (add/remove/focus/all-decks, deck-filter, deck-dialog-*) and the reset (reset-cards, reset-confirm). In the
    space view it is Decks (checked decks are loaded and shown), in the deck view Cards (checked cards are
    shown); the button's label follows the view.
  * The position inputs (toggle-drag, save-position, drag-x/y/z) and the drag store are gone.
  * With no dot selected the panel shows the dendrogram of the view's connections.
  * The card count reads "N decks mapped" in the space view and the deck name in the deck view.
  * "Random" (random-card) is hidden in the space view; the sun takes the colours of the entered deck's groups.
  * Switching views resets the camera, the group focus, the open dialogs and the navigation context.
  * A module action (services.actions): a click on the top bar button `module-action` runs the action's function
    on the router; the change is then saved and drawn like any other (a hook for the helper module).
  * The figure's meta carries the selected dot's constellation (its members), which camera.js fits into the
    window in the space view (the planetarium around the selected deck).
  * Connect and Disconnect open a dialog (link-dialog-submit/cancel, the link-dialog store), as in the main
    project since 2026-10-22; the dialog closes on a view change too, and the back key is blocked while it is open.
  * With no dot selected the progress slider is the cut-off line of the view's dendrogram (ViewRouter.cutoff):
    moving it cuts the tree, the map's connections and the constellations below the line; the dendrogram shows
    the line. The cut-off is runtime only and starts at the full tree.
  * Focus in the deck view is a checklist (the state dialog-group-checklist): Confirm keeps the checked groups
    (ViewRouter.set_checked_groups), All checks everything again; the space view keeps the one-group Focus.
  * The back of the card panel (a hook for the helper module): with `overview_back` and nothing selected, Enter
    or a click on the panel flips between the dendrogram and the back the function draws. The flip is the
    `revealed` store, which a selection and a view change reset; it is no longer reset just because nothing is
    selected. Without `overview_back` nothing flips.
"""

from dash import Input, Output, State

from project.layout.map import DEFAULT_CAMERA, make_figure
from project.layout.panels import (
    card_panel, choice_control, choice_label, connection_control, deck_panel, delete_constellation,
    difficulty_control, group_control, overview_panel,
)
from project.services import cards as cards_service
from project.services import dendrogram, navigation, views
from project.services.actions import ACTION_ID


FLIP_HINT = "Enter or a click on this frame turns it over."


def register_callbacks(app, state, none_deck=None, action=None, overview_back=None):
    """Register the card callback on `app`.

    `state` is the ViewRouter the callback reads and changes; `none_deck` is unused (kept for the main
    signature); `action` is the module action of the top bar button, or None; `overview_back` draws the back of
    the card panel from the router while nothing is selected, or None. Returns the callback function (for tests).
    """

    @app.callback(
        Output("sphere", "figure"),
        Output("selected-card", "children"),
        Output("difficulty-control", "children"),
        Output("group-control", "children"),
        Output("connection-control", "children"),
        Output("group-status", "children"),
        Output("selected-id", "data"),
        Output("revealed", "data"),
        Output("card-count", "children"),
        Output("keyboard-nav", "value"),
        Output("group-dialog", "data"),
        Output("focused-group", "data"),
        Output("choice-control", "children"),
        Output("choice-dialog", "data"),
        Output("nav-state", "data"),
        Output("random-card", "style"),
        Output("choice-open", "children"),
        Input("sphere", "clickData"),
        Input("selected-card", "n_clicks"),
        Input("random-card", "n_clicks"),
        Input("difficulty-slider", "value"),
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
        Input("keyboard-nav", "value"),
        Input("choice-open", "n_clicks"),
        Input("choice-dialog-submit", "n_clicks"),
        Input("choice-dialog-cancel", "n_clicks"),
        Input("delete-constellation", "n_clicks"),
        Input("constellation-dialog-submit", "n_clicks"),
        Input("constellation-dialog-cancel", "n_clicks"),
        Input("link-dialog-submit", "n_clicks"),
        Input("link-dialog-cancel", "n_clicks"),
        Input("navigation-open", "n_clicks"),
        Input("navigation-dialog-submit", "n_clicks"),
        Input("navigation-dialog-cancel", "n_clicks"),
        Input(ACTION_ID, "n_clicks"),
        State("selected-id", "data"),
        State("revealed", "data"),
        State("link-target", "value"),
        State("sphere", "relayoutData"),
        State("sphere", "hoverData"),
        State("group-dialog", "data"),
        State("focused-group", "data"),
        State("dialog-group-name", "value"),
        State("dialog-group-color", "value"),
        State("dialog-group-select", "value"),
        State("choice-dialog", "data"),
        State("choice-checklist", "value"),
        State("constellation-dialog", "data"),
        State("constellation-select", "value"),
        State("link-dialog", "data"),
        State("navigation-select", "value"),
        State("nav-state", "data"),
        State("dialog-group-checklist", "value"),
    )
    def update_card(
        click_data, panel_clicks, random_clicks, difficulty, new_group_clicks,
        create_link_clicks, disconnect_link_clicks, add_group_clicks, remove_group_clicks,
        delete_group_clicks, focus_group_clicks, all_groups_clicks, dialog_submit_clicks, dialog_cancel_clicks,
        keyboard_nav, choice_open_clicks, choice_submit_clicks, choice_cancel_clicks,
        delete_constellation_clicks, constellation_submit_clicks,
        constellation_cancel_clicks, link_submit_clicks, link_cancel_clicks,
        navigation_open_clicks, navigation_submit_clicks, navigation_cancel_clicks,
        action_clicks,
        selected_id, revealed, link_target, relayout_data, hover_data,
        group_dialog, focused_group, dialog_group_name, dialog_group_color,
        dialog_group_select, choice_dialog, choice_checked, constellation_dialog, constellation_select, link_dialog,
        navigation_select, nav_state, dialog_group_checked
    ):
        from dash import ctx
        import random

        cards = state.visible_cards(None, focused_group)
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
            and not (command in {"enter", "back"} and payload is None)
        )
        next_group_dialog = group_dialog
        next_focused_group = focused_group
        next_choice_dialog = bool(choice_dialog)
        # phase 4: constellations
        next_constellation_dialog = constellation_dialog
        next_link_dialog = link_dialog
        deleted_links = False
        view_before = (state.view, state.entered_deck)
        dialog_open = bool(group_dialog or choice_dialog or constellation_dialog or link_dialog or nav_state.get("dialog"))

        def current_view() -> views.ViewState:
            return views.ViewState(state.view, state.entered_deck, selected_id)

        def switch(result: views.ViewState) -> None:
            nonlocal selected_id, revealed
            state.set_view(result.view, result.entered)
            selected_id = result.selected
            revealed = False

        if trigger == "choice-open":
            next_choice_dialog = not bool(choice_dialog)
        elif trigger == "choice-dialog-cancel":
            next_choice_dialog = False
        elif trigger == "choice-dialog-submit":
            checked = set(choice_checked or [])
            if state.view == views.DECK:
                # Cards: checked cards are shown; unchecking only hides a card
                state.set_shown_cards([card.id for card in state.deck_cards() if card.id in checked])
            else:
                # Decks: checked decks are loaded and shown; unchecking strips the deck's card state
                for deck_name in state.available_decks():
                    if deck_name in checked and deck_name not in state.enabled_decks:
                        state.enable_deck(deck_name)
                    elif deck_name not in checked and deck_name in state.enabled_decks:
                        state.disable_deck(deck_name)
            next_choice_dialog = False
        elif trigger == "sphere" and click_data and click_data.get("points"):
            clicked_id = cards_service.select_from_click(click_data, hover_data)
            if clicked_id:
                selected_id = clicked_id
                revealed = False
        elif trigger == "selected-card" and selected_id:
            entered = views.enter(current_view())
            if entered is not None:
                switch(entered)
            else:
                revealed = not revealed
                if revealed:
                    state.mark_read(selected_id)
        elif trigger == "selected-card" and overview_back is not None:
            revealed = not revealed  # nothing selected: the panel turns between the dendrogram and its back
        elif trigger == "random-card" and cards and state.view == views.DECK:
            chosen = cards_service.choose_random_card(cards, state.progress, random)
            selected_id = chosen.id if chosen else None
            revealed = False
        elif trigger == "keyboard-nav" and keyboard_nav:
            if command == "back" and payload is None:
                switch(views.back(current_view(), dialog_open))
            elif command == "enter" and payload is None and selected_id:
                entered = views.enter(current_view())
                if entered is not None:
                    switch(entered)
                else:
                    revealed = not revealed
                    if revealed:
                        state.mark_read(selected_id)
            elif command == "enter" and payload is None and overview_back is not None:
                revealed = not revealed  # nothing selected: the panel turns between the dendrogram and its back
            elif mode == "card_order" and payload is None and command in {"next", "right", "down", "previous", "prev", "left", "up"}:
                direction = 1 if command in {"next", "right", "down"} else -1
                adjacent = cards_service.adjacent_card(cards, selected_id, direction)
                selected_id = adjacent.id if adjacent else None
                revealed = False
            # In constellation mode the JSON commands are handled after the visible
            # constellation refresh. Bare commands and malformed commands are ignored.
        elif trigger == "difficulty-slider" and selected_id and difficulty is not None and state.view == views.DECK:
            state.set_difficulty(selected_id, difficulty)
        elif trigger == "difficulty-slider" and not selected_id and difficulty is not None:
            state.set_cutoff(difficulty / 100)  # the slider is the cut-off line while nothing is selected
        elif trigger == "new-group" and selected_id:
            next_group_dialog = "new"
        elif trigger == "create-link" and selected_id:
            next_link_dialog = "connect"
        elif trigger == "disconnect-link" and selected_id:
            next_link_dialog = "disconnect"
        elif trigger == "link-dialog-cancel":
            next_link_dialog = None
        elif trigger == "link-dialog-submit" and link_dialog == "connect" and selected_id and link_target and link_target != selected_id:
            state.create_link(selected_id, link_target)
            next_link_dialog = None
        elif trigger == "link-dialog-submit" and link_dialog == "disconnect" and selected_id and link_target and link_target != selected_id:
            state.disconnect_link(selected_id, link_target)
            next_link_dialog = None
        elif trigger == "add-group" and selected_id:
            next_group_dialog = "add"
        elif trigger == "remove-group" and selected_id:
            next_group_dialog = "remove"
        elif trigger == "focus-group":
            next_group_dialog = "focus"
        elif trigger == "all-groups":
            next_focused_group = None
            state.set_checked_groups(None)
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
        elif trigger == "group-dialog-submit" and group_dialog == "focus" and state.view == views.DECK:
            # The deck view's Focus: the cards of the checked groups stay (the router keeps the checks)
            state.set_checked_groups(dialog_group_checked or [])
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
        elif trigger == ACTION_ID and action is not None:
            # The module's button: its function changes the state (connections, say); saved and drawn below
            action.run(state)
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

        # A view change (entered, left, or the entered deck unchecked) starts the new view clean
        view_changed = (state.view, state.entered_deck) != view_before
        if view_changed:
            revealed = False
            next_focused_group = None
            next_group_dialog = None
            next_choice_dialog = False
            next_constellation_dialog = None
            next_link_dialog = None
            nav_state.update({"context": None, "preview_id": None, "previous_id": None, "scroll_pos": None,
                              "scrolled_id": None, "message": None, "message_selected_id": None})

        cards = state.visible_cards(None, next_focused_group)
        if selected_id is not None and selected_id not in {card.id for card in cards}:
            selected_id = None
            revealed = False
        if selected_id is None and overview_back is None:
            revealed = False  # nothing to turn over
        # Constellations are runtime-derived from current visible cards and links.
        state.refresh_constellations(cards)
        if selected_id != selected_id_at_start:
            next_link_dialog = None  # a new selection closes a dialog listed for another dot

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
            "link-dialog-submit", "constellation-dialog-submit", "choice-dialog-submit",
            "choice-dialog-cancel", "focus-group", "all-groups", "group-dialog-submit", "group-dialog-cancel",
            ACTION_ID,
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
                generation = view.get("generation") if isinstance(view, dict) else None
                if selected_constellation is None:
                    # Non-member: message only, no view is read or validated.
                    context = None
                    preview_id = previous_id = scroll_pos = scrolled_id = None
                    if selected_id is not None:
                        message = "unconnected"
                        message_selected_id = selected_id
                elif not isinstance(view, dict):
                    # A member's Space must carry a view; a malformed command is ignored.
                    pass
                elif not navigation.validate_view(view)[0] or not isinstance(generation, int) or isinstance(generation, bool):
                    print("Ignoring keyboard navigation command with invalid camera view", navigation.validate_view(view)[1])
                elif view.get("map_token") != current_token:
                    # The rendered map is stale; refresh it without accepting the key.
                    pass
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

        # The camera: a view change starts at the default camera; until the user moves it in the new view,
        # relayoutData still holds the last camera of the previous view
        camera = (relayout_data or {}).get("scene.camera")
        if view_changed:
            nav_state["stale_camera"] = camera
            camera = DEFAULT_CAMERA
        elif camera is not None and camera == nav_state.get("stale_camera"):
            camera = DEFAULT_CAMERA

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
        space_view = state.view == views.SPACE
        selected_card = state.card_by_id.get(selected_id)
        preview_card = (
            state.card_by_id.get(preview_id)
            if preview_id and preview_id != selected_id else None
        )
        context_members = context.get("members") if context else None
        flip_hint = f" {FLIP_HINT}" if overview_back is not None else ""
        if selected_card is None and revealed and overview_back is not None:
            panel = overview_back(state)  # the back of the card panel
        elif selected_card is None:
            # state.links are the connections below the cut-off line; the line itself is measured on the full tree
            dot_ids = [card.id for card in cards]
            forest = dendrogram.build_forest(dot_ids, state.links)
            cut = dendrogram.cut_line(dot_ids, state.active.links, state.cutoff())
            label_of = {card.id: card.question for card in cards}
            if space_view:
                panel = overview_panel(
                    "Constellations of decks", forest, label_of,
                    "Select a deck to see its description. The Decks button chooses the decks on the map." + flip_hint,
                    cut=cut,
                )
            else:
                info = state.decks.by_id.get(state.entered_deck)
                panel = overview_panel(
                    state.entered_name or "", forest, label_of,
                    "Select a card to begin; the Cards button chooses the cards on the map. Backspace goes back to the decks."
                    + flip_hint,
                    subtitle=info.description() if info else None,
                    cut=cut,
                )
        elif space_view:
            panel = deck_panel(selected_card)
        else:
            panel = card_panel(selected_card, revealed)
        if not deleted_links and not navigation_only_trigger:
            state.save()
        return (
            make_figure(
                cards, selected_id, camera, state, next_focused_group,
                preview_id=preview_id if context else None,
                scrolled_id=scrolled_id if context else None,
                nav_members=context_members, map_token=current_token,
                view=state.view, entered=state.entered_deck,
                deck_counts={info.deck_id: info.cards for info in state.decks.infos} if space_view else None,
                sun_colors=None if space_view else state.deck_colors(state.entered_deck),
                constellation=sorted(selected_constellation.members) if selected_constellation else None,
            ),
            panel,
            # A selected card: its progress; a selected deck: nothing to rate; nothing selected: the cut-off line
            difficulty_control(
                selected_card, state, hidden=space_view and selected_card is not None,
                cutoff=None if selected_card else state.cutoff(),
            ),
            group_control(selected_card, next_group_dialog, state, next_focused_group),
            connection_control(
                selected_card, cards, state, next_constellation_dialog,
                navigation={**nav_state, "preview_card": preview_card}, view=state.view,
                link_dialog=next_link_dialog,
            ),
            "Saved" if trigger in {"link-dialog-submit", "group-dialog-submit", "delete-group", "constellation-dialog-submit", ACTION_ID} else "",
            selected_id,
            revealed,
            f"{len(cards)} {'deck' if len(cards) == 1 else 'decks'} mapped" if space_view else (state.entered_name or ""),
            "",
            next_group_dialog,
            next_focused_group,
            choice_control(next_choice_dialog, state),
            next_choice_dialog,
            nav_state,
            {"display": "none"} if space_view else {},
            choice_label(state.view),
        )

    return update_card
