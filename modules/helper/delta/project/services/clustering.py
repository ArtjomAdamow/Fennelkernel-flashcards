"""Connections from a hierarchical clustering (no Dash, no state).

scipy's average-linkage clustering on the cosine distances of a set of unit vectors gives a tree of merges. Each
merge becomes one connection between the two closest members of the two merged clusters, in merge order. The
cluster module's dendrogram replays stored connections in that order (services.dendrogram.build_forest): a
connection joins the two trees its ends belong to, which at that point are exactly the two clusters scipy merged.
So the connections give the same tree as scipy's, with the merge ranks as heights, and the cluster module needs no
scipy itself.
"""

from typing import Sequence

import numpy as np
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform

from project.services.layout import as_dense

METHOD = "average"


def cosine_distances(vectors) -> np.ndarray:
    """The dense matrix of cosine distances (1 - cosine) between the rows; a row of zeros is at distance 1 from
    everything. Symmetric, zero on the diagonal, values in [0, 2]."""
    matrix = as_dense(vectors)
    lengths = np.linalg.norm(matrix, axis=1, keepdims=True)
    units = np.divide(matrix, lengths, out=np.zeros_like(matrix), where=lengths > 0)
    distances = np.clip(1.0 - units @ units.T, 0.0, 2.0)
    distances = (distances + distances.T) / 2
    np.fill_diagonal(distances, 0.0)
    return distances


def merge_links(ids: Sequence[str], vectors, method: str = METHOD) -> list[tuple[str, str]]:
    """One connection per merge of the clustering, in merge order: the closest pair of the two merged clusters.
    Ties go to the lowest row indices, so the result is deterministic. Fewer than two ids give no connection."""
    ids = list(ids)
    count = len(ids)
    if count < 2:
        return []
    distances = cosine_distances(vectors)
    merges = linkage(squareform(distances, checks=False), method=method)
    clusters: dict[int, list[int]] = {row: [row] for row in range(count)}
    links: list[tuple[str, str]] = []
    for step, (left, right, _distance, _size) in enumerate(merges):
        first, second = clusters.pop(int(left)), clusters.pop(int(right))
        block = distances[np.ix_(first, second)]
        row, column = np.unravel_index(int(np.argmin(block)), block.shape)
        links.append((ids[first[row]], ids[second[column]]))
        clusters[count + step] = first + second
    return links
