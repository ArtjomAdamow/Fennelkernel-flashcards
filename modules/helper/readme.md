# Helper module: layout and launch

This module is where the recommender gets built. The first milestone is "TF-IDF similar cards"; the concept, architecture and roadmap are in `docs/draft/helper/`.

The helper builds on the cluster module (its views, navigation and assets) and depends on the flashcards package; no module is merged into the main project. **Not built yet:** the skeleton described below still layers the navigation module's assets. Step 1 of the roadmap switches the layers to main → cluster → helper, for Python files and assets.

Run the commands below from the root of the main project repository.

## Module structure

```text
modules/helper/
├── __init__.py
├── helper.py                  # isolated app launcher
├── delta/                     # mirrors the main project
│   ├── project/               # replaces project/<same path>; new files are added
│   ├── cards.py               # optional: replaces the composition root cards.py
│   └── assets/                # replaces assets/<same file name>
├── temp/                      # generated only, flat (no subfolders)
│   ├── camera.js, style.css, …  # merged assets (main, navigation, helper)
│   └── helper_state.json      # module run's independent persistence (+ *.bak backups)
└── tests/                     # module tests
```

The launcher uses a file from `delta/` when one exists, otherwise the main project's file:

- **Python:** an import hook serves the files in `delta/project/` under the main package name, so `delta/project/services/navigation.py` becomes `project.services.navigation`. New files that exist only there can be imported too: `delta/project/services/similar.py` becomes `project.services.similar`. The recommender code goes here.
- **Assets:** there are three layers, and a later layer replaces files of the same name:
  1. the main `assets/`;
  2. `modules/navigation/delta/assets/`;
  3. `delta/assets/`.
- The launcher prints the active overrides at startup, including the assets taken from the navigation module.

All generated output goes flat into `temp/`:
- On launch, the launcher empties `temp/` except `helper_state.json` and its backups. It then copies the three asset layers into it in order. File names must be unique after flattening.
- Dash serves `temp/` as its assets folder. Hot reload is off, because a state save in that folder would reload the browser. Restart the launcher after editing assets.
- The app's state is saved to `temp/helper_state.json`. The main project's `data/user_state.json` is never touched.
- No `__pycache__` folders are written.

The names in `delta/` match the main project: `delta/project/` stands for the package `project/`, and `delta/cards.py` for the composition root `cards.py`. The mechanism is the same as in `modules/book/book.py`, without the `data/*.json` rule and with the extra navigation asset layer.

## Start the module build

```bash
.\.venv\Scripts\python.exe modules/helper/helper.py
```

If `temp/helper_state.json` exists at startup, the launcher asks whether to back it up first (`helper_state.json_01.bak`, `_02.bak`, … in `temp/`) and then start fresh. Without input (a non-interactive start), the existing file is kept. The question is asked once, not again in the debug reloader's child process.

## Run the tests

```bash
.\.venv\Scripts\python.exe -B -m pytest modules/helper/tests -p no:cacheprovider -q
.\.venv\Scripts\python.exe -B -m unittest discover -s modules/helper/tests
```

`-B` stops Python from writing `__pycache__` folders next to the test files. The test files are imported before they could switch bytecode writing off themselves.

The tests are plain `unittest.TestCase` classes. `tests/conftest.py` loads `helper.py` as `helper_launcher` and installs its delta import hook. As a result, every `project.*` import in the tests runs the same code as the launcher. `test_launcher.py` loads the launcher on its own as well, so it also runs without pytest.

Keep `temp/` generated. Code and assets belong in `delta/`, tests in `tests/`.
