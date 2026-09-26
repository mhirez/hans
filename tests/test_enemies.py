import math

from game.geometry import angle_diff, angle_to, center, distance, tile_of
from tests.helpers import arena, place, step


def test_grunt_telegraphs_then_fires_three_rounds_down_the_locked_line():
    room = arena()
    g = place(room, "grunt", (9.0, 9.0), alert=True)
    g.cooldown = 0.0
    step(room, 0.3)
    assert g.state == "AIM" and g.uid in room.coordinator.holders
    locked_at = None
    shots = []
    for _ in range(90):
        step(room, 1 / 60)
        if g.locked and locked_at is None:
            locked_at = g.aim
        shots += [b for b in room.bullets if b.hostile and b not in shots]
    assert locked_at is not None and len(shots) == 3
    assert all(abs(angle_diff(b.angle, locked_at)) < math.radians(6) for b in shots)
    assert g.uid not in room.coordinator.holders                # token handed back


def test_only_two_attack_at_once():
    room = arena()
    grunts = [place(room, "grunt", (9.0, 5.0 + 3 * i), alert=True) for i in range(3)]
    for g in grunts:
        g.cooldown = 0.0
    step(room, 0.4)
    attacking = [g for g in grunts if g.state == "AIM"]
    assert len(attacking) <= 2 and len(room.coordinator.holders) <= 2


def test_hurt_grunt_under_fire_takes_cover_somewhere_you_cannot_see():
    room = arena(blocks=[(12, 6, 2, 1), (12, 11, 2, 1), (15, 8, 1, 2)])
    g = place(room, "grunt", (11.0, 9.0), alert=True)
    g.hp = g.max_hp * 0.3
    g.hit_time = room.time
    room.coordinator.acquire(g, room.time)                       # (someone else would be shooting)
    room.coordinator.holders = {99, 98}
    g.decide()
    assert g.state == "TAKE COVER"
    spot = g.spot_tile
    assert not room.grid.sees_tile(tile_of(room.player.pos), spot)
    assert room.grid.near_cover(spot)


def test_flanker_takes_a_route_out_of_the_line_of_fire():
    room = arena(blocks=[(8, 5, 1, 9)])
    room.player.pos = (5.0, 9.0)
    pinner = place(room, "grunt", (5.0, 3.0), alert=True)
    flanker = place(room, "grunt", (14.0, 9.0), alert=True)
    step(room, 0.3)
    room.coordinator.holders = {pinner.uid, 99}                 # no token free for the flanker
    flanker.decide()
    assert flanker.state == "FLANK" and room.coordinator.flanker == flanker.uid
    target = center(flanker.spot_tile)
    turn = abs(math.degrees(angle_to(room.player.pos, target) - angle_to(room.player.pos, pinner.pos)))
    assert 50 <= min(turn, 360 - turn) <= 150


def test_charger_rams_down_its_line_and_is_dazed_by_a_wall():
    room = arena()
    room.player.pos = (4.0, 9.0)
    h = place(room, "charger", (10.0, 9.0), alert=True)
    h.cooldown = 0.0
    step(room, 0.3)
    assert h.state == "WINDUP" and h.charge_len < 9.0          # the line ends at the west wall
    while not h.locked:
        step(room, 1 / 60)
    room.player.pos = (4.0, 3.0)                                # dodge once it has locked
    for _ in range(90):
        step(room, 1 / 60)
        if h.state == "STUNNED":
            break
    assert h.state == "STUNNED" and h.exposed                   # slammed into the wall
    before = h.hp
    h.take_hit(1.0, (1, 0), room.player.pos)
    assert abs((before - h.hp) - 2.0) < 1e-9                    # exposed: double damage


def test_charger_that_connects_hurts_you():
    room = arena()
    room.player.pos = (8.0, 9.0)
    h = place(room, "charger", (12.0, 9.0), alert=True)
    h.cooldown = 0.0
    step(room, 1.5)
    assert room.player.hp < room.player.stats.max_hp


def test_sniper_laser_stops_at_cover_and_it_runs_when_you_get_close():
    room = arena(blocks=[(10, 7, 1, 4)])
    s = place(room, "sniper", (18.0, 9.0), alert=True)
    s.aim = math.pi
    s.laser_len = room.grid.raycast(s.pos, s.aim, 30)
    assert s.laser_len < 18.0 - 10.0 + 0.01
    room.player.pos = (15.0, 9.0)
    s.senses.sees = True
    s.decide()
    assert s.state == "EVADE"
    assert distance(center(s.spot_tile), room.player.pos) > distance(s.pos, room.player.pos)


def test_medic_heals_the_most_hurt_ally():
    room = arena()
    room.player.pos = (2.0, 2.0)
    g = place(room, "grunt", (20.0, 12.0), alert=True)
    m = place(room, "medic", (22.0, 12.0), alert=True)
    g.hp = g.max_hp * 0.3
    room.coordinator.holders = {90, 91}                          # keep the grunt busy
    m.decide()
    assert m.state == "HEAL" and m.patient is g
    before = g.hp
    step(room, 1.0)
    assert g.hp > before and m.beam is g or g.hp > before


def test_medic_flees_when_you_get_close():
    room = arena()
    m = place(room, "medic", (5.0, 9.0), alert=True)
    room.player.pos = (3.0, 9.0)
    m.decide()
    assert m.state == "FLEE"
