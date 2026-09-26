"""HOUND (charger): closes in fast and rams you. Bait it into a wall and it's yours.

Combat states:
    ENGAGE   thinking
    STALK    A* toward you (or where it last knew you were)
    CIRCLE   has you in range but no attack token: circles at ~4.5 tiles, waiting its turn
    WINDUP   plants its feet; an orange line shows the charge path (to the wall, or 8 tiles).
             The line follows you, then flashes white and locks.
    CHARGE   rushes down the locked line at 15 tiles/s. Hits you: a heart. Hits a wall: DAZED.
    DAZED    stunned for 1.6 s and EXPOSED: your shots do double damage
    RECOVER  a short breather after a charge that hit nothing

Utility:  charge  sees you, 2-7 tiles, token free, recovered:  0.9
          stalk   can't see you / too far:                       0.6
          circle  sees you:                                      0.4
"""

import math

from game import config as C
from game.ai.agent import REACTION, Enemy, STUNNED
from game.ai.fsm import State
from game.geometry import angle_to, distance, from_angle, normalize

WINDUP = 0.65
CHARGE_SPEED = 15.0
CHARGE_DIST = 9.0
DAZE = 1.6


class Charger(Enemy):
    kind = "charger"
    name = "HOUND"
    base_hp = 6.0
    speed = 4.4
    radius = 0.34
    worth = 100

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.charge_len = 0.0
        self.travelled = 0.0
        self.orbit = 1

    def combat_state(self):
        return ENGAGE

    def states_for(self, action):
        return {"charge": (WINDUP_, CHARGE), "stalk": (STALK,), "circle": (CIRCLE,)}[action]

    def options(self):
        sees = self.senses.sees
        d = distance(self.pos, self.target())
        token = self.room.coordinator.can_attack(self, self.now)
        self.blocked = sees and not self.clear_shot(self.target(), 0.35)
        return {"charge": 0.9 if sees and 2.0 <= d <= 7.0 and token and self.cooldown <= 0 and not self.blocked
                else 0.0,
                "stalk": 0.6 if (not sees or d > 7.0) else 0.0,
                "circle": 0.4 if sees else 0.0}

    def feasible(self, action):
        if action == "charge":
            return self.room.coordinator.acquire(self, self.now)
        return True

    def charge_path(self) -> float:
        wall = self.room.grid.raycast(self.pos, self.aim, CHARGE_DIST + 1)
        return max(0.0, min(CHARGE_DIST, wall - self.radius))


class Engage(State):
    name = "ENGAGE"

    def enter(self, h):
        h.think = REACTION
        h.windup = 0.0

    def update(self, h, dt):
        h.brake(dt)
        h.face_foe(dt)
        h.rethink(dt)


class Stalk(State):
    name = "STALK"

    def enter(self, h):
        h.timer = 0.0
        h.go_to(h.target())

    def update(self, h, dt):
        h.timer -= dt
        if h.timer <= 0:
            h.timer = 0.3
            h.go_to(h.target())
            h.spot = h.target()
        h.follow(dt, h.speed)
        h.rethink(dt)


class Circle(State):
    name = "CIRCLE"

    def enter(self, h):
        h.path = []
        h.orbit = h.room.rng.choice((-1, 1))

    def update(self, h, dt):
        to = angle_to(h.pos, h.foe.pos)
        d = distance(h.pos, h.foe.pos)
        radial = 0.7 if d > 5.2 else (-0.7 if d < 3.8 else 0.0)
        side = from_angle(to + h.orbit * math.pi / 2)
        want, _ = normalize((side[0] + math.cos(to) * radial, side[1] + math.sin(to) * radial))
        before = h.pos
        h.steer(want, dt, h.speed * 0.6)
        if distance(before, h.pos) < h.speed * 0.15 * dt:
            h.orbit *= -1
        h.face(to, dt)
        h.rethink(dt)


class Windup(State):
    name = "WINDUP"

    def enter(self, h):
        h.path = []
        h.windup = 0.0
        h.locked = False
        h.aim = angle_to(h.pos, h.target())
        h.room.sound("growl")

    def update(self, h, dt):
        h.brake(dt)
        windup = WINDUP * h.room.tuning["windup"]
        h.windup = min(1.0, h.windup + dt / windup)
        if not h.locked:
            h.aim = angle_to(h.pos, h.target())
            h.facing = h.aim
            if h.windup >= 1 - C.LOCK_TIME / windup:
                h.locked = True
        h.charge_len = h.charge_path()
        if h.windup >= 1:
            h.fsm.change(CHARGE)


class Charge(State):
    name = "CHARGE"

    def enter(self, h):
        h.travelled = 0.0
        h.windup = 0.0
        h.room.sound("dash")

    def update(self, h, dt):
        direction = from_angle(h.aim)
        step = CHARGE_SPEED * dt
        before = h.pos
        h.vel = (direction[0] * CHARGE_SPEED, direction[1] * CHARGE_SPEED)
        h.pos = h.room.grid.move(h.pos, (direction[0] * step, direction[1] * step), h.radius)
        moved = distance(before, h.pos)
        h.travelled += moved
        h.room.trail(h)
        struck = next((t for t in h.hostiles() if distance(h.pos, t.pos) < h.radius + t.radius + 0.1), None)
        if struck is not None:
            h.room.strike(h, struck, 1)
            self.finish(h)
            h.fsm.change(RECOVER)
        elif moved < step * 0.5 or (h.travelled >= h.charge_len and h.charge_len < CHARGE_DIST - 0.05):
            self.finish(h)                               # slammed into a wall (the line ended at one)
            h.exposed = True
            h.room.slam(h)
            h.stun = DAZE
            h.fsm.change(STUNNED)
        elif h.travelled >= h.charge_len:
            self.finish(h)
            h.fsm.change(RECOVER)

    @staticmethod
    def finish(h):
        h.vel = (0.0, 0.0)
        h.locked = False
        h.room.coordinator.release(h)
        h.cooldown = h.room.rng.uniform(0.8, 1.3)
        h.action = ""


class Recover(State):
    name = "RECOVER"

    def enter(self, h):
        h.timer = 0.0

    def update(self, h, dt):
        h.timer += dt
        h.brake(dt)
        if h.timer > 0.45:
            h.fsm.change(ENGAGE)


ENGAGE, STALK, CIRCLE, WINDUP_, CHARGE, RECOVER = Engage(), Stalk(), Circle(), Windup(), Charge(), Recover()
