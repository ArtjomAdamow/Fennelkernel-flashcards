import pytest

from flashcards_app import parser
from flashcards_app.parser import CardsFile, MarkdownSourceDisabled, format_technical_terms, load_decks


def test_course_file_is_parsed(repo_root):
    # phase 2: the decks come from data/cards.json
    cards_file = CardsFile(repo_root / "data" / "cards.json")
    cards = cards_file.load_decks()
    assert len(cards) >= 20 and len(cards_file.deck_names) >= 2
    assert all(card.question and card.answer for card in cards)
    assert all(cards_file.card(card.id) is card for card in cards)


def test_md_source_is_switched_off(repo_root):
    with pytest.raises(MarkdownSourceDisabled, match="will be used for other content"):
        load_decks(repo_root / "data" / "cards")


def test_populated_decks_are_parsed(repo_root, monkeypatch):
    # the .md parser is kept: switched on, it works as before
    monkeypatch.setattr(parser, "MD_SOURCE_ENABLED", True)
    cards = load_decks(repo_root / "data" / "cards")
    assert len(cards) >= 20
    assert any(card.question.startswith("What is a Heuristic?") for card in cards)
    assert all(card.answer for card in cards)


def test_technical_term_formatting_preserves_existing_code():
    formatted = format_technical_terms("Use snake_case and already `safe_name`.")

    assert formatted == "Use `snake_case` and already `safe_name`."
