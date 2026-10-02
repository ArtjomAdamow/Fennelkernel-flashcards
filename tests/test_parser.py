from flashcards_app.parser import format_technical_terms, load_decks


def test_populated_decks_are_parsed(repo_root):
    cards = load_decks(repo_root / "data" / "cards")
    assert len(cards) >= 20
    assert any(card.question.startswith("What is a Heuristic?") for card in cards)
    assert all(card.answer for card in cards)


def test_technical_term_formatting_preserves_existing_code():
    formatted = format_technical_terms("Use snake_case and already `safe_name`.")

    assert formatted == "Use `snake_case` and already `safe_name`."
