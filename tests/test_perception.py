import math

from game.ai.perception import sees, hears, cone, Noise
from game.level import Level

ROOM = ["##########",
        "#........#",
        "#....h...#",
        "#........#",
        "##########"]


def test_sees_inside_the_cone_only():
    level = Level(ROOM)
    eye = (1.5, 1.5)
    assert sees(level, eye, 0.0, (4.5, 1.5), 6, math.radians(34)) is not None
    assert sees(level, eye, math.pi, (4.5, 1.5), 6, math.radians(34)) is None     # behind him
    assert sees(level, eye, 0.0, (6.5, 1.5), 6, math.radians(34)) is not None
    assert sees(level, eye, 0.0, (6.5, 1.5), 4, math.radians(34)) is None          # out of range


def test_hay_blocks_the_lantern():
    level = Level(ROOM)
    assert sees(level, (3.5, 2.5), 0.0, (7.5, 2.5), 6, math.radians(34)) is None


def test_cone_polygon_stops_at_hay():
    level = Level(ROOM)
    pts = cone(level, (3.5, 2.5), 0.0, 6, 0.05, rays=2)
    assert max(p[0] for p in pts) < 6                # the middle ray stops at the hay at x = 5


def test_hearing_is_a_radius():
    assert hears((0, 0), Noise((3, 4), 5.0)) and not hears((0, 0), Noise((3, 4), 4.9))
