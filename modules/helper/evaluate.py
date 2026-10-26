"""Offline evaluation of the helper's models on the course file. Run it in the module env, from the repository root:

    modules/helper/.venv/Scripts/python.exe modules/helper/evaluate.py [--course data/topics.json] [--part <part>]

What it measures (docs/draft/helper/concept.md, "Metrics"):
  * B0, the random floor: the same-deck precision@5 of the 5 nearest cards at random positions on the sphere's
    surface (as the cluster module places them), over several seeds;
  * M1, the TF-IDF variants: same-deck precision@5 (empty slots count as misses), the precision over the kept
    neighbours, the coverage and the number of distinct recommended cards, without and with the minimum score;
  * M1-map, the chosen model's positions: trustworthiness and top-3 overlap of the deck positions, the mean
    within-topic top-5 overlap of the card positions over the model's topics (and over the topics of decks 17 and
    24), against the SVD start and random positions on the surface; and the time the whole model takes to build;
  * D1, the difficulty model (docs/draft/helper/roadmap.md, step 10): out of fold on the rated quizzes, every
    feature set with the deck shares and with the most likely class, the two baselines, and the predicted levels
    of the unrated quizzes by the deck shares and by the cut points of the rated cards;
  * T1, the topic model (concept.md, "Topic model T1"): the agreement with the scripted topics of the nearest
    centroid rule, of the neighbour rule (the nearest other card of the deck) and of a logistic regression per
    deck, leave-one-out, next to chance by the topic sizes; by stack and per deck; T1's margin table (the cards
    kept at a threshold and their agreement), the coherence per topic, the moved cards and the emptied topics.

Every run appends one row per model and variant to modules/helper/results/results.csv (D1 to difficulty.csv and
T1 to topics.csv: their measures are others), and writes the hand-check candidates to
modules/helper/results/hand_check.md: about 20 cards of decks 17 and 24 with the top-5 neighbours of every variant
combined, to be judged by hand (relevant or not). Marks already in that file are kept, and once a card has a mark,
every variant's hand-judged precision@5 over the judged cards goes into the results as well. `--part similarity`,
`--part difficulty` or `--part topics` runs one part only. results/ is git-ignored: it holds derived course data.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
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
DIFFICULTY_FILE = RESULTS_DIR / "difficulty.csv"
DIFFICULTY_COLUMNS = [
    "date", "model", "variant", "features", "label_rule", "folds", "repeats", "seed",
    "macro_f1", "macro_f1_sd", "balanced_accuracy", "balanced_accuracy_sd", "kappa", "kappa_sd", "accuracy", "accuracy_sd",
    "spearman", "recall_easy", "recall_medium", "recall_hard", "rated", "unrated",
    "predicted_easy", "predicted_medium", "predicted_hard", "seconds", "notes",
]
TOPICS_FILE = RESULTS_DIR / "topics.csv"
TOPICS_COLUMNS = [
    "date", "model", "scope", "cards", "topics", "agreement", "kept_share", "coherence_median", "coherence_below_half",
    "coherence_at_one", "moved", "emptied", "seconds", "notes",
]
MARGINS = (0.0, 0.02, 0.05, 0.10, 0.15)  # the margin table of concept.md
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


def write_rows(rows: list[dict], path: Path = RESULTS_FILE, columns: list[str] = COLUMNS) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        if new_file:
            writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def fmt(value) -> str:
    return "" if value is None or (isinstance(value, float) and math.isnan(value)) else f"{value:.3f}"


def scope_note(deck_ids: dict[str, str]) -> str:
    """The decks of the course file, for the notes column: "decks 01 to 24"."""
    ids = sorted(deck_ids.values())
    return f"decks {ids[0]} to {ids[-1]}" if ids else "no decks"


# --- D1 -------------------------------------------------------------------------------


def difficulty_rows(report, today: str, model: str, variant: str, measures: dict, label_rule: str, note: str, predicted=None) -> dict:
    """One row of difficulty.csv: the measures (name -> (mean, sd)) and, if given, the predicted levels."""
    row = {"date": today, "model": model, "variant": variant, "features": report.feature_set, "label_rule": label_rule,
           "folds": report.folds, "repeats": report.repeats, "seed": 42, "rated": report.rated, "unrated": report.unrated,
           "seconds": f"{report.seconds:.2f}", "notes": note}
    for name, (mean, sd) in measures.items():
        row[name] = fmt(mean)
        if f"{name}_sd" in DIFFICULTY_COLUMNS:
            row[f"{name}_sd"] = fmt(sd)
    if predicted is not None:
        row["predicted_easy"], row["predicted_medium"], row["predicted_hard"] = report.counts(predicted)
    return row


def evaluate_difficulty(cards, today: str, note: str) -> list[dict]:
    """D1: every feature set, out of fold, with the deck shares and with the most likely class; the baselines once;
    the predicted levels of the unrated quizzes by the deck shares and by the cut points."""
    from project.services import similar
    from project.services.difficulty_model import DEFAULT_FEATURES, FEATURE_SETS, fit_difficulty

    index = similar.SimilarityIndex.fit(cards)  # as the app fits it
    rows = []
    for feature_set in FEATURE_SETS:
        report = fit_difficulty(cards, index, feature_set)
        if not report.measured:
            print(f"D1 {feature_set}: {report.note}")
            continue
        chosen = " (chosen)" if feature_set == DEFAULT_FEATURES else ""
        rows.append(difficulty_rows(report, today, "D1", f"{feature_set}{chosen}", report.metrics, "deck shares", note, report.predictions))
        rows.append(difficulty_rows(report, today, "D1", f"{feature_set}{chosen}", report.most_likely, "most likely class", note))
        rows.append(difficulty_rows(report, today, "D1", f"{feature_set}{chosen}", {}, "cut points of the rated cards", note,
                                    report.cut_point_predictions))
        f1, kappa = report.metrics["macro_f1"], report.metrics["kappa"]
        print(f"D1 {feature_set:20s} deck shares: macro-F1 {f1[0]:.3f} ± {f1[1]:.3f}, weighted kappa {kappa[0]:.3f} ± {kappa[1]:.3f}, "
              f"accuracy {report.metrics['accuracy'][0]:.3f}, recall {report.metrics['recall_easy'][0]:.2f} / "
              f"{report.metrics['recall_medium'][0]:.2f} / {report.metrics['recall_hard'][0]:.2f} | most likely class: macro-F1 "
              f"{report.most_likely['macro_f1'][0]:.3f} | {report.unrated} unrated quizzes: {report.predicted_counts} "
              f"(cut points {report.counts(report.cut_point_predictions)}) ({report.seconds:.2f}s)")
        if feature_set == DEFAULT_FEATURES:
            print("   confusion (rows true, columns predicted, shares): "
                  + " | ".join(" ".join(f"{value:.2f}" for value in row) for row in report.confusion))
            parts = [part for part in report.decks.values() if part.measured]
            kappas = [part.metrics["kappa"][0] for part in parts]
            print(f"   per deck ({len(parts)} measured): kappa mean {np.mean(kappas):.2f}, lowest {min(kappas):.2f}, highest {max(kappas):.2f}; "
                  f"accuracy mean {np.mean([part.metrics['accuracy'][0] for part in parts]):.2f}, "
                  f"macro-F1 mean {np.mean([part.metrics['macro_f1'][0] for part in parts]):.2f}")
    if rows:
        for name, measures in report.baselines.items():
            rows.append(difficulty_rows(report, today, "baseline", name, measures, "deck shares" if name == "similarity" else "constant", note))
            print(f"baseline {name:12s} macro-F1 {measures['macro_f1'][0]:.3f} ± {measures['macro_f1'][1]:.3f}, "
                  f"weighted kappa {measures['kappa'][0]:.3f} ± {measures['kappa'][1]:.3f}, accuracy {measures['accuracy'][0]:.3f}")
    return rows


# --- T1 -------------------------------------------------------------------------------


def topic_row(today: str, model: str, scope: str, cards: int, agreement: float, note: str, **extra) -> dict:
    row = {"date": today, "model": model, "scope": scope, "cards": cards, "agreement": fmt(agreement), "notes": note}
    row.update(extra)
    return row


def evaluate_topics(cards, cards_file, deck_ids: dict[str, str], today: str, note: str) -> list[dict]:
    """T1 against the scripted topics, with the neighbour rule, the per-deck logistic regression and chance: by
    course, by stack and per deck; T1's margin table, coherence, moved cards and emptied topics (concept.md)."""
    from project.services import evaluation, similar
    from project.services.topic_model import FOCUS_MARGIN, TopicModel, scripted_topics

    started = time.perf_counter()
    index = similar.SimilarityIndex.fit(cards)
    seeds = scripted_topics(cards_file)
    model = TopicModel(index, seeds)
    t1_seconds = time.perf_counter() - started
    scripted = model.scripted_of
    by_id = {card.id: card for card in cards}
    deck_order = sorted(cards_file.deck_names, key=lambda name: deck_ids.get(name, name))

    started = time.perf_counter()
    nearest: dict[str, str] = {}
    logistic: dict[str, str] = {}
    chance: dict[str, float] = {}
    for deck in deck_order:
        rows = index.rows_of_deck(deck)
        ids = [index.ids[row] for row in rows]
        labels = [scripted[card_id] for card_id in ids]
        vectors = index.vectors[rows]
        nearest.update(zip(ids, evaluation.nearest_labels(vectors, labels)))
        logistic.update(zip(ids, evaluation.leave_one_out_logistic(vectors, labels)))
        chance[deck] = evaluation.chance_by_sizes(labels)
    judges_seconds = time.perf_counter() - started

    def agree(predicted: dict, ids) -> float:
        ids = list(ids)
        return evaluation.agreement([predicted[card_id] for card_id in ids], [scripted[card_id] for card_id in ids])

    def chance_of(ids) -> float:
        ids = list(ids)
        return sum(chance[by_id[card_id].deck] for card_id in ids) / len(ids) if ids else math.nan

    all_ids = list(model.topic_of)
    coherences = [value for value in model.coherence.values() if not math.isnan(value)]
    rows = [
        topic_row(today, "T1", "all", len(all_ids), model.agreement, note, topics=len(seeds), kept_share=fmt(1.0),
                  coherence_median=fmt(float(np.median(coherences))), coherence_below_half=sum(value < 0.5 for value in coherences),
                  coherence_at_one=sum(value >= 1.0 for value in coherences), moved=model.moved, emptied=len(model.emptied),
                  seconds=f"{t1_seconds:.2f}"),
        topic_row(today, "1-NN", "all", len(all_ids), agree(nearest, all_ids), note, topics=len(seeds)),
        topic_row(today, "LR", "all", len(all_ids), agree(logistic, all_ids), note, topics=len(seeds), seconds=f"{judges_seconds:.2f}"),
        topic_row(today, "chance", "all", len(all_ids), chance_of(all_ids), note, topics=len(seeds)),
    ]
    print(f"T1 nearest centroid: agreement {model.agreement:.3f} over {len(all_ids)} cards in {len(seeds)} topics | "
          f"1-NN {agree(nearest, all_ids):.3f} | LR per deck {agree(logistic, all_ids):.3f} | chance {chance_of(all_ids):.3f} "
          f"(T1 {t1_seconds:.2f}s, the judges {judges_seconds:.2f}s)")
    print(f"   {model.moved} cards elsewhere ({model.moved / len(all_ids):.0%}), {len(model.emptied)} topics emptied; coherence median "
          f"{np.median(coherences):.2f}, {sum(value < 0.5 for value in coherences)} topics below 0.5, {sum(value >= 1.0 for value in coherences)} at 1.0; "
          f"FOCUS_MARGIN {FOCUS_MARGIN} hides {len(model.hidden)} cards")
    for stack in sorted({card.stack for card in cards}):
        ids = [card_id for card_id in all_ids if by_id[card_id].stack == stack]
        rows.append(topic_row(today, "T1", f"stack {stack}", len(ids), model.agreement_of(ids), note))
        print(f"   stack {stack}: T1 {model.agreement_of(ids):.3f} over {len(ids)} cards")
    print("   | Deck | Cards | Topics | T1 | 1-NN | LR | Chance |")
    print("   |---|---|---|---|---|---|---|")
    for deck in deck_order:
        ids = [card_id for card_id in all_ids if by_id[card_id].deck == deck]
        topics = len([seed for seed in seeds if seed.deck == deck])
        scope = f"deck {deck_ids.get(deck, '')} {deck}"
        values = (model.agreement_of(ids), agree(nearest, ids), agree(logistic, ids), chance_of(ids))
        for name, value in zip(("T1", "1-NN", "LR", "chance"), values):
            rows.append(topic_row(today, name, scope, len(ids), value, note, topics=topics))
        print(f"   | {deck_ids.get(deck, '')} {deck} | {len(ids)} | {topics} | " + " | ".join(f"{value:.2f}" for value in values) + " |")
    print("   | Margin at least | Share of the course | Agreement among them |")
    for threshold in MARGINS:
        share, agreement = model.kept(threshold)
        rows.append(topic_row(today, "T1", f"margin >= {threshold:.2f}", round(share * len(all_ids)), agreement, note, kept_share=fmt(share)))
        print(f"   | {threshold:.2f} | {share:.0%} | {agreement:.3f} |")
    return rows


