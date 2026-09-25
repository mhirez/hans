"""The stable boy: keeps his distance, throws a lasso that tangles Hans, hides when charged.

    POSITION  finds a spot 3.5-6.5 tiles from Hans with a clear line to him (scores ~30 nearby
              tiles), and walks there with A*          set up and reloaded -> THROW
    THROW     spins the lasso over his head (your cue), then throws it where Hans WILL be:
              he leads the target using Hans's current velocity                 -> POSITION
    COVER     Hans is galloping at him: runs to the nearest tile Hans can't see, behind something
              tall, and stays until the danger passes (re-decides twice a second)
"""

import math

from game.config import (LASSO_HP, LASSO_WANDER, LASSO_MOVE, LASSO_BEST_RANGE, LASSO_WINDUP, LASSO_RELOAD,
                         LASSO_SPEED, LASSO_RANGE)
from game.ai.enemy import Enemy
from game.ai.state_machine import State
from game.level import center, distance


class Position(State):
    name = "POSITION"

    def enter(self, b):
        b.timer = 0.0
        b.choose_spot()

    def update(self, b, dt):
        if b.lost_him():
            return
        hans = b.world.hans
        b.timer += dt
        arrived = b.walk(dt, b.run_speed * b.scale)
        if b.sees_hans:
            b.face(hans.pos, dt)
        d = distance(b.pos, hans.pos)
        if b.reload <= 0 and b.sees_hans and d <= LASSO_RANGE and (arrived or LASSO_BEST_RANGE[0] <= d):
            b.fsm.change(THROW)
            return
        if b.timer > 0.8 or (arrived and not b.sees_hans) or d < 2.5:
            b.timer = 0.0
            b.choose_spot()
        b.every(dt, lambda: b.decide() != "attack" and b.act())


class Throw(State):
    name = "THROW"

    def enter(self, b):
        b.timer = 0.0
        b.path = []
        b.events.append("spin")

    def update(self, b, dt):
        hans = b.world.hans
        b.timer += dt
        b.face(hans.pos, dt)
        if b.timer >= b.windup(LASSO_WINDUP):
            lead = distance(b.pos, hans.pos) / LASSO_SPEED
            vx, vy = b.world.hans_velocity
            aim = (hans.pos[0] + vx * lead, hans.pos[1] + vy * lead)
            b.world.throw_lasso(b, aim)
            b.reload = LASSO_RELOAD
            b.fsm.change(POSITION)

    @staticmethod
    def progress(b) -> float:
        return min(1.0, b.timer / b.windup(LASSO_WINDUP))


class Cover(State):
    name = "COVER"

    def enter(self, b):
        b.find_cover()

    def update(self, b, dt):
        b.walk(dt, b.run_speed * b.scale * 1.2)
        b.every(dt, lambda: b.decide() != "cover" and b.act())


POSITION, THROW, COVER = Position(), Throw(), Cover()


class StableBoy(Enemy):
    kind = "stableboy"
    max_hp = LASSO_HP
    aggression = 0.9
    cowardice = 0.9
    can_hide = True
    wander_speed = LASSO_WANDER
    run_speed = LASSO_MOVE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reload = 0.0
        self.spot_target = None

    def attack_state(self):
        return POSITION

    def cover_state(self):
        return COVER

    def update(self, dt, world):
        self.reload = max(0.0, self.reload - dt)
        super().update(dt, world)

    def choose_spot(self):
        """Score nearby tiles: right distance from Hans, a clear throw, not too far to walk."""
        hans = self.world.hans.pos
        lo, hi = LASSO_BEST_RANGE
        best, best_score = None, -math.inf
        for _ in range(30):
            c = int(hans[0]) + self.rng.randint(-7, 7)
            r = int(hans[1]) + self.rng.randint(-6, 6)
            if not self.level.walkable(c, r):
                continue
            p = center((c, r))
            d = distance(p, hans)
            score = -abs(d - (lo + hi) / 2) - 0.25 * distance(p, self.pos)
            if not self.level.line_of_sight(p, hans):
                score -= 6
            if d < lo:
                score -= 4
            if score > best_score:
                best, best_score = p, score
        self.spot_target = best
        if best is not None:
            self.go_to(best)

    def find_cover(self):
        """The nearest tile Hans can't see, preferring ones away from him."""
        hans = self.world.hans.pos
        here = (int(self.pos[0]), int(self.pos[1]))
        best, best_score = None, math.inf
        for r in range(here[1] - 6, here[1] + 7):
            for c in range(here[0] - 6, here[0] + 7):
                if not self.level.walkable(c, r):
                    continue
                p = center((c, r))
                if self.level.line_of_sight(hans, p):
                    continue
                score = distance(p, self.pos) - 0.5 * distance(p, hans)
                if score < best_score:
                    best, best_score = p, score
        if best is None:
            self.pick_escape()
        else:
            self.go_to(best)
