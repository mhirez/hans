"""Procedural rooms and what's in them.

Layout: every room is 32 x 18 tiles with an entry door on the left and an exit on the right.
Cover is placed in one of several STYLES, always mirrored top-to-bottom (and sometimes
left-to-right) so rooms look designed rather than random. A layout is only accepted if:
  - the landing zone by the entry and the approach to the exit are clear,
  - cover blocks never touch each other (so every gap is walkable),
  - a flood fill from the entry reaches every floor tile (no sealed pockets),
  - at least 78% of the interior stays open.

Contents: the first rooms introduce one enemy type at a time; after that a difficulty budget buys
enemies (grunt 1, charger 1, sniper 1.5, medic 1.5). The last room of each floor is a LOCKDOWN
(two waves); the last room of floor 3 is the Warden.
"""

from dataclasses import dataclass, field
import random

from game.config import COLS, ROWS, ROOMS_PER_FLOOR, FLOORS
from game.geometry import Tile

ENTRY = [(0, 8), (0, 9)]
EXIT = [(COLS - 1, 8), (COLS - 1, 9)]
START = (1.7, 9.0)
STYLES = ("pillars", "bunkers", "crates", "center", "lanes")
COST = {"grunt": 1.0, "charger": 1.0, "sniper": 1.5, "medic": 1.5}


@dataclass
class Layout:
    rows: list[str]
    style: str


FLOOR_NAMES = {1: "SUB-LEVEL 1", 2: "SUB-LEVEL 2", 3: "SUB-LEVEL 3"}
ROOM_NAMES = {1: ["LOBBY", "SERVER HALL A", "SERVER HALL B", "SECURITY"],
              2: ["COOLING PLANT", "POWER ROOM", "NETWORK CORE", "UPLINK"],
              3: ["DEEP STORAGE", "TRAINING CLUSTER", "MODEL VAULT", "THE CORE"]}


@dataclass
class RoomPlan:
    floor: int
    index: int                         # 0-based within the floor
    kind: str                          # "normal", "lockdown" or "boss"
    waves: list[list[str]] = field(default_factory=list)
    mods: list[str] = field(default_factory=list)      # ARGUS's countermeasures (see director.py)
    line: str = ""                                     # what ARGUS says as you enter

    @property
    def number(self) -> int:
        return self.index + 1

    @property
    def name(self) -> str:
        names = ROOM_NAMES.get(self.floor)
        return names[self.index] if names and self.index < len(names) else f"ROOM {self.number}"

    @property
    def floor_name(self) -> str:
        return FLOOR_NAMES.get(self.floor, f"SUB-LEVEL {self.floor}")


# --- layout ----------------------------------------------------------------------------------
def _blank() -> list[list[str]]:
    g = [["." for _ in range(COLS)] for _ in range(ROWS)]
    for c in range(COLS):
        g[0][c] = g[ROWS - 1][c] = "#"
    for r in range(ROWS):
        g[r][0] = g[r][COLS - 1] = "#"
    for c, r in ENTRY + EXIT:
        g[r][c] = "D"
    return g


def _reserved(c: int, r: int) -> bool:
    """Tiles that must stay open: the entry landing zone, the exit approach, the inner ring."""
    if c <= 1 or c >= COLS - 2 or r <= 1 or r >= ROWS - 2:
        return True
    if c <= 5 and 5 <= r <= 12:
        return True
    return c >= COLS - 5 and 6 <= r <= 11


def _pieces(style: str, rng: random.Random) -> list[tuple[int, int, int, int]]:
    """Blocks (col, row, width, height) for the TOP half; the room mirrors them."""
    out = []
    if style == "pillars":
        for c in (7, 12, 17, 22):
            for r in (3, 6):
                if rng.random() < 0.7:
                    out.append((c + rng.randint(-1, 1), r, 2, 2))
    elif style == "bunkers":
        for _ in range(rng.randint(4, 6)):
            if rng.random() < 0.6:
                out.append((rng.randint(6, 24), rng.randint(3, 7), rng.randint(2, 4), 1))
            else:
                out.append((rng.randint(6, 25), rng.randint(2, 6), 1, rng.randint(2, 3)))
    elif style == "crates":
        for _ in range(rng.randint(6, 9)):
            w, h = rng.choice(((1, 1), (2, 1), (1, 2), (2, 2)))
            out.append((rng.randint(6, 25), rng.randint(2, 7), w, h))
    elif style == "center":
        out.append((13, 7, 6, 2))                              # the big block straddles the middle
        out.append((rng.randint(7, 9), 3, 2, 2))
        out.append((rng.randint(21, 23), 3, 2, 2))
        out.append((rng.randint(10, 20), rng.randint(2, 4), 3, 1))
    elif style == "lanes":
        for c in (8, 14, 20):
            c += rng.randint(-1, 1)
            out.append((c, rng.randint(2, 4), 1, rng.randint(3, 4)))
        out.append((rng.randint(10, 18), 7, 2, 1))
    return out


