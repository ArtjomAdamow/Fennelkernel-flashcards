"""Tests of the draft loader and its launcher. Run from the repository root:
    .venv/Scripts/python.exe -m pytest modules/loader/test_loader_draft.py -p no:cacheprovider
"""

import difflib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from .deck_catalog import DeckCatalog, JsonDeckCatalog
from .models import Flashcard
from .parser import CardsFile, comb_id, format_markdown_terms, format_technical_terms, load_decks

DRAFT_DIR = Path(__file__).resolve().parent
ROOT = DRAFT_DIR.parents[1]
CARDS_FILE = ROOT / "data" / "cards.json"


def write_course(tmp_path: Path, decks: list, version=2) -> Path:
    path = tmp_path / "cards.json"
    path.write_text(json.dumps({"courseName": "c", "version": version, "decks": decks}), encoding="utf-8")
    return path


def deck(deck_id: str, name: str, *cards: dict) -> dict:
    return {"id": deck_id, "name": name, "cards": list(cards)}


def card(card_id: str, **extra) -> dict:
    return {"card_id": card_id, "question": f"Q {card_id}", "feedback": f"A {card_id}", **extra}


@pytest.fixture(scope="module")
def course():
    return CardsFile(CARDS_FILE)


# --- real course file -------------------------------------------------------

def test_course_file_loads_every_card_into_its_stack(course):
    cards = course.load_decks()
    assert len(cards) == 1670
    assert Counter(card.stack for card in cards) == {1: 1092, 2: 56, 3: 522}
    assert len({card.id for card in cards}) == len(cards)
    assert all(card.question and card.answer for card in cards)


def test_comb_id_is_stack_deck_id_card_id(course):
    cards = {card.id: card for card in course.load_decks(["Git & Version Control Workflows"])}
    graded = cards["302032"]
    assert (graded.question, graded.stack, graded.difficulty) == ("What is Git, fundamentally?", 3, "easy")
    assert graded.weblink == "https://en.wikipedia.org/wiki/Git"
    assert cards["202044"].stack == 2 and cards["202044"].difficulty is None
    assert cards["102001"].stack == 1


def test_markdown_survives_parsing(course):
    cards = {card.id: card for card in course.load_decks()}
    # fenced code keeps its lines and gets no backticks inside
    assert "```\nmy_string = 'DS-Bootcamp'\nmy_string[3:7]\n```" in cards["201002"].question
    # <placeholders> are kept, not stripped as HTML tags
    assert cards["102013"].question == "What does git switch -c <branch> do, and what is its older equivalent?"
    # bullet lists keep their line breaks
    assert cards["103001"].answer.count("\n- ") == 3


# --- JSON parser ------------------------------------------------------------

def test_stack_is_decided_by_keys(tmp_path):
    path = write_course(tmp_path, [
        deck("07", "d", card("001"), card("002", quiz=True), card("003", quiz=True, difficulty="hard")),
    ])
    assert [(c.id, c.stack, c.difficulty) for c in CardsFile(path).load_decks()] == [
        ("107001", 1, None), ("207002", 2, None), ("307003", 3, "hard"),
    ]


def test_decks_are_filtered_and_ordered_by_name(tmp_path):
    cards_file = CardsFile(write_course(tmp_path, [deck("01", "beta", card("001")), deck("02", "alpha", card("001"))]))
    assert cards_file.deck_names == ("alpha", "beta")
    assert [c.deck for c in cards_file.load_decks()] == ["alpha", "beta"]
    assert [c.id for c in cards_file.load_decks(["beta"])] == ["101001"]
    assert cards_file.load_decks([]) == []


def test_load_decks_returns_a_new_list(tmp_path):
    cards_file = CardsFile(write_course(tmp_path, [deck("01", "d", card("001"))]))
    cards_file.load_decks().clear()
    assert len(cards_file.load_decks()) == 1


