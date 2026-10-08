from flashcards_app import runtime
from flashcards_app.models import CardGroup


def create_group(selected_id: str, name: str, color: str) -> None:
    group_id = f"group-{len(runtime.GROUPS) + 1}"
    runtime.GROUPS.append(CardGroup(group_id, name.strip(), color, [selected_id]))


def add_to_group(selected_id: str, group_id: str) -> None:
    group = next((item for item in runtime.GROUPS if item.id == group_id), None)
    if group and selected_id not in group.card_ids:
        group.card_ids.append(selected_id)


def remove_from_group(selected_id: str, group_id: str) -> None:
    group = next((item for item in runtime.GROUPS if item.id == group_id), None)
    if group:
        group.card_ids = [card_id for card_id in group.card_ids if card_id != selected_id]


def delete_group(group_id: str) -> None:
    runtime.GROUPS[:] = [group for group in runtime.GROUPS if group.id != group_id]
    runtime.LINKS[:] = [link for link in runtime.LINKS if link.group_id != group_id]
