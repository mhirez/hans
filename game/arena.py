"""Procedural courtyards: every wave gets a fresh layout of hay, carts and troughs.

Rules that keep a layout fair:
  - a clear ring just inside the walls, and clear space around Hans's start and every gate
  - obstacles never touch each other, so there are no dead-end pockets
  - every open tile must be reachable (flood fill), or the layout is thrown away and re-rolled
Enemies come in through four stable doors (D) in the walls; their spawn tiles are 1-4.
"""

import random

from game.config import ARENA_COLS as COLS, ARENA_ROWS as ROWS
from game.level import Level

SHAPES = [                       # (tile, width, height)
    ("h", 2, 1), ("h", 1, 2), ("h", 2, 2), ("h", 2, 1),
    ("c", 3, 1), ("t", 3, 1), ("h", 1, 1),
]
GATES = [((COLS // 2 - 6, 0), (COLS // 2 - 6, 1)), ((COLS // 2 + 5, 0), (COLS // 2 + 5, 1)),
         ((0, ROWS // 2), (1, ROWS // 2)), ((COLS - 1, ROWS // 2), (COLS - 2, ROWS // 2))]
START = (COLS // 2, ROWS // 2 + 3)


def _blank() -> list[list[str]]:
    grid = [["." for _ in range(COLS)] for _ in range(ROWS)]
    for c in range(COLS):
        grid[0][c] = grid[ROWS - 1][c] = "#"
    for r in range(ROWS):
        grid[r][0] = grid[r][COLS - 1] = "#"
    return grid


def _connected(grid) -> bool:
    open_tiles = {(c, r) for r in range(ROWS) for c in range(COLS) if grid[r][c] in ".H1234"}
    seen, stack = {START}, [START]
    while stack:
        c, r = stack.pop()
        for n in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            if n in open_tiles and n not in seen:
                seen.add(n)
                stack.append(n)
    return seen == open_tiles


def generate(wave: int, rng: random.Random) -> list[str]:
    count = min(12, 6 + wave // 2)
    for _ in range(200):
        grid = _blank()
        for i, (door, spawn) in enumerate(GATES):
            grid[door[1]][door[0]] = "D"
            grid[spawn[1]][spawn[0]] = str(i + 1)
        grid[START[1]][START[0]] = "H"
        keep_clear = [START] + [spawn for _, spawn in GATES]
        placed = 0
        for _ in range(400):
            if placed == count:
                break
            tile, w, h = rng.choice(SHAPES)
            c, r = rng.randint(2, COLS - 3 - w), rng.randint(2, ROWS - 3 - h)
            cells = [(c + dc, r + dr) for dc in range(w) for dr in range(h)]
            if any(abs(x - kx) <= 3 and abs(y - ky) <= 2 for x, y in cells for kx, ky in keep_clear):
                continue
            around = [(x + dx, y + dy) for x, y in cells for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
            if any(grid[y][x] != "." for x, y in around if (x, y) not in cells):
                continue
            for x, y in cells:
                grid[y][x] = tile
            placed += 1
        if placed == count and _connected(grid):
            return ["".join(row) for row in grid]
    raise RuntimeError("could not generate a fair courtyard")


def make_level(wave: int, rng: random.Random) -> Level:
    return Level(generate(wave, rng))
