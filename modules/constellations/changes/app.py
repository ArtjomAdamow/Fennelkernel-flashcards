# Placeholder for app.py - to be modified for constellations feature
# This file will contain wiring changes for the constellations module
# Based on the original flashcards_app/app.py but with constellations-specific modifications

# For now, this is a placeholder that mirrors the structure
# Actual implementation will follow the constellations draft design

"""
Flashcards application entry point.
"""

import os
import sys
from pathlib import Path

# Add the project root to sys.path so we can import flashcards_app
ROOT = Path(__file__).resolve().parents[2]  # Go up to project root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Import the actual app from the project (will be rerouted by launcher)
# This file will be modified by the constellations launcher to use constellations components
from flashcards_app.app import main

if __name__ == "__main__":
    main()