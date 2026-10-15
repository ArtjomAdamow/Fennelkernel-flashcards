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

from . import parser as parser_module
from .deck_catalog import DeckCatalog, JsonDeckCatalog
from .models import CardPosition, CardProgress, Flashcard
from .parser import (
    MD_SOURCE_NOTICE, CardsFile, MarkdownSourceDisabled, comb_id, format_markdown_terms, format_technical_terms,
    load_decks, parse_deck,
)

DRAFT_DIR = Path(__file__).resolve().parent
ROOT = DRAFT_DIR.parents[1]
CARDS_FILE = ROOT / "data" / "cards.json"
LAUNCHER_DIR = ROOT / "tools" / "loader"  # phase 1: the launcher lives outside the module


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

# --- .md decks (kept from the project, switched off in phase 1) -------------

@pytest.fixture
def md_source(monkeypatch):
    # The old behaviour stays covered: switch the .md source on for one test
    monkeypatch.setattr(parser_module, "MD_SOURCE_ENABLED", True)


def test_md_source_is_switched_off_with_the_notice(tmp_path):
    (tmp_path / "alpha.md").write_text("", encoding="utf-8")
    assert MD_SOURCE_NOTICE == "Loading decks from .md files is disabled: it will be used for other content."
    for call in (lambda: parse_deck(tmp_path / "alpha.md"), lambda: load_decks(tmp_path), lambda: DeckCatalog(tmp_path)):
        with pytest.raises(MarkdownSourceDisabled, match="will be used for other content"):
            call()


def test_md_catalog_built_while_switched_on_is_switched_off_later(tmp_path, monkeypatch):
    monkeypatch.setattr(parser_module, "MD_SOURCE_ENABLED", True)
    catalog = DeckCatalog(tmp_path)
    monkeypatch.setattr(parser_module, "MD_SOURCE_ENABLED", False)
    with pytest.raises(MarkdownSourceDisabled):
        catalog.available()


def test_md_decks_still_parse(md_source):
    # same expectations as tests/test_parser.py
    cards = load_decks(ROOT / "data" / "cards")
    assert len(cards) >= 20
    assert any(card.question.startswith("What is a Heuristic?") for card in cards)
    assert all(card.answer and re.fullmatch(r".+:\d+", card.id) for card in cards)
    assert format_technical_terms("Use snake_case and already `safe_name`.") == "Use `snake_case` and already `safe_name`."


def test_md_catalog_keeps_its_live_update(tmp_path, md_source):
    (tmp_path / "alpha.md").write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    catalog = DeckCatalog(tmp_path, exclude={"readme"})
    assert catalog.available() == ["alpha"]
    (tmp_path / "beta.md").write_text("", encoding="utf-8")
    assert catalog.available() == ["alpha", "beta"] and catalog.is_available("beta")


# --- card content by comb_id (phase 1) --------------------------------------

def test_every_card_is_readable_by_comb_id_enabled_or_not(tmp_path):
    cards_file = CardsFile(write_course(tmp_path, [deck("01", "alpha", card("001")), deck("02", "beta", card("001", quiz=True))]))
    assert cards_file.load_decks(["alpha"])[0].id == "101001"
    beta = cards_file.card("202001")  # deck beta is not loaded above
    assert (beta.deck, beta.question, beta.answer) == ("beta", "Q 001", "A 001")
    assert cards_file.card("999999") is None


def test_real_course_resolves_every_card(course):
    assert all(course.card(card.comb_id) is card for card in course.load_decks())


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


def test_state_models_are_keyed_by_comb_id():
    # asdict() writes the field names, so the state file keys follow the model (phase 1)
    from dataclasses import asdict
    assert list(asdict(CardPosition("101001", 0.0, 0.0, 0.0)))[0] == "comb_id"
    assert asdict(CardProgress("101001")) == {"comb_id": "101001", "read": False, "difficulty": 1}
    assert CardProgress("101001", difficulty=500).difficulty == 100


# --- changes/ against the project -------------------------------------------

# A changed spot of a copy must mention one of these (deck wiring, comb_id, the dropped positions.json fallback)
_ALLOWED_CHANGE = re.compile(r"deck|Deck|CARDS|cards_file|card_source|load_decks|CardsFile|catalog|comb_id|related_ids|LEGACY_STATE_PATH")


