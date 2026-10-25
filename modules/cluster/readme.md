# Cluster module: layout and launch

The map gets three levels:
- **Decks view:** every dot is a deck of the course, on the surface of a sphere. Selecting one shows its description, and Enter opens it.
- **Topics view:** the entered deck's topics sit around its centroid. Selecting one shows its description, and Enter opens it.
- **Cards view:** the entered topic's cards sit on the surface of a sphere and work as flashcards. Backspace goes back up.

The concept, architecture and roadmap are in `docs/draft/cluster/`. Dot positions are random in this module; the helper module adds model positions on top of it.

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
│   ├── cluster_state.json     # card state: the cards and topic dots of the checked decks (+ *.bak backups)
│   ├── cluster_space_state.json  # deck state of the decks view (+ *.bak backups)
│   └── cluster_view_state.json   # checked topics and cards of each deck (+ *.bak backups)
└── tests/                     # module tests
```

The launcher uses a file from `delta/` when one exists, otherwise the main project's file:
- **Python:** an import hook serves the files in `delta/project/` under the main package name, so `delta/project/layout/map.py` becomes `project.layout.map`. New files that exist only there can be imported too: `delta/project/content/topics.py` becomes `project.content.topics`.
- **Assets:** the module has its own overlay. `delta/assets/` files replace the main `assets/` files with the same name.
- **Startup:** the launcher prints the active overrides.

All generated output goes flat into `temp/`:
- On launch, the launcher empties `temp/` except the three state files and their backups. It then copies the main `assets/` and then `delta/assets/` over them. File names must be unique after flattening.
- Dash serves `temp/` as its assets folder. Hot reload is off, because a state save in that folder would reload the browser. Restart the launcher after editing assets.
- The app's state is saved to `temp/cluster_state.json` (the cards and the topic dots), `temp/cluster_space_state.json` (the decks) and `temp/cluster_view_state.json` (the checked topics and cards of each deck); the main project's `data/user_state.json` stays untouched.
- No `__pycache__` folders are written.

The names in `delta/` match the main project: `delta/project/` stands for the package `project/`, and `delta/cards.py` for the composition root `cards.py`. The mechanism is the same as in `modules/book/book.py`, without the `data/*.json` rule. The module runs in the main project's env and needs no extra dependencies.

## The course file

The module reads `data/topics.json`, the course file of version 3 written by `scripts/topics.py`: decks 01 to 24, each deck with a `topics` list and every card with its `topic`. Version 2 files (the main project's `data/cards.json`) are refused: the module gives the flashcards of the quiz file (`"source": "quizes"`) their own stack 4, so their ids differ from the main project's (`4…` instead of `1…`). The four stacks: 1 a flashcard of the lecture notebooks, 2 a quiz without an authored difficulty, 3 a quiz with one, 4 a flashcard of the quiz file. A topic dot's id is the deck id, the topic id and a 4-character hash of the topic's card ids (`0203a1f9`): a topic whose cards changed is a new dot, an unchanged topic keeps its position and connections.

## Using it

- **Decks** (top bar, decks view): check the decks to work with. A fresh start has every deck checked, so the first picture is the whole course. Checking a deck loads all its cards and all its topics. Unchecking a deck erases its topics' and cards' progress, positions, groups and connections.
- **Topics** (top bar, topics view; the same button): check the topics of the open deck to show. A freshly checked deck shows all of them. Unchecking a topic hides it and its cards and drops the topic's own connections; the cards keep their settings and come back with the topic.
- **Cards** (top bar, cards view; the same button): check the cards of the open topic to show. A freshly checked deck shows all of them. Unchecking a card only hides it. A checked card stays checked whichever topic it is in.
- **Random** (topics and cards views) picks a random topic, or a random card among the shown ones.
- **Decks view:** the checked decks sit on the surface of a sphere, with a glow sized by their number of cards. The camera always sits at the centre of the sphere. With nothing selected it looks at a random deck and turns the sphere like a globe, in a random direction or the one of your last drag. Select a deck to see its description: the camera looks at the deck and only the sphere turns around the line of sight, so the deck stays in the middle and its neighbours wheel around it. Unselect, and the globe turns again.
- **Entering a deck:** Enter, or a click on the description, opens the topics view: the deck's topics around its centroid (a faint dot in the colours of the deck's groups), one size for every topic; a topic for the cards that fit no other is an open circle. The camera turns around the centroid; a selected topic is centred and the camera turns around it.
- **Entering a topic:** Enter, or a click on the description, opens the cards view: the topic's cards on the surface of a sphere drawn half transparent in the topic's colour (its oldest group, grey without one), sized by difficulty, working as flashcards. The camera turns around the sphere. Select a card, and the camera takes a seat outside the sphere on the axis through the card and the sphere's centre, looks at the card, and only the sphere turns around that axis; unselecting goes back to the turn around the sphere.
- **Mouse drag, wheel:** pause the turning. When you let go, it goes on from where you left the camera, in the direction of your drag. With a deck selected the camera returns to the centre first (a wheel zoom is dropped there); with a card selected it returns onto the card's axis at the distance you left it, but never inside the sphere.
- **Backspace:** unselects the selected dot; with nothing selected, it goes up one level with that level's dot selected: from the cards to the topics with the topic selected, from the topics to the decks with the deck selected. It is ignored in text fields, dropdowns and while a dialog is open.
- **The line above the map:** "N decks mapped", the deck's name, or "deck › topic".
- **Connect, Disconnect:** each opens a dialog with a dropdown: Connect lists the dots of the view not yet connected to the selected one, Disconnect only the connected ones. Confirm applies, Cancel closes; selecting another dot or changing the view closes it too. Deck connections, topic connections and card connections are separate: each view draws its own. In the cards view the lines bend along the sphere's surface; elsewhere they are straight.
- **Dendrogram:** with nothing selected, the card panel shows the dendrogram of the view's connections, with the entered deck's or topic's description.
  - A module on top can give the card panel a back (`compose(..., overview_back=...)`, used by the helper for its difficulty model's metrics). Enter or a click on the panel then turns it over and back, and a selection or a view change turns it back.
  - In this module alone there is no back, and Enter with nothing selected does nothing.
- **Hooks for a module on top:** `compose` takes the position sources of the decks, the cards and the topic dots (`deck_positions`, `card_positions`, `topic_positions`; random by default), a module action (a button in the top bar) and the back of the card panel. The helper module uses them for its model positions, connections and metrics.
- **Cut-off line:** with nothing selected, the slider under the card panel is the dendrogram's cut-off line, from 0 % to 100 % of the tree's height. At 100 % the tree is whole; lower it and the merges above the line are cut: the tree falls apart, the map draws only the connections below the line, and those parts are the constellations. Nothing is stored; every start shows the whole tree, and each view, deck and topic keeps its own line while the app runs.
- **Groups in the topics and cards views:**
  - Focus opens a checklist of the groups plus "No group", all checked, like the Cards dialog. Confirm hides the dots none of whose groups is checked (a dot in no group: when "No group" is unchecked). It changes no membership.
  - A dot takes the colour of its oldest checked group. All checks everything again, and so does every view change.
  - The panel's counts cover the view's dots only: the open deck's cards and topics, or the open topic's cards.
  - The decks view keeps the one-group Focus dropdown. Groups of the card state can hold cards and topics alike.
- **Space:**
  - Navigation by card order: stops the camera's motion until the next selection or view change.
  - Navigation within constellation, with a constellation member selected: stops the motion and starts the navigation (the view capture), as before.
  - Within constellation, with nothing selected or a dot outside every constellation: always stops the motion, and the next Space lets it go on from where it stopped. A drag in between doesn't bring it back but sets its direction. A selected dot also shows its "not connected" message.
- **Two states:** connections, groups and progress of decks (`temp/cluster_space_state.json`) and of topics and cards (`temp/cluster_state.json`) are separate.

## Start the module build

```bash
.\.venv\Scripts\python.exe modules/cluster/cluster.py
```

If state files exist in `temp/` at startup, the launcher asks once whether to back them up first (`cluster_state.json_01.bak`, `_02.bak`, …) and then start fresh. Without input (a non-interactive start), the existing file is kept. The question is asked once, not again in the debug reloader's child process. State files from before the four stacks (2026-10-25) name other cards: start fresh.

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
