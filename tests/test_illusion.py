"""The 'illusion of intelligence' features: barks, the learning Commission, teamwork, tracking, morale."""

import math
import random

from game.ai.barks import Barks, BARK_COOLDOWN
from game.ai.commission import Commission
from game.ai.desire import desires
from game.ai.dog import Dog
from game.ai.scientist import Scientist
from game.level import distance
from game.match import Match, Print
from test_enemies import World, make, run


class Speaker:
    def __init__(self, uid, kind="scientist"):
        self.uid, self.kind, self.gone = uid, kind, False


def test_barks_have_cooldowns_but_urgent_lines_get_through():
    barks = Barks(random.Random(0))
    s = Speaker(1)
    assert barks.say(s, "hear")
    assert not barks.say(s, "lost")                  # too soon
    assert barks.say(s, "spotted")                   # urgent
    barks.update(BARK_COOLDOWN + 0.1)
    assert barks.say(s, "lost")
    assert len([b for b in barks.bubbles if b.enemy is s]) == 1


def test_commission_learns_the_strongest_habit_once():
    c = Commission()
    c.habits.minutes = 1.0
    c.habits.kicks = 20                              # 20 kicks a minute: a kicker
    c.habits.moving, c.habits.galloping = 60, 25     # and a fair bit of galloping
    assert c.learn() and c.tactics == ["wary"]
    c.habits.minutes, c.habits.moving, c.habits.galloping = 1.0, 60, 40
    c.learn()
    assert c.tactics == ["wary", "intercept"]


def test_commission_ignores_a_player_without_strong_habits():
    c = Commission()
    c.habits.minutes, c.habits.kicks = 1.0, 2
    assert c.learn() == [] and c.tactics == []


def test_second_scientist_goes_round_the_far_side():
    w = World(hans_pos=(12.5, 2.5))
    first = make(Scientist, w, (10.5, 2.5))
    second = make(Scientist, w, (5.5, 2.5))
    first.fsm.change(__import__("game.ai.scientist", fromlist=["CHASE"]).CHASE)
    second.last_seen, second.sees_hans = w.hans.pos, True
    target, mode = second.chase_target()
    assert mode == "flank" and target[0] > w.hans.pos[0]      # the far side from his partner


def test_dog_follows_hoofprints_toward_fresher_ones():
    w = World(hans_pos=(19.5, 5.5))
    w.prints = [Print((4.5 + i, 1.5), 1, age=12 - i) for i in range(10)]   # a trail getting fresher to the right
    d = make(Dog, w, (3.5, 1.5), facing=0.0)
    run(w, 0.2)
    assert d.state == "TRACK"
    run(w, 2.5)
    assert d.pos[0] > 6


def test_morale_makes_them_more_likely_to_run():
    w = World()
    s = make(Scientist, w, (13.5, 2.5))
    calm = desires(s, w)["flee"]
    w.morale = 0.3
    assert desires(s, w)["flee"] > calm


def test_wary_scientists_hop_back_from_a_missed_kick():
    m = Match(random.Random(3))
    m.commission.tactics.append("wary")
    m.spawn_enemy("scientist")
    e = m.enemies[0]
    e.pos, e.aware = (m.hans.pos[0] + 2.2, m.hans.pos[1]), True
    m.kick()
    assert e.knockback[0] > 0 and "wary" in e.events


def test_guard_tactic_posts_a_guard_by_the_carrots():
    m = Match(random.Random(4))
    m.commission.tactics.append("guard")
    m.spawn_enemy("scientist")
    e = m.enemies[0]
    for _ in range(120):
        m.update(1 / 30, (0, 0), False, False)
        if e.state == "GUARD":
            break
    assert e.guard and e.state == "GUARD"


def test_sweep_finds_spots_hidden_behind_hay():
    w = World()
    s = make(Scientist, w, (6.5, 2.5))
    spots = s.hiding_spots((8.5, 3.5))
    assert spots and all(not w.level.line_of_sight((8.5, 3.5), p) for p in spots)
    assert all(distance(p, (8.5, 3.5)) < 6 for p in spots)
    assert math.isfinite(spots[0][0])
