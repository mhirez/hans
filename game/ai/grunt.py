"""SENTRY (grunt): a soldier that fights like one. Shoots, takes cover when hurt, flanks.

Combat states:
    ENGAGE      thinking (decides straight away)
    AIM         stands still, a red aim line tracks you, flashes white and LOCKS, then...
    FIRE        a 3-round burst down the locked line
    STRAFE      has a line on you but no attack token / still reloading: sidesteps
    REPOSITION  can't see you, or wrong range: walks to a scored firing spot
    FLANK       someone else has you pinned: goes round to hit you from the side (A* that
                treats every tile you can see as expensive)
    TAKE COVER  hurt or under fire: runs to a scored hiding spot, then HIDE (crouches)

Utility scores (0..1, best feasible wins, +0.12 for the current action):
    shoot       sees you, reloaded, token free, NO ALLY IN THE LINE OF FIRE:
                                                 0.6 + 0.2 x health + 0.2 x (range 2.5-8.5)
    cover       hurt or under fire:              0.75 x (1 - health) + 0.35 x under fire
    strafe      sees you:                        0.35 + 0.15 x (range 3-8), +0.2 if an ally blocks
    reposition  lost sight (but fresh memory):   0.5;  sees you but too close/far: 0.45
    flank       no shot, an ally is engaged, nobody else flanking, not badly hurt: 0.62
"""

import math

from game import config as C
from game.ai.agent import REACTION, Enemy, THINK_EVERY, muzzle
from game.ai.fsm import State
from game.geometry import angle_diff, angle_to, band, center, clamp, distance, from_angle, normalize

WINDUP = 0.6
BURST = 3
BURST_GAP = 0.12
FAN = math.radians(5)                   # the 3 rounds fan out a little: step well clear of the line
# A Sentry that ARGUS taught to PREDICT brackets you instead: one round where you are, one where
# you're heading, one halfway. Dodging and running on are both covered (the three lines show it).


class Grunt(Enemy):
    kind = "grunt"
    name = "SENTRY"
    base_hp = 7.0
    speed = 3.3
    radius = 0.36
    worth = 100

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cover_ban = 0.0              # just left cover: fight for a bit before hiding again
        self.spot_tile = None
        self.fan = FAN
        self.strafe_dir = 1
        self.shots_left = 0

    def combat_state(self):
        return ENGAGE

    def states_for(self, action):
        return {"shoot": (AIM, FIRE), "cover": (TAKE_COVER, HIDE), "strafe": (STRAFE,),
                "reposition": (REPOSITION,), "flank": (FLANK,)}[action]

    def options(self):
        room, s = self.room, self.senses
        sees = s.sees
        d = distance(self.pos, self.foe.pos) if sees else distance(self.pos, self.target())
        health = self.health
        fire = self.under_fire()
        fresh = s.age(self.now) < C.MEMORY_TIME
        token = room.coordinator.can_attack(self, self.now)
        self.blocked = sees and not self.clear_shot(self.foe.pos)
        o = {}
        o["shoot"] = (0.6 + 0.2 * health + 0.2 * band(d, 2.5, 8.5)) if (
            sees and self.cooldown <= 0 and token and d < self.view_range and not self.blocked) else 0.0
        o["cover"] = 0.0 if self.now < self.cover_ban else (
            clamp(0.75 * (1 - health) + 0.35 * fire, 0, 1.2) if (health < 0.6 or fire > 0.5) else 0.0)
        o["strafe"] = 0.35 + 0.15 * band(d, 3, 8) + (0.2 if self.blocked else 0.0) if sees else 0.0
        if not sees:
            o["reposition"] = 0.5 if fresh else 0.0
        else:
            o["reposition"] = 0.45 if (d < 2.5 or d > 9) else 0.0
        engaged = sum(1 for e in room.enemies if e is not self and e.side == self.side and e.alert
                      and e.senses.sees and e.foe is self.foe)
        o["flank"] = 0.62 if ((not sees or not token) and fresh and health > 0.4 and engaged >= 1
                              and room.coordinator.flank_free(self)) else 0.0
        return o

    def feasible(self, action):
        tactics = self.room.tactics
        if action == "cover":
            self.spot_tile = tactics.cover_spot(self, self.target())
            if self.spot_tile is None:
                self.cover_ban = self.now + 1.0
                return False
        elif action == "reposition":
            self.spot_tile = tactics.firing_spot(self, self.target(), 3.0, 8.0)
            return self.spot_tile is not None or self.senses.last_known is not None
        elif action == "flank":
            pinners = [e for e in self.room.enemies if e is not self and e.side == self.side and e.alert
                       and e.senses.sees and e.foe is self.foe]
            if not pinners:
                return False
            anchor = min(pinners, key=lambda e: distance(e.pos, self.foe.pos))
            pinned_from = angle_to(self.foe.pos, anchor.pos)
            self.spot_tile = tactics.flank_spot(self, self.target(), pinned_from)
            return self.spot_tile is not None
        elif action == "shoot":
            return self.room.coordinator.acquire(self, self.now)
        return True


class Engage(State):
    name = "ENGAGE"

    def enter(self, g):
        g.think = REACTION
        g.windup = 0.0
        g.crouch = False
        g.room.tactics.claim(g, None)

    def update(self, g, dt):
        g.brake(dt)
        g.face_foe(dt)
        g.rethink(dt)


