"""Card parser of the cluster module (replaces project/content/parser.py): course files of version 3 only.

Changes against the main file:
  * read_decks accepts only the versions in SOURCE_VERSIONS (version 3, TOPICS_VERSION); read_course gives the
    version with the decks. SOURCE_VERSION stays 2, the main project's version, which this parser refuses: a
    version 2 file carries no "source" key, so its JS flashcards would land on stack 1 with other comb_ids.
  * Version 3 (written by scripts/topics.py, docs/draft/cluster/dataset.md section 9.6) adds a "topics" list per
    deck and a "topic" key per card. read_decks checks them (check_topics): unique topic ids, and every card's
    topic one of its deck's.
  * CardsFile keeps them: topics(deck_name) gives a deck's topics (Topic) in file order, topic_of(comb_id) a
    card's topic id; version is the file's version.
  * A fourth stack: the flashcards of the quiz file (scripts/input/flashcard_quiz.js) carry "source": "quizes"
    (combi_json_js.py marks them) and get stack 4 (STACK_SOURCE); stack 1 keeps the flashcards without a source
    (the ones of Q_and_A.json). A card with "quiz" and "source" together, or a "source" other than "quizes", is
    refused like a "quiz" that is not true. The comb_ids of the JS flashcards therefore differ from the main
    project's (4... instead of 1...).

Card parser. Two sources:

  * .md deck files, as in the project: parse_deck(path), load_decks(folder, deck_names).
    Every call reads the files again; with deck_catalog.DeckCatalog this is the live update of the .md decks.
    Switched off (phase 1): the code is kept, but every call raises MarkdownSourceDisabled while
    MD_SOURCE_ENABLED is False.
  * the JSON course file (data/cards.json): CardsFile reads and parses it once, on construction.
    No live update: the file is read again only by CardsFile.reload() (phase 2: the deck "Add" button).

Course file layout (version 3, the cluster module's data/topics.json; the main project's version 2 is refused):
    {"courseName": ..., "version": 3, "decks": [{"id": "02", "name": ..., "topics": [{"topic_id": "01", "name": ..., ...}, ...],
                                                 "cards": [{"card_id": "032", "topic": "01", ...}, ...]}, ...]}
    The rest topic, for the cards that fit no other, carries "rest": true.

Every card belongs to one of four stacks, decided by the keys it carries:
    stack 1: neither "quiz" nor "source"   plain question / answer card (the lecture notebooks' Q_and_A.json)
    stack 2: "quiz" without "difficulty"   quiz question without an authored difficulty
    stack 3: "difficulty"                  quiz question with an authored difficulty (the quizzes of the JS file)
    stack 4: "source": "quizes"            plain question / answer card of the JS quiz file

A card's global id is comb_id = stack + deck "id" + "card_id" (e.g. "3" + "02" + "032" -> "302032").
The local "id" and "card_id" are not kept on the card.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from project.models import Flashcard


# --- .md deck files (project/content/parser.py, unchanged but for one keyword and the guard) ----

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
        # (keyword comb_id, the model's renamed id field; the value is unchanged)
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

# The main project's course file format is version 2; version 3 adds the topics and the source key, and this
# parser reads version 3 only (a version 2 file would give the JS flashcards other comb_ids)
SOURCE_VERSION = 2
TOPICS_VERSION = 3
SOURCE_VERSIONS = (TOPICS_VERSION,)

STACK_PLAIN = 1
STACK_QUIZ = 2
STACK_DIFFICULTY = 3
STACK_SOURCE = 4
# The only value of a card's "source" key: a flashcard of the quiz file (combi_json_js.py marks them)
QUIZ_FILE_SOURCE = "quizes"

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
    """The stack by the keys a card carries, in the order difficulty, quiz, source (check_card_keys has refused a
    card with both "quiz" and "source")."""
    if "difficulty" in raw_card:
        return STACK_DIFFICULTY
    if "quiz" in raw_card:
        return STACK_QUIZ
    if "source" in raw_card:
        return STACK_SOURCE
    return STACK_PLAIN

def check_card_keys(raw: dict, where: str) -> None:
    """The keys that decide the stack: "quiz" must be true, "source" must be the quiz file's mark, and a card
    cannot carry both (a quiz of the JS file carries "quiz" and a difficulty, never "source")."""
    # "quiz" only marks the stack; anything but true would make that ambiguous
    if "quiz" in raw and raw["quiz"] is not True:
        raise ValueError(f"{where}: 'quiz' must be true when present, got {raw['quiz']!r}")
    if "source" in raw and raw["source"] != QUIZ_FILE_SOURCE:
        raise ValueError(f"{where}: 'source' must be {QUIZ_FILE_SOURCE!r} when present, got {raw['source']!r}")
    if "source" in raw and "quiz" in raw:
        raise ValueError(f"{where}: a card cannot carry both 'quiz' and 'source'")

def comb_id(stack: int, deck_id: str, card_id: str) -> str:
    return f"{stack}{deck_id}{card_id}"

@dataclass(frozen=True)
class Topic:
    """A topic of a deck (course file version 3): its id within the deck, its name, and whether it is the rest
    topic of the cards that fit no other."""
    topic_id: str
    name: str
    rest: bool = False

def check_topics(deck: dict, where: str) -> None:
    """A version 3 deck: a "topics" list with unique ids, and every card's "topic" one of them. A topic without
    cards is allowed."""
    topics = deck.get("topics")
    if not isinstance(topics, list):
        raise ValueError(f"{where}: expected a 'topics' list in a version {TOPICS_VERSION} course")
    ids = set()
    for position, topic in enumerate(topics, start=1):
        topic_where = f"{where} topic #{position}"
        if not isinstance(topic, dict):
            raise ValueError(f"{topic_where}: expected an object")
        topic_id = _text(topic, "topic_id", topic_where)
        _text(topic, "name", topic_where)
        if not isinstance(topic.get("rest", False), bool):
            raise ValueError(f"{topic_where}: 'rest' must be true or false, got {topic['rest']!r}")
        if topic_id in ids:
            raise ValueError(f"{topic_where}: duplicate topic_id {topic_id!r}")
        ids.add(topic_id)
    for card in deck["cards"]:
        if not isinstance(card, dict):
            raise ValueError(f"{where}: expected every card to be an object")
        if card.get("topic") not in ids:
            raise ValueError(f"{where} card {card.get('card_id')!r}: topic {card.get('topic')!r} is not one of the deck's topics")

def parse_topics(raw_deck: dict) -> Tuple[Topic, ...]:
    """The topics of a checked version 3 deck, in file order."""
    return tuple(Topic(topic["topic_id"], topic["name"], topic.get("rest", False)) for topic in raw_deck["topics"])

def read_course(path: Path) -> Tuple[int, List[dict]]:
    """The version and the raw "decks" of the course file, with the deck level (and in version 3 the topics)
    checked."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    # Refuse other formats instead of guessing at their layout
    version = data.get("version")
    if version not in SOURCE_VERSIONS:
        raise ValueError(f"{path}: unsupported version {version!r}, expected one of {SOURCE_VERSIONS}")
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
        if version == TOPICS_VERSION:
            check_topics(deck, where)
    return version, decks

