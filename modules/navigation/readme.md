# Navigation module: layout, tests, and launch

Run the commands below from the main project repository root.

## Module structure

```text
modules/navigation/
├── __init__.py
├── navigation.py              # isolated app launcher
├── delta/                     # mirrors the main project
│   ├── project/               # replaces project/<same path>, e.g. project/layout/map.py
│   ├── cards.py               # optional: replaces the composition root cards.py
│   └── assets/                # replaces assets/<same file name>
├── temp/                      # generated only, flat (no subfolders)
│   ├── camera.js, style.css, …  # main assets merged with delta/assets
│   └── navigation_user_state.json  # module run's independent persistence
└── tests/                     # all Python and Node tests, flat
```

A file found in `delta/` is used, otherwise the main project's file. Python files in `delta/project/` are served by an import hook under the main package name (`delta/project/services/navigation.py` becomes `project.services.navigation`); new files that exist only there are importable too (`delta/project/recommender.py` becomes `project.recommender`). The launcher prints the active overrides at startup.

All generated output goes flat into `temp/`. On launch the launcher empties `temp/` except `navigation_user_state.json`, copies the main `assets/` and then `delta/assets/` over them (file names must be unique after flattening). Dash serves `temp/` as its assets folder; its hot reload is off, because a state save in that folder would reload the browser. Restart the launcher after editing assets. The app's persistence goes to `temp/navigation_user_state.json`; the main project's `data/user_state.json` stays untouched. No `__pycache__` folders are written.

`delta/` mirrors the main project's names: `delta/project/` the package `project/`, `delta/cards.py` the composition root `cards.py`.

The tests in `tests/` run on the same code as the launcher. The launcher's delta import hook is installed by `tests/conftest.py` under pytest and by `tests/navigation_support.py` under `unittest discover`, which does not read conftest. Files loaded by path come from `code_source()` / `asset_source()` (delta if present, otherwise main).

The tests are `unittest.TestCase` classes, one per file, so they run under both runners. `navigation_support.py` provides what pytest's fixtures and helpers used to: `tmp_path`, `monkeypatch`, `capsys`, class-wide fixtures, `approx`, `raises`, `skip` and `fail`.

## Start the module build

```bash
.\.venv\Scripts\python.exe modules/navigation/navigation.py
```

The project dependencies must be installed in the selected Python environment. If `python` does not point to that environment, use its interpreter, for example on Windows: `.venv/Scripts/python.exe modules/navigation/navigation.py`.

## Run all tests

```bash
.\.venv\Scripts\python.exe -B -m pytest modules/navigation/tests -p no:cacheprovider -q
.\.venv\Scripts\python.exe -B -m unittest discover -s modules/navigation/tests
node --test modules/navigation/tests/nav.test.js
```

`-B` keeps Python from writing `__pycache__` folders next to the test files.

Both Python commands run all 108 Python tests. `test_nav_js.py` also runs the Node suite (32 tests) when Node 18 or newer is installed, and is skipped without Node. A skip is not a pass: check that the Node suite really ran. The explicit Node command prints the browser suite result separately.

`nav.test.js` tests the module's `keyboard.js` and `camera.js`, or the main project's while `delta/assets/` has none. A change to the main assets can therefore break this suite, so run it after changing them. Its key configuration must follow `keyboard.js`: for example, the `member` flag (`data-member`) decides whether Space captures a view. Without a member (nothing selected, or a card outside every constellation) Space captures no view: it stops the camera's motion, and the next Space resumes it (`constellationNav.toggleMotion` in `camera.js`, since 2026-10-23).

For focused iteration:

```bash
.\.venv\Scripts\python.exe -m pytest modules/navigation/tests/test_constellations.py -q
.\.venv\Scripts\python.exe -m pytest modules/navigation/tests/test_nav_foundation.py -q
.\.venv\Scripts\python.exe -m pytest modules/navigation/tests/test_nav_integration.py -q
.\.venv\Scripts\python.exe -m pytest modules/navigation/tests/test_nav_logic.py -q
.\.venv\Scripts\python.exe -m pytest modules/navigation/tests/test_nav_js.py -q
node --test modules/navigation/tests/nav.test.js
```

Keep `temp/` generated. Source files belong in `delta/` (code and assets) or `tests/`.
