"""Composition root of the helper module (replaces the cluster module's delta/cards.py, which replaces cards.py):
the course model's topics, positions and connections on the cluster module's app (project.model_composition).

Changes against the cluster module's file: the course file (data/topics.json, version 3) is the model's input, and
the app reads the model's derived course file (temp/helper_topics.json, written before compose in the serving
process); the model is fitted and the startup save happens in the serving process only. app.run(debug=True) runs
this file twice, once in the reloader's parent process and once in the child that serves (WERKZEUG_RUN_MAIN); the
parent composes the cluster app on the raw file without the model and must not store its random positions, or the
child would read them as stored positions. The launcher (modules/helper/helper.py) keeps the state files in its
temp/ folder, where the derived file goes too (rebuilt at every serving start, never backed up).
"""

import uuid
from pathlib import Path

from project.model_composition import DERIVED_NAME, compose_model, serving_process

# Application configuration. This file is modules/helper/delta/cards.py: parents[3] is the repository root and
# parents[1] the module folder, whose temp/ the launcher generates.
BASE_DIR = Path(__file__).resolve().parents[3]
TEMP_DIR = Path(__file__).resolve().parents[1] / "temp"
STATE_PATH = BASE_DIR / "data" / "user_state.json"  # card state (topics and cards views); the launcher keeps it as temp/helper_state.json
SPACE_STATE_PATH = BASE_DIR / "data" / "space_state.json"  # decks state (decks view): temp/helper_space_state.json
CARDS_FILE = BASE_DIR / "data" / "topics.json"  # course file, version 3: the model's input, read at startup
DERIVED_FILE = TEMP_DIR / DERIVED_NAME  # the model's topics as the course file the cluster module reads
SERVER_BOOT_ID = uuid.uuid4().hex
RELOADER = True  # app.run restarts the app on code changes; a child process serves (and fits the model)


composition = compose_model(
    BASE_DIR, SERVER_BOOT_ID, CARDS_FILE, STATE_PATH, SPACE_STATE_PATH, fit=serving_process(RELOADER),
    derived_path=DERIVED_FILE,
)
app = composition.dash_app


def main() -> None:
    if serving_process(RELOADER):
        # The startup save writes everything: the checked decks and topics, the shown cards, the positions,
        # connections and groups
        composition.user_state.save()
    app.run(debug=True, use_reloader=RELOADER)


if __name__ == "__main__":
    main()
