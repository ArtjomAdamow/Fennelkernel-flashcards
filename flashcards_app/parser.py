import re
from pathlib import Path

from .models import Flashcard

_DETAILS_PATTERN = re.compile(r"<details>(?P<body>.*?)</details>", re.IGNORECASE | re.DOTALL)
_SUMMARY_PATTERN = re.compile(r"<summary>(?P<body>.*?)</summary>", re.IGNORECASE | re.DOTALL)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_PLACEHOLDER_PATTERN = re.compile(r"^\s*\[.*?\]\s*:\s*$", re.DOTALL)


def _clean_question(value: str) -> str:
    value = re.sub(r"<sd\b", "", value, flags=re.IGNORECASE)
    value = _TAG_PATTERN.sub(" ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n")


def _clean_answer(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t\r\n")


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
