"""Hans, controlled by the player: walks quietly, trots fast but loudly."""

import math

from game.config import (WALK_SPEED, TROT_SPEED, HANS_RADIUS, STEP_WALK, STEP_TROT, TROT_NOISE,
                         GRAVEL_WALK_NOISE, GRAVEL_TROT_NOISE)
from game.ai.perception import Noise
from game.level import Level, Point


class Hans:
    def __init__(self, pos: Point):
        self.pos = pos
        self.facing = 1              # 1 right, -1 left (the sprite is drawn side-on)
        self.moving = False
        self.trotting = False
        self.walk_phase = 0.0
        self.step_timer = 0.0
        self.walked = 0.0            # total distance, for the tutorial
        self.steps: list[bool] = []  # hoof-falls this frame (True = loud), for sound

    def update(self, dt: float, move: tuple[float, float], trot: bool, level: Level) -> list[Noise]:
        mx, my = move
        length = math.hypot(mx, my)
        self.moving = length > 0
        self.trotting = trot and self.moving
        self.steps = []
        if not self.moving:
            self.step_timer = 0.0
            return []
        speed = TROT_SPEED if self.trotting else WALK_SPEED
        dx, dy = mx / length * speed * dt, my / length * speed * dt
        before = self.pos
        if level.free((self.pos[0] + dx, self.pos[1]), HANS_RADIUS):     # slide along walls:
            self.pos = (self.pos[0] + dx, self.pos[1])                    # x and y separately
        if level.free((self.pos[0], self.pos[1] + dy), HANS_RADIUS):
            self.pos = (self.pos[0], self.pos[1] + dy)
        self.walked += math.hypot(self.pos[0] - before[0], self.pos[1] - before[1])
        if abs(mx) > 0.01:
            self.facing = 1 if mx > 0 else -1
        self.walk_phase += dt * (16 if self.trotting else 10)

        self.step_timer += dt
        interval = STEP_TROT if self.trotting else STEP_WALK
        if self.step_timer < interval:
            return []
        self.step_timer = 0.0
        on_gravel = level.noisy(self.pos)
        radius = (GRAVEL_TROT_NOISE if on_gravel else TROT_NOISE) if self.trotting else \
                 (GRAVEL_WALK_NOISE if on_gravel else 0.0)
        self.steps.append(radius > 0)
        return [Noise(self.pos, radius)] if radius > 0 else []
