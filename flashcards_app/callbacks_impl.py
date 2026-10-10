from dash import Input, Output, State

from flashcards_app.services import cards as cards_service
from flashcards_app.visualization.map import make_figure
from flashcards_app.visualization.panels import (
    card_panel, connection_control, deck_control, deck_filter_options, difficulty_control,
    group_control, position_control,
)


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
    )
    def update_card(
        click_data, panel_clicks, random_clicks, deck, difficulty, save_position_clicks, new_group_clicks,
        create_link_clicks, disconnect_link_clicks, add_group_clicks, remove_group_clicks,
        delete_group_clicks, focus_group_clicks, all_groups_clicks, dialog_submit_clicks, dialog_cancel_clicks,
        toggle_drag_clicks, drag_x, drag_y, drag_z, keyboard_nav, reset_clicks, reset_submit_clicks,
        add_deck_clicks, remove_deck_clicks, focus_deck_clicks, all_decks_clicks, deck_dialog_submit_clicks,
        deck_dialog_cancel_clicks, selected_id, revealed, link_target, relayout_data, hover_data,
        drag_enabled, group_dialog, focused_group, dialog_group_name, dialog_group_color,
        dialog_group_select, deck_dialog_state, deck_dialog_select
    ):
        from dash import ctx
        import random

        cards = visible_cards(deck, focused_group)
        trigger = ctx.triggered_id
        reset_dialog = False
        next_group_dialog = group_dialog
        next_focused_group = focused_group
        next_deck_dialog = deck_dialog_state
        next_deck = deck

        if trigger == "reset-cards":
            reset_dialog = True
        elif trigger == "reset-confirm":
            state.reset_all_state()
            selected_id = None
            revealed = False
            drag_enabled = False
            next_focused_group = None
        elif trigger == "add-deck":
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
            direction = 1 if keyboard_nav == "next" else -1
            adjacent = cards_service.adjacent_card(cards, selected_id, direction)
            selected_id = adjacent.id if adjacent else None
            revealed = False
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
            next_group_dialog = None
        elif trigger == "group-dialog-submit" and group_dialog == "focus" and dialog_group_select:
            next_focused_group = dialog_group_select
            next_group_dialog = None
        elif trigger == "delete-group" and selected_id:
            next_group_dialog = "delete"
        elif trigger == "deck-filter":
            if selected_id not in {card.id for card in cards}:
                selected_id = None
            revealed = False

        cards = visible_cards(next_deck, next_focused_group)
        if next_focused_group:
            focused_group = next((group for group in state.groups if group.id == next_focused_group), None)
            focused_ids = set(focused_group.card_ids) if focused_group else set()
            cards = [card for card in cards if card.id in focused_ids]
        if selected_id not in {card.id for card in cards}:
            selected_id = None
            revealed = False

        selected_card = state.card_by_id.get(selected_id)
        state.save()
        return (
            make_figure(cards, selected_id, (relayout_data or {}).get("scene.camera"), state, next_focused_group),
            card_panel(selected_card, revealed),
            difficulty_control(selected_card, state),
            position_control(selected_card, bool(drag_enabled), state),
            group_control(selected_card, next_group_dialog, state),
            connection_control(selected_card, next_deck or "all", next_focused_group or focused_group, state),
            "Saved" if trigger in {"save-position", "create-link", "disconnect-link", "group-dialog-submit", "delete-group"} else "",
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
        )

    return update_card
