"""A level: the courtyard grid parsed from a text map, plus the geometry queries the AI needs.

Map legend
    #  wall              D  door (in a wall; numbered left to right, top to bottom)
    .  cobbles           g  gravel (noisy underfoot)
    h  hay bales (tall: blocks walking AND light)
    c  cart (tall)       s  cloth screen (tall)
    t  water trough (low: blocks walking, not light)
    H  Hans starts here  O  von Osten starts here;  x y z  further stops he walks to
    1-9  scientist waypoints (routes are given as strings like "12" in levels.py)
"""

from dataclasses import dataclass
import math

from game.ai.pathfinding import astar, SearchResult

Point = tuple[float, float]
TileXY = tuple[int, int]

BLOCKS_MOVE = frozenset("#Dhcst")
BLOCKS_SIGHT = frozenset("#Dhcs")
NOISY = frozenset("g")
MARKERS = frozenset("HOxyz123456789")


def tile_of(p: Point) -> TileXY:
    return int(math.floor(p[0])), int(math.floor(p[1]))


def center(t: TileXY) -> Point:
    return t[0] + 0.5, t[1] + 0.5


def distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angle_to(a: Point, b: Point) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def angle_diff(a: float, b: float) -> float:
    """Signed smallest difference b - a, in [-pi, pi]."""
    return (b - a + math.pi) % (2 * math.pi) - math.pi


@dataclass(frozen=True)
class Door:
    index: int
    tile: TileXY
    front: Point        # where Hans stands to tap it

    @property
    def name(self) -> str:
        return "I II III IV V VI".split()[self.index]


class Level:
    def __init__(self, rows: list[str]):
        width = max(len(r) for r in rows)
        self.cols, self.rows = width, len(rows)
        self.grid = [list(r.ljust(width, "#")) for r in rows]
        self.start: Point = (1.5, 1.5)
        self.owner_stops: list[Point] = []
        self.waypoints: dict[str, Point] = {}
        extra_stops = {}
        for r, row in enumerate(self.grid):
            for c, ch in enumerate(row):
                if ch in MARKERS:
                    if ch == "H":
                        self.start = center((c, r))
                    elif ch == "O":
                        self.owner_stops.insert(0, center((c, r)))
                    elif ch in "xyz":
                        extra_stops[ch] = center((c, r))
                    else:
                        self.waypoints[ch] = center((c, r))
                    self.grid[r][c] = "."
        self.owner_stops += [extra_stops[k] for k in sorted(extra_stops)]
        self.doors = self._find_doors()
        self._routes: dict[tuple, SearchResult] = {}

    def _find_doors(self) -> list[Door]:
        doors = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] != "D":
                    continue
                for dc, dr in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    if self.walkable(c + dc, r + dr):
                        front = (c + 0.5 + dc * 0.9, r + 0.5 + dr * 0.9)
                        doors.append(Door(len(doors), (c, r), front))
                        break
        return doors

    # --- tiles ---------------------------------------------------------------------------
    def at(self, c: int, r: int) -> str:
        return self.grid[r][c] if 0 <= c < self.cols and 0 <= r < self.rows else "#"

    def walkable(self, c: int, r: int) -> bool:
        return self.at(c, r) not in BLOCKS_MOVE

    def blocks_sight(self, c: int, r: int) -> bool:
        return self.at(c, r) in BLOCKS_SIGHT

    def noisy(self, p: Point) -> bool:
        return self.at(*tile_of(p)) in NOISY

    # --- sight ---------------------------------------------------------------------------
    def line_of_sight(self, a: Point, b: Point, step: float = 0.15) -> bool:
        n = max(1, int(distance(a, b) / step))
        for i in range(1, n):
            t = i / n
            if self.blocks_sight(*tile_of((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))):
                return False
        return True

    def ray(self, origin: Point, angle: float, max_dist: float, step: float = 0.1) -> float:
        """How far light travels from `origin` in direction `angle` before hitting something tall."""
        dx, dy = math.cos(angle), math.sin(angle)
        d = step
        while d < max_dist:
            if self.blocks_sight(*tile_of((origin[0] + dx * d, origin[1] + dy * d))):
                return d
            d += step
        return max_dist

    # --- movement ------------------------------------------------------------------------
    def free(self, p: Point, radius: float) -> bool:
        """Is a circle of this radius at p clear of every blocking tile?"""
        x, y = p
        for r in range(int(math.floor(y - radius)), int(math.floor(y + radius)) + 1):
            for c in range(int(math.floor(x - radius)), int(math.floor(x + radius)) + 1):
                if self.walkable(c, r):
                    continue
                nx, ny = min(max(x, c), c + 1), min(max(y, r), r + 1)
                if (x - nx) ** 2 + (y - ny) ** 2 < radius * radius:
                    return False
        return True

    def nearest_walkable(self, t: TileXY) -> TileXY:
        if self.walkable(*t):
            return t
        best, best_d = t, math.inf
        for r in range(self.rows):
            for c in range(self.cols):
                if self.walkable(c, r):
                    d = (c - t[0]) ** 2 + (r - t[1]) ** 2
                    if d < best_d:
                        best, best_d = (c, r), d
        return best

    def route(self, start: TileXY, goal: TileXY) -> SearchResult:
        """A* between two tiles, cached (the courtyard never changes during a level)."""
        key = (start, goal)
        if key not in self._routes:
            self._routes[key] = astar(start, self.nearest_walkable(goal), self.walkable)
        return self._routes[key]
