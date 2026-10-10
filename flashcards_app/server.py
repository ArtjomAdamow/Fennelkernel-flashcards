from flashcards_app.runtime import BASE_DIR, GROUPS, LINKS, POSITIONS, PROGRESS, SERVER_BOOT_ID, STATE_PATH, USER_STATE
from flashcards_app.server_impl import create_app
from flashcards_app.state import save_state

app = create_app(BASE_DIR, SERVER_BOOT_ID, USER_STATE)


def main() -> None:
    save_state(STATE_PATH, POSITIONS, PROGRESS, GROUPS, LINKS)
    app.run(debug=True)
