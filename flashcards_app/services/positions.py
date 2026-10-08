from flashcards_app import runtime


def set_position(card_id: str, x: float, y: float, z: float) -> None:
    runtime.USER_STATE.set_position(card_id, x, y, z)