def _changed_spots(original: list, changed: list) -> list:
    """The differing lines, grouped by diff hunk (n=0: one hunk per changed spot)."""
    spots = []
    for line in difflib.unified_diff(original, changed, lineterm="", n=0):
        if line.startswith("@@"):
            spots.append([])
        elif line[:1] in "+-" and not line.startswith(("+++", "---")):
            spots[-1].append(line[1:])
    return spots


@pytest.mark.parametrize("project_file, changed_file", [
    ("app.py", "changes/app.py"),
    ("flashcards_app/user_state_service.py", "changes/user_state_service.py"),
    ("flashcards_app/state.py", "changes/state.py"),
    ("flashcards_app/state_core.py", "changes/state_core.py"),
    ("flashcards_app/geometry.py", "changes/geometry.py"),
    ("flashcards_app/visualization/map.py", "changes/map.py"),
])
def test_changes_differ_from_the_project_only_in_planned_spots(project_file, changed_file):
    # Guards against a stale copy: if the project file moves on elsewhere, the copy has to be redone
    original = (ROOT / project_file).read_text(encoding="utf-8").splitlines()
    changed = (DRAFT_DIR / changed_file).read_text(encoding="utf-8").splitlines()
    spots = _changed_spots(original, changed)
    assert spots and all(any(_ALLOWED_CHANGE.search(line) for line in spot) for spot in spots), spots
    # comb_id replaces card_id as the attribute of positions and progress
    assert not re.search(r"(position|point|item)\.card_id|\[\"card_id\"\]", "\n".join(changed))


# --- the launcher (tools/loader, phase 1: saves to a scratch state) ---------

# Runs in a fresh interpreter: records every file the launched app opens or lists.
# "edit" changes the state and saves it; "read" is the restart: it reports what came back, then saves again.
_LAUNCH_PROBE = """
import json, os, sys
from pathlib import Path

events = []

def audit(event, args):
    if event in ("open", "os.scandir", "os.listdir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
        events.append((event, os.path.normcase(os.path.abspath(os.fsdecode(args[0])))))

sys.addaudithook(audit)
sys.path.insert(0, sys.argv[1])
import deck_v2_launcher as launcher

mode, launcher.SCRATCH_STATE = sys.argv[2], Path(sys.argv[3])
app = launcher.load_app()
state = app.composition.user_state
report = {"loaded": {"cards": len(state.cards), "enabled": len(state.enabled_decks), "available": len(state.available_decks())}}
first, second = [card.id for card in state.cards if card.deck == state.available_decks()[1]][:2]
report["ids"] = [first, second]
if mode == "edit":
    deck = state.available_decks()[0]
    report["toggled"] = [state.disable_deck(deck), state.enable_deck(deck)]
    state.set_position(first, 0.1, 0.2, 0.3)
    state.set_difficulty(first, 70)
    state.mark_read(first)
    group_id = state.create_group(first, "probe", "#123456")
    state.add_to_group(second, group_id)
    state.create_link(first, second)
    state.get_position_by_id(first).related_ids = [second, "unknown"]
else:
    position = state.get_position_by_id(first)
    progress = state.progress[first]
    report["restored"] = {
        "position": [position.x, position.y, position.z],
        "related_ids": position.related_ids,
        "progress": [progress.read, progress.difficulty],
        "groups": [[group.name, group.card_ids] for group in state.groups],
        "links": [[link.source_id, link.target_id] for link in state.links],
    }
state.save()
report["modules"] = {name: sys.modules[name].__file__ for name in [*launcher.REROUTES, "app"]}
report["events"], report["base_dir"] = events, str(app.BASE_DIR)
print(json.dumps(report))
"""


def _run_launcher(mode: str, scratch: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", _LAUNCH_PROBE, str(LAUNCHER_DIR), mode, str(scratch)],
        cwd=ROOT, capture_output=True, text=True, timeout=180,
    )


def _report(result: subprocess.CompletedProcess) -> dict:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def scratch(tmp_path_factory):
    return tmp_path_factory.mktemp("scratch") / "user_state.json"


