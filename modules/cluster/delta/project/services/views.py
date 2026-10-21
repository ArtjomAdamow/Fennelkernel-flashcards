"""Enter and back rules of the two views (no Dash, no state).

The space view shows decks, the deck view the cards of the entered deck. Both behave the same way:

| key, view               | space view                         | deck view                                  |
|-------------------------|------------------------------------|--------------------------------------------|
| Enter, dot selected     | enter the selected deck            | not a view change: the card flips          |
| back, dot selected      | unselect the deck                  | unselect the card                          |
| back, nothing selected  | nothing (top level)                | back to the space view, the deck selected  |

Back (the Backspace key) does nothing while a dialog is open.
"""

from dataclasses import dataclass
from typing import Optional

SPACE = "space"
DECK = "deck"


@dataclass(frozen=True)
class ViewState:
    view: str = SPACE
    entered: Optional[str] = None  # deck id of the entered deck (deck view only)
    selected: Optional[str] = None  # the selected dot: a deck id (space view) or a comb_id (deck view)


def enter(current: ViewState) -> Optional[ViewState]:
    """Enter, or a click on the description. None in the deck view: the callback flips the card as before."""
    if current.view == DECK:
        return None
    if current.selected is None:
        return current
    return ViewState(DECK, entered=current.selected, selected=None)


def back(current: ViewState, dialog_open: bool = False) -> ViewState:
    """The back key: unselect the dot, or with nothing selected leave the deck view."""
    if dialog_open:
        return current
    if current.selected is not None:
        return ViewState(current.view, current.entered, None)
    if current.view == DECK:
        return ViewState(SPACE, None, selected=current.entered)
    return current
