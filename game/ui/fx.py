"""Game feel: particles, screen shake, hit-stop, screen flashes and floating text.

The room reports effects as tuples (see room.py); FX turns them into things on screen.
Positions here are in pixels.
"""

from dataclasses import dataclass
import math
import random

import pygame

from game.config import TILE, WIDTH, HEIGHT
from game.ui import style as S


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    colour: tuple
    size: float
    kind: str = "dot"          # dot, spark, ring, text, plus
    text: str = ""
    drag: float = 3.0
    grow: float = 0.0


class FX:
    def __init__(self, seed: int = 5):
        self.rng = random.Random(seed)
        self.particles: list[Particle] = []
        self.trauma = 0.0
        self.stop = 0.0
        self.flash_colour = (255, 255, 255)
        self.flash = 0.0
        self.warps: list[list] = []      # [x, y, age]
        self.t = 0.0

    def clear(self):
        self.particles.clear()
        self.warps.clear()
        self.trauma = 0.0
        self.flash = 0.0

    # --- input -----------------------------------------------------------------------------
    def consume(self, events: list[tuple]):
        for ev in events:
            kind = ev[0]
            if kind == "shake":
                self.trauma = min(1.0, self.trauma + ev[1])
            elif kind == "stop":
                self.stop = max(self.stop, ev[1])
            elif kind == "flash":
                self.flash_colour, self.flash = ev[1], 0.25
            elif kind == "spark":
                self.sparks(px(ev[1]), ev[2], 5, 260)
            elif kind == "burst":
                self.burst(px(ev[1]), ev[2], ev[3])
            elif kind == "ring":
                x, y = px(ev[1])
                self.particles.append(Particle(x, y, 0, 0, 0.45, 0.45, ev[2], 8, "ring", grow=ev[3] * TILE / 0.45))
            elif kind == "text":
                x, y = px(ev[1])
                self.particles.append(Particle(x, y - 20, 0, -50, 0.9, 0.9, ev[3], 20, "text", ev[2], drag=1.5))
            elif kind == "muzzle":
                x, y = px(ev[1])
                a = ev[2]
                for _ in range(3):
                    s = self.rng.uniform(80, 260)
                    b = a + self.rng.uniform(-0.35, 0.35)
                    self.particles.append(Particle(x, y, math.cos(b) * s, math.sin(b) * s, 0.09, 0.09, ev[3], 3, "spark"))
            elif kind == "trail":
                x, y = px(ev[1])
                self.particles.append(Particle(x, y, 0, 0, 0.18, 0.18, ev[2], ev[3] * TILE, "ghost"))
            elif kind == "heal":
                x, y = px(ev[1])
                self.particles.append(Particle(x + self.rng.uniform(-10, 10), y, 0, -40, 0.6, 0.6,
                                               S.GOOD, 5, "plus", drag=0.5))
            elif kind == "warp":
                x, y = px(ev[1])
                self.warps.append([x, y, 0.0])

    def sparks(self, pos, colour, n: int, speed: float):
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            s = self.rng.uniform(0.3, 1.0) * speed
            self.particles.append(Particle(pos[0], pos[1], math.cos(a) * s, math.sin(a) * s,
                                           0.25, 0.25, colour, 2, "spark", drag=6))

    def burst(self, pos, colour, size: float):
        n = int(14 + 20 * size)
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            s = self.rng.uniform(80, 420) * (0.6 + 0.4 * size)
            life = self.rng.uniform(0.3, 0.7)
            kind = "spark" if self.rng.random() < 0.6 else "dot"
            self.particles.append(Particle(pos[0], pos[1], math.cos(a) * s, math.sin(a) * s, life, life,
                                           S.mix(colour, S.WHITE, self.rng.random() * 0.4),
                                           self.rng.uniform(2, 5), kind, drag=4))
        self.particles.append(Particle(pos[0], pos[1], 0, 0, 0.35, 0.35, colour, 6, "ring",
                                       grow=(1.4 + size) * TILE / 0.35))
        self.particles.append(Particle(pos[0], pos[1], 0, 0, 0.18, 0.18, S.WHITE, 18 + 14 * size, "flash"))

    # --- time --------------------------------------------------------------------------------
    def update(self, dt: float):
        self.t += dt
        self.trauma = max(0.0, self.trauma - dt * 1.8)
        self.flash = max(0.0, self.flash - dt)
        for w in self.warps:
            w[2] += dt
        self.warps = [w for w in self.warps if w[2] < 1.15]
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            k = math.exp(-p.drag * dt)
            p.vx, p.vy = p.vx * k, p.vy * k
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.size += p.grow * dt
            alive.append(p)
        self.particles = alive[-900:]

    def offset(self) -> tuple[int, int]:
        amount = self.trauma ** 2 * 14
        if amount < 0.3:
            return 0, 0
        return (int(math.sin(self.t * 71) * amount), int(math.cos(self.t * 57) * amount))

    # --- drawing -----------------------------------------------------------------------------
    def draw_under(self, surface, off):
        """Warp-in markers (drawn under the enemies)."""
        for x, y, age in self.warps:
            k = age / 1.1
            r = int(TILE * (1.2 - 0.7 * k))
            c = S.scale(S.DANGER, 0.5 + 0.5 * abs(math.sin(age * 14)))
            pygame.draw.circle(surface, c, (x + off[0], y + off[1]), r, 2)
            pygame.draw.circle(surface, c, (x + off[0], y + off[1]), int(r * 0.45), 1)
            S.add_glow(surface, (x + off[0], y + off[1]), int(TILE * 0.9), S.scale(S.DANGER, 0.45))

    def draw(self, surface, off):
        ox, oy = off
        for p in self.particles:
            k = p.life / p.max_life
            x, y = p.x + ox, p.y + oy
            if p.kind == "spark":
                tail = (x - p.vx * 0.03, y - p.vy * 0.03)
                pygame.draw.line(surface, S.scale(p.colour, 0.4 + 0.6 * k), (x, y), tail, max(1, int(p.size)))
            elif p.kind == "dot":
                pygame.draw.circle(surface, S.scale(p.colour, 0.4 + 0.6 * k), (int(x), int(y)), max(1, int(p.size * k)))
            elif p.kind == "ring":
                pygame.draw.circle(surface, S.scale(p.colour, k), (int(x), int(y)), int(p.size), max(1, int(3 * k)))
            elif p.kind == "flash":
                S.add_glow(surface, (x, y), int(p.size * 2), S.scale(p.colour, k))
            elif p.kind == "ghost":
                S.add_glow(surface, (x, y), int(p.size * 1.6), S.scale(p.colour, 0.55 * k))
            elif p.kind == "plus":
                c = S.scale(p.colour, k)
                pygame.draw.line(surface, c, (x - 4, y), (x + 4, y), 2)
                pygame.draw.line(surface, c, (x, y - 4), (x, y + 4), 2)
            elif p.kind == "text":
                S.text(surface, p.text, S.display(int(p.size)), p.colour, (x, y), "center", int(255 * min(1, k * 2)))
        if self.flash > 0:
            veil = vignette(self.flash_colour)
            veil.set_alpha(int(255 * self.flash / 0.25))
            surface.blit(veil, (0, 0))


_vignettes: dict = {}


def vignette(colour) -> pygame.Surface:
    """A coloured glow round the screen edge (the 'you got hit' flash)."""
    if colour not in _vignettes:
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(40):
            a = int(150 * (1 - i / 40) ** 2)
            pygame.draw.rect(veil, (*colour, a), (i * 2, i * 2, WIDTH - i * 4, HEIGHT - i * 4), 2)
        _vignettes[colour] = veil
    return _vignettes[colour]


def px(p) -> tuple[float, float]:
    return p[0] * TILE, p[1] * TILE
