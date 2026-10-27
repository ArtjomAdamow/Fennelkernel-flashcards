"""Enter and back rules of the three views (no Dash, no state).

The decks view shows the decks, the topics view the topics of the entered deck, the cards view the cards of the
entered topic. Enter goes down one level with the selected dot, back goes up one level with that level's dot
selected:

| key, view               | decks view                  | topics view                              | cards view                               |
|-------------------------|-----------------------------|------------------------------------------|------------------------------------------|
| Enter, dot selected     | enter the selected deck     | enter the selected topic                 | not a view change: the card flips        |
| back, dot selected      | unselect the deck           | unselect the topic                       | unselect the card                        |
| back, nothing selected  | nothing (top level)         | back to the decks view, the deck selected | back to the topics view, the topic selected |

Back (the Backspace key) does nothing while a dialog is open.
"""

from dataclasses import dataclass, replace
from typing import Optional

DECKS = "decks"
TOPICS = "topics"
CARDS = "cards"
LEVELS = (DECKS, TOPICS, CARDS)


@dataclass(frozen=True)
class ViewState:
    view: str = DECKS
    entered: Optional[str] = None  # deck id of the entered deck (topics and cards views)
    entered_topic: Optional[str] = None  # dot id of the entered topic (cards view)
    selected: Optional[str] = None  # the selected dot: a deck id, a topic dot id or a card's comb_id


def enter(current: ViewState) -> Optional[ViewState]:
    """Enter, or a click on the description. None in the cards view: the callback flips the card as before."""
    if current.view == CARDS:
        return None
    if current.selected is None:
        return current
    if current.view == DECKS:
        return ViewState(TOPICS, entered=current.selected)
    return ViewState(CARDS, entered=current.entered, entered_topic=current.selected)


def back(current: ViewState, dialog_open: bool = False) -> ViewState:
    """The back key: unselect the dot, or with nothing selected go up one level with that level's dot selected."""
    if dialog_open:
        return current
    if current.selected is not None:
        return replace(current, selected=None)
    if current.view == CARDS:
        return ViewState(TOPICS, entered=current.entered, selected=current.entered_topic)
    if current.view == TOPICS:
        return ViewState(DECKS, selected=current.entered)
    return current
