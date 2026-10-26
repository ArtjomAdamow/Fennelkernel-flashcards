"""The helper module's composition: the course model's topics, positions and connections on the cluster module's
app (used by delta/cards.py and the tests).

It fits the model on the course file (data/topics.json, version 3: its scripted topics are the model's input),
writes the model's topics as a derived course file in the cluster module's format (temp/helper_topics.json,
services.topic_model) and calls the cluster module's compose (project.composition, the layer below) on that file,
with the model's two position sources instead of the random ones. The cluster module's parser, TopicIndex, dialogs
and state then work unchanged on the model's topics; the topic dots are its own (random in the shell). On a fresh
card state it fills what the model gives (check_everything):
  * every topic's card connections from the clustering (none between topics, and no deck connections: the Helper
    button in the decks view adds those on request);
  * the difficulty groups of the rated quizzes and the predicted groups of the unrated ones (services.difficulty_groups,
    services.difficulty_model);
  * T1's focus: the cards whose margin is below the threshold are left out of the shown cards (the cluster module's
    view settings), once; the Cards dialog shows them again.
Everything else is the cluster module's default: every deck and every topic checked. Stored state wins: a state file
that exists is left as it is, positions, connections, groups and checks included.

The Helper button (the cluster module's module action, left of Random) fills the current view with what the model
gives and the view is missing: the deck connections in the decks view; the entered deck's cards' difficulty and
predicted memberships in the topics view (nothing to connect there); the entered topic's card connections and its
cards' memberships in the cards view. What exists already is kept; a deck unchecked and checked again gets its
connections and memberships back this way, and the generated groups are made the oldest groups again.

The difficulty model D1 (services.difficulty_model) is fitted with the course model, and its metrics are the back of
the card panel (the cluster module's overview_back, layout.difficulty_metrics): with nothing selected, Enter or a
click on the panel turns it over, to the metrics of the course in the decks view, of the entered deck in the topics
view, and of the entered topic's counts with the deck's metrics in the cards view (metrics_back).

The models are fitted in the serving process only (serving_process): with Dash's reloader the launcher's parent
process composes too, but never serves and never saves, so it composes the cluster app on the raw course file
without them.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from project.composition import Composition, compose
from project.content.parser import CardsFile, read_decks
from project.layout.difficulty_metrics import metrics_panel
from project.models import CardLink, Flashcard
from project.services.actions import ModuleAction
from project.services.course_model import CourseModel
from project.services.difficulty_groups import fill_difficulty_groups, fill_predicted_groups
from project.services.difficulty_model import DifficultyReport, fit_difficulty
from project.services.topic_model import scripted_topics, write_derived_course
from project.services.views import CARDS, DECKS, TOPICS
from project.store import state as state_store

HELPER_LABEL = "Helper"
HELPER_TITLE = (
    "Add what the model gives and this view is missing: the deck connections in the decks view; in a deck the "
    "difficulty groups of its cards, rated and predicted; in a topic its card connections and its cards' groups"
)
DERIVED_NAME = "helper_topics.json"  # the model's topics as a course file for the cluster module (temp/)


@dataclass(frozen=True)
class ModelComposition:
    composition: Composition
    model: Optional[CourseModel]  # None when the model was not fitted (the reloader's parent process)
    fresh_cards: bool  # the card state file did not exist before composing
    fresh_decks: bool  # the decks state file did not exist before composing
    action: Optional[ModuleAction] = None  # the Helper button, with the model
    difficulty: Optional[DifficultyReport] = None  # D1's metrics and predictions, with the model
    derived_path: Optional[Path] = None  # the derived course file compose read (None without the model)

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

    @property
    def topics(self):
        return self.composition.topics


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
    """Fit the course model on every card of the course file, seeded by its scripted topics (read_decks gives the
    deck ids). The file is version 3: the cluster module's parser refuses anything else."""
    cards_path = Path(cards_path)
    cards_file = CardsFile(cards_path)
    deck_ids = {deck["name"]: deck["id"] for deck in read_decks(cards_path)}
    return CourseModel(cards_file.load_decks(), deck_ids, scripted_topics(cards_file), vectoriser)


def build_difficulty(cards_path: Path, model: CourseModel) -> DifficultyReport:
    """Measure and fit D1 on the course file's cards, with the course model's similarity index."""
    return fit_difficulty(CardsFile(Path(cards_path)).load_decks(), model.index)


def derive_course(cards_path: Path, derived_path: Path, model: CourseModel) -> Path:
    """Write the model's topics as the course file the cluster module reads (services.topic_model)."""
    return write_derived_course(cards_path, derived_path, model.topic_model.topic_of, hidden=len(model.hidden))


