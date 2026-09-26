"""Oskar Pfungst: the psychologist who worked out Clever Hans's secret. Here, the boss who reads YOU.

He arrives every fifth wave. While he's on the field the Commission's orders come twice as fast
(tactics.py), and he fights with the player model (playermodel.py), everything the scientists
have seen of how you escape their attacks:

    STALK        closes in (A*), stopping just outside the range you usually kick from
    READ         winds up his net and predicts where you'll dodge: the side you've dodged to most.
                 A chalk X marks his guess (you can read HIS tell, as Hans read people).
                 When the net comes down he checks which way you actually went (the same classifier
                 the player model uses). Standing still, or dodging the side he's netting, gets you
                 caught; dodging another way, or getting clean out of reach, makes him miss.
    OFF-BALANCE  a wrong read leaves him stumbling for a moment: your chance to kick.

He also thinks one step deeper. The player model records how you reply to his chalk X. If you
usually dodge AWAY from it (you're reading him, as Hans read people), he BLUFFS: he still draws
the X on his first guess, but nets the opposite side. How often he bluffs is how often you've
dodged away (a mixed strategy, so he can't be read either). Level-2 reasoning: "he knows that I
know". Beat him by not being predictable at all.

Five kicks to stop him. He drinks coffee to think, and says what he's thinking.
"""

import math

from game.config import REPLAN_TIME
from game.ai.playermodel import PlayerModel, OPPOSITE
from game.ai.scientist import Scientist
from game.ai.state_machine import State
from game.level import distance, angle_to

PFUNGST_HP = 5
PFUNGST_SPEED = 3.4
PFUNGST_WINDUP = 0.85
PFUNGST_REACH = 1.9          # starts reading from this close
PFUNGST_LUNGE = 6.0          # he THROWS the net where he predicts: running fast the way he guessed won't save you
STILL = 0.35                 # moved less than this: "didn't dodge at all"
BLUFFING = True              # tools/pfungst_lab.py switches this off to measure what bluffing adds


class Stalk(State):
    name = "STALK"

    def enter(self, p):
        p.replan = 0.0

    def update(self, p, dt):
        if p.lost_him():
            return
        hans = p.world.hans
        target = hans.pos if p.sees_hans else p.last_seen
        p.replan -= dt
        if p.replan <= 0:
            p.go_to(target)
            p.replan = REPLAN_TIME
        d = distance(p.pos, hans.pos)
        keep_out = max(1.2, p.world.model.kick_range + 0.2) if p.world.hans.can_kick() else 0.0
        if d > keep_out:
            p.walk(dt, p.run_speed * p.scale)
        if p.sees_hans:
            p.face(hans.pos, dt)
            if d <= PFUNGST_REACH:
                p.fsm.change(READ)
                return
        p.every(dt, lambda: p.decide() != "attack" and p.act())


class Read(State):
    name = "READ"

    def enter(self, p):
        p.timer = 0.0
        p.swung = False
        p.path = []
        hans = p.world.hans
        p.aim_from = hans.pos                                    # where Hans stood when the read began
        p.pred_side, p.pred_conf = p.world.model.predict()
        reads_x = p.world.model.reads_the_x()
        p.bluffing = (BLUFFING and p.pred_side in OPPOSITE and reads_x > 0.5 and p.rng.random() < reads_x)
        p.net_side = OPPOSITE[p.pred_side] if p.bluffing else p.pred_side
        p.pred_spot = p.world.model.landing_spot(p.pos, hans.pos, p.pred_side, reach=1.6)
        p.events.append("windup")
        p.events.append("bluff" if p.bluffing else "read")

    def update(self, p, dt):
        hans = p.world.hans
        p.timer += dt
        if not p.swung:
            p.face(hans.pos, dt * 0.6)
            if p.timer >= p.windup(PFUNGST_WINDUP):
                p.swung = True
                p.events.append("swing")
                p.dodged = p.dodge_side(hans.pos)
                p.world.model.saw_reply_to_x(p.pred_side, p.dodged)
                if p.catches(hans.pos, p.dodged):
                    p.fooled = 0
                    p.world.hit_hans(p, "net")
                    p.events.append("bluffed" if p.bluffing else "predicted")
                else:
                    p.fooled += 1
                    p.events.append("surprised")
                    p.fsm.change(OFF_BALANCE)
        elif p.timer >= p.windup(PFUNGST_WINDUP) + 0.6:
            p.act(force=True)

    @staticmethod
    def progress(p) -> float:
        return min(1.0, p.timer / p.windup(PFUNGST_WINDUP)) if not p.swung else 0.0


class OffBalance(State):
    name = "OFF-BALANCE"

    def enter(self, p):
        p.timer = 0.0
        p.pred_spot = None
        a = angle_to(p.world.hans.pos, p.pos)
        p.knockback = (math.cos(a) * 1.5, math.sin(a) * 1.5)

    def update(self, p, dt):
        p.timer += dt
        if p.timer > 1.4:
            p.act(force=True)


STALK, READ, OFF_BALANCE = Stalk(), Read(), OffBalance()


class Pfungst(Scientist):
    kind = "pfungst"
    name = "Oskar Pfungst"
    max_hp = PFUNGST_HP
    aggression = 1.4
    cowardice = 0.15
    wander_speed = 1.9
    run_speed = PFUNGST_SPEED

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pred_side = None
        self.pred_conf = 0.0
        self.pred_spot = None
        self.aim_from = None
        self.net_side = None
        self.dodged = None
        self.bluffing = False
        self.fooled = 0                              # wrong reads in a row
        self.events.append("arrive")

    def attack_state(self):
        return STALK

    def dodge_side(self, hans_pos):
        """Which way did Hans go since the read began? None if he stayed put."""
        if distance(self.aim_from, hans_pos) < STILL:
            return None
        return PlayerModel.classify(self.pos, self.aim_from, hans_pos)

    def catches(self, hans_pos, side) -> bool:
        if distance(self.pos, hans_pos) > PFUNGST_LUNGE:
            return False                             # clean out of reach
        return side is None or side == self.net_side
