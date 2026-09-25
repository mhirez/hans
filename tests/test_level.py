from game.level import Level
from game.levels import LEVELS
from tools.danger_map import check

MAP = ["##D##D##",
       "#......#",
       "#.hh.t.#",
       "#O...gH#",
       "#1...2.#",
       "########"]


def test_parsing_finds_everyone():
    level = Level(MAP)
    assert level.start == (6.5, 3.5)
    assert level.owner_stops == [(1.5, 3.5)]
    assert set(level.waypoints) == {"1", "2"}
    assert [d.tile for d in level.doors] == [(2, 0), (5, 0)]
    assert level.doors[0].front[1] > 0.5           # the front is inside the yard, below the door


def test_tall_things_block_light_but_troughs_do_not():
    level = Level(MAP)
    assert not level.line_of_sight((1.5, 2.5), (4.5, 2.5))     # hay in between
    assert level.line_of_sight((4.5, 1.5), (6.5, 2.5)) and not level.walkable(5, 2)   # trough: low
    assert level.noisy((5.5, 3.5))


def test_collision_circle():
    level = Level(MAP)
    assert level.free((1.5, 1.5), 0.3)
    assert not level.free((1.1, 1.5), 0.3)         # overlapping the left wall


def test_every_level_is_well_formed_and_reachable():
    for i in range(len(LEVELS)):
        assert check(i) == [], LEVELS[i].name