def test_course_file_is_read_once(tmp_path):
    path = write_course(tmp_path, [deck("01", "alpha", card("001"))])
    cards_file = CardsFile(path)
    write_course(tmp_path, [deck("01", "alpha", card("001")), deck("02", "beta", card("001"))])
    assert cards_file.deck_names == ("alpha",)
    assert [c.id for c in cards_file.load_decks()] == ["101001"]
    path.unlink()
    assert len(cards_file.load_decks(["alpha"])) == 1


def test_missing_file_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        CardsFile(tmp_path / "missing.json")


def test_empty_question_is_skipped(tmp_path):
    path = write_course(tmp_path, [deck("01", "d", {"card_id": "001", "question": "  ", "feedback": "A"})])
    assert CardsFile(path).load_decks() == []


@pytest.mark.parametrize("version", [None, 1, 3, "2"])
def test_other_versions_are_refused(tmp_path, version):
    path = write_course(tmp_path, [deck("01", "d", card("001"))], version=version)
    with pytest.raises(ValueError, match="unsupported version"):
        CardsFile(path)


def test_quiz_other_than_true_is_refused(tmp_path):
    path = write_course(tmp_path, [deck("01", "d", card("001", quiz=False))])
    with pytest.raises(ValueError, match="'quiz' must be true"):
        CardsFile(path)


def test_missing_text_is_refused(tmp_path):
    path = write_course(tmp_path, [deck("01", "d", {"card_id": "001", "question": "Q"})])
    with pytest.raises(ValueError, match="'feedback' must be a string"):
        CardsFile(path)


def test_duplicate_deck_names_are_refused(tmp_path):
    path = write_course(tmp_path, [deck("01", "d"), deck("02", "d")])
    with pytest.raises(ValueError, match="duplicate deck name"):
        CardsFile(path)


def test_comb_id_clash_is_refused(tmp_path):
    # 1 + "1" + "1001" and 1 + "11" + "001" both give "111001"
    assert comb_id(1, "1", "1001") == comb_id(1, "11", "001") == "111001"
    path = write_course(tmp_path, [deck("1", "a", card("1001")), deck("11", "b", card("001"))])
    with pytest.raises(ValueError, match="duplicate comb_id"):
        CardsFile(path)


def test_markdown_term_formatting_preserves_existing_code():
    # same expectation as tests/test_parser.py for format_technical_terms
    assert format_markdown_terms("Use snake_case and already `safe_name`.") == "Use `snake_case` and already `safe_name`."


def test_markdown_term_formatting_skips_fences_math_and_placeholders():
    value = "Call my_func() on <branch_name>:\n```\nx_val = 1\n```\n$feature_{1}$ and $a_b$"
    assert format_markdown_terms(value) == (
        "Call `my_func()` on <branch_name>:\n```\nx_val = 1\n```\n$feature_{1}$ and $a_b$"
    )


# --- .md decks (kept from the project) --------------------------------------

def test_md_decks_still_parse():
    # same expectations as tests/test_parser.py
    cards = load_decks(ROOT / "data" / "cards")
    assert len(cards) >= 20
    assert any(card.question.startswith("What is a Heuristic?") for card in cards)
    assert all(card.answer and re.fullmatch(r".+:\d+", card.id) for card in cards)
    assert format_technical_terms("Use snake_case and already `safe_name`.") == "Use `snake_case` and already `safe_name`."


def test_md_catalog_keeps_its_live_update(tmp_path):
    (tmp_path / "alpha.md").write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    catalog = DeckCatalog(tmp_path, exclude={"readme"})
    assert catalog.available() == ["alpha"]
    (tmp_path / "beta.md").write_text("", encoding="utf-8")
    assert catalog.available() == ["alpha", "beta"] and catalog.is_available("beta")


# --- JSON catalog -----------------------------------------------------------

def test_json_catalog_lists_names_without_excluded(tmp_path):
    path = write_course(tmp_path, [deck("01", "beta"), deck("02", "alpha"), deck("03", "None"), deck("04", "README")])
    catalog = JsonDeckCatalog(CardsFile(path), exclude={"readme", "none"})
    assert catalog.available() == ["alpha", "beta"]
    assert catalog.is_available("alpha") and not catalog.is_available("None")
    catalog.available().clear()
    assert catalog.available() == ["alpha", "beta"]


