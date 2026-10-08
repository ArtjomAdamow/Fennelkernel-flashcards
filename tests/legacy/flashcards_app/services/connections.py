from flashcards_app import runtime
from flashcards_app.models import CardLink


def create_link(selected_id: str, target_id: str) -> None:
    exists = any(
        (link.source_id == selected_id and link.target_id == target_id)
        or (link.source_id == target_id and link.target_id == selected_id)
        for link in runtime.LINKS
    )
    if not exists:
        runtime.LINKS.append(CardLink(selected_id, target_id))


def disconnect_link(selected_id: str, target_id: str) -> None:
    runtime.LINKS[:] = [
        link for link in runtime.LINKS
        if not (
            (link.source_id == selected_id and link.target_id == target_id)
            or (link.source_id == target_id and link.target_id == selected_id)
        )
    ]
