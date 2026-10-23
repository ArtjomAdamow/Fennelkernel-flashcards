"""The helper module's composition: the course model's positions and connections on the cluster module's app
(used by delta/cards.py and the tests).

It calls the cluster module's compose (project.composition, the layer below) with the model's two position
sources instead of the random ones, and on a fresh start fills the state:
  * a fresh card state checks all decks and shows all of their cards (the pilot: every card is placed), and gets
    the card connections of every deck from the clustering, the difficulty groups of the rated cards and the
    predicted groups of the unrated quizzes (services.difficulty_groups, services.difficulty_model);
  * a fresh space state gets the deck connections from the clustering.
Stored state wins: a state file that exists is left as it is, positions, connections and groups included.

The Helper button (the cluster module's module action, left of Random) fills the current view with the model's
connections: the entered deck's card connections, difficulty groups and predicted groups in the deck view, the
deck connections in the space view. What exists already is kept; a deck unchecked and checked again gets its
connections and memberships back this way, and the generated groups are made the oldest groups again.

The difficulty model D1 (services.difficulty_model) is fitted with the course model, and its metrics are the back
of the card panel (the cluster module's overview_back, layout.difficulty_metrics): with nothing selected, Enter or
a click on the panel turns it over, to the metrics of all decks in the space view and of the entered deck in the
deck view (metrics_back).

The models are fitted in the serving process only (serving_process): with Dash's reloader the launcher's parent
process composes too, but never serves and never saves, so it composes without them.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from project.composition import Composition, compose
from project.content.parser import CardsFile, read_decks
from project.layout.difficulty_metrics import metrics_panel
from project.models import CardLink
from project.services.actions import ModuleAction
from project.services.course_model import CourseModel
from project.services.difficulty_groups import fill_difficulty_groups, fill_predicted_groups
from project.services.difficulty_model import DifficultyReport, fit_difficulty
from project.services.views import DECK
from project.store import state as state_store

HELPER_LABEL = "Helper"
HELPER_TITLE = (
    "Add the model's connections to this view (the deck's cards here, the decks in the space view), "
    "and in a deck the difficulty groups of its cards, rated and predicted"
)


@dataclass(frozen=True)
class ModelComposition:
    composition: Composition
    model: Optional[CourseModel]  # None when the model was not fitted (the reloader's parent process)
    fresh_cards: bool  # the card state file did not exist before composing
    fresh_decks: bool  # the space state file did not exist before composing
    action: Optional[ModuleAction] = None  # the Helper button, with the model
    difficulty: Optional[DifficultyReport] = None  # D1's metrics and predictions, with the model

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


def build_difficulty(cards_path: Path, model: CourseModel) -> DifficultyReport:
    """Measure and fit D1 on the course file's cards, with the course model's similarity index."""
    return fit_difficulty(CardsFile(Path(cards_path)).load_decks(), model.index)


def compose_model(
    base_dir: Path,
    boot_id: str,
    cards_path: Path,
    state_path: Path,
    space_state_path: Path,
    fit: bool = True,
    model: Optional[CourseModel] = None,
    difficulty: Optional[DifficultyReport] = None,
) -> ModelComposition:
    """Compose the cluster app with the model's positions; fill a fresh state with all decks, all cards, the
    generated connections and the difficulty groups. With fit=False and no model, the app is the cluster module's
    (random positions, no Helper button, no back of the card panel). D1 is fitted with the model unless given."""
    fresh_cards = is_fresh(state_path)
    fresh_decks = is_fresh(space_state_path)
    if fit and model is None:
        model = build_model(cards_path)
    action = None
    if model is None:
        composition = compose(base_dir, boot_id, cards_path, state_path, space_state_path)
    else:
        if difficulty is None:
            difficulty = build_difficulty(cards_path, model)
        action = helper_action(model, difficulty)
        composition = compose(
            base_dir, boot_id, cards_path, state_path, space_state_path,
            deck_positions=model.deck_positions, card_positions=model.card_positions, action=action,
            overview_back=lambda state: metrics_back(state, difficulty),
        )
        if fresh_cards:
            check_everything(composition, model, difficulty)
        if fresh_decks:
            add_links(composition.space_core, model.deck_links)
    return ModelComposition(
        composition=composition, model=model, fresh_cards=fresh_cards, fresh_decks=fresh_decks, action=action,
        difficulty=difficulty if model is not None else None,
    )


def metrics_back(state, difficulty: DifficultyReport):
    """The back of the card panel: D1's metrics of all decks in the space view, of the entered deck in the deck view."""
    return metrics_panel(difficulty, state.entered_name if state.view == DECK else None)


def check_everything(composition: Composition, model: CourseModel, difficulty: Optional[DifficultyReport] = None) -> None:
    """The pilot's fresh start: every deck checked, every card of every deck shown, every deck's connections, the
    difficulty groups of all rated cards and the predicted groups of the unrated quizzes (the oldest groups)."""
    router = composition.user_state
    for name in router.available_decks():
        router.enable_deck(name)  # its cards get the model's positions
    for info in router.decks.infos:
        router.settings.set_shown(info.deck_id, [card.id for card in composition.core.visible_cards(info.name)])
        add_links(composition.core, model.card_links(info.name))
    fill_difficulty_groups(composition.core, composition.core.cards)
    if difficulty is not None:
        loaded = {card.id for card in composition.core.cards}
        fill_predicted_groups(composition.core, {card_id: level for card_id, level in difficulty.predictions.items() if card_id in loaded})


def helper_action(model: CourseModel, difficulty: Optional[DifficultyReport] = None) -> ModuleAction:
    """The Helper button of the top bar."""
    return ModuleAction(HELPER_LABEL, lambda state: fill_view(state, model, difficulty), HELPER_TITLE)


def fill_view(state, model: CourseModel, difficulty: Optional[DifficultyReport] = None) -> int:
    """The Helper button: the missing connections of the current view and, in the deck view, the entered deck's
    missing difficulty memberships, rated and predicted (the generated groups become the oldest again). Returns
    what was added."""
    added = fill_connections(state, model)
    if state.view == DECK:
        cards = state.deck_cards()
        added += fill_difficulty_groups(state.cards_state, cards)
        if difficulty is not None:
            ids = {card.id for card in cards}
            added += fill_predicted_groups(
                state.cards_state, {card_id: level for card_id, level in difficulty.predictions.items() if card_id in ids}
            )
    return added


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
