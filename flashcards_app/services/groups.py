from flashcards_app import runtime


def create_group(selected_id: str, name: str, color: str) -> None:
    runtime.USER_STATE.create_group(selected_id, name, color)


def add_to_group(selected_id: str, group_id: str) -> None:
    runtime.USER_STATE.add_to_group(selected_id, group_id)


def remove_from_group(selected_id: str, group_id: str) -> None:
    runtime.USER_STATE.remove_from_group(selected_id, group_id)


def delete_group(group_id: str) -> None:
    runtime.USER_STATE.delete_group(group_id)
