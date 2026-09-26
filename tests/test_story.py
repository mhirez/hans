"""The data-center story rules: crossfire between ARGUS's robots, and the upload deadline."""

import math
import random

from game import config as C
from game.ai.warden import SWEEP
from game.projectiles import Bullet
from game.rooms import plan
from game.run import Run
from tests.helpers import arena, place, step


def test_a_robots_bullet_hurts_another_robot():
    room = arena()
    room.player.pos = (3.0, 3.0)
    shooter = place(room, "grunt", (10.0, 9.0), alert=True)
    victim = place(room, "grunt", (12.0, 9.0), alert=True)
    hp = victim.hp
    room.bullets.append(Bullet((10.6, 9.0), (10.0, 0.0), 0.16, 1, "argus", shooter, life=2.0))
    step(room, 0.2)
    assert victim.hp < hp and room.stats["crossfire"] == 1
    assert shooter.hp == shooter.max_hp                          # never its own bullet


def test_robots_hold_fire_when_a_friend_is_in_the_way():
    room = arena()
    room.player.pos = (4.0, 9.0)
    shooter = place(room, "grunt", (14.0, 9.0), alert=True)
    place(room, "grunt", (9.0, 9.0), alert=True)                 # right in the line of fire
    shooter.cooldown = 0.0
    step(room, 0.05)
    options = shooter.options()
    assert shooter.blocked and options["shoot"] == 0.0 and options["strafe"] > 0.5
    assert shooter.clear_shot((14.0, 2.0))                       # a different line is clear


def test_argus_sweeps_its_laser_through_its_own_robots():
    room = arena()
    boss = place(room, "warden", (20.0, 9.0))
    minion = place(room, "grunt", (15.0, 9.0), alert=True)
    room.player.pos = (3.0, 2.0)
    boss.sweep_from, boss.sweep_dir = math.pi, 1
    boss.fsm.change(SWEEP)
    hp = minion.hp
    step(room, 0.05)
    assert minion.hp < hp


def test_if_the_upload_reaches_100_percent_argus_gets_out():
    run = Run(seed=1)
    run.time = C.UPLOAD_TIME * 0.5 + 0.1
    run.update(1 / 60, (0, 0), (5, 5), False, False)
    assert 25 in run.announced and 50 in run.announced and run.state == "room"
    run.time = C.UPLOAD_TIME
    run.update(1 / 60, (0, 0), (5, 5), False, False)
    assert run.state == "lost" and run.killer == "upload"


def test_rooms_are_named_like_a_data_center():
    rng = random.Random(0)
    assert plan(1, 1, rng).name == "SERVER HALL A"
    assert plan(3, 3, rng).name == "THE CORE" and plan(3, 3, rng).floor_name == "SUB-LEVEL 3"
