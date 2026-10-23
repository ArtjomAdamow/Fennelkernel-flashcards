# Helper module: layout and launch

The helper puts model positions and connections on the cluster module's map: in the space view the decks are placed by the similarity of their cards, in the deck view the cards sit around their deck's centroid by how central they are, and the connections of both views come from a hierarchical clustering. The first milestone is "TF-IDF similar cards"; the concept, architecture, roadmap and baseline numbers are in `docs/draft/helper/`.

The helper builds on the cluster module (its views, keys and assets) and depends on the flashcards package (the main project); no module is merged into the main project.

Run the commands below from the root of the main project repository.

## Module structure

```text
modules/helper/
├── __init__.py
├── helper.py                  # isolated app launcher (layers, env check, state files)
├── evaluate.py                # offline evaluation script (run in the module env)
├── pyproject.toml, uv.lock, .python-version, .venv/   # the module's own uv project and env
├── delta/                     # mirrors the main project
│   ├── project/
│   │   ├── model_composition.py        # the model's positions, connections, groups and metrics on the cluster app
│   │   ├── layout/
│   │   │   └── difficulty_metrics.py   # the back of the card panel: the difficulty model's metrics
│   │   └── services/
│   │       ├── similar.py              # card text, vectoriser, unit vectors, neighbours, deck vectors
│   │       ├── layout.py               # the layout step: SVD start, force layout on the sphere, measures
│   │       ├── clustering.py           # connections from scipy's clustering, in merge order
│   │       ├── course_model.py         # the fitted model: position sources and connections
│   │       ├── difficulty_model.py     # D1: the difficulty of the unrated quizzes, measured out of fold
│   │       ├── difficulty_groups.py    # easy, medium, hard and "predicted" as generated groups (always the oldest)
│   │       └── evaluation.py           # the offline measures
│   ├── cards.py               # the composition root (replaces the cluster module's)
│   └── assets/                # replaces assets/<same file name> (empty so far)
├── temp/                      # generated only, flat (no subfolders)
│   ├── camera.js, style.css, …   # merged assets (main, cluster, helper)
│   ├── helper_state.json         # card state of the deck view (+ *.bak backups)
│   ├── helper_space_state.json   # deck state of the space view (+ *.bak backups)
│   └── helper_view_state.json    # checked cards of each deck (+ *.bak backups)
├── results/                   # evaluation results (git-ignored: derived course data)
└── tests/                     # module tests
```

The launcher uses a file from a higher layer when one exists, otherwise the layer below: this module's `delta/`, then the cluster module's `modules/cluster/delta/`, then the main project.

- **Python:** an import hook serves the files of both delta layers under the main package name, so the cluster module's `delta/project/composition.py` becomes `project.composition`, and this module's `delta/project/services/similar.py` becomes `project.services.similar`. The composition root is this module's `delta/cards.py`, which uses the cluster module's `composition.py` through `project.model_composition`.
- **Assets:** three layers, a later layer replaces files of the same name: the main `assets/`, then `modules/cluster/delta/assets/`, then `delta/assets/`.
- **Startup:** the launcher prints the active overrides of both layers.

All generated output goes flat into `temp/`:
- On launch, the launcher empties `temp/` except the three state files and their backups, then copies the asset layers into it in order. File names must be unique after flattening.
- Dash serves `temp/` as its assets folder. Hot reload is off, because a state save in that folder would reload the browser. Restart the launcher after editing assets.
- The app's state is saved to `temp/helper_state.json` (cards), `temp/helper_space_state.json` (decks) and `temp/helper_view_state.json` (the checked cards of each deck). The main project's `data/user_state.json` is never touched.
- No `__pycache__` folders are written.

## The module env

