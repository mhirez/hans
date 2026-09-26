"""Grid A*: 8-way movement, octile heuristic, no cutting corners, and an optional TACTICAL cost.

The tactical cost is how flanking works: a flanker's search adds a penalty to every tile the
player can see, so the cheapest path goes round behind cover instead of through the line of fire.
"""

from dataclasses import dataclass, field
import heapq
import math

SQRT2 = math.sqrt(2)
STEPS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, SQRT2), (1, -1, SQRT2), (-1, 1, SQRT2), (-1, -1, SQRT2)]


@dataclass
class SearchResult:
    path: list[tuple[int, int]] | None
    cost: float = math.inf
    explored: set = field(default_factory=set)


def octile(a, b) -> float:
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return (dx + dy) + (SQRT2 - 2) * min(dx, dy)


def astar(start, goal, walkable, extra_cost=None, max_nodes: int = 4000) -> SearchResult:
    """walkable(c, r) -> bool; extra_cost(c, r) -> float added for entering a tile."""
    if not walkable(*goal):
        return SearchResult(None)
    open_heap = [(octile(start, goal), 0.0, start)]
    came_from = {}
    g = {start: 0.0}
    closed = set()
    while open_heap and len(closed) < max_nodes:
        _, cost, node = heapq.heappop(open_heap)
        if node in closed:
            continue
        if node == goal:
            path = [node]
            while node in came_from:
                node = came_from[node]
                path.append(node)
            return SearchResult(path[::-1], cost, closed)
        closed.add(node)
        c, r = node
        for dc, dr, step in STEPS:
            nxt = (c + dc, r + dr)
            if nxt in closed or not walkable(*nxt):
                continue
            if dc and dr and not (walkable(c + dc, r) and walkable(c, r + dr)):
                continue
            new_cost = cost + step + (extra_cost(*nxt) if extra_cost else 0.0)
            if new_cost < g.get(nxt, math.inf):
                g[nxt] = new_cost
                came_from[nxt] = node
                heapq.heappush(open_heap, (new_cost + octile(nxt, goal), new_cost, nxt))
    return SearchResult(None, math.inf, closed)
