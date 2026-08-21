import re
from pathlib import Path

from .models import Flashcard

_DETAILS_PATTERN = re.compile(r"<details>(?P<body>.*?)</details>", re.IGNORECASE | re.DOTALL)
_SUMMARY_PATTERN = re.compile(r"<summary>(?P<body>.*?)</summary>", re.IGNORECASE | re.DOTALL)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_PLACEHOLDER_PATTERN = re.compile(r"^\s*\[.*?\]\s*:\s*$", re.DOTALL)
_CODELIKE_PATTERN = re.compile(
    r"(?<![`\w])(?:[A-Za-z_][A-Za-z0-9_]*\(\)|[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+)(?![`\w])"
)


def format_technical_terms(value: str) -> str:
    """Wrap unmistakable code-like terms without touching existing Markdown code."""
    parts = re.split(r"(`[^`]*`)", value)
    for index in range(0, len(parts), 2):
        parts[index] = _CODELIKE_PATTERN.sub(r"`\g<0>`", parts[index])
    return "".join(parts)


def _clean_question(value: str) -> str:
    value = re.sub(r"<sd\b", "", value, flags=re.IGNORECASE)
    value = _TAG_PATTERN.sub(" ", value)
    value = re.sub(r"\s+", " ", value)
    return format_technical_terms(value.strip(" \t\r\n"))


def _clean_answer(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    return format_technical_terms(value.strip(" \t\r\n"))


def parse_deck(path: Path) -> list[Flashcard]:
    text = path.read_text(encoding="utf-8")
    cards: list[Flashcard] = []

    for index, match in enumerate(_DETAILS_PATTERN.finditer(text), start=1):
        body = match.group("body")
        summary_match = _SUMMARY_PATTERN.search(body)
        if summary_match is None:
            continue

        question = _clean_question(summary_match.group("body"))
        answer = _clean_answer(body[summary_match.end() :])
        if not question or _PLACEHOLDER_PATTERN.match(question):
            continue

        cards.append(
            Flashcard(
                id=f"{path.stem}:{index}",
                deck=path.stem,
                question=question,
                answer=answer,
            )
        )

    return cards


def load_decks(folder: Path) -> list[Flashcard]:
    cards: list[Flashcard] = []
    for path in sorted(folder.glob("*.md")):
        cards.extend(parse_deck(path))
    return cards
