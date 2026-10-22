"""Composition root of the helper module (replaces the cluster module's delta/cards.py, which replaces cards.py):
the course model's positions and connections on the cluster module's app (project.model_composition).

Changes against the cluster module's file: the model is fitted and the startup save happens in the serving
process only. app.run(debug=True) runs this file twice, once in the reloader's parent process and once in the
child that serves (WERKZEUG_RUN_MAIN); the parent composes without the model and must not store its random
positions, or the child would read them as stored positions. The launcher (modules/helper/helper.py) keeps the
state files in its temp/ folder.
"""

import uuid
from pathlib import Path

from project.model_composition import compose_model, serving_process

# Application configuration. This file is modules/helper/delta/cards.py: parents[3] is the repository root.
BASE_DIR = Path(__file__).resolve().parents[3]
STATE_PATH = BASE_DIR / "data" / "user_state.json"  # card state (deck view); the launcher keeps it as temp/helper_state.json
SPACE_STATE_PATH = BASE_DIR / "data" / "space_state.json"  # deck state (space view): temp/helper_space_state.json
CARDS_FILE = BASE_DIR / "data" / "cards.json"  # course file, read at startup
SERVER_BOOT_ID = uuid.uuid4().hex
RELOADER = True  # app.run restarts the app on code changes; a child process serves (and fits the model)


composition = compose_model(
    BASE_DIR, SERVER_BOOT_ID, CARDS_FILE, STATE_PATH, SPACE_STATE_PATH, fit=serving_process(RELOADER)
)
app = composition.dash_app


def main() -> None:
    if serving_process(RELOADER):
        # The startup save writes everything: the checked decks, the shown cards, the positions and connections
        composition.user_state.save()
    app.run(debug=True, use_reloader=RELOADER)


if __name__ == "__main__":
    main()
