"""Offline evaluation of the helper's models on the course file. Run it in the module env, from the repository root:

    modules/helper/.venv/Scripts/python.exe modules/helper/evaluate.py [--course data/cards.json]

What it measures (docs/draft/helper/early.md, "Metrics"):
  * B0, the random floor: the same-deck precision@5 of the 5 nearest cards at random positions, over several seeds;
  * M1, the TF-IDF variants: same-deck precision@5 (empty slots count as misses), the precision over the kept
    neighbours, the coverage and the number of distinct recommended cards, without and with the minimum score;
  * M1-map, the chosen model's positions: trustworthiness and top-3 overlap of the 48 deck positions, the mean
    within-deck top-5 overlap of the card positions (and decks 17 and 24), against the SVD start and random
    positions; and the time the whole model takes to build.

Every run appends one row per model and variant to modules/helper/results/results.csv, and writes the hand-check
candidates to modules/helper/results/hand_check.md: about 20 cards of decks 17 and 24 with the top-5 neighbours of
every variant combined, to be judged by hand (relevant or not). Marks already in that file are kept, and once a
card has a mark, every variant's hand-judged precision@5 over the judged cards goes into the results as well.
results/ is git-ignored: it holds derived course data.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True  # as in the launcher: no __pycache__ next to the module's sources

MODULE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = MODULE_DIR / "results"
RESULTS_FILE = RESULTS_DIR / "results.csv"
HAND_CHECK_FILE = RESULTS_DIR / "hand_check.md"
SEEDS = (42, 1, 2, 3, 4)
HAND_CHECK_DECKS = {"NLP Fundamentals": 4, "LLM Foundations & Embeddings": 3}  # deck -> every n-th card
COLUMNS = [
    "date", "model", "variant", "params", "seed", "precision_at_5", "kept_precision", "coverage", "distinct",
    "hand_precision", "judged_cards", "trust_decks", "overlap_decks", "overlap_cards", "overlap_17", "overlap_24",
    "seconds", "notes",
]
MARKED = re.compile(r"^- \[([xX])\] (\S+) \(")
NONE_RELEVANT = re.compile(r"^- \[[xX]\] none\b")  # judged: no candidate of this card is relevant
HEADING = re.compile(r"^## (\S+) \(")


def install_launcher():
    """Load helper.py as helper_launcher and install its layered import hook (as the tests do)."""
    if "helper_launcher" not in sys.modules:
        spec = importlib.util.spec_from_file_location("helper_launcher", MODULE_DIR / "helper.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["helper_launcher"] = module
        spec.loader.exec_module(module)
    launcher = sys.modules["helper_launcher"]
    if not any(isinstance(finder, launcher.DeltaFinder) for finder in sys.meta_path):
        launcher.install_delta_finder()
    return launcher


def variants():
    """The vectoriser variants of the roadmap (step 3) plus the chosen settings."""
    from project.services import similar

    return [
        ("unigrams, min_df=2", dict(ngram_range=(1, 1), min_df=2, sublinear_tf=False), False),
        ("uni+bigrams, min_df=1", dict(ngram_range=(1, 2), min_df=1, sublinear_tf=False), False),
        ("uni+bigrams, min_df=2", dict(ngram_range=(1, 2), min_df=2, sublinear_tf=False), False),
        ("uni+bigrams, min_df=3", dict(ngram_range=(1, 2), min_df=3, sublinear_tf=False), False),
        ("uni+bigrams, min_df=2, explain", dict(ngram_range=(1, 2), min_df=2, sublinear_tf=False), True),
        ("uni+bigrams, min_df=2, sublinear", dict(ngram_range=(1, 2), min_df=2, sublinear_tf=True), False),
        (
            "chosen: uni+bigrams, min_df=2, sublinear, explain",
            dict(ngram_range=similar.NGRAM_RANGE, min_df=similar.MIN_DF, sublinear_tf=similar.SUBLINEAR_TF),
            similar.WITH_EXPLAIN,
        ),
    ]


def write_rows(rows: list[dict]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    new_file = not RESULTS_FILE.exists()
    with RESULTS_FILE.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in COLUMNS})


def fmt(value) -> str:
    return "" if value is None or (isinstance(value, float) and np.isnan(value)) else f"{value:.3f}"


def hand_check_cards(cards):
    """About 20 cards of the two NLP decks: every n-th card of each, in deck order."""
    chosen = []
    for deck, step in HAND_CHECK_DECKS.items():
        members = [card for card in cards if card.deck == deck]
        chosen.extend(members[::step])
    return chosen


def short(text: str, length: int = 90) -> str:
    text = " ".join(text.replace("`", "").replace("**", "").split())
    return text if len(text) <= length else text[: length - 1] + "…"


def read_hand_check(path: Path = HAND_CHECK_FILE) -> dict[str, set[str]]:
    """The marks of the hand-check file: card id -> the candidate ids marked `[x]` under it. Only judged cards are
    in the result: cards with at least one mark, or with the `- [x] none` line marked (no candidate is relevant);
    a card without any mark counts as not judged yet."""
    if not path.exists():
        return {}
    marks: dict[str, set[str]] = {}
    card_id = None
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = HEADING.match(line)
        if heading:
            card_id = heading.group(1)
            continue
        if card_id and NONE_RELEVANT.match(line):
            marks.setdefault(card_id, set())
            continue
        marked = MARKED.match(line)
        if marked and card_id:
            marks.setdefault(card_id, set()).add(marked.group(2))
    return marks


def hand_precision(neighbours: dict[str, list], marks: dict[str, set[str]], k: int = 5) -> float:
    """Hand-judged precision@k over the judged cards: the share of a variant's top-k neighbours that are marked."""
    if not marks:
        return float("nan")
    shares = [sum(other in marked for other, _ in neighbours.get(card_id, [])[:k]) / k for card_id, marked in marks.items()]
    return float(np.mean(shares))


