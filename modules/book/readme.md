# Book module: layout and launch

Placeholder module. Its first feature (the cards loader) was merged into the main project a while ago; the module is kept as the place for the next one: importing course content (session notebooks, markdown decks) for a RAG system.

Run the commands below from the main project repository root.

## Module structure

```text
modules/book/
├── __init__.py
├── book.py                    # isolated app launcher
├── delta/                     # mirrors the main project
│   ├── project/               # replaces project/<same path>, e.g. project/content/parser.py
│   ├── cards.py               # optional: replaces the composition root cards.py
│   └── assets/                # replaces assets/<same file name>
├── data/
│   ├── *.json                 # optional: replaces the main data/<same name>.json, e.g. cards.json
│   ├── cards/                 # former .md decks (the format of the deactivated markdown loader)
│   ├── sessions/              # bootcamp session notebooks (.ipynb) and their helpers
│   └── aipm_sessions/         # AI product management session notebooks
├── temp/                      # generated only, flat (no subfolders)
│   ├── camera.js, style.css, …  # main assets merged with delta/assets
│   └── book_user_state.json   # module run's independent persistence (+ *.bak backups)
└── tests/                     # module tests (none yet)
```

A file found in `delta/` or `data/` is used, otherwise the main project's file:

- Python files in `delta/project/` are served by an import hook under the main package name (`delta/project/content/parser.py` becomes `project.content.parser`); new files that exist only there are importable too (`delta/project/rag_import.py` becomes `project.rag_import`).
- `data/<name>.json` (top level only) replaces the main project's `data/<name>.json` wherever the app opens a course file (`CardsFile`): a `data/cards.json` here makes the app show this course instead of the main one. The subfolders of `data/` are source content for the RAG import and are ignored by the launcher.
- The launcher prints the active overrides at startup.

All generated output goes flat into `temp/`. On launch the launcher empties `temp/` except `book_user_state.json` and its backups, copies the main `assets/` and then `delta/assets/` over them (file names must be unique after flattening). Dash serves `temp/` as its assets folder; its hot reload is off, because a state save in that folder would reload the browser. Restart the launcher after editing assets. The app's persistence goes to `temp/book_user_state.json`; the main project's `data/user_state.json` stays untouched. No `__pycache__` folders are written.

`delta/` mirrors the main project's names: `delta/project/` the package `project/`, `delta/cards.py` the composition root `cards.py`. The mechanism is the same as in `modules/navigation/navigation.py`, plus the `data/*.json` rule.

## Start the module build

```bash
.\.venv\Scripts\python.exe modules/book/book.py
```

If `temp/book_user_state.json` exists at startup, the launcher asks whether to back it up first (`book_user_state.json_01.bak`, `_02.bak`, … in `temp/`) and then starts fresh. Without input (non-interactive start) the existing file is kept. The question is asked once, not again in the debug reloader's child process.

## Markdown loader (deactivated)

The main project still contains the former markdown deck source, switched off since the move to `data/cards.json`:

- `project/content/parser.py`: `MD_SOURCE_ENABLED = False`; `parse_deck()` and `load_decks()` call `require_md_source()` and raise `MarkdownSourceDisabled` while the flag is off.
- `project/content/deck_catalog.py`: `DeckCatalog(cards_dir)` (the `.md` folder catalog) is guarded the same way; the app uses `JsonDeckCatalog`.

The code is kept on purpose: it will be reused to import other content (the material in `data/`) for the RAG system, typically by changing a copy in `delta/project/` first. A markdown deck is a `# Deck name` heading followed by alternating question/answer blocks, see `data/cards/`.

## Tests

`tests/` is empty. When tests are added, give them a `tests/conftest.py` like `modules/navigation/tests/conftest.py` (load `book.py`, install its delta import hook) so they run on the same code as the launcher.

Keep `temp/` generated. Code and assets belong in `delta/`, course files and RAG source content in `data/`, tests in `tests/`.
