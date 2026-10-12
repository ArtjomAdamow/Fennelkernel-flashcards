"""Loads the app for a scenario script, in the project the script runs in (the current working directory).

Two kinds of project exist in the tests:
  * legacy:  the original code (flashcards_app.runtime with module-level state, services/*.py, original callbacks/server);
  * current: the code as it is built since tranche 8: app.py composes everything (app.composition).
Both offer the same small interface, so one scenario script can drive both and the results can be compared.
The scenarios import this file by name (`from world import load_world`); it sits next to them in tests/.
"""

from pathlib import Path


def load_world():
    return CurrentWorld() if (Path.cwd() / "app.py").exists() else LegacyWorld()


class LegacyWorld:
    current = False
    user_state = None
    catalog = None

    def __init__(self):
        from flashcards_app import runtime
        from flashcards_app.services import cards, connections, decks, groups, positions, progress

        self._rt = runtime
        self._cards_service, self._connections, self._decks = cards, connections, decks
        self._groups, self._positions, self._progress = groups, positions, progress
        self.base_dir, self.state_path = runtime.BASE_DIR, runtime.STATE_PATH
        self.cards_dir, self.none_deck, self.boot_id = runtime.CARDS_DIR, runtime.NONE_DECK, runtime.SERVER_BOOT_ID

    # live containers
    cards = property(lambda self: self._rt.CARDS)
    positions = property(lambda self: self._rt.POSITIONS)
    progress = property(lambda self: self._rt.PROGRESS)
    groups = property(lambda self: self._rt.GROUPS)
    links = property(lambda self: self._rt.LINKS)
    enabled_decks = property(lambda self: self._rt.ENABLED_DECKS)
    card_by_id = property(lambda self: self._rt.CARD_BY_ID)
    position_by_id = property(lambda self: self._rt.POSITION_BY_ID)

    def available_decks(self):
        return self._rt.available_decks()

    def visible_cards(self, deck, group):
        return self._rt.visible_cards(deck, group)

    # what the old services did
    def set_position(self, card_id, x, y, z):
        self._positions.set_position(card_id, x, y, z)

    def set_difficulty(self, card_id, difficulty):
        self._progress.set_difficulty(card_id, difficulty)

    def reveal(self, card_id):
        self._cards_service.toggle_reveal(card_id, False)

    def create_group(self, card_id, name, color):
        self._groups.create_group(card_id, name, color)

    def add_to_group(self, card_id, group_id):
        self._groups.add_to_group(card_id, group_id)

    def remove_from_group(self, card_id, group_id):
        self._groups.remove_from_group(card_id, group_id)

    def delete_group(self, group_id):
        self._groups.delete_group(group_id)

    def create_link(self, source_id, target_id):
        self._connections.create_link(source_id, target_id)

    def disconnect_link(self, source_id, target_id):
        self._connections.disconnect_link(source_id, target_id)

    def add_enabled_deck(self, deck_name):
        self._decks.add_enabled_deck(deck_name)

    def remove_enabled_deck(self, deck_name):
        return self._decks.remove_enabled_deck(deck_name)

    def deck_filter_options(self):
        return self._decks.deck_filter_options()

    def state_kw(self):
        """Keyword arguments for the visualization functions: the originals take no state."""
        return {}

    def connection_control(self, card, deck, focused_group):
        from flashcards_app.visualization import panels

        return panels.connection_control(card, deck, focused_group)

    @property
    def dash_app(self):
        from flashcards_app import callbacks  # noqa: F401  (the original module registers the callback at import)
        from flashcards_app.server import app

        return app


class CurrentWorld:
    current = True

    def __init__(self):
        import app as application
        from flashcards_app import runtime

        self.composition = application.composition
        self.user_state = self.composition.user_state
        self.catalog = self.composition.catalog
        self.base_dir, self.state_path, self.cards_dir = application.BASE_DIR, application.STATE_PATH, application.CARDS_DIR
        self.none_deck, self.boot_id = runtime.NONE_DECK, application.SERVER_BOOT_ID

    cards = property(lambda self: self.user_state.cards)
    positions = property(lambda self: self.user_state.positions)
    progress = property(lambda self: self.user_state.progress)
    groups = property(lambda self: self.user_state.groups)
    links = property(lambda self: self.user_state.links)
    enabled_decks = property(lambda self: self.user_state.enabled_decks)
    card_by_id = property(lambda self: self.user_state.card_by_id)
    position_by_id = property(lambda self: self.user_state.position_by_id)

    def available_decks(self):
        return self.user_state.available_decks()

    def visible_cards(self, deck, group):
        if deck in {None, self.none_deck}:  # UI sentinels: the state only knows "one deck" or "any deck"
            return []
        return self.user_state.visible_cards(None if deck == "all" else deck, group)

    def set_position(self, card_id, x, y, z):
        self.user_state.set_position(card_id, x, y, z)

    def set_difficulty(self, card_id, difficulty):
        self.user_state.set_difficulty(card_id, difficulty)

    def reveal(self, card_id):
        self.user_state.mark_read(card_id)

    def create_group(self, card_id, name, color):
        self.user_state.create_group(card_id, name, color)

    def add_to_group(self, card_id, group_id):
        self.user_state.add_to_group(card_id, group_id)

    def remove_from_group(self, card_id, group_id):
        self.user_state.remove_from_group(card_id, group_id)

    def delete_group(self, group_id):
        self.user_state.delete_group(group_id)

    def create_link(self, source_id, target_id):
        self.user_state.create_link(source_id, target_id)

    def disconnect_link(self, source_id, target_id):
        self.user_state.disconnect_link(source_id, target_id)

    def add_enabled_deck(self, deck_name):
        self.user_state.enable_deck(deck_name)

    def remove_enabled_deck(self, deck_name):
        return self.user_state.disable_deck(deck_name)

    def deck_filter_options(self):
        from flashcards_app.visualization.panels import deck_filter_options

        return deck_filter_options(self.user_state)

    def state_kw(self):
        return {"state": self.user_state}

    def connection_control(self, card, deck, focused_group):
        from flashcards_app.visualization import panels

        return panels.connection_control(card, self.visible_cards(deck, focused_group))

    @property
    def dash_app(self):
        return self.composition.dash_app