def write_hand_check(cards, by_id, indexes: dict[str, object], seen_today: str, marks: dict[str, set[str]]) -> int:
    """The combined candidates of all variants for the hand check, as a markdown checklist; existing marks stay."""
    lines = [
        "# Hand check: related cards of decks 17 and 24",
        "",
        f"Written by evaluate.py on {seen_today}. For every card below, mark every candidate that is a genuinely "
        "related card for a learner (the same concept, a prerequisite, or the natural next card): put `x` in its "
        "`[ ]`, as many or as few as apply; leave the others empty. If no candidate fits, mark the `none` line. "
        "A card without any mark counts as not judged yet. The columns say which variants listed the candidate, "
        "with the cosine. Later runs keep the marks and compute every variant's hand-judged precision@5 from them.",
        "",
    ]
    names = list(indexes)
    for card in hand_check_cards(cards):
        lines.append(f"## {card.id} ({card.deck}): {short(card.question)}")
        lines.append("")
        candidates: dict[str, dict[str, float]] = {}
        for name, index in indexes.items():
            for other, score in index.related(card.id):
                candidates.setdefault(other, {})[name] = score
        ordered = sorted(candidates, key=lambda other: (-len(candidates[other]), -max(candidates[other].values())))
        for other in ordered:
            columns = ", ".join(f"{name}: {candidates[other][name]:.2f}" for name in names if name in candidates[other])
            box = "[x]" if other in marks.get(card.id, set()) else "[ ]"
            lines.append(f"- {box} {other} ({by_id[other].deck}): {short(by_id[other].question)}  —  {columns}")
        judged_none = card.id in marks and not marks[card.id]
        lines.append(f"- {'[x]' if judged_none else '[ ]'} none of these is relevant")
        lines.append("")
    HAND_CHECK_FILE.write_text("\n".join(lines), encoding="utf-8")
    return len(hand_check_cards(cards))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--course", default=None, help="the course file (default: data/cards.json of the repository)")
    arguments = parser.parse_args()

    launcher = install_launcher()
    from project.content.parser import CardsFile, read_decks
    from project.services import evaluation, layout, similar
    from project.services.course_model import CARD_NEIGHBOURS, DECK_NEIGHBOURS, CourseModel
    from project.services.geometry import sphere_positions
    from project.services.positions import shell_positions

    course = Path(arguments.course) if arguments.course else launcher.ROOT / "data" / "cards.json"
    cards = CardsFile(course).load_decks()
    by_id = {card.id: card for card in cards}
    deck_of = {card.id: card.deck for card in cards}
    deck_ids = {deck["name"]: deck["id"] for deck in read_decks(course)}
    ids = [card.id for card in cards]
    today = date.today().isoformat()
    rows: list[dict] = []
    marks = read_hand_check()
    print(f"{len(cards)} cards in {len(deck_ids)} decks ({course}); hand-check marks for {len(marks)} cards")

    # B0: the random floor
    floors = [evaluation.random_floor(ids, deck_of, seed) for seed in SEEDS]
    for seed, floor in zip(SEEDS, floors):
        rows.append({"date": today, "model": "B0", "variant": "random positions, 5 nearest", "params": "sphere_positions",
                     "seed": seed, "precision_at_5": fmt(floor)})
    print(f"B0 random floor: same-deck precision@5 {np.mean(floors):.3f} ± {np.std(floors):.3f} over seeds {SEEDS}")

    # M1: the vectoriser variants, without and with the minimum score
    indexes = {}
    for name, options, with_explain in variants():
        started = time.perf_counter()
        index = similar.SimilarityIndex.fit(cards, similar.tfidf_vectoriser(**options), min_score=0.0, with_explain=with_explain)
        seconds = time.perf_counter() - started
        precision = evaluation.same_deck_precision(index.neighbours, deck_of)
        kept = similar.top_neighbours(ids, similar.cosine_similarities(index.vectors), similar.TOP_K, similar.MIN_SCORE)
        kept_precision = evaluation.same_deck_precision(kept, deck_of)
        kept_only = evaluation.kept_precision(kept, deck_of)
        covered, distinct = evaluation.coverage(kept)
        params = f"{options}, explain={with_explain}, vocab={len(index.vectoriser.vocabulary_)}"
        judged = hand_precision(kept, marks)
        rows.append({"date": today, "model": "M1", "variant": name, "params": params, "seed": "",
                     "precision_at_5": fmt(precision), "kept_precision": fmt(kept_only), "coverage": fmt(covered),
                     "distinct": distinct, "hand_precision": fmt(judged), "judged_cards": len(marks) if marks else "",
                     "seconds": f"{seconds:.2f}",
                     "notes": f"precision with min_score {similar.MIN_SCORE}: {kept_precision:.3f}"})
        print(f"M1 {name:52s} precision@5 {precision:.3f} | min_score {similar.MIN_SCORE}: precision {kept_precision:.3f}, "
              f"kept-slot precision {kept_only:.3f}, coverage {covered:.3f}, distinct {distinct}, vocab {len(index.vectoriser.vocabulary_)}"
              + (f", hand-judged precision@5 {judged:.3f} over {len(marks)} cards" if marks else "") + f" ({seconds:.2f}s)")
        indexes[name] = similar.SimilarityIndex(index.ids, index.decks, index.vectors, kept, index.vectoriser)

    # The score distribution of the chosen settings (the basis of MIN_SCORE)
    chosen = indexes[next(reversed(indexes))]
    cosines = similar.cosine_similarities(chosen.vectors)
    np.fill_diagonal(cosines, -1.0)
    top = -np.sort(-cosines, axis=1)[:, : similar.TOP_K]
    for rank in range(similar.TOP_K):
        column = top[:, rank]
        print(f"  score of neighbour {rank + 1}: p10 {np.percentile(column, 10):.3f}, median {np.median(column):.3f}, p90 {np.percentile(column, 90):.3f}")

    # M1-map: the chosen model's positions
    started = time.perf_counter()
    model = CourseModel(cards, deck_ids)
    seconds = time.perf_counter() - started
    start = layout.svd_start(model.deck_vectors)
    random_decks = np.array([[p.x, p.y, p.z] for p in sphere_positions(list(model.deck_points), 42)])
    deck_measures = {
        "model": (model.deck_trustworthiness, model.deck_overlap),
        "SVD start": (layout.trustworthiness_score(model.deck_vectors, start, DECK_NEIGHBOURS), layout.neighbour_overlap(model.deck_vectors, start, DECK_NEIGHBOURS)),
        "random": (layout.trustworthiness_score(model.deck_vectors, random_decks, DECK_NEIGHBOURS), layout.neighbour_overlap(model.deck_vectors, random_decks, DECK_NEIGHBOURS)),
    }
    card_overlaps = {"model": [], "SVD start": [], "random": []}
    per_deck = {}
    for name, deck in model.decks.items():
        vectors = layout.as_dense(model.index.vectors[model.index.rows_of_deck(name)])
        points = np.array([deck.positions[card_id] for card_id in deck.ids])
        svd = layout.svd_start(vectors)
        random_cards = np.array([[p.x, p.y, p.z] for p in shell_positions(deck.ids, 42)])
        values = (
            layout.neighbour_overlap(vectors, points, CARD_NEIGHBOURS),
            layout.neighbour_overlap(vectors, svd, CARD_NEIGHBOURS),
            layout.neighbour_overlap(vectors, random_cards, CARD_NEIGHBOURS),
        )
        per_deck[name] = values
        for key, value in zip(card_overlaps, values):
            card_overlaps[key].append(value)
    for key in ("model", "SVD start", "random"):
        trust, overlap = deck_measures[key]
        mean_cards = float(np.nanmean(card_overlaps[key]))
        overlap_17 = per_deck.get("NLP Fundamentals", (np.nan,) * 3)[["model", "SVD start", "random"].index(key)]
        overlap_24 = per_deck.get("LLM Foundations & Embeddings", (np.nan,) * 3)[["model", "SVD start", "random"].index(key)]
        rows.append({"date": today, "model": "M1-map", "variant": key, "params": f"k_decks={DECK_NEIGHBOURS}, k_cards={CARD_NEIGHBOURS}, "
                     f"iterations={layout.ITERATIONS}, step={layout.STEP}, repulsion={layout.REPULSION}", "seed": 42 if key == "random" else "",
                     "trust_decks": fmt(trust), "overlap_decks": fmt(overlap), "overlap_cards": fmt(mean_cards),
                     "overlap_17": fmt(overlap_17), "overlap_24": fmt(overlap_24),
                     "seconds": f"{seconds:.2f}" if key == "model" else "", "notes": "deck layout and per-deck card layouts"})
        print(f"M1-map {key:10s} decks: trustworthiness {trust:.3f}, top-3 overlap {overlap:.3f} | cards: mean top-5 overlap "
              f"{mean_cards:.3f}, deck 17 {overlap_17:.3f}, deck 24 {overlap_24:.3f}")
    print(f"the whole model (index, deck layout, {len(model.decks)} deck layouts, clustering) built in {seconds:.2f}s; "
          f"{sum(len(deck.links) for deck in model.decks.values())} card connections, {len(model.deck_links)} deck connections")

    write_rows(rows)
    listed = write_hand_check(cards, by_id, indexes, today, marks)
    print(f"{len(rows)} rows appended to {RESULTS_FILE}; hand check for {listed} cards in {HAND_CHECK_FILE}"
          + (f" ({len(marks)} judged, marks kept)" if marks else " (no marks yet)"))


if __name__ == "__main__":
    main()
