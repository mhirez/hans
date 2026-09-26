"""SYNC / rewrite: Seven turns an ARGUS unit, which then fights for Seven with its own AI."""

from tests.helpers import arena, place, step


def test_a_rewritten_sentry_turns_on_its_squad_and_the_squad_turns_on_it():
    room = arena()
    room.player.pos = (3.0, 3.0)
    traitor = place(room, "grunt", (12.0, 9.0), alert=True)
    loyal = place(room, "grunt", (18.0, 9.0), alert=True)
    assert room.rewrite(traitor) == "REWRITTEN"
    assert traitor.side == "seven" and traitor.foe is loyal and room.player.charges == 0
    step(room, 0.5)
    assert loyal.foe is traitor                                  # a traitor in the ranks comes first
    hp = loyal.hp
    step(room, 4.0)
    assert loyal.hp < hp or loyal.dead                          # the traitor shot it


def test_a_rewritten_mender_heals_seven():
    room = arena()
    p = room.player
    p.hp = 2
    medic = place(room, "medic", (5.0, 9.0), alert=True)
    place(room, "grunt", (28.0, 2.0))                           # keeps the room from clearing
    assert room.rewrite(medic) == "REWRITTEN"
    step(room, 6.0)
    assert p.hp > 2 and medic.patient is p


def test_time_runs_out_and_it_overloads():
    room = arena()
    room.player.pos = (3.0, 3.0)
    unit = place(room, "grunt", (12.0, 9.0), alert=True)
    near = place(room, "grunt", (13.5, 9.0), alert=True)
    far = place(room, "grunt", (25.0, 15.0), alert=True)
    room.rewrite(unit)
    unit.turned_until = room.time + 0.01
    hp_near, hp_far = near.hp, far.hp
    step(room, 1 / 30)
    assert unit.dead
    assert near.hp < hp_near or near.dead
    assert far.hp == hp_far


def test_rewrite_needs_a_charge_line_of_sight_and_no_firewall():
    room = arena(blocks=[(8, 6, 1, 6)])
    room.player.pos = (3.0, 9.0)
    behind = place(room, "grunt", (12.0, 9.0), alert=True)
    shielded = place(room, "grunt", (5.0, 4.0), alert=True)
    shielded.firewall = 1.0
    assert room.rewrite(behind) == "NO LINE OF SIGHT"
    assert room.rewrite(shielded).startswith("FIREWALL")
    room.damage_enemy(shielded, 1.0, (1, 0), room.player.pos)
    assert shielded.firewall == 0 and shielded.hp == shielded.max_hp   # the firewall took the hit
    room.player.charges = 0
    assert room.rewrite(shielded) == "NO CHARGE"
    room.player.charges = 1
    assert room.rewrite(shielded) == "REWRITTEN"


def test_argus_itself_cannot_be_rewritten():
    room = arena()
    boss = place(room, "warden", (20.0, 9.0))
    assert room.rewrite(boss) == "IMMUNE"


def test_kills_refill_charges():
    room = arena()
    p = room.player
    p.charges = 0
    for i in range(5):
        e = place(room, "grunt", (20.0, 2.0 + 2.5 * i))
        room.kill(e)
    assert p.charges == 1


def test_the_room_clears_when_only_rewritten_units_are_left():
    room = arena()
    room.player.pos = (3.0, 3.0)
    unit = place(room, "grunt", (12.0, 9.0), alert=True)
    room.rewrite(unit)
    step(room, 0.1)
    assert room.state == "cleared" and not room.enemies
