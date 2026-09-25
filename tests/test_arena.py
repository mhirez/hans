import random

from game.arena import generate, make_level, START


def test_every_courtyard_is_fully_connected_with_four_gates():
    for wave in range(1, 25):
        level = make_level(wave, random.Random(wave))
        assert len(level.doors) == 4 and set(level.waypoints) == {"1", "2", "3", "4"}
        for spawn in level.waypoints.values():
            assert level.route((int(spawn[0]), int(spawn[1])), START).path is not None


def test_layouts_differ_between_waves():
    assert generate(1, random.Random(1)) != generate(2, random.Random(2))


def test_start_is_clear():
    rows = generate(7, random.Random(7))
    c, r = START
    around = [rows[y][x] for y in range(r - 2, r + 3) for x in range(c - 3, c + 4)]
    assert set(around) <= {".", "H"}
