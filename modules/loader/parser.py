"""Card parser (draft replacement for flashcards_app/parser.py). Two sources:

  * .md deck files, as in the project: parse_deck(path), load_decks(folder, deck_names).
    Every call reads the files again; with deck_catalog.DeckCatalog this is the live update of the .md decks.
    Switched off (phase 1): the code is kept, but every call raises MarkdownSourceDisabled while
    MD_SOURCE_ENABLED is False.
  * the JSON course file (data/cards.json): CardsFile reads and parses it once, on construction.
    No live update: changes to the file show up only after a restart.

Course file layout:
    {"courseName": ..., "version": 2, "decks": [{"id": "02", "name": ..., "cards": [{"card_id": "032", ...}, ...]}, ...]}

Every card belongs to one of three stacks, decided by the keys it carries:
    stack 1: no "quiz"                   plain question / answer card
    stack 2: "quiz" without "difficulty" quiz question
    stack 3: "difficulty"                quiz question with an authored difficulty

A card's global id is comb_id = stack + deck "id" + "card_id" (e.g. "3" + "02" + "032" -> "302032").
The local "id" and "card_id" are not kept on the card.
"""

import json
import re
from pathlib import Path
from typing import List, Optional

from .models import Flashcard


# --- .md deck files (flashcards_app/parser.py, unchanged but for one keyword and the guard) ----

# phase 1: the .md source is switched off; the code below the guard is kept, it will be used for other content
MD_SOURCE_ENABLED = False
MD_SOURCE_NOTICE = "Loading decks from .md files is disabled: it will be used for other content."


class MarkdownSourceDisabled(RuntimeError):
    """Raised on any use of the .md deck source while MD_SOURCE_ENABLED is False."""


def require_md_source() -> None:
    # Read at call time, so tests can switch the source on for one test
    if not MD_SOURCE_ENABLED:
        raise MarkdownSourceDisabled(MD_SOURCE_NOTICE)


# Regex patterns for parsing markdown deck files
# Matches <details> tags with DOTALL flag to span multiple lines
_DETAILS_PATTERN = re.compile(r"<details>(?P<body>.*?)</details>", re.IGNORECASE | re.DOTALL)
# Matches <summary> tags within the details body
_SUMMARY_PATTERN = re.compile(r"<summary>(?P<body>.*?)</summary>", re.IGNORECASE | re.DOTALL)
# Matches any HTML tags for stripping from content
_TAG_PATTERN = re.compile(r"<[^>]+>")
# Detects placeholder lines like "[...]: " that should be skipped
_PLACEHOLDER_PATTERN = re.compile(r"^\s*\[.*?\]\s*:\s*$", re.DOTALL)
# Detects code-like terms (snake_case, function calls) that need backtick wrapping
_CODELIKE_PATTERN = re.compile(
    r"(?<![`\w])(?:[A-Za-z_][A-Za-z0-9_]*\(\)|[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+)(?![`\w])"
)


def format_technical_terms(value: str) -> str:
    # Split on existing backtick-wrapped code to avoid modifying it
    parts = re.split(r"(`[^`]*`)", value)
    # Process only non-code parts (even indices)
    for index in range(0, len(parts), 2):
        parts[index] = _CODELIKE_PATTERN.sub(r"`\g<0>`", parts[index])
    return "".join(parts)

def _clean_question(value: str) -> str:
    # Remove leading <sd artifacts that appear in some markdown sources
    value = re.sub(r"<sd\b", "", value, flags=re.IGNORECASE)
    # Strip all HTML tags
    value = _TAG_PATTERN.sub(" ", value)
    # Normalize whitespace
    value = re.sub(r"\s+", " ", value)
    # Apply technical term formatting
    return format_technical_terms(value.strip(" \t\r\n"))

def _clean_answer(value: str) -> str:
    # Normalize whitespace
    value = re.sub(r"\s+", " ", value)
    # Apply technical term formatting
    return format_technical_terms(value.strip(" \t\r\n"))

def parse_deck(path: Path) -> List[Flashcard]:
    require_md_source()
    # Read the file content
    text = path.read_text(encoding="utf-8")
    cards: List[Flashcard] = []

    # Iterate through each <details> block in the file
    for index, match in enumerate(_DETAILS_PATTERN.finditer(text), start=1):
        body = match.group("body")
        # Extract the summary (question) from the details body
        summary_match = _SUMMARY_PATTERN.search(body)
        if summary_match is None:
            # Skip blocks without a summary tag
            continue

        # Clean and format question and answer
        question = _clean_question(summary_match.group("body"))
        answer = _clean_answer(body[summary_match.end():])
        
        # Skip cards with empty questions or placeholder content
        if not question or _PLACEHOLDER_PATTERN.match(question):
            continue

        # Create flashcard with unique ID based on deck name and sequence number
        # (draft: keyword comb_id, the model's renamed id field; the value is unchanged)
        cards.append(
            Flashcard(
                comb_id=f"{path.stem}:{index}",
                deck=path.stem,
                question=question,
                answer=answer,
            )
        )

    return cards

def load_decks(folder: Path, deck_names: Optional[List[str]] = None) -> List[Flashcard]:
    require_md_source()
    cards: List[Flashcard] = []
    # Get all markdown files in the folder, sorted alphabetically
    paths = sorted(folder.glob("*.md"))
    
    # Filter by deck names if specified
    if deck_names is not None:
        selected_decks = set(deck_names)
        paths = [path for path in paths if path.stem in selected_decks]
    
    # Parse each deck file and collect all flashcards
    for path in paths:
        cards.extend(parse_deck(path))
    
    return cards


# --- JSON course file -----------------------------------------------------------

