Create archive/card_position_fields_note.txt (plain text, not .md) documenting that CardPosition.status and CardPosition.related_ids (models.py:17-18) are persisted in positions.json but never read anywhere in current code — status was meant as an edit-lifecycle marker ("new"/"edited"/"saved"), related_ids was meant as a planned list of related card IDs for a position (distinct from CardLink). No code or data migration now, per your decision.

CardPosition.status and CardPosition.related_ids (flashcards_app/models.py) are persisted in data/positions.json but never read anywhere in current code.

status was intended as an edit-lifecycle marker ("new" / "edited" / "saved") for manual position edits; related_ids was intended as a planned list of related card IDs attached to a position, distinct from CardLink. Neither has been wired up yet.
