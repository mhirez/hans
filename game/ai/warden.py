"""ARGUS: the mind of the facility, met in person at the end of floor 3 (its body is "the warden").

Named after the hundred-eyed watchman of Greek myth: every camera and sensor in ARGUS DEEP is
one of its eyes. It is the one unit Seven can never rewrite.

Three PHASES by health (100-66%, 66-33%, 33-0%). Each phase change: a shockwave, a moment of
invulnerability, reinforcements, and new attacks. Between attacks it decides with utility
scores, and every attack has its own cooldown so it never repeats itself too much.

    VOLLEY    a fan of 7 rounds at you (phase 2+: a second, offset fan)
    RING      a ring of rounds all round it (phase 3: two rings)
    SWEEP     a laser that sweeps through 120 degrees. Walls stop it: get behind cover
    CHARGE    (phase 2+) rams at you like a hound; hits a wall -> DAZED and EXPOSED for 2 s
    SUMMON    warps in reinforcements (at most 2 alive, 3 in the last phase)

Every attack is telegraphed in the same language as the other enemies: it glows while it
charges, shows where the attack will go, then flashes white and locks.
"""

import math

from game import config as C
from game.ai.agent import Enemy, STUNNED
from game.ai.fsm import State
from game.geometry import angle_diff, angle_to, band, distance, from_angle, normalize

WINDUPS = {"volley": 0.8, "ring": 0.9, "sweep": 1.0, "charge": 0.8, "summon": 0.9}
COOLDOWNS = {"volley": 2.2, "ring": 4.0, "sweep": 6.0, "charge": 5.0, "summon": 9.0}
SWEEP_ARC = math.radians(120)
SWEEP_TIME = 1.5
CHARGE_SPEED = 13.0


class Warden(Enemy):
    kind = "warden"
    name = "ARGUS"
    base_hp = 95.0
    speed = 1.8
    radius = 0.9
    worth = 2500
    view_range = 40.0
    hackable = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alert = True
        self.phase = 1
        self.shield = 1.6                  # invulnerable while it introduces itself / changes phase
        self.ready = {k: 1.0 for k in COOLDOWNS}
        self.ready["summon"] = 3.0
        self.attack = ""
        self.sweep_from = 0.0
        self.sweep_dir = 1
        self.beam_len = 0.0
        self.travelled = 0.0
        self.spin = 0.0
        self.fsm.change(ENGAGE)

    def combat_state(self):
        return ENGAGE

    def states_for(self, action):
        return {"move": (DRIFT,)}.get(action, (WINDUP,))

    def update(self, dt):
        self.shield = max(0.0, self.shield - dt)
        self.spin += dt * (1.5 + self.phase)
        for k in self.ready:
            self.ready[k] = max(0.0, self.ready[k] - dt)
        super().update(dt)

    def perceive(self, dt):
        self.senses.update(self, dt)             # it's always alert; it just needs to see you

    def take_hit(self, damage, direction, source, attacker=None):
        if self.shield > 0:
            return 0.0
        dealt = super().take_hit(damage, (direction[0] * 0.1, direction[1] * 0.1), source, attacker)
        phase = 1 if self.health > 0.66 else 2 if self.health > 0.33 else 3
        if phase != self.phase and not self.dead:
            self.phase = phase
            self.shield = 1.2
            self.room.boss_phase(self)
            self.ready["summon"] = 0.0
            self.fsm.change(ENGAGE)
        return dealt

    def minions(self) -> int:
        return sum(1 for e in self.room.enemies if e is not self and not e.dead)

    @property
    def minion_cap(self) -> int:
        return 3 if self.phase == 3 else 2

    def options(self):
        sees = self.senses.sees
        d = distance(self.pos, self.foe.pos)
        r = self.ready
        cap = self.minion_cap
        o = {"summon": 0.85 * (1 - self.minions() / cap) if r["summon"] <= 0 and self.minions() < cap else 0.0,
             "volley": 0.6 + 0.1 * band(d, 4, 12) if sees and r["volley"] <= 0 else 0.0,
             "ring": 0.75 if d < 5 and r["ring"] <= 0 else (0.35 if r["ring"] <= 0 else 0.0),
             "sweep": 0.7 if sees and r["sweep"] <= 0 else 0.0,
             "charge": 0.72 if self.phase >= 2 and sees and 3 < d < 11 and r["charge"] <= 0 else 0.0,
             "move": 0.3}
        return o

    def decide(self):
        self.think = 0.6 if self.phase < 3 else 0.35
        scores = self.options()
        self.scores = dict(scores)
        best = max(scores, key=scores.get)
        self.action = best
        self.attack = best
        self.fsm.change(DRIFT if best == "move" else WINDUP)


class Engage(State):
    name = "ENGAGE"

    def enter(self, w):
        w.think = 0.8 if w.shield > 0 else 0.3
        w.windup = 0.0

    def update(self, w, dt):
        w.brake(dt)
        w.face_foe(dt, 3.0)
        w.think -= dt
        if w.think <= 0 and w.shield <= 0:
            w.decide()


class Drift(State):
    """Between attacks: drift toward the middle of the room, keeping some distance from you."""
    name = "DRIFT"

    def enter(self, w):
        w.timer = 0.0
        mid = (w.room.grid.cols / 2, w.room.grid.rows / 2)
        away, _ = normalize((mid[0] - w.foe.pos[0], mid[1] - w.foe.pos[1]))
        w.spot = (mid[0] + away[0] * 2.5, mid[1] + away[1] * 2.5)
        w.go_to(w.spot)

    def update(self, w, dt):
        w.timer += dt
        w.follow(dt, w.speed * (1 + 0.25 * (w.phase - 1)), face=False)
        w.face_foe(dt, 3.0)
        if w.timer > 1.0:
            w.fsm.change(ENGAGE)