class Aim(State):
    name = "AIM"

    def enter(self, g):
        g.path = []
        g.windup = 0.0
        g.locked = False
        g.blind = 0.0
        g.aim = angle_to(g.pos, g.target())
        g.fan = FAN

    def update(self, g, dt):
        g.brake(dt)
        windup = WINDUP * g.room.tuning["windup"]
        g.windup = min(1.0, g.windup + dt / windup)
        if not g.locked:
            if g.senses.sees:
                g.blind = 0.0
                now = angle_to(g.pos, g.foe.pos)
                ahead = angle_to(g.pos, g.lead(C.ENEMY_BULLET_SPEED * g.room.tuning["bullet"]))
                half = angle_diff(now, ahead) / 2
                g.fan = half if abs(half) > FAN else math.copysign(FAN, half or 1.0)
                g.aim = now + half
            else:
                g.blind += dt
                if g.blind > 0.3:                       # lost the shot: give the token back
                    g.room.coordinator.release(g)
                    g.windup = 0.0
                    g.fsm.change(ENGAGE)
                    return
            g.facing = g.aim
            if g.windup >= 1 - C.LOCK_TIME / windup:
                g.locked = True
        if g.windup >= 1:
            g.fsm.change(FIRE)


class Fire(State):
    name = "FIRE"

    def enter(self, g):
        g.shots_left = BURST
        g.timer = 0.0

    def update(self, g, dt):
        g.brake(dt)
        g.timer -= dt
        if g.timer <= 0 and g.shots_left > 0:
            a = g.aim + (g.shots_left - 2) * g.fan
            g.room.enemy_shot(g, muzzle(g, a), a, C.ENEMY_BULLET_SPEED * g.room.tuning["bullet"])
            g.shots_left -= 1
            g.timer = BURST_GAP
        if g.shots_left == 0 and g.timer <= 0:
            g.windup = 0.0
            g.locked = False
            g.room.coordinator.release(g)
            g.cooldown = g.room.rng.uniform(0.9, 1.4)
            g.action = ""
            g.fsm.change(ENGAGE)


class Strafe(State):
    name = "STRAFE"

    def enter(self, g):
        g.path = []
        g.timer = g.room.rng.uniform(0.8, 1.6)
        g.strafe_dir = g.room.rng.choice((-1, 1))

    def update(self, g, dt):
        g.timer -= dt
        if g.timer <= 0:
            g.strafe_dir *= -1
            g.timer = g.room.rng.uniform(0.8, 1.6)
        to_player = angle_to(g.pos, g.foe.pos)
        d = distance(g.pos, g.foe.pos)
        side = from_angle(to_player + g.strafe_dir * math.pi / 2)
        radial = 0.0 if 3.5 < d < 7.5 else (-0.8 if d <= 3.5 else 0.6)
        want, _ = normalize((side[0] + math.cos(to_player) * radial, side[1] + math.sin(to_player) * radial))
        before = g.pos
        g.steer(want, dt, g.speed * 0.55)
        if distance(before, g.pos) < g.speed * 0.2 * dt:
            g.strafe_dir *= -1                           # bumped into something
        g.face(to_player, dt)
        g.rethink(dt)


class Reposition(State):
    name = "REPOSITION"

    def enter(self, g):
        g.timer = 0.0
        goal = center(g.spot_tile) if g.spot_tile else g.senses.last_known
        g.room.tactics.claim(g, g.spot_tile)
        g.spot = goal
        g.go_to(goal)

    def exit(self, g):
        g.room.tactics.claim(g, None)

    def update(self, g, dt):
        g.timer += dt
        arrived = g.follow(dt, g.speed, face=not g.senses.sees)
        if g.senses.sees:
            g.face(angle_to(g.pos, g.foe.pos), dt)
        if arrived or g.timer > 4:
            g.action = ""
            g.think = 0.0
        g.rethink(dt)


class Flank(State):
    name = "FLANK"

    def enter(self, g):
        g.timer = 0.0
        g.room.coordinator.take_flank(g)
        g.room.tactics.claim(g, g.spot_tile)
        g.spot = center(g.spot_tile)
        g.go_to(g.spot, g.room.tactics.danger_cost(g.target()))
        g.think = THINK_EVERY * 2

    def exit(self, g):
        g.room.coordinator.drop_flank(g)
        g.room.tactics.claim(g, None)

    def update(self, g, dt):
        g.timer += dt
        arrived = g.follow(dt, g.speed * 1.1)
        if arrived or g.timer > 5:
            g.action = ""
            g.think = 0.0
        g.rethink(dt)


class TakeCover(State):
    name = "TAKE COVER"

    def enter(self, g):
        g.timer = 0.0
        g.room.tactics.claim(g, g.spot_tile)
        g.spot = center(g.spot_tile)
        g.go_to(g.spot)

    def update(self, g, dt):
        g.timer += dt
        if g.follow(dt, g.speed * 1.15) or g.timer > 4:
            g.fsm.change(HIDE)


class Hide(State):
    name = "HIDE"

    def enter(self, g):
        g.timer = 0.0
        g.crouch = True
        g.hide_for = g.room.rng.uniform(1.2, 2.0)

    def exit(self, g):
        g.crouch = False
        g.room.tactics.claim(g, None)
        g.cover_ban = g.now + 3.0

    def update(self, g, dt):
        g.timer += dt
        g.brake(dt)
        g.face_foe(dt)
        close = g.senses.sees and distance(g.pos, g.foe.pos) < 2.5
        if g.timer > g.hide_for or close:
            g.action = ""
            g.fsm.change(ENGAGE)


ENGAGE, AIM, FIRE, STRAFE = Engage(), Aim(), Fire(), Strafe()
REPOSITION, FLANK, TAKE_COVER, HIDE = Reposition(), Flank(), TakeCover(), Hide()
