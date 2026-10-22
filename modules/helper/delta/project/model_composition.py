"""The helper module's composition: the course model's positions and connections on the cluster module's app
(used by delta/cards.py and the tests).

It calls the cluster module's compose (project.composition, the layer below) with the model's two position
sources instead of the random ones, and on a fresh start fills the state:
  * a fresh card state checks all decks and shows all of their cards (the pilot: every card is placed), and gets
    the card connections of every deck from the clustering;
  * a fresh space state gets the deck connections from the clustering.
Stored state wins: a state file that exists is left as it is, positions and connections included.

The Helper button (the cluster module's module action, left of Random) fills the current view with the model's
connections: the entered deck's card connections in the deck view, the deck connections in the space view.
Connections that exist already are kept; a deck unchecked and checked again gets its connections back this way.

The model is fitted in the serving process only (serving_process): with Dash's reloader the launcher's parent
process composes too, but never serves and never saves, so it composes without the model.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from project.composition import Composition, compose
from project.content.parser import CardsFile, read_decks
from project.models import CardLink
from project.services.actions import ModuleAction
from project.services.course_model import CourseModel
from project.services.views import DECK
from project.store import state as state_store

HELPER_LABEL = "Helper"
HELPER_TITLE = "Add the model's connections to this view: the deck's cards here, the decks in the space view"


@dataclass(frozen=True)
class ModelComposition:
    composition: Composition
    model: Optional[CourseModel]  # None when the model was not fitted (the reloader's parent process)
    fresh_cards: bool  # the card state file did not exist before composing
    fresh_decks: bool  # the space state file did not exist before composing
    action: Optional[ModuleAction] = None  # the Helper button, with the model

    @property
    def user_state(self):
        return self.composition.user_state

    @property
    def dash_app(self):
        return self.composition.dash_app

    @property
    def core(self):
        return self.composition.core

    @property
    def space_core(self):
        return self.composition.space_core


def serving_process(reloader: bool = True, environ: Mapping[str, str] = os.environ) -> bool:
    """Whether this process serves the app. With Dash's reloader (app.run(debug=True)) the parent process only
    watches for changes and the child (WERKZEUG_RUN_MAIN) serves; without the reloader, this process serves."""
    return not reloader or environ.get("WERKZEUG_RUN_MAIN") == "true"


def is_fresh(state_path: Path) -> bool:
    """Whether the state file is still to be written. Asked through the store, not the path: the launcher
    redirects the store by the requested file name to its temp/ folder, where the file may not exist even though
    the requested path (data/user_state.json of the main project) does."""
    return state_store.JsonStateStore(state_path).read() is None


def build_model(cards_path: Path, vectoriser=None) -> CourseModel:
    """Fit the course model on every card of the course file (read_decks gives the deck ids)."""
    cards_path = Path(cards_path)
    cards = CardsFile(cards_path).load_decks()
    deck_ids = {deck["name"]: deck["id"] for deck in read_decks(cards_path)}
    return CourseModel(cards, deck_ids, vectoriser)


def compose_model(
    base_dir: Path,
    boot_id: str,
    cards_path: Path,
    state_path: Path,
    space_state_path: Path,
    fit: bool = True,
    model: Optional[CourseModel] = None,
) -> ModelComposition:
    """Compose the cluster app with the model's positions; fill a fresh state with all decks, all cards and the
    generated connections. With fit=False and no model, the app is the cluster module's (random positions)."""
    fresh_cards = is_fresh(state_path)
    fresh_decks = is_fresh(space_state_path)
    if fit and model is None:
        model = build_model(cards_path)
    action = None
    if model is None:
        composition = compose(base_dir, boot_id, cards_path, state_path, space_state_path)
    else:
        action = helper_action(model)
        composition = compose(
            base_dir, boot_id, cards_path, state_path, space_state_path,
            deck_positions=model.deck_positions, card_positions=model.card_positions, action=action,
        )
        if fresh_cards:
            check_everything(composition, model)
        if fresh_decks:
            add_links(composition.space_core, model.deck_links)
    return ModelComposition(
        composition=composition, model=model, fresh_cards=fresh_cards, fresh_decks=fresh_decks, action=action
    )


def check_everything(composition: Composition, model: CourseModel) -> None:
    """The pilot's fresh start: every deck checked, every card of every deck shown, every deck's connections."""
    router = composition.user_state
    for name in router.available_decks():
        router.enable_deck(name)  # its cards get the model's positions
    for info in router.decks.infos:
        router.settings.set_shown(info.deck_id, [card.id for card in composition.core.visible_cards(info.name)])
        add_links(composition.core, model.card_links(info.name))


def helper_action(model: CourseModel) -> ModuleAction:
    """The Helper button of the top bar."""
    return ModuleAction(HELPER_LABEL, lambda state: fill_connections(state, model), HELPER_TITLE)


def fill_connections(state, model: CourseModel) -> int:
    """The Helper button: add the model's connections of the current view that are missing. `state` is the
    ViewRouter; in the deck view the entered deck's card connections go into the card state, in the space view
    the deck connections into the space state. Returns the number of connections added."""
    if state.view == DECK:
        name = state.entered_name
        return add_links(state.cards_state, model.card_links(name)) if name else 0
    return add_links(state.space, model.deck_links)


def add_links(core, pairs) -> int:
    """Append generated connections in order, skipping pairs that exist already (in either direction). The
    existence check of create_link (a scan of all stored links per call) is done once here; the list is changed
    in place, as always. `core` is anything with a live `links` list (a StateCore or a UserStateService)."""
    known = {frozenset(link_pair) for link_pair in ((link.source_id, link.target_id) for link in core.links)}
    added = 0
    for source, target in pairs:
        if source == target or frozenset((source, target)) in known:
            continue
        core.links.append(CardLink(source, target))
        known.add(frozenset((source, target)))
        added += 1
    return added
