from flashcards_app.callbacks_impl import register_callbacks
from flashcards_app.runtime import NONE_DECK, USER_STATE
from flashcards_app.server import app

register_callbacks(app, USER_STATE, NONE_DECK)
