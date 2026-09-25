"""Hans, controlled by the player: runs, gallops (fast, loud, tiring), and bucks to kick."""

import math

from game.config import (RUN_SPEED, GALLOP_SPEED, TANGLED_SPEED, HANS_RADIUS, STAMINA, STAMINA_REGEN, HEARTS,
                         HURT_INVULNERABLE, KICK_COOLDOWN, GALLOP_NOISE, TANGLE_TIME, POWER_TIME)
from game.ai.perception import Noise
from game.level import Level, Point


class Hans:
    def __init__(self, pos: Point):
        self.pos = pos
        self.facing = 1                  # the sprite is drawn side-on: 1 right, -1 left
        self.moving = False
        self.galloping = False
        self.walk_phase = 0.0
        self.stamina = STAMINA
        self.hearts = HEARTS
        self.invulnerable = 0.0
        self.tangled = 0.0
        self.power = 0.0
        self.kick_cooldown = 0.0
        self.kick_flash = 0.0            # for drawing the buck
        self.step_timer = 0.0
        self.knock = (0.0, 0.0)          # pushed by a pouncing dog

    @property
    def powered(self) -> bool:
        return self.power > 0

    @property
    def alive(self) -> bool:
        return self.hearts > 0

    def update(self, dt: float, move: tuple[float, float], gallop: bool, level: Level) -> list[Noise]:
        for name in ("invulnerable", "tangled", "power", "kick_cooldown", "kick_flash"):
            setattr(self, name, max(0.0, getattr(self, name) - dt))
        mx, my = move
        length = math.hypot(mx, my)
        self.moving = length > 0
        self.galloping = gallop and self.moving and self.stamina > 0.05 and not self.tangled
        if self.galloping:
            self.stamina = max(0.0, self.stamina - dt)
        else:
            self.stamina = min(STAMINA, self.stamina + STAMINA_REGEN * dt)
        noises = []
        if self.moving:
            speed = TANGLED_SPEED if self.tangled else GALLOP_SPEED if self.galloping else RUN_SPEED
            self._slide(level, mx / length * speed * dt, my / length * speed * dt)
            if abs(mx) > 0.01:
                self.facing = 1 if mx > 0 else -1
            self.walk_phase += dt * (18 if self.galloping else 11)
            self.step_timer += dt
            if self.galloping and self.step_timer > 0.22:
                self.step_timer = 0.0
                noises.append(Noise(self.pos, GALLOP_NOISE))
        kx, ky = self.knock
        if kx or ky:
            self._slide(level, kx * dt, ky * dt)
            self.knock = (kx * 0.85, ky * 0.85) if math.hypot(kx, ky) > 0.3 else (0.0, 0.0)
        return noises

    def _slide(self, level: Level, dx: float, dy: float):
        """Move, sliding along walls: x and y separately."""
        if level.free((self.pos[0] + dx, self.pos[1]), HANS_RADIUS):
            self.pos = (self.pos[0] + dx, self.pos[1])
        if level.free((self.pos[0], self.pos[1] + dy), HANS_RADIUS):
            self.pos = (self.pos[0], self.pos[1] + dy)

    def can_kick(self) -> bool:
        return self.kick_cooldown <= 0

    def start_kick(self):
        self.kick_cooldown = KICK_COOLDOWN
        self.kick_flash = 0.25

    def hurt(self) -> bool:
        """Lose a heart unless still flashing from the last hit (or powered up)."""
        if self.invulnerable > 0 or self.powered:
            return False
        self.hearts -= 1
        self.invulnerable = HURT_INVULNERABLE
        return True

    def tangle(self):
        if not self.powered:
            self.tangled = TANGLE_TIME

    def heal(self):
        self.hearts = min(HEARTS, self.hearts + 1)

    def power_up(self):
        self.power = POWER_TIME
        self.tangled = 0.0
