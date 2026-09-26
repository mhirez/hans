"""v0.4.2: the player model, the tactics blackboard, Pfungst's reads (and bluffs), von Osten."""

from types import SimpleNamespace

from game.ai.pfungst import Pfungst, READ
from game.ai.playermodel import PlayerModel, SIDES
from game.ai.scientist import Scientist, SWING
from game.ai.tactics import Tactics
from game.ai.vonosten import VonOsten, DECIDE_EVERY
from game.entities.hans import Hans
from game.level import Level, distance
from game.match import Item
from tests.test_enemies import World, YARD, make


def attacker(uid=1, pos=(0.0, 0.0)):
    return SimpleNamespace(uid=uid, pos=pos)


# --- the player model ------------------------------------------------------------------------
def test_every_side_is_classified_the_way_it_is_predicted():
    a, h = (3.0, 3.0), (5.0, 4.0)
    for side in SIDES:
        assert PlayerModel.classify(a, h, PlayerModel().landing_spot(a, h, side)) == side


def test_model_learns_the_players_favourite_dodge():
    m = PlayerModel()
    for _ in range(3):
        m.attack_started(attacker(), (2.0, 0.0))
        assert m.attack_released(attacker(), m.landing_spot((0.0, 0.0), (2.0, 0.0), "left")) == "left"
    side, p = m.predict()
    assert side == "left" and abs(p - 4 / 7) < 1e-9          # 1 prior + 3 seen, out of 4 + 3


def test_standing_still_teaches_the_model_nothing():
    m = PlayerModel()
    m.attack_started(attacker(), (2.0, 0.0))
    assert m.attack_released(attacker(), (2.1, 0.0)) is None
    assert all(n == 1.0 for n in m.dodges.values())


# --- the tactics blackboard ------------------------------------------------------------------
def field(hans_pos, velocity, items, enemies=()):
    return SimpleNamespace(level=Level(YARD), hans=Hans(hans_pos), hans_velocity=velocity,
                           items=list(items), enemies=list(enemies))


def chaser(uid, pos):
    return SimpleNamespace(uid=uid, pos=pos, kind="scientist", aware=True, guard=False, state="CHASE",
                           role=None, events=[])


def test_goal_recognition_follows_where_hans_is_heading():
    east, south = Item("carrot", (15.5, 2.5), 1), Item("carrot", (4.5, 5.5), 2)
    m = field((4.5, 2.5), (4.0, 0.0), [east, south])
    t = Tactics()
    for _ in range(30):
        t.update(m, 1 / 30)
    assert t.goal is east and t.goal_conf > 0.6
    m.hans_velocity = (0.0, 4.0)                              # he turns toward the other carrot
    for _ in range(45):
        t.update(m, 1 / 30)
    assert t.goal is south


def test_roles_chaser_blocker_flanker():
    carrot = Item("carrot", (17.5, 2.5), 1)
    near, by_goal, behind = chaser(1, (7.5, 2.5)), chaser(2, (16.5, 4.5)), chaser(3, (2.5, 5.5))
    m = field((5.5, 2.5), (4.0, 0.0), [carrot], [near, by_goal, behind])
    t = Tactics()
    t.update(m, 1 / 30)
    assert t.roles == {1: "chaser", 2: "blocker", 3: "flanker"}
    assert "blocker" in by_goal.events and "flanker" in behind.events
    spot, role = t.target_for(by_goal, m)
    assert role == "blocker" and spot[0] < carrot.pos[0]        # stands on Hans's side of the carrot


def test_a_tired_or_hurt_hans_gets_pressed():
    m = field((5.5, 2.5), (0.0, 0.0), [], [chaser(1, (7.5, 2.5))])
    t = Tactics()
    t.update(m, 1 / 30)
    assert not t.pressing
    m.hans.hearts = 1
    t.update(m, 1 / 30)
    assert t.pressing and "weak" in m.enemies[0].events


# --- Pfungst -----------------------------------------------------------------------------------
def pfungst_reading(habit="left", reads_x=False):
    w = World(hans_pos=(8.3, 2.5))
    w.model = PlayerModel()
    w.model.dodges[habit] = 10.0
    if reads_x:
        w.model.x_replies["away"] = 9.0                       # Hans has been dodging away from the X
    p = make(Pfungst, w, (6.5, 2.5))
    p.rng.random = lambda: 0.0                                # always bluff when he wants to
    p.fsm.change(READ)
    return w, p


