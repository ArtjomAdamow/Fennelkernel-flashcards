# Placeholder for user_state_service.py - to be modified for constellations feature
# This file will contain wiring changes for the constellations module
# Based on the original flashcards_app/user_state_service.py but with constellations-specific modifications

"""
User state service for the flashcards application.
"""

from pathlib import Path
from typing import Union

from flashcards_app.state_core import StateCore
from modules.constellations.models import Flashcard
from modules.constellations.deck_catalog import DeckCatalog

# Type alias for deck catalog (will be modified by launcher)
DeckCatalogType = Union[DeckCatalog, "JsonDeckCatalog"]

class UserStateService:
    """Service for managing user state and progress."""
    
    def __init__(self, state_core: StateCore):
        self.state_core = state_core
    
    def get_progress(self, card_id: str) -> dict:
        """Get progress for a specific card."""
        return self.state_core.get_progress(card_id)
    
    def update_progress(self, card_id: str, progress: dict) -> None:
        """Update progress for a specific card."""
        self.state_core.update_progress(card_id, progress)
    
    def get_deck_state(self, deck_name: str) -> dict:
        """Get state for a specific deck."""
        return self.state_core.get_deck_state(deck_name)
    
    def update_deck_state(self, deck_name: str, state: dict) -> None:
        """Update state for a specific deck."""
        self.state_core.update_deck_state(deck_name, state)

# For now, this is a placeholder
# Actual implementation will follow the constellations draft design