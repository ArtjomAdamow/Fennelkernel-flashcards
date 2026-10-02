from flashcards_app import runtime
from flashcards_app.models import CardProgress, Flashcard


def choose_random_card(cards: list[Flashcard], progress: dict, rng) -> Flashcard | None:
    if not cards:
        return None

    read_cards = [card for card in cards if progress.get(card.id) and progress[card.id].read]
    candidates = read_cards or cards
    weights = [101 - progress.get(card.id, CardProgress(card.id)).difficulty for card in candidates]
    return rng.choices(candidates, weights=weights, k=1)[0]


def adjacent_card(cards: list[Flashcard], selected_id: str | None, direction: int) -> Flashcard | None:
    if not cards:
        return None
    if selected_id not in {card.id for card in cards}:
        return cards[0 if direction > 0 else -1]
    index = next(index for index, card in enumerate(cards) if card.id == selected_id)
    return cards[(index + direction) % len(cards)]


def select_from_click(click_data: dict, hover_data: dict | None) -> str | None:
    hovered_points = (hover_data or {}).get("points", [])
    hovered_id = hovered_points[0].get("customdata") if hovered_points else None
    return hovered_id or click_data["points"][0].get("customdata")


def toggle_reveal(selected_id: str, revealed: bool) -> bool:
    revealed = not revealed
    if revealed and selected_id in runtime.PROGRESS:
        runtime.PROGRESS[selected_id].read = True
    return revealed


def pick_random(cards: list[Flashcard], rng) -> str | None:
    selected = choose_random_card(cards, runtime.PROGRESS, rng)
    return selected.id if selected else None


def pick_adjacent(cards: list[Flashcard], selected_id: str | None, direction: int) -> str | None:
    selected = adjacent_card(cards, selected_id, direction)
    return selected.id if selected else None
