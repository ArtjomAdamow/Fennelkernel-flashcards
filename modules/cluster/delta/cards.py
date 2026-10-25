"""Composition root of the cluster module (replaces cards.py): reads the configuration, builds the services, the
Dash app and its callback (project.composition), starts the server.

Changes against the main file: two state files (cards and decks) instead of one, and the ViewRouter as the
state the app works with. The launcher (modules/cluster/cluster.py) keeps both files in its temp/ folder.
The course is data/topics.json, the version 3 file with topics (decks 01 to 24, written by scripts/topics.py),
read by the module's parser (delta/project/content/parser.py), which reads version 2 too.
"""

import uuid
from pathlib import Path

from project.composition import compose

# Application configuration. This file is modules/cluster/delta/cards.py: parents[3] is the repository root.
BASE_DIR = Path(__file__).resolve().parents[3]
STATE_PATH = BASE_DIR / "data" / "user_state.json"  # card state (cards view); the launcher keeps it as temp/cluster_state.json
SPACE_STATE_PATH = BASE_DIR / "data" / "space_state.json"  # deck state (decks view): temp/cluster_space_state.json
CARDS_FILE = BASE_DIR / "data" / "topics.json"  # course file, version 3, read at startup
SERVER_BOOT_ID = uuid.uuid4().hex


composition = compose(BASE_DIR, SERVER_BOOT_ID, CARDS_FILE, STATE_PATH, SPACE_STATE_PATH)
app = composition.dash_app


def main() -> None:
    # The startup save writes everything, including the checked decks
    composition.user_state.save()
    app.run(debug=True)


if __name__ == "__main__":
    main()
