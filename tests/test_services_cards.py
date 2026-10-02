from flashcards_app.models import CardProgress, Flashcard
from flashcards_app.services.cards import choose_random_card


def test_random_card_prefers_read_cards_and_low_difficulty():
    cards = [Flashcard("new", "deck", "new", "answer"), Flashcard("review", "deck", "review", "answer")]
    progress = {
        "new": CardProgress("new", read=False, difficulty=1),
        "review": CardProgress("review", read=True, difficulty=80),
    }

    selected = choose_random_card(cards, progress, __import__("random"))

    assert selected == cards[1]