def _flood(g, start: Tile) -> set[Tile]:
    seen, todo = {start}, [start]
    while todo:
        c, r = todo.pop()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c + dc, r + dr)
            if n not in seen and 0 <= n[0] < COLS and 0 <= n[1] < ROWS and g[n[1]][n[0]] == ".":
                seen.add(n)
                todo.append(n)
    return seen


def _try_layout(style: str, rng: random.Random, mirror_x: bool) -> list[list[str]] | None:
    g = _blank()
    placed: set[Tile] = set()
    for c0, r0, w, h in _pieces(style, rng):
        cells = set()
        for dc in range(w):
            for dr in range(h):
                c, r = c0 + dc, r0 + dr
                for cc, rr in ((c, r), (c, ROWS - 1 - r)):
                    cells.add((cc, rr))
                    if mirror_x:
                        cells.add((COLS - 1 - cc, rr))
        if any(_reserved(c, r) for c, r in cells):
            continue
        halo = {(c + dc, r + dr) for c, r in cells for dc in (-1, 0, 1) for dr in (-1, 0, 1)} - cells
        if halo & placed:
            continue                                           # would touch another block
        placed |= cells
    if len(placed) < 6:
        return None
    for c, r in placed:
        g[r][c] = "X"
    interior = (COLS - 2) * (ROWS - 2)
    open_tiles = sum(row.count(".") for row in g)
    if open_tiles < 0.78 * interior:
        return None
    if len(_flood(g, (1, 9))) != open_tiles:
        return None
    return g


def generate(rng: random.Random, style: str | None = None) -> Layout:
    for _ in range(80):
        s = style or rng.choice(STYLES)
        g = _try_layout(s, rng, mirror_x=rng.random() < 0.4)
        if g is not None:
            return Layout(["".join(row) for row in g], s)
    g = _blank()                                               # (practically never) a bare room
    return Layout(["".join(row) for row in g], "empty")


# --- contents --------------------------------------------------------------------------------
INTRO = {                       # floor 1 teaches one enemy at a time
    0: [["grunt", "grunt"]],
    1: [["grunt", "grunt", "charger"]],
    2: [["grunt", "sniper", "charger", "grunt"]],
    3: [["grunt", "grunt", "medic", "grunt"], ["charger", "sniper", "charger", "grunt"]],
}


def _buy(budget: float, kinds: list[str], rng: random.Random) -> list[str]:
    out = ["grunt"]
    budget -= COST["grunt"]
    while budget >= 1.0:
        affordable = [k for k in kinds if COST[k] <= budget]
        if not affordable:
            break
        weights = [3 if k == "grunt" else 1.2 if k == "charger" else 1 for k in affordable]
        if "medic" in out:                                     # one healer per group is plenty
            weights = [0 if k == "medic" else w for k, w in zip(affordable, weights)]
        k = rng.choices(affordable, weights)[0]
        out.append(k)
        budget -= COST[k]
    return out


def plan(floor: int, index: int, rng: random.Random) -> RoomPlan:
    last = index == ROOMS_PER_FLOOR - 1
    if floor == FLOORS and last:
        return RoomPlan(floor, index, "boss", [["warden"]])
    if floor == 1:
        return RoomPlan(floor, index, "lockdown" if last else "normal", [list(w) for w in INTRO[index]])
    budget = 3.0 + 1.2 * (floor - 1) + 0.6 * index
    kinds = ["grunt", "charger", "sniper", "medic"]
    waves = [_buy(budget, kinds, rng)]
    if last:
        waves.append(_buy(budget + 0.5, kinds, rng))
    return RoomPlan(floor, index, "lockdown" if last else "normal", waves)
