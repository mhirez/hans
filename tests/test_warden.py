from tests.helpers import arena, place, step


def test_warden_changes_phase_with_a_shield_and_reinforcements():
    room = arena()
    w = place(room, "warden", (20.0, 9.0))
    room.boss = w
    w.shield = 0.0
    w.take_hit(w.max_hp * 0.4, (1, 0), room.player.pos)
    assert w.phase == 2 and w.shield > 0
    assert w.take_hit(5.0, (1, 0), room.player.pos) == 0.0     # shielded
    assert w.ready["summon"] == 0.0


def test_warden_never_keeps_more_minions_than_its_cap():
    room = arena()
    w = place(room, "warden", (20.0, 9.0))
    for _ in range(4):
        room.summon(w, ["grunt", "grunt", "grunt"], w.minion_cap)
        step(room, 1.3)
    assert sum(1 for e in room.enemies if e is not w) <= w.minion_cap


def test_sweep_laser_is_stopped_by_cover():
    room = arena(blocks=[(12, 7, 1, 4)])
    w = place(room, "warden", (20.0, 9.0))
    from game.ai.warden import _on_beam
    import math
    length = room.grid.raycast(w.pos, math.pi, 40)
    assert not _on_beam(w.pos, math.pi, length, (8.0, 9.0), 0.4)    # hiding behind the block
    assert _on_beam(w.pos, math.pi, length, (15.0, 9.0), 0.4)