@pytest.fixture(scope="module")
def launch(scratch):
    edit = _report(_run_launcher("edit", scratch))
    saved = json.loads(scratch.read_text(encoding="utf-8"))
    restart = _report(_run_launcher("read", scratch))
    return {"edit": edit, "saved": saved, "restart": restart, "resaved": json.loads(scratch.read_text(encoding="utf-8"))}


def _norm(path: Path) -> str:
    return os.path.normcase(str(path))


def _touched(report: dict) -> list:
    return [path for _, path in report["events"]]


def test_launcher_reads_the_course_file_once(launch):
    for run in ("edit", "restart"):
        opened = [path for event, path in launch[run]["events"] if event == "open"]
        assert opened.count(_norm(CARDS_FILE)) == 1


def test_launcher_touches_nothing_in_data_but_the_course_file(launch):
    data_dir = _norm(ROOT / "data")
    for run in ("edit", "restart"):
        touched = _touched(launch[run])
        assert not [path for path in touched if path.endswith(".md")]
        assert {path for path in touched if path == data_dir or path.startswith(data_dir + os.sep)} == {_norm(CARDS_FILE)}


def test_launcher_runs_the_app_on_the_module(launch):
    edit = launch["edit"]
    assert edit["loaded"] == launch["restart"]["loaded"] == {"cards": 1670, "enabled": 48, "available": 48}
    assert edit["toggled"] == [True, True]
    assert Path(edit["base_dir"]) == ROOT
    assert {name: Path(file) for name, file in edit["modules"].items()} == {
        "flashcards_app.models": DRAFT_DIR / "models.py",
        "flashcards_app.parser": DRAFT_DIR / "parser.py",
        "flashcards_app.deck_catalog": DRAFT_DIR / "deck_catalog.py",
        "flashcards_app.state": DRAFT_DIR / "changes" / "state.py",
        "flashcards_app.state_core": DRAFT_DIR / "changes" / "state_core.py",
        "flashcards_app.geometry": DRAFT_DIR / "changes" / "geometry.py",
        "flashcards_app.visualization.map": DRAFT_DIR / "changes" / "map.py",
        "flashcards_app.user_state_service": DRAFT_DIR / "changes" / "user_state_service.py",
        # what app.py itself sees; the code is compiled from changes/app.py
        "app": ROOT / "app.py",
    }


def _state_ids(payload: dict) -> list:
    """Every card id the state file holds, except related_ids."""
    return [
        *(item["comb_id"] for section in ("positions", "progress") for item in payload[section]),
        *(card_id for group in payload["groups"] for card_id in group["card_ids"]),
        *(link[key] for link in payload["links"] for key in ("source_id", "target_id")),
    ]


def test_scratch_state_is_keyed_by_comb_id(launch, course):
    for payload in (launch["saved"], launch["resaved"]):
        assert payload["version"] == 2
        assert all("comb_id" in item and "card_id" not in item for section in ("positions", "progress") for item in payload[section])
        assert len(payload["positions"]) == 1670
        # name, question and feedback stay readable for every id the state holds
        assert all(course.card(card_id) is not None for card_id in _state_ids(payload))
    # related_ids are saved as set and filtered on the next start
    assert all(course.card(card_id) for position in launch["resaved"]["positions"] for card_id in position["related_ids"])


def test_restart_restores_the_saved_state(launch):
    first, second = launch["edit"]["ids"]
    assert launch["restart"]["ids"] == [first, second]
    assert launch["restart"]["restored"] == {
        "position": [0.1, 0.2, 0.3],
        "related_ids": [second],  # "unknown" is not a card of the course
        "progress": [True, 70],
        "groups": [["probe", [first, second]]],
        "links": [[first, second]],
    }


def test_state_file_with_card_id_is_refused(tmp_path):
    scratch = tmp_path / "user_state.json"
    scratch.write_text(json.dumps({"version": 2, "positions": [], "progress": [{"card_id": "101001", "read": True, "difficulty": 1}]}), encoding="utf-8")
    result = _run_launcher("read", scratch)
    assert result.returncode != 0
    assert "StateFileError" in result.stderr and "card_id" in result.stderr