The module has its own uv project next to the launcher: `pyproject.toml` with `scikit-learn`, `scipy`, `pytest` (dev) and the flashcards package (`spatial-flashcards`, the main project, editable by path), `uv.lock` and `.venv/`. At every start the launcher runs `uv sync --project modules/helper --locked --check` (well under a second). If the env is out of sync it asks "Install it now with uv? (y/n)"; without input it prints the command and exits. On the first run without a lockfile it runs `uv lock` before `uv sync`. When started from another interpreter (for example the main project's `.venv`), it restarts itself with the module env's Python; `HELPER_ENV_READY=1` marks the restarted process, so it and the reloader's child skip the check.

To set the env up by hand:

```bash
uv sync --project modules/helper
```

## Start the module build

```bash
.\.venv\Scripts\python.exe modules/helper/helper.py
```

or directly on the module env:

```bash
.\modules\helper\.venv\Scripts\python.exe modules/helper/helper.py
```

If state files exist in `temp/` at startup, the launcher asks once whether to back them up first (`helper_state.json_01.bak`, `_02.bak`, …) and then start fresh. Without input (a non-interactive start), the existing files are kept. The question is asked once, not again in the debug reloader's child process. **To see the model positions, answer "y":** stored positions and connections always win over generated ones, so an old state file keeps its random positions.

What a fresh start does (the pilot run): all 48 decks are checked and all 1,670 cards are shown, every deck and every card gets its model position (cards between the cluster module's inner radius and 1 from the sun; the radius is `INNER_RADIUS` in `modules/cluster/delta/project/services/positions.py`), every deck gets its card connections from the clustering (12 to 56 per deck) and the decks get theirs (47), every card with a difficulty joins its difficulty group (345 easy, 130 medium, 47 hard), and the 56 unrated quizzes join "Quiz difficulty: predicted" and their predicted level's group (38 easy, 15 medium, 3 hard). With nothing selected, the card panel shows the dendrogram of those connections: the clustering tree of the decks in the space view, of the deck's cards in the deck view; Enter turns it over to the difficulty model's metrics. The models are fitted in the serving process at every start (about 3 s for the course model and 1.6 s for the difficulty model with its per-deck metrics); nothing but positions, connections and group memberships is stored.

The views, keys and dialogs are the cluster module's (`modules/cluster/readme.md`), plus one button:

- **Cut-off line** (the slider under the card panel while nothing is selected, from the cluster module): it cuts the clustering tree at a share of its height. At 100 % the whole tree of the deck (or of the decks) is one constellation; lower it and the tree falls apart into its topics, drawn as separate constellations on the map and side by side in the dendrogram. Nothing is stored; every start shows the whole tree.
- **Helper** (top bar, left of Random) adds what the model gives and the current view is missing.
  - In the deck view: the entered deck's card connections, its rated cards' difficulty memberships, and its predicted quizzes' memberships.
  - In the space view: the deck connections.
  - What exists already is kept, and the generated groups become the oldest groups again, so a deleted one comes back as the oldest.
  - Unchecking a deck strips its cards' state, connections and memberships included. Check the deck again, enter it, check its cards in the Cards dialog, and Helper brings them back.
- **Difficulty colours** (deck view): the course's difficulty colours the cards: easy blue, medium beige-brown, hard red-orange. Unrated cards stay grey.
  - These are three generated groups ("Quiz: easy", "Quiz: medium", "Quiz: hard"). They can be combined with your own groups: a card may be in both.
  - They are always the oldest groups, so a rated card shows its difficulty colour. Uncheck them in Focus, and the card takes the colour of its oldest checked group.
  - Their colours are in `delta/project/services/difficulty_groups.py`.
- **Predicted difficulty** (deck view): the difficulty model D1 rates the flattened quizzes that have no difficulty (56 in the course; plain flashcards are not rated yet).
  - A predicted quiz is in two generated groups: the grey "Quiz difficulty: predicted" and the group of its predicted level ("Quiz: easy", …), with the same colour as the rated cards.
  - "Quiz difficulty: predicted" is always the oldest group, so a predicted quiz shows grey. Uncheck it in Focus, and the quiz shows its predicted level's colour.
  - The "Quiz:" groups therefore count rated and predicted quizzes together (in the course, "Quiz: easy" has 345 rated and 38 predicted).
  - The predictions are tentative: treat them as an order within the deck, not as a level (`docs/draft/helper/early.md`, "Quality of the predicted groups").
  - The levels are relative to the deck: each deck's quizzes keep the course's shares (8 easy, 3 medium and 1 hard of 12).
- **The back of the card panel:** with nothing selected, press Enter or click the card panel, and it turns over from the dendrogram to the model's metrics. Press Enter or click again to turn it back; selecting a dot turns it back too.
  - The back shows a table of D1's scores next to two baselines, the confusion matrix of the rated quizzes and the shares of the levels.
  - In the space view the numbers cover all decks. In the deck view they cover the entered deck only: its rated quizzes, out of fold under the course-wide model, and its predicted quizzes. A deck without rated quizzes (deck 01) shows its predicted shares and says why there is nothing to measure.
  - A click on the dendrogram plot itself may be taken by the plot; Enter always works.

## Run the tests

The tests need the module env (scikit-learn and scipy):

```bash
.\modules\helper\.venv\Scripts\python.exe -B -m pytest modules/helper/tests -p no:cacheprovider -q
.\modules\helper\.venv\Scripts\python.exe -B -m unittest discover -s modules/helper/tests
```

`-B` stops Python from writing `__pycache__` folders next to the test files.

The tests are plain `unittest.TestCase` classes. `tests/helper_support.py` loads `helper.py` as `helper_launcher`, installs its layered delta import hook and holds a small test course (three decks, ten cards; too small for the difficulty model, so its tests use `difficulty_course()`, three decks of 12 rated quizzes, and `difficulty_report()`), so every `project.*` import in the tests runs the same code as the launcher under both runners (`conftest.py` does the same for pytest). One test fits the index of the real course and is skipped without `data/cards.json`.

## Offline evaluation

```bash
.\modules\helper\.venv\Scripts\python.exe modules/helper/evaluate.py [--part similarity|difficulty]
```

`--part difficulty` measures only the difficulty model D1. It appends one row per feature set and label rule, plus the two baselines, to `results/difficulty.csv`: out of fold on the rated quizzes, as mean ± sd over the repeats, and the predicted levels of the unrated quizzes. `--part similarity` runs only the measures below; without `--part` both run.

The similarity part measures the random floor (B0), the TF-IDF variants (same-deck precision@5, coverage, distinct recommended cards) and the chosen model's map (trustworthiness and neighbour overlap of the deck layout, the within-deck overlap of the card layouts), appends one row per model and variant to `results/results.csv`, and writes the hand-check candidates for 20 NLP cards to `results/hand_check.md`, to be judged by hand: mark every relevant candidate with `x`, or the `none` line when nothing fits. Later runs keep the marks and add every variant's hand-judged precision@5 over the judged cards (`hand_precision` in the results). The numbers are in `docs/draft/helper/early.md`.

Keep `temp/` and `results/` generated. Code belongs in `delta/`, tests in `tests/`.
