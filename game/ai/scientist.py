"""The scientist: runs you down and swings his butterfly net.

    CHASE   runs at Hans along an A* path, re-planned every REPLAN_TIME   in reach -> SWING
                                                                        lost him  -> SEARCH
                                                                        re-decides twice a second
            TEAMWORK: if a colleague is already closer, he runs to the far side of Hans instead,
            so the two close in from opposite sides (a pincer).
            INTERCEPT (learned tactic): he runs to where Hans will be, not where he is.
    SWING   stops, winds up (the red arc on screen: your cue to get out), then swings.
            If Hans is still in reach and in front of him, Hans loses a heart.   -> decides again
"""

import math

from game.config import (SCIENTIST_HP, SCIENTIST_WANDER, SCIENTIST_CHASE, NET_REACH, NET_WINDUP, NET_RECOVER,
                         REPLAN_TIME)
from game.ai.enemy import Enemy
from game.ai.state_machine import State
from game.level import distance, angle_to, angle_diff


class Chase(State):
    name = "CHASE"

    def enter(self, s):
        s.replan = 0.0
        s.announced = set()

    def update(self, s, dt):
        if s.lost_him():
            return
        hans = s.world.hans
        target, mode = s.chase_target()
        s.chase_mode = mode
        if mode and mode not in s.announced:          # say it once per chase, not every flicker
            s.announced.add(mode)
            s.events.append(mode)
        s.replan -= dt
        if s.replan <= 0:
            s.go_to(target)
            s.replan = REPLAN_TIME
        s.walk(dt, s.run_speed * s.scale)
        if s.sees_hans and distance(s.pos, hans.pos) <= NET_REACH:
            s.fsm.change(SWING)
            return
        s.every(dt, lambda: s.decide() != "attack" and s.act())


class Swing(State):
    name = "SWING"

    def enter(self, s):
        s.timer = 0.0
        s.swung = False
        s.path = []
        s.events.append("windup")

    def update(self, s, dt):
        hans = s.world.hans
        s.timer += dt
        if not s.swung:
            s.face(hans.pos, dt * 0.6)              # he commits: turns slowly while winding up
            if s.timer >= s.windup(NET_WINDUP):
                s.swung = True
                s.events.append("swing")
                in_front = abs(angle_diff(s.angle, angle_to(s.pos, hans.pos))) < math.radians(80)
                if distance(s.pos, hans.pos) <= NET_REACH + 0.25 and in_front:
                    s.world.hit_hans(s, "net")
        elif s.timer >= s.windup(NET_WINDUP) + NET_RECOVER:
            s.act(force=True)

    @staticmethod
    def progress(s) -> float:
        """0..1 while winding up, for drawing the warning arc."""
        return min(1.0, s.timer / s.windup(NET_WINDUP)) if not s.swung else 0.0


CHASE, SWING = Chase(), Swing()


class Scientist(Enemy):
    kind = "scientist"
    max_hp = SCIENTIST_HP
    aggression = 1.0
    cowardice = 0.7
    wander_speed = SCIENTIST_WANDER
    run_speed = SCIENTIST_CHASE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.announced: set[str] = set()

    def attack_state(self):
        return CHASE

    def chase_target(self):
        """Where to run: his role from the Commission, else at Hans (or ahead of him: INTERCEPT)."""
        hans = self.world.hans
        target = hans.pos if self.sees_hans else self.last_seen
        tactics = getattr(self.world, "tactics", None)
        role = None
        if tactics is not None:
            spot, role = tactics.target_for(self, self.world)
            if spot is not None:
                return spot, role
        d = distance(self.pos, hans.pos)
        if (role == "flanker" or tactics is None) and d > 2.2:
            flank = self.flank_point()
            if flank is not None:
                return flank, "flank"
        if self.tactic("intercept") and self.sees_hans and d > 2.0:
            vx, vy = self.world.hans_velocity
            look = min(1.2, d / (self.run_speed * self.scale))
            ahead = (hans.pos[0] + vx * look, hans.pos[1] + vy * look)
            if self.level.walkable(int(ahead[0]), int(ahead[1])):
                return ahead, "intercept"
        return target, None

    def flank_point(self):
        """The far side of Hans from the colleague who's already closer (the pincer)."""
        hans = self.world.hans
        d = distance(self.pos, hans.pos)
        partners = [e for e in self.world.enemies if e is not self and e.kind in ("scientist", "pfungst") and
                    e.state in ("CHASE", "SWING", "READ") and distance(e.pos, hans.pos) < d]
        if not partners:
            return None
        p = min(partners, key=lambda e: distance(e.pos, hans.pos))
        a = angle_to(p.pos, hans.pos)
        flank = (hans.pos[0] + math.cos(a) * 1.8, hans.pos[1] + math.sin(a) * 1.8)
        return flank if self.level.walkable(int(flank[0]), int(flank[1])) else None
