from flashcards_app import runtime


def create_link(selected_id: str, target_id: str) -> None:
    runtime.USER_STATE.create_link(selected_id, target_id)


def disconnect_link(selected_id: str, target_id: str) -> None:
    runtime.USER_STATE.disconnect_link(selected_id, target_id)