class Windup(State):
    name = "WINDUP"

    def enter(self, w):
        w.path = []
        w.windup = 0.0
        w.locked = False
        w.aim = angle_to(w.pos, w.foe.pos)
        w.sweep_dir = 1 if angle_diff(w.facing, w.aim) >= 0 else -1
        w.room.sound({"sweep": "laser", "charge": "growl", "summon": "alarm"}.get(w.attack, "charge"))

    def update(self, w, dt):
        w.brake(dt)
        total = WINDUPS[w.attack] * (0.85 if w.phase == 3 else 1.0)
        w.windup = min(1.0, w.windup + dt / total)
        if not w.locked:
            w.aim = angle_to(w.pos, w.foe.pos)
            w.facing = w.aim
            if w.windup >= 1 - C.LOCK_TIME / total:
                w.locked = True
                w.sweep_from = w.aim - w.sweep_dir * SWEEP_ARC / 2
        if w.attack == "charge":
            wall = w.room.grid.raycast(w.pos, w.aim, 20)
            w.beam_len = max(0.0, wall - w.radius)
        if w.windup >= 1:
            w.ready[w.attack] = COOLDOWNS[w.attack] * (0.75 if w.phase == 3 else 1.0)
            if w.attack == "volley":
                fans = 2 if w.phase >= 2 else 1
                for f in range(fans):
                    for i in range(7):
                        a = w.aim + math.radians(-30 + 10 * i) + (math.radians(5) if f else 0)
                        w.room.enemy_shot(w, add_out(w, a), a, (7.5 + 1.5 * f) * w.room.tuning["bullet"])
                w.fsm.change(PAUSE)
            elif w.attack == "ring":
                rings = 2 if w.phase == 3 else 1
                for k in range(rings):
                    n = 18
                    for i in range(n):
                        a = w.spin + (i + 0.5 * k) * 2 * math.pi / n
                        w.room.enemy_shot(w, add_out(w, a), a, (6.5 + 1.5 * k) * w.room.tuning["bullet"])
                w.fsm.change(PAUSE)
            elif w.attack == "summon":
                w.room.summon(w, {1: ["grunt", "grunt"], 2: ["charger", "grunt"], 3: ["medic", "grunt", "charger"]}[w.phase],
                              w.minion_cap)
                w.fsm.change(PAUSE)
            elif w.attack == "sweep":
                w.fsm.change(SWEEP)
            elif w.attack == "charge":
                w.fsm.change(CHARGE)


def add_out(w, a):
    return w.pos[0] + math.cos(a) * (w.radius + 0.2), w.pos[1] + math.sin(a) * (w.radius + 0.2)


class Sweep(State):
    name = "SWEEP"

    def enter(self, w):
        w.timer = 0.0
        w.windup = 0.0
        w.hit_this_sweep = set()

    def update(self, w, dt):
        w.timer += dt
        w.brake(dt)
        t = min(1.0, w.timer / SWEEP_TIME)
        w.aim = w.sweep_from + w.sweep_dir * SWEEP_ARC * t
        w.facing = w.aim
        w.beam_len = w.room.grid.raycast(w.pos, w.aim, 40)
        for target in w.hostiles():
            if id(target) not in w.hit_this_sweep and _on_beam(w.pos, w.aim, w.beam_len, target.pos,
                                                            target.radius + 0.15):
                w.hit_this_sweep.add(id(target))
                w.room.strike(w, target, 1)
        if t >= 1:
            w.beam_len = 0.0
            w.fsm.change(PAUSE)


def _on_beam(origin, angle, length, point, width) -> bool:
    dx, dy = math.cos(angle), math.sin(angle)
    px, py = point[0] - origin[0], point[1] - origin[1]
    along = px * dx + py * dy
    if along < 0 or along > length:
        return False
    return abs(px * dy - py * dx) < width


class Charge(State):
    name = "CHARGE"

    def enter(self, w):
        w.travelled = 0.0
        w.windup = 0.0
        w.room.sound("dash")

    def update(self, w, dt):
        direction = from_angle(w.aim)
        step = CHARGE_SPEED * dt
        before = w.pos
        w.pos = w.room.grid.move(w.pos, (direction[0] * step, direction[1] * step), w.radius)
        moved = distance(before, w.pos)
        w.travelled += moved
        w.room.trail(w)
        for target in w.hostiles():
            if distance(w.pos, target.pos) < w.radius + target.radius + 0.1:
                w.room.strike(w, target, 1)
        if moved < step * 0.5 or w.travelled > 20:
            w.room.slam(w)
            w.exposed = True
            w.stun = 2.0
            w.fsm.change(STUNNED)


class Pause(State):
    name = "RECOVER"

    def enter(self, w):
        w.timer = 0.0
        w.windup = 0.0
        w.locked = False

    def update(self, w, dt):
        w.timer += dt
        w.brake(dt)
        w.face_foe(dt, 3.0)
        if w.timer > (0.9 if w.phase == 1 else 0.7 if w.phase == 2 else 0.45):
            w.fsm.change(ENGAGE)


ENGAGE, DRIFT, WINDUP, SWEEP, CHARGE, PAUSE = Engage(), Drift(), Windup(), Sweep(), Charge(), Pause()
