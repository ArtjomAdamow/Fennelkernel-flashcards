"""Dendrogram from connections (no Dash, no state).

The stored links of a view are replayed in the order they were made (create_link appends). A link that joins
two separate groups of dots is a merge, with its rank among the merges (1, 2, 3, ...) as height; a link inside
one group (a cycle) adds nothing. The result is a forest with one tree per constellation. Dots without links
are not part of it; without links it is empty.

The merges have the same shape as scipy's linkage output, so connections written in the merge order of a
clustering replay to the same tree.

The cut-off line: a share between 0 and 1 of the tree's height. Below 1, only the merges up to that share of
the merge count are kept (cut_links), so the tree falls apart into the sub-trees below the line, on the map as
separate constellations and in the dendrogram as trees side by side. At 1 (the full tree) every stored link
counts, cycles included.
"""

import math
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple


@dataclass(frozen=True)
class Node:
    height: int  # 0 for a leaf, the merge rank for a merge
    leaf: Optional[str] = None  # the dot id of a leaf
    children: Tuple["Node", ...] = ()  # the two merged subtrees of a merge

    def leaves(self) -> list[str]:
        """The dot ids of the tree, left to right."""
        if self.leaf is not None:
            return [self.leaf]
        return [dot for child in self.children for dot in child.leaves()]


def _replay(dot_ids: Iterable[str], links: Iterable) -> tuple[list[Node], list[Optional[int]]]:
    """Replay the links: the forest, and every link's merge rank (None for a cycle or a link leaving the view)."""
    visible = set(dot_ids)
    parent: dict[str, str] = {}
    tree: dict[str, Node] = {}  # root dot -> its subtree
    started: dict[str, int] = {}  # root dot -> rank of the tree's first merge
    ranks: list[Optional[int]] = []

    def find(dot: str) -> str:
        root = dot
        while parent[root] != root:
            root = parent[root]
        while parent[dot] != root:
            parent[dot], dot = root, parent[dot]
        return root

    rank = 0
    for link in links:
        a, b = link.source_id, link.target_id
        if a == b or a not in visible or b not in visible:
            ranks.append(None)
            continue
        for dot in (a, b):
            if dot not in parent:
                parent[dot] = dot
                tree[dot] = Node(0, leaf=dot)
        first, second = find(a), find(b)
        if first == second:
            ranks.append(None)
            continue  # a cycle: the two dots are joined already
        # The older tree stays on the left; a single dot counts as the newest
        if started.get(second, math.inf) < started.get(first, math.inf):
            first, second = second, first
        rank += 1
        ranks.append(rank)
        parent[second] = first
        tree[first] = Node(rank, children=(tree[first], tree.pop(second)))
        started[first] = min(started.get(first, rank), started.pop(second, rank))
    return [tree[root] for root in sorted(tree, key=lambda root: started[root])], ranks


def build_forest(dot_ids: Iterable[str], links: Iterable) -> list[Node]:
    """The trees of the links between the given dots, in the order their first merge was made."""
    return _replay(dot_ids, links)[0]


def merge_ranks(dot_ids: Iterable[str], links: Iterable) -> list[Optional[int]]:
    """Every link's merge rank, in link order; None for a cycle or a link with an end outside the view."""
    return _replay(dot_ids, links)[1]


def kept_merges(dot_ids: Iterable[str], links: Iterable, cutoff: float) -> tuple[int, int]:
    """(the number of merges below the cut-off line, the full tree's number of merges)."""
    ranks = merge_ranks(dot_ids, links)
    top = max((rank for rank in ranks if rank is not None), default=0)
    share = min(1.0, max(0.0, float(cutoff)))
    return int(math.floor(share * top + 1e-9)), top


def cut_links(dot_ids: Iterable[str], links: Iterable, cutoff: float) -> list:
    """The links below the cut-off line. At 1 every link, as stored; below it only the merges whose rank is at
    most the kept share of the merge count (cycles and links leaving the view go with the cut)."""
    links = list(links)
    if cutoff >= 1.0:
        return links
    ranks = merge_ranks(dot_ids, links)
    kept, _top = kept_merges(dot_ids, links, cutoff)
    return [link for link, rank in zip(links, ranks) if rank is not None and rank <= kept]


def cut_line(dot_ids: Iterable[str], links: Iterable, cutoff: float) -> Optional[tuple[float, int]]:
    """Where the dendrogram draws the cut-off line: (its height, the full tree's number of merges). The line sits
    half a rank above the last kept merge, between kept and cut. None without any merge."""
    kept, top = kept_merges(dot_ids, links, cutoff)
    if not top:
        return None
    return kept + 0.5, top
