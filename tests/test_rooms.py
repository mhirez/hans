import random

from game.config import COLS, ROWS, FLOORS, ROOMS_PER_FLOOR
from game.rooms import generate, plan, _flood


def test_every_generated_room_is_fair():
    rng = random.Random(0)
    for _ in range(150):
        layout = generate(rng)
        g = [list(r) for r in layout.rows]
        assert len(g) == ROWS and len(g[0]) == COLS
        open_tiles = sum(row.count(".") for row in g)
        assert len(_flood(g, (1, 9))) == open_tiles                  # no sealed pockets
        assert all(g[r][c] == "." for c in range(1, 6) for r in range(5, 13))        # landing zone
        assert all(g[r][c] == "." for c in range(COLS - 5, COLS - 1) for r in range(6, 12))  # exit approach
        assert open_tiles >= 0.78 * (COLS - 2) * (ROWS - 2)


def test_rooms_look_designed_because_they_are_mirrored():
    layout = generate(random.Random(3), "pillars")
    rows = layout.rows
    for r in range(ROWS):
        for c in range(COLS):
            if rows[r][c] == "X":
                assert rows[ROWS - 1 - r][c] == "X"


def test_floor_one_teaches_then_the_last_floor_ends_with_the_warden():
    rng = random.Random(1)
    first = [plan(1, i, rng) for i in range(ROOMS_PER_FLOOR)]
    assert first[0].waves == [["grunt", "grunt"]]
    assert "charger" in first[1].waves[0] and "sniper" in first[2].waves[0]
    assert first[-1].kind == "lockdown" and len(first[-1].waves) == 2
    assert plan(FLOORS, ROOMS_PER_FLOOR - 1, rng).kind == "boss"
    small, big = plan(2, 0, random.Random(5)), plan(3, 2, random.Random(5))
    assert len(big.waves[0]) >= len(small.waves[0])
