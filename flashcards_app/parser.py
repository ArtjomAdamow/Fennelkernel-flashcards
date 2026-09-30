import re
from pathlib import Path
from typing import List, Optional

from .models import Flashcard


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
        cards.append(
            Flashcard(
                id=f"{path.stem}:{index}",
                deck=path.stem,
                question=question,
                answer=answer,
            )
        )

    return cards

def load_decks(folder: Path, deck_names: Optional[List[str]] = None) -> List[Flashcard]:
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
