"""LENS (sniper): keeps its distance, finds a long sight line, and fires one fast round.

Combat states:
    ENGAGE    thinking
    POSITION  walks to a scored firing spot 7-12 tiles from you with a clear line; after every
              shot it RELOCATES (the new spot must be 3+ tiles from the old one)
    AIM       a purple laser tracks you for 0.9 s (it stops at walls: hide behind something!),
              then flashes white and locks for 0.25 s, then fires a 24 tiles/s round
    EVADE     you got within 4.5 tiles: it runs for the spot furthest from you

Utility:  evade     you're within 4.5 tiles:                       0.95
          shoot     sees you, 4+ tiles away, reloaded, token free:  0.9
          position  otherwise:                                      0.5
"""

from game import config as C
from game.ai.agent import REACTION, Enemy, muzzle
from game.ai.fsm import State
from game.geometry import angle_to, center, distance, tile_of

TRACK = 0.8
SNIPE_SPEED = 24.0


class Sniper(Enemy):
    kind = "sniper"
    name = "LENS"
    base_hp = 5.0
    speed = 2.9
    radius = 0.32
    worth = 150
    view_range = 13.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spot_tile = None
        self.last_perch = None
        self.laser_len = 0.0

    def combat_state(self):
        return ENGAGE

    def states_for(self, action):
        return {"shoot": (AIM,), "position": (POSITION,), "evade": (EVADE,)}[action]

    def options(self):
        sees = self.senses.sees
        d = distance(self.pos, self.foe.pos)
        token = self.room.coordinator.can_attack(self, self.now)
        return {"evade": 0.95 if d < 4.5 else 0.0,
                "shoot": 0.9 if sees and d >= 4.0 and self.cooldown <= 0 and token else 0.0,
                "position": 0.5}

    def feasible(self, action):
        tactics = self.room.tactics
        if action == "shoot":
            return self.room.coordinator.acquire(self, self.now)
        if action == "position":
            self.spot_tile = tactics.firing_spot(self, self.target(), 7.0, 12.0, radius=9,
                                                 prefer_far=True, avoid=self.last_perch)
            return self.spot_tile is not None
        if action == "evade":
            self.spot_tile = tactics.escape_spot(self, self.foe.pos)
            return self.spot_tile is not None
        return True


class Engage(State):
    name = "ENGAGE"

    def enter(self, s):
        s.think = REACTION
        s.windup = 0.0

    def update(self, s, dt):
        s.brake(dt)
        s.face_foe(dt)
        s.rethink(dt)


class Position(State):
    name = "POSITION"

    def enter(self, s):
        s.timer = 0.0
        s.room.tactics.claim(s, s.spot_tile)
        s.spot = center(s.spot_tile)
        s.go_to(s.spot)

    def exit(self, s):
        s.room.tactics.claim(s, None)

    def update(self, s, dt):
        s.timer += dt
        arrived = s.follow(dt, s.speed, face=not s.senses.sees)
        if s.senses.sees:
            s.face(angle_to(s.pos, s.foe.pos), dt)
        if arrived:
            s.last_perch = None
        if arrived or s.timer > 5:
            s.action = ""
            s.think = min(s.think, 0.1)
        s.rethink(dt)


class Aim(State):
    name = "AIM"

    def enter(self, s):
        s.path = []
        s.windup = 0.0
        s.locked = False
        s.blind = 0.0
        s.aim = angle_to(s.pos, s.target())
        s.room.sound("laser")

    def update(self, s, dt):
        s.brake(dt)
        total = (TRACK + C.LOCK_TIME) * s.room.tuning["windup"]
        s.windup = min(1.0, s.windup + dt / total)
        if not s.locked:
            if s.senses.sees:
                s.blind = 0.0
                s.aim = angle_to(s.pos, s.foe.pos)
            else:
                s.blind += dt
                if s.blind > 0.25:
                    self.done(s, cooldown=0.4)
                    return
            s.facing = s.aim
            if s.windup >= 1 - C.LOCK_TIME / total:
                s.locked = True
        s.laser_len = s.room.grid.raycast(s.pos, s.aim, 30)
        if s.windup >= 1:
            s.room.enemy_shot(s, muzzle(s, s.aim), s.aim, SNIPE_SPEED * s.room.tuning["bullet"], heavy=True)
            s.last_perch = tile_of(s.pos)
            self.done(s, cooldown=s.room.rng.uniform(1.4, 2.0))

    @staticmethod
    def done(s, cooldown):
        s.windup = 0.0
        s.locked = False
        s.room.coordinator.release(s)
        s.cooldown = cooldown
        s.action = ""
        s.fsm.change(ENGAGE)


class Evade(State):
    name = "EVADE"

    def enter(self, s):
        s.timer = 0.0
        s.room.tactics.claim(s, s.spot_tile)
        s.spot = center(s.spot_tile)
        s.go_to(s.spot)

    def exit(self, s):
        s.room.tactics.claim(s, None)

    def update(self, s, dt):
        s.timer += dt
        if s.follow(dt, s.speed * 1.3) or s.timer > 3:
            s.action = ""
            s.think = 0.0
        s.rethink(dt)


ENGAGE, POSITION, AIM, EVADE = Engage(), Position(), Aim(), Evade()