def test_json_catalog_matches_course_file(course):
    names = JsonDeckCatalog(course).available()
    assert len(names) == 48 and names == sorted({card.deck for card in course.load_decks()})


# --- model ------------------------------------------------------------------

def test_flashcard_keeps_the_positional_constructor_and_id():
    # the app and its tests build cards as Flashcard(id, deck, question, answer)
    card = Flashcard("x:1", "x", "Q", "A")
    assert (card.id, card.comb_id, card.stack, card.difficulty, card.explain, card.weblink) == ("x:1", "x:1", 1, None, None, None)


# --- changes/ and the launcher ----------------------------------------------

_DECK_RELATED = re.compile(r"deck|Deck|CARDS|cards_file|card_source|load_decks|CardsFile|catalog")


@pytest.mark.parametrize("project_file, changed_file", [
    ("app.py", "changes/app.py"),
    ("flashcards_app/user_state_service.py", "changes/user_state_service.py"),
])
def test_changes_differ_from_the_project_only_in_deck_lines(project_file, changed_file):
    # Guards against a stale copy: if the project file moves on, the copy has to be redone
    original = (ROOT / project_file).read_text(encoding="utf-8").splitlines()
    changed = (DRAFT_DIR / changed_file).read_text(encoding="utf-8").splitlines()
    differing = [
        line[1:] for line in difflib.unified_diff(original, changed, lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]
    assert differing and all(_DECK_RELATED.search(line) for line in differing), differing


# Runs in a fresh interpreter: records every file the launched app opens or lists
_LAUNCH_PROBE = """
import json, os, sys

events = []

def audit(event, args):
    if event in ("open", "os.scandir", "os.listdir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
        events.append((event, os.path.normcase(os.path.abspath(os.fsdecode(args[0])))))

sys.addaudithook(audit)
sys.path.insert(0, sys.argv[1])
import deck_v2_launcher as launcher

app = launcher.load_app()
state = app.composition.user_state
loaded = {"cards": len(state.cards), "enabled": len(state.enabled_decks), "available": len(state.available_decks())}
deck = state.available_decks()[0]
toggled = [state.disable_deck(deck), state.enable_deck(deck)]
state.save()
launcher.load_app()
modules = {name: sys.modules[name].__file__ for name in [*launcher.REROUTES, "app"]}
print(json.dumps({"events": events, "loaded": loaded, "toggled": toggled, "modules": modules, "base_dir": str(app.BASE_DIR)}))
"""


@pytest.fixture(scope="module")
def launch():
    result = subprocess.run(
        [sys.executable, "-c", _LAUNCH_PROBE, str(DRAFT_DIR)],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def _norm(path: Path) -> str:
    return os.path.normcase(str(path))


def test_launcher_reads_the_course_file_once(launch):
    opened = [path for event, path in launch["events"] if event == "open"]
    assert opened.count(_norm(CARDS_FILE)) == 1


def test_launcher_leaves_md_decks_and_state_file_alone(launch):
    cards_dir = _norm(ROOT / "data" / "cards")
    touched = [path for _, path in launch["events"]]
    assert not [path for path in touched if path.endswith(".md") or path == cards_dir or path.startswith(cards_dir + os.sep)]
    assert not [path for path in touched if "positions" in path]


def test_launcher_runs_the_app_on_the_draft(launch):
    assert launch["loaded"] == {"cards": 1670, "enabled": 48, "available": 48}
    assert launch["toggled"] == [True, True]
    assert Path(launch["base_dir"]) == ROOT
    assert {name: Path(file) for name, file in launch["modules"].items()} == {
        "flashcards_app.models": DRAFT_DIR / "models.py",
        "flashcards_app.parser": DRAFT_DIR / "parser.py",
        "flashcards_app.deck_catalog": DRAFT_DIR / "deck_catalog.py",
        "flashcards_app.user_state_service": DRAFT_DIR / "changes" / "user_state_service.py",
        # what app.py itself sees; the code is compiled from changes/app.py
        "app": ROOT / "app.py",
    }