def read_decks(path: Path) -> List[dict]:
    """The raw "decks" of the course file, with the deck level checked."""
    return read_course(path)[1]

def parse_json_deck(raw_deck: dict) -> List[Flashcard]:
    deck_id, deck_name = raw_deck["id"], raw_deck["name"]
    cards: List[Flashcard] = []

    for raw in raw_deck["cards"]:
        where = f"deck {deck_id} card {raw.get('card_id')!r}"
        check_card_keys(raw, where)
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
    """The course file, read and parsed once on construction. It is read again only by reload()
    (phase 2: when the deck "Add" button is clicked); nothing is ever written."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.version, self.deck_names, self._cards, self._by_id, self._topics, self._card_topics = self._read()

    def _read(self) -> tuple:
        # Decks in name order, as the sorted *.md files were; cards in file order
        version, decks = read_course(self.path)
        raw_decks = sorted(decks, key=lambda deck: deck["name"])
        deck_names = tuple(deck["name"] for deck in raw_decks)

        cards: List[Flashcard] = []
        seen = {}
        topics: Dict[str, Tuple[Topic, ...]] = {}
        card_topics: Dict[str, str] = {}
        for raw_deck in raw_decks:
            for card in parse_json_deck(raw_deck):
                # comb_id is a plain concatenation, unique only while the widths stay 1 + 2 + 3.
                # Checked over all decks, so a clash shows at startup, not when a deck is enabled later.
                if card.comb_id in seen:
                    raise ValueError(f"duplicate comb_id {card.comb_id!r} in decks {seen[card.comb_id]!r} and {card.deck!r}")
                seen[card.comb_id] = card.deck
                cards.append(card)
            if version == TOPICS_VERSION:
                topics[raw_deck["name"]] = parse_topics(raw_deck)
                for raw in raw_deck["cards"]:
                    card_topics[comb_id(card_stack(raw), raw_deck["id"], raw["card_id"])] = raw["topic"]
        # phase 1: every card of the course by comb_id, enabled or not, for card()
        by_id = {card.comb_id: card for card in cards}
        # A card skipped for its empty question has no topic either
        return version, deck_names, cards, by_id, topics, {k: v for k, v in card_topics.items() if k in by_id}

    def reload(self) -> bool:
        """phase 2: read the file again. If it is missing or invalid now, the current course is kept and the
        result is False: a file being edited must not stop the running app."""
        try:
            self.version, self.deck_names, self._cards, self._by_id, self._topics, self._card_topics = self._read()
        except (OSError, ValueError):
            return False
        return True

    def topics(self, deck_name: str) -> Tuple[Topic, ...]:
        """The deck's topics in file order; none for an unknown deck."""
        return self._topics.get(deck_name, ())

    def topic_of(self, comb_id: str) -> Optional[str]:
        """The topic id of the card with this comb_id; None for an unknown card."""
        return self._card_topics.get(comb_id)

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
