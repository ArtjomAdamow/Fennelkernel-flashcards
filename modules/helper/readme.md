# Helper module: layout and launch

The helper puts the model's topics, positions and connections on the cluster module's map (`modules/cluster/readme.md`): in the decks view the decks are placed by the similarity of their cards; the topics of a deck are the topic model's decision over the course file's scripted topics; in the cards view a topic's cards sit on the surface of the topic's sphere, placed by similarity and connected by a hierarchical clustering. The first milestone is "TF-IDF similar cards"; the concept, architecture, roadmap and measured numbers are in `docs/draft/helper/`.

The helper builds on the cluster module (its three views `decks`, `topics` and `cards`, its keys, dialogs and assets) and depends on the flashcards package (the main project); no module is merged into the main project. It reads the course file `data/topics.json` (version 3: decks 01 to 24, 1,064 cards in 133 topics, four stacks), the same file as the cluster module, and refuses any other version.

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
│   │   ├── model_composition.py        # the model's topics, positions, connections, groups and metrics on the cluster app
│   │   ├── layout/
│   │   │   └── difficulty_metrics.py   # the back of the card panel: the difficulty model's metrics per view
│   │   └── services/
│   │       ├── similar.py              # card text, vectoriser, unit vectors, neighbours, deck vectors
│   │       ├── topic_model.py          # T1: nearest centroid over the scripted topics, the derived course file
│   │       ├── layout.py               # the layout step: SVD start, force layout on the sphere, measures
│   │       ├── clustering.py           # connections from scipy's clustering, in merge order
│   │       ├── course_model.py         # the fitted model: position sources, the topics' layouts and connections
│   │       ├── difficulty_model.py     # D1: the difficulty of the unrated quizzes, measured out of fold
│   │       ├── difficulty_groups.py    # easy, medium, hard and "predicted" as generated groups (always the oldest)
│   │       └── evaluation.py           # the offline measures and the judges of the topic model
│   ├── cards.py               # the composition root (replaces the cluster module's)
│   └── assets/                # replaces assets/<same file name> (empty so far)
├── temp/                      # generated only, flat (no subfolders)
│   ├── camera.js, style.css, …   # merged assets (main, cluster, helper)
│   ├── helper_topics.json        # the model's topics as the course file the app reads (rewritten at every start)
│   ├── helper_state.json         # card state: the cards and topic dots of the checked decks (+ *.bak backups)
│   ├── helper_space_state.json   # decks state of the decks view (+ *.bak backups)
│   └── helper_view_state.json    # the checked topics and the shown cards of each deck (+ *.bak backups)
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
- The serving process writes `temp/helper_topics.json`, the course file with the model's topics, before it composes the app, and the app reads that file instead of `data/topics.json`. It is rebuilt at every start and is not a state file: it is never backed up.
- The app's state is saved to `temp/helper_state.json` (the cards and the topic dots of the checked decks), `temp/helper_space_state.json` (the decks) and `temp/helper_view_state.json` (the checked topics and the shown cards of each deck). The main project's `data/user_state.json` is never touched.
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

If state files exist in `temp/` at startup, the launcher asks once whether to back them up first (`helper_state.json_01.bak`, `_02.bak`, …) and then start fresh. Without input (a non-interactive start), the existing files are kept. The question is asked once, not again in the debug reloader's child process. **Answer "y" the first time after 2026-10-26:** state files written before that date are of the old course (48 decks, other card ids, positions inside the sphere) and are not converted; and stored positions, connections and checks always win over generated ones, so an old state file keeps what it has.

What a fresh start does:

