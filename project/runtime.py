"""Hub between the services.

Today there is one service, the user state. Later services (RAG control, comprehension, guidance) join here, so that
flows between them go through this one place and the services never import each other.
Holds no state of its own and does nothing at import time: cards.py builds the services and the hub.
"""

from dataclasses import dataclass

from project.store.user_state_service import UserStateService

# Name of the placeholder deck that shows an empty map on startup (a UI sentinel: no cards belong to it)
NONE_DECK = "None"


@dataclass(frozen=True)
class Runtime:
    user_state: UserStateService