# The only course file format this parser understands
SOURCE_VERSION = 2

STACK_PLAIN = 1
STACK_QUIZ = 2
STACK_DIFFICULTY = 3

# Spans the term formatting must not touch: fenced code, inline code, inline math and
# <placeholder> arguments such as "git push -u origin <branch_name>"
_PROTECTED_PATTERN = re.compile(r"(```.*?```|`[^`]*`|\$[^$\n]+\$|<[^<>\n]+>)", re.DOTALL)


def format_markdown_terms(value: str) -> str:
    # Like format_technical_terms, but the JSON texts also hold fenced code, math and <placeholders>
    parts = _PROTECTED_PATTERN.split(value)
    # Process only unprotected parts (even indices)
    for index in range(0, len(parts), 2):
        parts[index] = _CODELIKE_PATTERN.sub(r"`\g<0>`", parts[index])
    return "".join(parts)

def _clean_markdown(value: str) -> str:
    # The JSON texts already are Markdown (lists, fenced code, <placeholders>) and are shown with
    # dcc.Markdown: unlike the .md parser, no tag stripping and no whitespace collapsing
    value = value.replace("\r\n", "\n").strip()
    # Apply technical term formatting
    return format_markdown_terms(value)

def _text(raw: dict, key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{where}: '{key}' must be a string, got {value!r}")
    return value

def _optional_text(raw: dict, key: str, where: str) -> Optional[str]:
    return _text(raw, key, where) if key in raw else None

def card_stack(raw_card: dict) -> int:
    if "difficulty" in raw_card:
        return STACK_DIFFICULTY
    if "quiz" in raw_card:
        return STACK_QUIZ
    return STACK_PLAIN

def comb_id(stack: int, deck_id: str, card_id: str) -> str:
    return f"{stack}{deck_id}{card_id}"

def read_decks(path: Path) -> List[dict]:
    """The raw "decks" of the course file, with the deck level checked."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    # Refuse other formats instead of guessing at their layout
    if data.get("version") != SOURCE_VERSION:
        raise ValueError(f"{path}: unsupported version {data.get('version')!r}, expected {SOURCE_VERSION}")
    decks = data.get("decks")
    if not isinstance(decks, list):
        raise ValueError(f"{path}: expected an object with a 'decks' list")

    names = set()
    for position, deck in enumerate(decks, start=1):
        where = f"{path.name}: deck #{position}"
        if not isinstance(deck, dict) or not isinstance(deck.get("cards"), list):
            raise ValueError(f"{where}: expected an object with a 'cards' list")
        _text(deck, "id", where)
        name = _text(deck, "name", where)
        # Decks are enabled, persisted and filtered by name, so a name must be unique
        if name in names:
            raise ValueError(f"{where}: duplicate deck name {name!r}")
        names.add(name)
    return decks

def parse_json_deck(raw_deck: dict) -> List[Flashcard]:
    deck_id, deck_name = raw_deck["id"], raw_deck["name"]
    cards: List[Flashcard] = []

    for raw in raw_deck["cards"]:
        where = f"deck {deck_id} card {raw.get('card_id')!r}"
        # "quiz" only marks the stack; anything but true would make that ambiguous
        if "quiz" in raw and raw["quiz"] is not True:
            raise ValueError(f"{where}: 'quiz' must be true when present, got {raw['quiz']!r}")
        stack = card_stack(raw)
        question = _clean_markdown(_text(raw, "question", where))

        # Skip cards with an empty question, as the .md parser did
        if not question:
            continue

        explain = _optional_text(raw, "explain", where)
        weblink = _optional_text(raw, "weblink", where)
        cards.append(
            Flashcard(
                comb_id=comb_id(stack, deck_id, _text(raw, "card_id", where)),
                deck=deck_name,
                question=question,
                answer=_clean_markdown(_text(raw, "feedback", where)),
                stack=stack,
                difficulty=_optional_text(raw, "difficulty", where),
                explain=_clean_markdown(explain) if explain is not None else None,
                weblink=weblink.strip() if weblink is not None else None,
            )
        )

    return cards


class CardsFile:
    """The course file, read and parsed once on construction; the file is not touched again."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        # Decks in name order, as the sorted *.md files were; cards in file order
        raw_decks = sorted(read_decks(self.path), key=lambda deck: deck["name"])
        self.deck_names = tuple(deck["name"] for deck in raw_decks)

        self._cards: List[Flashcard] = []
        seen = {}
        for raw_deck in raw_decks:
            for card in parse_json_deck(raw_deck):
                # comb_id is a plain concatenation, unique only while the widths stay 1 + 2 + 3.
                # Checked over all decks, so a clash shows at startup, not when a deck is enabled later.
                if card.comb_id in seen:
                    raise ValueError(f"duplicate comb_id {card.comb_id!r} in decks {seen[card.comb_id]!r} and {card.deck!r}")
                seen[card.comb_id] = card.deck
                self._cards.append(card)
        # phase 1: every card of the course by comb_id, enabled or not, for card()
        self._by_id = {card.comb_id: card for card in self._cards}

    def card(self, comb_id: str) -> Optional[Flashcard]:
        """The card with this comb_id (name as card.deck, question, answer = feedback), whether its deck is
        enabled or not. None if the course has no such card."""
        return self._by_id.get(comb_id)

    def load_decks(self, deck_names: Optional[List[str]] = None) -> List[Flashcard]:
        """Same contract as load_decks(folder, deck_names), served from memory (a state_core.CardSource)."""
        if deck_names is None:
            return list(self._cards)
        # Filter by deck names
        selected_decks = set(deck_names)
        return [card for card in self._cards if card.deck in selected_decks]
