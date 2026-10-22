"""A module action: one button in the top bar, left of Random, that runs a function on the state (no Dash here).

A module on top of this one (the helper) passes a ModuleAction to compose. The server draws the button with its
label (hidden when there is no action, so the callback's input always exists), and the callback runs `run(state)`
when it is clicked, then saves and redraws like any other change. `state` is the ViewRouter: `run` can read the
view, the entered deck and the two services (cards_state, space).
"""

from dataclasses import dataclass
from typing import Callable

ACTION_ID = "module-action"


@dataclass(frozen=True)
class ModuleAction:
    label: str
    run: Callable[[object], object]  # run(state) -> ignored
    title: str = ""  # the button's hover text
