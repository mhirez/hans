import math
import random

from game.ai.dog import Dog
from game.ai.scientist import Scientist
from game.ai.stableboy import StableBoy
from game.ai.perception import Noise
from game.entities.hans import Hans
from game.level import Level, distance

YARD = ["######################",
        "#....................#",
        "#....................#",
        "#.........hh.........#",
        "#....................#",
        "#....................#",
        "######################"]


class World:
    """Just enough of a Match for enemies to live in."""

    def __init__(self, hans_pos=(15.5, 2.5)):
        self.level = Level(YARD)
        self.hans = Hans(hans_pos)
        self.hans_velocity = (0.0, 0.0)
        self.enemies, self.items, self.prints = [], [], []
        self.hits, self.lassos = [], []

    @property
    def cups(self):
        return [i for i in self.items if getattr(i, "kind", "") == "coffee"]

    def hit_hans(self, enemy, how):
        self.hits.append(how)
        self.hans.hurt()

    def throw_lasso(self, thrower, aim):
        self.lassos.append(aim)

    def on_spotted(self, enemy):
        pass

    def pack_slot(self, dog):
        return (self.hans.pos[0] - 2.0, self.hans.pos[1])

    def drink(self, cup, enemy):
        self.items.remove(cup)
        enemy.hp += 1


def make(kind, world, pos, facing=0.0):
    e = kind(world.level, pos, len(world.enemies) + 1, random.Random(1))
    e.world, e.angle = world, facing
    world.enemies.append(e)
    return e


def run(world, seconds, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        for e in list(world.enemies):
            e.update(dt, world)


def test_scientist_spots_chases_and_swings():
    w = World(hans_pos=(15.5, 1.5))
    s = make(Scientist, w, (9.5, 1.5))
    run(w, 0.7)
    assert s.aware and s.state == "CHASE"
    run(w, 4)
    assert "net" in w.hits


def test_hiding_behind_hay_breaks_line_of_sight():
    w = World(hans_pos=(12.5, 3.5))
    s = make(Scientist, w, (8.5, 3.5))
    run(w, 1)
    assert not s.sees_hans and not s.aware


def test_noise_makes_him_come_and_look():
    w = World(hans_pos=(19.5, 5.5))
    s = make(Scientist, w, (2.5, 1.5), facing=math.pi)
    s.hear(Noise((12.5, 5.5), 30))
    assert s.state == "INVESTIGATE"


def test_kicks_stun_then_knock_out():
    w = World()
    s = make(Scientist, w, (14.5, 2.5))
    assert not s.kicked(w.hans.pos) and s.state == "STUNNED"
    assert s.kicked(w.hans.pos) and s.state == "KO"


def test_wounded_scientist_goes_for_coffee_he_has_seen():
    class Cup:
        uid, pos, kind = 99, (3.5, 1.5), "coffee"
    w = World(hans_pos=(18.5, 4.5))
    s = make(Scientist, w, (6.5, 1.5), facing=math.pi)
    w.items.append(Cup())
    s.hp = 1
    run(w, 0.1)
    assert 99 in s.known_cups
    s.aware = True
    s.act(force=True)
    assert s.state == "HEAL"
    run(w, 3)
    assert s.hp == 2


def test_everyone_flees_a_golden_horse():
    w = World()
    s = make(Scientist, w, (8.5, 2.5))
    w.hans.power_up()
    s.aware = True
    s.act(force=True)
    assert s.state == "FLEE"


def test_stable_boy_keeps_distance_and_throws_ahead():
    w = World(hans_pos=(15.5, 1.5))
    b = make(StableBoy, w, (9.5, 1.5))
    w.hans_velocity = (0.0, 2.0)
    run(w, 4)
    assert w.lassos and w.lassos[0][1] > 1.5          # led the target: aimed where Hans is going
    assert distance(b.pos, w.hans.pos) > 2.5


def test_dog_smells_hans_behind_hay_and_pounces():
    w = World(hans_pos=(12.5, 4.5))
    d = make(Dog, w, (9.5, 2.5), facing=math.pi)       # facing away, hay in between
    run(w, 0.1)
    assert d.aware
    run(w, 4)
    assert "bite" in w.hits