- **Decks and topics checked:** the cluster module itself checks all 24 decks and all of their topics; the helper changes none of its defaults.
- **The topics are the model's.** The course file's topics are scripted (`scripts/topics.py`, from the lecture headings), so the topic model T1 takes them as its input and decides every card's topic: the nearest of the deck's topic centroids by cosine, each centroid the mean of the topic's cards' vectors (leave-one-out, so a card never votes for itself). The result goes into `temp/helper_topics.json`, the course file the app reads, so the topic dots, the Topics and Cards dialogs and the state follow the model's topics. On the course 351 of the 1,064 cards (33 %) get another topic than the script; 2 topics end up empty and keep their dots. Nothing is removed, and the raw scripted topics stay in `data/topics.json`.
- **Hidden cards:** a card whose margin (its best cosine minus the second best) is below 0.05 sits between two topics and is left out of the shown cards, once, at the fresh start: 314 cards (30 %) on the course. The Cards dialog of its topic lists it unchecked and shows it again; its position, connections and groups are stored all along.
- **Positions:** the 24 decks are placed on the sphere's surface by the similarity of their cards; every card sits on the surface of its topic's sphere, placed by its similarity to the topic's other cards (a layout per topic); the topic dots take the cluster module's random positions in the shell around the centroid.
- **Connections:** every topic's cards are connected as the hierarchical clustering tree of the topic (933 connections on the course: one per merge), drawn as arcs over the surface of the sphere. There are no connections between topics, and none between decks at the start: the Helper button in the decks view adds the 23 deck connections.
- **Groups:** every rated quiz joins its difficulty group (184 easy, 69 medium, 23 hard), and the 56 unrated quizzes join "Quiz difficulty: predicted" and their predicted level's group (38 easy, 15 medium, 3 hard).

With nothing selected, the card panel shows the dendrogram of the view's connections; Enter turns it over to the difficulty model's metrics. The models are fitted in the serving process at every start (about 1.7 s for the course model with the topic model and 131 topic layouts, about 0.9 s for the difficulty model with its per-deck metrics); nothing but positions, connections, group memberships and the checks is stored.

The views, keys and dialogs are the cluster module's (`modules/cluster/readme.md`), plus one button:

- **Cut-off line** (the slider under the card panel while nothing is selected, from the cluster module): it cuts the clustering tree at a share of its height. At 100 % the whole tree of the topic (or of the decks) is one constellation; lower it and the tree falls apart into its parts, drawn as separate constellations on the map and side by side in the dendrogram. Nothing is stored; every start shows the whole tree.
- **Helper** (top bar, left of Random) adds what the model gives and the current view is missing.
  - In the decks view: the deck connections.
  - In the topics view: the entered deck's cards' difficulty memberships, rated and predicted. Nothing is connected there: there are no connections between topics.
  - In the cards view: the entered topic's card connections and its cards' memberships.
  - What exists already is kept, and the generated groups become the oldest groups again, so a deleted one comes back as the oldest.
  - Unchecking a deck strips its cards' state, connections and memberships included. Check the deck again, enter a topic, and Helper brings the topic's connections and groups back.
- **Difficulty colours** (cards view): the course's difficulty colours the cards: easy blue, medium beige-brown, hard red-orange. Unrated cards stay grey.
  - These are three generated groups ("Quiz: easy", "Quiz: medium", "Quiz: hard"). They can be combined with your own groups: a card may be in both.
  - They are always the oldest groups, so a rated card shows its difficulty colour. Uncheck them in Focus, and the card takes the colour of its oldest checked group.
  - Their colours are in `delta/project/services/difficulty_groups.py`.
  - The cluster module's predefined groups of the topic dots ("hard quizes", "more flashcards", "composite") stay in front of them with their own ranks: they hold topic dots, the difficulty groups cards.
