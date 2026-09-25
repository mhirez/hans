import math

from game.ai.scientist import Scientist
from game.ai.perception import Noise
from game.level import Level

YARD = ["####################",
        "#..................#",
        "#..................#",
        "#..................#",
        "#..................#",
        "####################"]


class FakeHans:
    def __init__(self, pos, trotting=False):
        self.pos = pos
        self.trotting = trotting


def run(s, hans, seconds, dt=1 / 30):
    for _ in range(int(seconds / dt)):
        s.update(dt, hans)


def guard(route=((3.5, 2.5), (15.5, 2.5)), **kw):
    return Scientist(Level(YARD), list(route), "Dr. Test", **kw)


def test_patrols_his_route():
    s = guard()
    run(s, FakeHans((-9, -9)), 10)
    assert s.state == "PATROL" and s.pos[0] > 10


def test_seen_hans_makes_him_suspicious_then_chase():
    s = guard(route=((3.5, 2.5), (3.6, 2.5)), facing=0.0)
    hans = FakeHans((8.5, 2.5))
    run(s, hans, 0.1)
    assert s.state == "SUSPICIOUS" and s.icon == "?"
    run(s, hans, 2.0)
    assert s.state == "CHASE" and s.icon == "!" and "alert" in s.drain_events()


def test_losing_hans_sends_him_to_look_then_home():
    s = guard(route=((3.5, 2.5), (3.6, 2.5)), facing=0.0)
    run(s, FakeHans((8.5, 2.5)), 0.5)           # a proper look, not a glimpse
    gone = FakeHans((-9, -9))
    run(s, gone, 1.5)
    assert s.state == "INVESTIGATE"
    run(s, gone, 12)
    assert s.state in ("RETURN", "PATROL")


def test_a_mere_glimpse_is_shrugged_off():
    s = guard(route=((3.5, 2.5), (3.6, 2.5)), facing=0.0)
    run(s, FakeHans((8.5, 2.5)), 0.1)
    run(s, FakeHans((-9, -9)), 1.5)
    assert s.state in ("RETURN", "PATROL")


def test_noise_brings_him_over():
    s = guard()
    s.hear(Noise((10.5, 4.5), 20))
    assert s.state == "INVESTIGATE" and s.target == (10.5, 4.5)


def test_colleague_whistle():
    s = guard()
    s.alert((12.5, 3.5))
    assert s.state == "INVESTIGATE"


def test_sentry_sweeps_but_stays():
    s = guard(route=((10.5, 2.5),), facing=math.pi / 2)
    angles = []
    for _ in range(90):
        s.update(1 / 30, FakeHans((-9, -9)))
        angles.append(s.angle)
    assert s.pos == (10.5, 2.5) and max(angles) - min(angles) > 0.5


def test_watcher_keeps_lantern_on_a_point():
    s = guard(watch=(9.5, 4.5))
    run(s, FakeHans((-9, -9)), 3)
    to_point = math.atan2(4.5 - s.pos[1], 9.5 - s.pos[0])
    assert abs((s.angle - to_point + math.pi) % (2 * math.pi) - math.pi) < 0.4


def test_tired_scientists_are_slower():
    fast, slow = guard(), guard(slow=0.76)
    run(fast, FakeHans((-9, -9)), 3)
    run(slow, FakeHans((-9, -9)), 3)
    assert slow.pos[0] < fast.pos[0]
