"""Dendrogram from connections (no Dash, no state).

The stored links of a view are replayed in the order they were made (create_link appends). A link that joins
two separate groups of dots is a merge, with its rank among the merges (1, 2, 3, ...) as height; a link inside
one group (a cycle) adds nothing. The result is a forest with one tree per constellation. Dots without links
are not part of it; without links it is empty.

The merges have the same shape as scipy's linkage output, so connections written in the merge order of a
clustering replay to the same tree.
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


def build_forest(dot_ids: Iterable[str], links: Iterable) -> list[Node]:
    """The trees of the links between the given dots, in the order their first merge was made."""
    visible = set(dot_ids)
    parent: dict[str, str] = {}
    tree: dict[str, Node] = {}  # root dot -> its subtree
    started: dict[str, int] = {}  # root dot -> rank of the tree's first merge

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
            continue
        for dot in (a, b):
            if dot not in parent:
                parent[dot] = dot
                tree[dot] = Node(0, leaf=dot)
        first, second = find(a), find(b)
        if first == second:
            continue  # a cycle: the two dots are joined already
        # The older tree stays on the left; a single dot counts as the newest
        if started.get(second, math.inf) < started.get(first, math.inf):
            first, second = second, first
        rank += 1
        parent[second] = first
        tree[first] = Node(rank, children=(tree[first], tree.pop(second)))
        started[first] = min(started.get(first, rank), started.pop(second, rank))
    return [tree[root] for root in sorted(tree, key=lambda root: started[root])]
