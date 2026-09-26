"""ARGUS the director: it models the player's habits and deploys countermeasures between rooms."""

import math
import random

from game.ai.director import Director, LINES, OPENING
from game.player import Player
from game.rooms import plan
from tests.helpers import arena, place, step


def fresh(floor=2, index=1, seed=1):
    return plan(floor, index, random.Random(seed))


def test_the_first_rooms_are_just_a_greeting():
    d = Director()
    p = d.adapt(fresh(1, 0), Player(pos=(1, 1)), random.Random(0))
    assert d.deployed == [] and p.line == OPENING[0]


def test_fighting_from_far_away_brings_snipers():
    d = Director()
    d.profile.far = 0.8
    before = fresh()
    snipers = before.waves[0].count("sniper")
    p = d.adapt(fresh(), Player(pos=(1, 1)), random.Random(0))
    assert d.deployed[0] == "long sight" and p.line in LINES["long sight"]
    assert p.waves[0].count("sniper") == snipers + 1           # a Lens is added


def test_rewriting_its_units_brings_firewalls():
    d = Director()
    d.profile.rewrites = 2.0
    p = d.adapt(fresh(), Player(pos=(1, 1)), random.Random(0))
    assert "firewalls" in p.mods
    room = arena()
    room.plan.mods.append("firewalls")
    shielded = [place(room, "grunt", (20.0, 3.0 + 2 * i)).firewall > 0 for i in range(6)]
    assert any(shielded)


def test_a_nearly_dead_player_gets_mercy():
    d = Director()
    hurt = Player(pos=(1, 1))
    hurt.hp = 2
    base = fresh(2, 2)
    size = len(base.waves[0])
    p = d.adapt(fresh(2, 2), hurt, random.Random(0))
    assert "mercy" in d.deployed and "mercy" in p.mods
    assert len(p.waves[0]) == max(2, size - 1) or len(p.waves[0]) <= size


def test_the_profile_learns_from_a_room():
    room = arena()
    room.stats.update(fighting=20.0, far=15.0, close=1.0, hidden=2.0, moving=10.0, shots=40, hits=30, dashes=4)
    room.rewrites = 1
    d = Director()
    d.profile.absorb(room)
    assert abs(d.profile.far - 0.75) < 1e-9 and abs(d.profile.accuracy - 0.75) < 1e-9
    assert d.profile.rewrites == 1


def test_prediction_makes_a_sentry_aim_where_you_are_going():
    room = arena()
    p = room.player
    p.pos = (8.0, 9.0)
    g = place(room, "grunt", (16.0, 9.0), alert=True)
    step(room, 0.3)
    p.vel = (0.0, 6.0)                                           # running south
    g.predicts = False
    plain = g.lead(10.0)
    g.predicts = True
    ahead = g.lead(10.0)
    assert plain == p.pos and ahead[1] > p.pos[1] + 2.0
    assert math.isclose(ahead[0], p.pos[0])
