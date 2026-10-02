from flashcards_app import runtime


def set_difficulty(selected_id: str, difficulty: int) -> None:
    runtime.PROGRESS[selected_id].difficulty = difficulty