- **Predicted difficulty** (cards view): the difficulty model D1 rates the flattened quizzes that have no difficulty (56 in the course; flashcards are not rated, the lecture notebooks' and the quiz file's alike).
  - A predicted quiz is in two generated groups: the grey "Quiz difficulty: predicted" and the group of its predicted level ("Quiz: easy", …), with the same colour as the rated cards.
  - "Quiz difficulty: predicted" is always the oldest group, so a predicted quiz shows grey. Uncheck it in Focus, and the quiz shows its predicted level's colour.
  - The "Quiz:" groups therefore count rated and predicted quizzes together (in the course, "Quiz: easy" has 184 rated and 38 predicted).
  - The predictions are tentative: treat them as an order within the deck, not as a level (`docs/draft/helper/concept.md`, "Quality of the predicted groups").
  - The levels are relative to the deck: each deck's quizzes keep the course's shares (8 easy, 3 medium and 1 hard of 12).
- **The back of the card panel:** with nothing selected, press Enter or click the card panel, and it turns over from the dendrogram to the model's metrics. Press Enter or click again to turn it back; selecting a dot or changing the view turns it back too.
  - The back shows a table of D1's scores next to two baselines, the confusion matrix of the rated quizzes and the shares of the levels.
  - In the decks view the numbers cover all decks. In the topics view they cover the entered deck only: its rated quizzes, out of fold under the course-wide model, and its predicted quizzes. In the cards view the back counts the entered topic's rated and unrated quizzes and shows the deck's metrics with them (a topic's two or three rated quizzes are too few to measure). A deck without rated quizzes (deck 01) shows its predicted shares and says why there is nothing to measure.
  - A click on the dendrogram plot itself may be taken by the plot; Enter always works.

## Run the tests

The tests need the module env (scikit-learn and scipy):

```bash
.\modules\helper\.venv\Scripts\python.exe -B -m pytest modules/helper/tests -p no:cacheprovider -q
.\modules\helper\.venv\Scripts\python.exe -B -m unittest discover -s modules/helper/tests
```

`-B` stops Python from writing `__pycache__` folders next to the test files.

The tests are plain `unittest.TestCase` classes (153). `tests/helper_support.py` loads `helper.py` as `helper_launcher`, installs its layered delta import hook and holds a small test course in version 3 (three decks, 13 cards in seven scripted topics, one of them empty and one the rest topic, a flashcard of the quiz file and a quiz with its options; too small for the difficulty model, so its tests use `difficulty_course()`, three decks of 12 rated quizzes, and `difficulty_report()`), so every `project.*` import in the tests runs the same code as the launcher under both runners (`conftest.py` does the same for pytest). One test fits the index of the real course and is skipped without `data/topics.json`.

## Offline evaluation

```bash
.\modules\helper\.venv\Scripts\python.exe modules/helper/evaluate.py [--part similarity|difficulty|topics]
```

`--part topics` measures the topic model T1 against the scripted topics of `data/topics.json`: the agreement of the nearest centroid rule next to the neighbour rule, a logistic regression per deck and chance, over the course, by stack and per deck; the margin table (the cards kept at a threshold and their agreement), the coherence per topic, the moved cards and the emptied topics. One row per model and scope goes to `results/topics.csv`.

`--part difficulty` measures only the difficulty model D1. It appends one row per feature set and label rule, plus the two baselines, to `results/difficulty.csv`: out of fold on the rated quizzes, as mean ± sd over the repeats, and the predicted levels of the unrated quizzes.

`--part similarity` measures the random floor (B0), the TF-IDF variants (same-deck precision@5, coverage, distinct recommended cards) and the chosen model's map (trustworthiness and neighbour overlap of the deck layout, the within-topic overlap of the card layouts over the model's topics), appends one row per model and variant to `results/results.csv`, and writes the hand-check candidates for 20 NLP cards to `results/hand_check.md`, to be judged by hand: mark every relevant candidate with `x`, or the `none` line when nothing fits. Later runs keep the marks and add every variant's hand-judged precision@5 over the judged cards (`hand_precision` in the results). Without `--part` all three parts run. The rows note the course's decks ("decks 01 to 24"); the rows of the 48-deck course of October 22 and 23 stay above them. The numbers are in `docs/draft/helper/concept.md`.

Keep `temp/` and `results/` generated. Code belongs in `delta/`, tests in `tests/`.
