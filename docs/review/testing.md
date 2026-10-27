# Commands for launching and testing

Run every command from the repository root. In PowerShell or cmd, use backslashes: `.venv\Scripts\python.exe`.

## Launching the app

`.venv/Scripts/python.exe cards.py`

`cards.py` is the composition root: it reads `data/cards.json`, uses `data/user_state.json` as the state file and starts Dash in debug mode on http://127.0.0.1:8050/. The startup save rewrites `data/user_state.json`; back it up before test launches if it matters.

## Project tests

`.venv/Scripts/python.exe -m pytest tests -p no:cacheprovider -q`

## Unittest

`.venv/Scripts/python.exe -m unittest discover -s tests -t .`

The project tests are plain `unittest.TestCase` classes (no pytest import), so both runners work; the VS Code test explorer uses unittest. pytest additionally counts subtests.

## Module launchers

The modules run the main project with their own changes and never touch `data/`. Each one:

- uses a file from its `delta/` folder if present, otherwise the main project's file (`delta/project/<path>.py` replaces `project/<path>.py`, `delta/cards.py` replaces `cards.py`, `delta/assets/<file>` replaces `assets/<file>`);
- writes all generated output flat into its `temp/` folder: the merged assets and its own state file;
- runs Dash with hot reload off (restart after editing assets) and writes no `__pycache__` folders.

### Navigation

`.venv/Scripts/python.exe modules/navigation/navigation.py`

State file: `modules/navigation/temp/navigation_user_state.json`.

### Book

`.venv/Scripts/python.exe modules/book/book.py`

State file: `modules/book/temp/book_user_state.json`. If it exists, the launcher asks whether to back it up first (`book_user_state.json_01.bak`, … in `temp/`); without input it keeps the file. In addition, a top-level `modules/book/data/<name>.json` replaces the main `data/<name>.json` (e.g. `cards.json`); the subfolders of `modules/book/data/` are ignored.

## Module tests

`.venv/Scripts/python.exe -m pytest modules/navigation/tests -p no:cacheprovider -q`

`node --test modules/navigation/tests/nav.test.js`

The module tests run on the same code as the launcher: `modules/navigation/tests/conftest.py` installs the launcher's delta import hook. They use pytest (fixtures), so the unittest runner does not apply. The browser tests (`nav.test.js`, also wrapped by `test_nav_js.py`) need Node 18 or newer and are skipped without it. The book module has no tests yet.

## Single file tests

`.venv/Scripts/python.exe -m pytest tests/test_parser.py -q`
`.venv/Scripts/python.exe -m pytest "tests/test_parser.py::ParserTest::test_md_source_is_switched_off" -q`
`.venv/Scripts/python.exe -m unittest tests.test_parser -v`

`-p no:cacheprovider` only keeps pytest from writing a `.pytest_cache` folder, so you can leave it out.