# --- the hand check -------------------------------------------------------------------


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


def write_hand_check(cards, by_id, indexes: dict[str, object], seen_today: str, marks: dict[str, set[str]], note: str) -> int:
    """The combined candidates of all variants for the hand check, as a markdown checklist; existing marks stay."""
    lines = [
        "# Hand check: related cards of decks 17 and 24",
        "",
        f"Written by evaluate.py on {seen_today} ({note}). For every card below, mark every candidate that is a "
        "genuinely related card for a learner (the same concept, a prerequisite, or the natural next card): put `x` "
        "in its `[ ]`, as many or as few as apply; leave the others empty. If no candidate fits, mark the `none` "
        "line. A card without any mark counts as not judged yet. The columns say which variants listed the "
        "candidate, with the cosine. Later runs keep the marks and compute every variant's hand-judged precision@5 "
        "from them.",
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


# --- the similarity models and the map ------------------------------------------------


def evaluate_similarity(cards, cards_file, deck_ids: dict[str, str], today: str, note: str, marks: dict[str, set[str]]) -> tuple[list[dict], dict]:
    """B0, the M1 variants and M1-map (the deck layout and the per-topic card layouts of the chosen model)."""
    from project.services import evaluation, layout, similar
    from project.services.course_model import CARD_NEIGHBOURS, DECK_NEIGHBOURS, CourseModel
    from project.services.positions import surface_positions
    from project.services.topic_model import scripted_topics

    by_id = {card.id: card for card in cards}
    deck_of = {card.id: card.deck for card in cards}
    ids = [card.id for card in cards]
    rows: list[dict] = []

    # B0: the random floor
    floors = [evaluation.random_floor(ids, deck_of, seed) for seed in SEEDS]
    for seed, floor in zip(SEEDS, floors):
        rows.append({"date": today, "model": "B0", "variant": "random positions, 5 nearest", "params": "surface_positions",
                     "seed": seed, "precision_at_5": fmt(floor), "notes": note})
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
                     "notes": f"precision with min_score {similar.MIN_SCORE}: {kept_precision:.3f}; {note}"})
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

    # M1-map: the chosen model's positions (the deck layout and the card layouts per model topic)
    started = time.perf_counter()
    model = CourseModel(cards, deck_ids, scripted_topics(cards_file))
    seconds = time.perf_counter() - started
    start = layout.svd_start(model.deck_vectors)
    random_decks = np.array([[p.x, p.y, p.z] for p in surface_positions(list(model.deck_points), 42)])
    deck_measures = {
        "model": (model.deck_trustworthiness, model.deck_overlap),
        "SVD start": (layout.trustworthiness_score(model.deck_vectors, start, DECK_NEIGHBOURS), layout.neighbour_overlap(model.deck_vectors, start, DECK_NEIGHBOURS)),
        "random": (layout.trustworthiness_score(model.deck_vectors, random_decks, DECK_NEIGHBOURS), layout.neighbour_overlap(model.deck_vectors, random_decks, DECK_NEIGHBOURS)),
    }
    kinds = ("model", "SVD start", "random")
    topic_overlaps = {kind: [] for kind in kinds}
    per_deck: dict[str, dict[str, list]] = {}
    row_of = {card_id: row for row, card_id in enumerate(model.index.ids)}
    laid_out = 0
    for placed in model.topics.values():
        if len(placed.ids) < 2:
            continue
        laid_out += 1
        vectors = layout.as_dense(model.index.vectors[[row_of[card_id] for card_id in placed.ids]])
        points = np.array([placed.positions[card_id] for card_id in placed.ids])
        svd = layout.svd_start(vectors)
        random_cards = np.array([[p.x, p.y, p.z] for p in surface_positions(placed.ids, 42)])
        k = min(CARD_NEIGHBOURS, len(placed.ids) - 1)
        values = (
            layout.neighbour_overlap(vectors, points, k),
            layout.neighbour_overlap(vectors, svd, k),
            layout.neighbour_overlap(vectors, random_cards, k),
        )
        for kind, value in zip(kinds, values):
            topic_overlaps[kind].append(value)
            per_deck.setdefault(placed.deck, {kind: [] for kind in kinds})[kind].append(value)
    for kind in kinds:
        trust, overlap = deck_measures[kind]
        mean_cards = float(np.nanmean(topic_overlaps[kind])) if topic_overlaps[kind] else math.nan
        overlap_17 = float(np.nanmean(per_deck["NLP Fundamentals"][kind])) if "NLP Fundamentals" in per_deck else math.nan
        overlap_24 = float(np.nanmean(per_deck["LLM Foundations & Embeddings"][kind])) if "LLM Foundations & Embeddings" in per_deck else math.nan
        rows.append({"date": today, "model": "M1-map", "variant": kind, "params": f"k_decks={DECK_NEIGHBOURS}, k_cards=min({CARD_NEIGHBOURS}, n-1), "
                     f"iterations={layout.ITERATIONS}, step={layout.STEP}, repulsion={layout.REPULSION}", "seed": 42 if kind == "random" else "",
                     "trust_decks": fmt(trust), "overlap_decks": fmt(overlap), "overlap_cards": fmt(mean_cards),
                     "overlap_17": fmt(overlap_17), "overlap_24": fmt(overlap_24),
                     "seconds": f"{seconds:.2f}" if kind == "model" else "",
                     "notes": f"deck layout and card layouts per model topic ({laid_out} topics with two cards or more); {note}"})
        print(f"M1-map {kind:10s} decks: trustworthiness {trust:.3f}, top-3 overlap {overlap:.3f} | cards: mean within-topic overlap "
              f"{mean_cards:.3f}, deck 17 {overlap_17:.3f}, deck 24 {overlap_24:.3f}")
    print(f"the whole model (index, deck layout, T1, {laid_out} topic layouts, clustering) built in {seconds:.2f}s; "
          f"{sum(len(placed.links) for placed in model.topics.values())} card connections, {len(model.deck_links)} deck connections, "
          f"{len(model.hidden)} cards hidden")
    return rows, indexes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--course", default=None, help="the course file (default: data/topics.json of the repository)")
    parser.add_argument("--part", choices=("all", "similarity", "difficulty", "topics"), default="all",
                        help="the similarity models (B0, M1, M1-map), the difficulty model D1, the topic model T1, or all (default)")
    arguments = parser.parse_args()

    launcher = install_launcher()
    from project.content.parser import CardsFile, read_decks

    course = Path(arguments.course) if arguments.course else launcher.ROOT / "data" / "topics.json"
    cards_file = CardsFile(course)
    cards = cards_file.load_decks()
    by_id = {card.id: card for card in cards}
    deck_ids = {deck["name"]: deck["id"] for deck in read_decks(course)}
    note = scope_note(deck_ids)
    today = date.today().isoformat()
    marks = read_hand_check()
    print(f"{len(cards)} cards in {len(deck_ids)} decks ({course}, {note}); hand-check marks for {len(marks)} cards")

    # T1: the topic model, into its own file
    if arguments.part in ("all", "topics"):
        topics = evaluate_topics(cards, cards_file, deck_ids, today, note)
        write_rows(topics, TOPICS_FILE, TOPICS_COLUMNS)
        print(f"{len(topics)} rows appended to {TOPICS_FILE}")
    # D1: the difficulty model, into its own file
    if arguments.part in ("all", "difficulty"):
        difficulty = evaluate_difficulty(cards, today, note)
        write_rows(difficulty, DIFFICULTY_FILE, DIFFICULTY_COLUMNS)
        print(f"{len(difficulty)} rows appended to {DIFFICULTY_FILE}")
    if arguments.part not in ("all", "similarity"):
        return

    rows, indexes = evaluate_similarity(cards, cards_file, deck_ids, today, note, marks)
    write_rows(rows)
    listed = write_hand_check(cards, by_id, indexes, today, marks, note)
    print(f"{len(rows)} rows appended to {RESULTS_FILE}; hand check for {listed} cards in {HAND_CHECK_FILE}"
          + (f" ({len(marks)} judged, marks kept)" if marks else " (no marks yet)"))


if __name__ == "__main__":
    main()
