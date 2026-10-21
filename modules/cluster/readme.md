# Cluster module: layout and launch

The map gets two levels:
- **Space view:** the decks are stars. Selecting one shows its description, and Enter opens it.
- **Deck view:** the deck's cards sit around a sun, its centroid, and work as flashcards. Escape goes back.

The concept, architecture and roadmap are in `docs/draft/cluster/`. Dot positions are random in this module; the helper module will later add model positions on top of it.

Run the commands below from the main project repository root.

## Module structure

```text
modules/cluster/
├── __init__.py
├── cluster.py                 # isolated app launcher
├── delta/                     # mirrors the main project
│   ├── project/               # replaces project/<same path>; new files are added
│   ├── cards.py               # optional: replaces the composition root cards.py
│   └── assets/                # replaces assets/<same file name>
├── temp/                      # generated only, flat (no subfolders)
│   ├── camera.js, style.css, …  # main assets merged with delta/assets
│   ├── cluster_state.json     # card state of the deck view (+ *.bak backups)
│   ├── cluster_space_state.json  # deck state of the space view (+ *.bak backups)
│   └── cluster_view_state.json   # checked cards of each deck (+ *.bak backups)
└── tests/                     # module tests
```

The launcher uses a file from `delta/` when one exists, otherwise the main project's file:
- **Python:** an import hook serves the files in `delta/project/` under the main package name, so `delta/project/layout/map.py` becomes `project.layout.map`. New files that exist only there can be imported too: `delta/project/services/dendrogram.py` becomes `project.services.dendrogram`.
- **Assets:** the module has its own overlay. `delta/assets/` files replace the main `assets/` files with the same name.
- **Startup:** the launcher prints the active overrides.

All generated output goes flat into `temp/`:
- On launch, the launcher empties `temp/` except the three state files and their backups. It then copies the main `assets/` and then `delta/assets/` over them. File names must be unique after flattening.
- Dash serves `temp/` as its assets folder. Hot reload is off, because a state save in that folder would reload the browser. Restart the launcher after editing assets.
- The app's state is saved to `temp/cluster_state.json` (cards), `temp/cluster_space_state.json` (decks) and `temp/cluster_view_state.json` (the checked cards of each deck); the main project's `data/user_state.json` stays untouched.
- No `__pycache__` folders are written.

The names in `delta/` match the main project: `delta/project/` stands for the package `project/`, and `delta/cards.py` for the composition root `cards.py`. The mechanism is the same as in `modules/book/book.py`, without the `data/*.json` rule. The module runs in the main project's env and needs no extra dependencies.

## Using it

- **Decks** (top bar, space view): check the decks to work with. A fresh start has none checked. Unchecking a deck erases its cards' progress, positions, groups and connections.
- **Cards** (top bar, deck view; the same button): check the cards of the open deck to show. A freshly checked deck shows none. Unchecking a card only hides it.
- **Random** (deck view only) picks a random card among the shown ones.
- **Space view:** the checked decks are stars, with a glow sized by their number of cards. Select a deck to see its description.
- **Entering a deck:** Enter, or a click on the description, opens the deck view: the deck's cards around a sun, sized by difficulty, working as flashcards. The camera rotates around the sun.
- **Backspace:** unselects the selected dot; with nothing selected, it goes back from the deck view to the decks. It is ignored in text fields, dropdowns and while a dialog is open.
- **Dendrogram:** with nothing selected, the card panel shows the dendrogram of the view's connections.
- **Two states:** connections, groups and progress of decks (`temp/cluster_space_state.json`) and of cards (`temp/cluster_state.json`) are separate.

## Start the module build

```bash
.\.venv\Scripts\python.exe modules/cluster/cluster.py
```

If state files exist in `temp/` at startup, the launcher asks once whether to back them up first (`cluster_state.json_01.bak`, `_02.bak`, …) and then start fresh. Without input (a non-interactive start), the existing file is kept. The question is asked once, not again in the debug reloader's child process.

## Run the tests

```bash
.\.venv\Scripts\python.exe -B -m pytest modules/cluster/tests -p no:cacheprovider -q
.\.venv\Scripts\python.exe -B -m unittest discover -s modules/cluster/tests
```

`-B` keeps Python from writing `__pycache__` folders next to the test files. The test files are imported before they could switch bytecode writing off themselves.

The tests are plain `unittest.TestCase` classes:
- `tests/conftest.py` loads `cluster.py` as `cluster_launcher` and installs its delta import hook, so every `project.*` import in the tests runs the same code as the launcher.
- `test_launcher.py` loads the launcher on its own as well, so it also runs without pytest.
- `cluster.test.js` tests the module's `keyboard.js` and `camera.js` copies with Node (18 or newer). `test_cluster_js.py` runs it from both Python runners and is skipped without Node. To run it alone: `node --test modules/cluster/tests/cluster.test.js`.

Keep `temp/` generated. Code and assets belong in `delta/`, tests in `tests/`.