def finish(w, p, seconds=1.0, dt=1 / 60):
    for _ in range(int(seconds / dt)):
        p.update(dt, w)
        if p.swung:
            break


def test_pfungst_nets_the_dodge_he_predicted():
    w, p = pfungst_reading("left")
    assert p.pred_side == "left" and not p.bluffing
    w.hans.pos = w.model.landing_spot(p.pos, w.hans.pos, "left")
    finish(w, p)
    assert "net" in w.hits and "predicted" in p.events and p.fooled == 0


def test_pfungst_nets_you_if_you_stand_still():
    w, p = pfungst_reading("left")
    finish(w, p)
    assert "net" in w.hits


def test_a_new_dodge_throws_pfungst_off_balance():
    w, p = pfungst_reading("left")
    w.hans.pos = w.model.landing_spot(p.pos, w.hans.pos, "right")
    finish(w, p)
    assert not w.hits and p.state == "OFF-BALANCE" and p.fooled == 1


def test_pfungst_bluffs_a_player_who_reads_his_x():
    w, p = pfungst_reading("left", reads_x=True)
    assert p.bluffing and p.pred_side == "left" and p.net_side == "right"
    w.hans.pos = w.model.landing_spot(p.pos, w.hans.pos, "right")   # away from the chalk X...
    finish(w, p)
    assert "net" in w.hits and "bluffed" in p.events               # ...which is what he expected


def test_pfungst_learns_whether_you_read_his_x():
    m = PlayerModel()
    assert m.reads_the_x() == 0.5
    for _ in range(4):
        m.saw_reply_to_x("left", "right")                          # X on the left, Hans went right
    m.saw_reply_to_x("left", "left")
    assert abs(m.reads_the_x() - 5 / 7) < 1e-9
    w, p = pfungst_reading("left")
    assert not p.bluffing                                           # no reason to bluff a stranger


# --- von Osten ---------------------------------------------------------------------------------
def with_von_osten(hans_pos, pos):
    w = World(hans_pos=hans_pos)
    w.tactics = Tactics()
    v = VonOsten(w.level, pos)
    v.world = w
    v.decide_timer = DECIDE_EVERY                                   # think on the first frame
    return w, v


def test_von_osten_grabs_a_net_mid_swing():
    w, v = with_von_osten((7.7, 2.5), (6.5, 4.5))
    s = make(Scientist, w, (6.5, 2.5))
    s.aware, s.last_seen = True, w.hans.pos
    s.fsm.change(SWING)
    for _ in range(40):
        s.update(1 / 60, w)
        v.update(1 / 60, w)
    assert s.state == "STUNNED" and "grappled" in s.events and not w.hits
    assert v.winded > 0


def test_von_osten_distracts_a_scientist_on_command():
    w, v = with_von_osten((3.5, 1.5), (4.5, 1.5))
    s = make(Scientist, w, (12.5, 5.5), facing=3.14)
    assert v.order_distract() and v.state == "DISTRACT"
    seen = set()
    for _ in range(240):
        s.update(1 / 60, w)
        v.update(1 / 60, w)
        seen.add(s.state)
    assert "DISTRACTED" in seen and not v.order_distract()           # then he needs a rest


def test_von_osten_nods_at_sugar_when_hans_is_hurt():
    w, v = with_von_osten((2.5, 1.5), (3.5, 1.5))
    w.hans.hearts = 1
    sugar = Item("sugar", (18.5, 5.5), 7)
    w.items.append(sugar)
    for _ in range(300):
        v.update(1 / 60, w)
    assert v.state == "POINT" and v.item is sugar
    assert v.nodding and distance(v.pos, sugar.pos) < 3.5


def test_von_osten_shouts_down_a_growling_dog():
    from game.ai.dog import Dog, POUNCE
    w, v = with_von_osten((8.5, 1.5), (6.5, 1.5))
    d = make(Dog, w, (5.5, 2.5))
    d.aware, d.last_seen = True, w.hans.pos
    d.fsm.change(POUNCE)
    for _ in range(20):
        d.update(1 / 60, w)
        v.update(1 / 60, w)
    assert d.state == "STUNNED" and "shoo" in v.events and not w.hits
