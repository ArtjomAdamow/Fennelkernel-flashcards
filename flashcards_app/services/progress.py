from flashcards_app import runtime


def set_difficulty(selected_id: str, difficulty: int) -> None:
    runtime.USER_STATE.set_difficulty(selected_id, difficulty)
