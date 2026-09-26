import math

from game.config import MEMORY_TIME
from tests.helpers import arena, place, step


def test_a_calm_guard_facing_away_does_not_see_you():
    room = arena()
    g = place(room, "grunt", (8.5, 9.0), facing=0.0)            # facing east, player is west
    step(room, 1.0)
    assert not g.alert and g.state == "PATROL"


def test_suspicion_builds_then_it_spots_you():
    room = arena()
    g = place(room, "grunt", (9.5, 9.0), facing=math.pi)
    step(room, 0.2)
    assert 0 < g.senses.suspicion < 1 and not g.alert            # a double take first
    step(room, 1.0)
    assert g.alert and g.icon == "!"


def test_cover_blocks_sight():
    room = arena(blocks=[(5, 7, 1, 4)])
    g = place(room, "grunt", (9.5, 9.0), facing=math.pi)
    step(room, 1.5)
    assert not g.alert


def test_a_gunshot_makes_it_investigate_where_it_came_from():
    room = arena(blocks=[(5, 7, 1, 4)])
    g = place(room, "grunt", (9.5, 9.0), facing=0.0)
    step(room, 0.1, firing=True, aim=(2.0, 1.0))
    assert g.state == "INVESTIGATE" and g.noise is not None


def test_spotting_alerts_nearby_allies():
    room = arena()
    a = place(room, "grunt", (9.5, 9.0), facing=math.pi)
    b = place(room, "grunt", (14.5, 4.5), facing=0.0)           # facing away, can't see you
    step(room, 1.2)
    assert a.alert and b.alert


def test_losing_you_for_long_enough_turns_into_a_search():
    room = arena(blocks=[(5, 4, 1, 10)])
    g = place(room, "grunt", (12.5, 9.0), alert=True)
    g.senses.seen_at = g.senses.heard_at = room.time - MEMORY_TIME - 1
    g.decide()
    assert g.state == "SEARCH"
