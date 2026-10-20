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
│   └── const_user_state.json  # module run's independent persistence
└── tests/                     # all Python and Node tests, flat
```

A file found in `delta/` is used, otherwise the main project's file. Python files in `delta/project/` are served by an import hook under the main package name (`delta/project/services/navigation.py` becomes `project.services.navigation`); new files that exist only there are importable too (`delta/project/recommender.py` becomes `project.recommender`). The launcher prints the active overrides at startup.

All generated output goes flat into `temp/`. On launch the launcher empties `temp/` except `const_user_state.json`, copies the main `assets/` and then `delta/assets/` over them (file names must be unique after flattening). Dash serves `temp/` as its assets folder; its hot reload is off, because a state save in that folder would reload the browser. Restart the launcher after editing assets. The app's persistence goes to `temp/const_user_state.json`; the main project's `data/user_state.json` stays untouched. No `__pycache__` folders are written.

`delta/` mirrors the main project's names: `delta/project/` the package `project/`, `delta/cards.py` the composition root `cards.py`.

The tests in `tests/` run on the same code as the launcher: `tests/conftest.py` installs the launcher's delta import hook, and files loaded by path come from `code_source()` / `asset_source()` (delta if present, otherwise main).

## Start the module build

```bash
.\.venv\Scripts\python.exe modules/navigation/navigation.py
```

The project dependencies must be installed in the selected Python environment. If `python` does not point to that environment, use its interpreter, for example on Windows: `.venv/Scripts/python.exe modules/navigation/navigation.py`.

## Run all tests

```bash
.\.venv\Scripts\python.exe -m pytest modules/navigation/tests -q
node --test modules/navigation/tests/nav.test.js
```

The pytest command runs all Python test files; `test_nav_js.py` also invokes the Node suite when Node 18 or newer is installed, and skips that wrapper when Node is unavailable. The explicit Node command prints the browser suite result separately. Run it in a CI environment if Node is not installed locally.

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