def compose_model(
    base_dir: Path,
    boot_id: str,
    cards_path: Path,
    state_path: Path,
    space_state_path: Path,
    fit: bool = True,
    model: Optional[CourseModel] = None,
    difficulty: Optional[DifficultyReport] = None,
    derived_path: Optional[Path] = None,
) -> ModelComposition:
    """Compose the cluster app on the model's derived course file with the model's positions; fill a fresh card
    state with the generated connections, the difficulty groups and T1's focus. With fit=False and no model, the
    app is the cluster module's on the raw course file (random positions, no Helper button, no back of the card
    panel), and nothing is written. D1 is fitted with the model unless given. `derived_path` is where the derived
    course file goes (the launcher's cards.py passes its temp/); by default next to the requested card state."""
    derived_path = Path(derived_path) if derived_path is not None else Path(state_path).with_name(DERIVED_NAME)
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
        derive_course(cards_path, derived_path, model)
        action = helper_action(model, difficulty)
        composition = compose(
            base_dir, boot_id, derived_path, state_path, space_state_path,
            deck_positions=model.deck_positions, card_positions=model.card_positions, action=action,
            overview_back=lambda state: metrics_back(state, difficulty),
        )
        if fresh_cards:
            check_everything(composition, model, difficulty)
    return ModelComposition(
        composition=composition, model=model, fresh_cards=fresh_cards, fresh_decks=fresh_decks, action=action,
        difficulty=difficulty if model is not None else None, derived_path=derived_path if model is not None else None,
    )


def metrics_back(state, difficulty: DifficultyReport):
    """The back of the card panel: D1's metrics of the course in the decks view, of the entered deck in the topics
    view, and of the entered topic (its counts and predictions with the deck's metrics) in the cards view."""
    if state.view == DECKS:
        return metrics_panel(difficulty)
    if state.view == TOPICS:
        return metrics_panel(difficulty, state.entered_name)
    return metrics_panel(difficulty, state.entered_name, state.entered_topic_info)


def check_everything(composition: Composition, model: CourseModel, difficulty: Optional[DifficultyReport] = None) -> None:
    """The fresh start: the cluster module has checked every deck and every topic itself; the model adds every
    topic's card connections (none between topics, none between decks), leaves T1's hidden cards out of the shown
    cards (once; the Cards dialog shows them again), and fills the difficulty groups of all rated cards and the
    predicted groups of the unrated quizzes (the oldest groups)."""
    router = composition.user_state
    core = composition.core
    hidden = model.hidden
    for name in router.enabled_decks:
        info = router.decks.by_name.get(name)
        if info is None:
            continue
        for topic in composition.topics.topics(info.deck_id):
            add_links(core, model.card_links(topic.deck_id, topic.topic_id))
        card_ids = [card.id for card in core.visible_cards(name) if not composition.topics.is_dot(card.id)]
        if any(card_id in hidden for card_id in card_ids):
            router.settings.set_shown(info.deck_id, [card_id for card_id in card_ids if card_id not in hidden])
    fill_difficulty_groups(core, core.cards)
    if difficulty is not None:
        loaded = {card.id for card in core.cards}
        fill_predicted_groups(core, {card_id: level for card_id, level in difficulty.predictions.items() if card_id in loaded})


def helper_action(model: CourseModel, difficulty: Optional[DifficultyReport] = None) -> ModuleAction:
    """The Helper button of the top bar."""
    return ModuleAction(HELPER_LABEL, lambda state: fill_view(state, model, difficulty), HELPER_TITLE)


def view_cards(state) -> list[Flashcard]:
    """The cards whose memberships the Helper button fills: the entered deck's cards (no topic dots) in the topics
    view, the entered topic's cards (shown or not) in the cards view, none in the decks view."""
    name = state.entered_name
    if state.view == DECKS or not name:
        return []
    cards = [card for card in state.cards_state.visible_cards(name) if not state.is_topic(card.id)]
    if state.view == TOPICS:
        return cards
    topic = state.entered_topic_info
    members = set(topic.card_ids) if topic else set()
    return [card for card in cards if card.id in members]


def fill_view(state, model: CourseModel, difficulty: Optional[DifficultyReport] = None) -> int:
    """The Helper button: the missing connections of the current view (fill_connections) and, in the topics and
    cards views, the missing difficulty memberships of the view's cards, rated and predicted (the generated groups
    become the oldest again). Returns what was added."""
    added = fill_connections(state, model)
    cards = view_cards(state)
    if cards:
        added += fill_difficulty_groups(state.cards_state, cards)
        if difficulty is not None:
            ids = {card.id for card in cards}
            added += fill_predicted_groups(
                state.cards_state, {card_id: level for card_id, level in difficulty.predictions.items() if card_id in ids}
            )
    return added


def fill_connections(state, model: CourseModel) -> int:
    """The Helper button: add the model's connections of the current view that are missing. `state` is the
    ViewRouter; in the decks view the deck connections go into the decks state, in the cards view the entered
    topic's card connections into the card state; the topics view has none (no connections between topics).
    Returns the number of connections added."""
    if state.view == DECKS:
        return add_links(state.decks_state, model.deck_links)
    if state.view == CARDS:
        topic = state.entered_topic_info
        return add_links(state.cards_state, model.card_links(topic.deck_id, topic.topic_id)) if topic else 0
    return 0


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
