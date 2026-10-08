from flashcards_app import runtime


def set_position(card_id: str, x: float, y: float, z: float) -> None:
    position = runtime.POSITION_BY_ID[card_id]
    position.x = float(x)
    position.y = float(y)
    position.z = float(z)
