import random

from game.config import CARROT_POINTS, WAVE_BONUS
from game.match import Match
from game.waves import plan
from tools.autoplay import player


def test_waves_grow():
    a, b = plan(1, random.Random(0)), plan(12, random.Random(0))
    assert len(b.enemies) > len(a.enemies) and b.carrots > a.carrots and b.speed > a.speed
    assert {kind for _, kind in plan(9, random.Random(1)).enemies} == {"scientist", "stableboy", "dog"}


def test_eating_carrots_clears_the_wave_and_starts_the_next():
    m = Match(random.Random(0))
    for _ in range(m.wave.carrots):
        carrot = next(i for i in m.items if i.kind == "carrot")
        m.hans.pos = carrot.pos
        m.update(1 / 30, (0, 0), False, False)
    assert m.state == "cleared" and m.score >= m.wave.carrots * CARROT_POINTS + WAVE_BONUS
    for _ in range(90):
        m.update(1 / 30, (0, 0), False, False)
    assert m.wave.number == 2 and m.state == "playing"


def test_kick_knocks_down_nearby_enemies():
    m = Match(random.Random(1))
    m.spawn_enemy("scientist")
    e = m.enemies[0]
    e.pos = (m.hans.pos[0] + 0.8, m.hans.pos[1])
    assert m.kick() == 1 and e.state == "STUNNED"


def test_losing_all_hearts_ends_the_game():
    m = Match(random.Random(2))
    m.hans.hearts = 0
    m.update(1 / 30, (0, 0), False, False)
    assert m.state == "over"


def test_a_sensible_player_survives_wave_one():
    for seed in range(4):
        m = Match(random.Random(seed))
        t = 0.0
        while m.wave.number == 1 and m.state != "over" and t < 120:
            m.update(1 / 30, *player(m))
            t += 1 / 30
        assert m.state != "over"
