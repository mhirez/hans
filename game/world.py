"""The courtyard: a tile grid plus the people and doors in it.

The world owns *geometry* (what blocks walking, what blocks sight, where things stand).
It does not know where the carrot is; that lives in Trial.
"""

from dataclasses import dataclass
from enum import IntEnum
import math

from game.config import COLS, ROWS, N_DOORS, ROMAN

Point = tuple[float, float]
TileXY = tuple[int, int]


class Tile(IntEnum):
    FLOOR = 0
    WALL = 1
    HAY = 2
    TROUGH = 3
    CART = 4
    FENCE = 5
    SCREEN = 6


BLOCKS_MOVE = frozenset({Tile.WALL, Tile.HAY, Tile.TROUGH, Tile.CART, Tile.FENCE, Tile.SCREEN})
BLOCKS_SIGHT = frozenset({Tile.WALL, Tile.CART, Tile.SCREEN})   # hay, trough and fence are low

START: Point = (11.0, 15.5)
OWNER_SPOTS: dict[str, tuple[Point, TileXY]] = {    # where he stands, where Hans studies him
    "near": ((6.5, 13.5), (7, 12)),
    "far": ((2.5, 4.5), (3, 5)),
}
SCREEN_TILES = [(8, r) for r in range(12, 17)]
CROWD_POS: Point = (19.5, 10.5)
CROWD_LISTEN_TILE: TileXY = (17, 10)
CROWD_SLOTS = [(19.5, 6.6), (20.4, 7.6), (19.4, 8.7), (20.5, 9.8), (19.5, 11.0),
               (20.4, 12.1), (19.4, 13.3), (20.5, 14.4)]


def tile_of(p: Point) -> TileXY:
    return int(math.floor(p[0])), int(math.floor(p[1]))


def center(t: TileXY) -> Point:
    return t[0] + 0.5, t[1] + 0.5


def distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


@dataclass(frozen=True)
class Door:
    index: int
    left: int                 # leftmost of the two wall tiles the door occupies
    front: Point              # where Hans stands to sniff or tap
    front_tile: TileXY

    @property
    def name(self) -> str:
        return ROMAN[self.index]

    @property
    def center_x(self) -> float:
        return self.left + 1.0


@dataclass(frozen=True)
class Source:
    """Something Hans can perceive a cue from, and the tile he walks to to study it."""
    id: str
    cue: str
    pos: Point
    observe_tile: TileXY
    label: str


class World:
    def __init__(self):
        self.cols, self.rows = COLS, ROWS
        self.base = [[Tile.FLOOR] * COLS for _ in range(ROWS)]
        for c in range(COLS):
            self.base[0][c] = self.base[ROWS - 1][c] = Tile.WALL
        for r in range(ROWS):
            self.base[r][0] = self.base[r][COLS - 1] = Tile.WALL
        for c, r in [(7, 6), (8, 6), (13, 6), (14, 6)]:
            self.base[r][c] = Tile.HAY
        for c in (10, 11, 12):
            self.base[9][c] = Tile.TROUGH
        for c in (2, 3):
            self.base[15][c] = Tile.CART
        for r in range(5, ROWS - 1):
            self.base[r][18] = Tile.FENCE

        self.doors = [Door(i, 4 + 6 * i, (5.0 + 6 * i, 1.55), (4 + 6 * i, 1)) for i in range(N_DOORS)]
        self.owner_present = True
        self.owner_spot = "near"
        self.screen_up = False
        self.crowd_present = False
        self.grid = [row[:] for row in self.base]

    # --- configuration per trial --------------------------------------------------
    def configure(self, owner_present: bool, owner_far: bool, screen: bool, crowd_present: bool):
        self.owner_present = owner_present
        self.owner_spot = "far" if owner_far else "near"
        self.screen_up = screen
        self.crowd_present = crowd_present
        self.grid = [row[:] for row in self.base]
        if screen:
            for c, r in SCREEN_TILES:
                self.grid[r][c] = Tile.SCREEN

    @property
    def owner_pos(self) -> Point:
        return OWNER_SPOTS[self.owner_spot][0]

    @property
    def owner_observe_tile(self) -> TileXY:
        return OWNER_SPOTS[self.owner_spot][1]

    # --- queries ------------------------------------------------------------------
    def in_bounds(self, c: int, r: int) -> bool:
        return 0 <= c < self.cols and 0 <= r < self.rows

    def walkable(self, c: int, r: int) -> bool:
        if not self.in_bounds(c, r) or self.grid[r][c] in BLOCKS_MOVE:
            return False
        return not (self.owner_present and (c, r) == tile_of(self.owner_pos))

    def blocks_sight(self, c: int, r: int) -> bool:
        return not self.in_bounds(c, r) or self.grid[r][c] in BLOCKS_SIGHT

    def line_of_sight(self, a: Point, b: Point) -> bool:
        """Sample the segment every 0.2 tiles; any sight-blocking tile in between breaks it."""
        ends = {tile_of(a), tile_of(b)}
        steps = max(1, int(distance(a, b) / 0.2))
        for i in range(1, steps):
            t = i / steps
            p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            tt = tile_of(p)
            if tt not in ends and self.blocks_sight(*tt):
                return False
        return True

    def sources(self) -> list[Source]:
        out = []
        if self.owner_present:
            out.append(Source("owner", "owner", self.owner_pos, self.owner_observe_tile, "von Osten"))
        for d in self.doors:
            out.append(Source(f"scent_{d.index}", "scent", d.front, d.front_tile, f"door {d.name}"))
        if self.crowd_present:
            out.append(Source("crowd", "crowd", CROWD_POS, CROWD_LISTEN_TILE, "the crowd"))
        return out

    def source(self, source_id: str) -> Source | None:
        return next((s for s in self.sources() if s.id == source_id), None)
