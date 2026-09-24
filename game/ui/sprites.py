"""Hand-drawn (well, code-drawn) figures. Everything is primitives, so no image assets are needed.

Figures are drawn side-on, standing on the top-down courtyard like board-game standees.
Each function takes the pixel point where the figure's feet touch the ground.
"""

import math
import random

import pygame

from game.config import TILE
from game.ui import theme as T


def _flip(surface: pygame.Surface, facing: int) -> pygame.Surface:
    return pygame.transform.flip(surface, True, False) if facing < 0 else surface


def hans(surface, feet, facing=1, walk_phase=0.0, moving=False, head="up", tap_up=False, blinkers=False):
    """Hans, 64x56, feet at the bottom centre. head: 'up' (looking) or 'down' (sniffing)."""
    s = pygame.Surface((64, 56), pygame.SRCALPHA)
    legs = [(19, 0.0, T.HORSE_DARK), (23, math.pi, T.HORSE), (38, math.pi, T.HORSE_DARK), (42, 0.0, T.HORSE)]
    for i, (x, phase, col) in enumerate(legs):
        swing = math.sin(walk_phase + phase) * 3 if moving else 0
        if i == 3 and tap_up:
            pygame.draw.lines(s, col, False, [(x, 33), (x + 6, 40), (x + 5, 45)], 4)
            pygame.draw.rect(s, T.MANE, (x + 3, 44, 5, 3))
        else:
            pygame.draw.line(s, col, (x, 33), (x + swing, 49), 4)
            pygame.draw.rect(s, T.MANE, (x + swing - 2, 48, 5, 3))
    tail_swish = math.sin(walk_phase * 0.5) * 2
    pygame.draw.lines(s, T.MANE, False, [(14, 25), (9, 31 + tail_swish), (7, 41)], 3)
    pygame.draw.ellipse(s, T.HORSE, (11, 21, 38, 16))
    pygame.draw.ellipse(s, T.HORSE_DARK, (15, 31, 30, 6))
    if head == "down":
        pygame.draw.polygon(s, T.HORSE, [(38, 23), (46, 21), (54, 36), (47, 38)])
        pygame.draw.polygon(s, T.HORSE, [(47, 33), (56, 34), (60, 46), (53, 47)])
        pygame.draw.line(s, T.MANE, (39, 22), (47, 20), 3)
        pygame.draw.polygon(s, T.HORSE_DARK, [(48, 32), (49, 27), (51, 32)])
        pygame.draw.circle(s, T.INK, (53, 38), 1)
        if blinkers:
            pygame.draw.polygon(s, T.INK, [(50, 34), (55, 35), (55, 40), (50, 39)])
    else:
        pygame.draw.polygon(s, T.HORSE, [(37, 27), (44, 11), (51, 13), (47, 31)])
        pygame.draw.polygon(s, T.HORSE, [(44, 9), (57, 13), (59, 18), (46, 17)])
        pygame.draw.lines(s, T.MANE, False, [(38, 25), (41, 17), (45, 10)], 3)
        pygame.draw.polygon(s, T.HORSE_DARK, [(45, 10), (46, 4), (49, 10)])
        pygame.draw.circle(s, T.INK, (50, 12), 1)
        if blinkers:
            pygame.draw.polygon(s, T.INK, [(48, 9), (54, 9), (54, 15), (48, 15)])
            pygame.draw.line(s, T.INK, (46, 11), (57, 14), 1)
    img = _flip(s, facing)
    surface.blit(img, (feet[0] - 32, feet[1] - 52))


def von_osten(surface, feet, lean=0.0):
    """Wilhelm von Osten: long dark coat, white beard, black slouch hat."""
    x, y = feet
    lx = int(lean * 3)
    pygame.draw.line(surface, T.INK, (x - 4, y - 14), (x - 4, y), 3)
    pygame.draw.line(surface, T.INK, (x + 4, y - 14), (x + 4, y), 3)
    pygame.draw.polygon(surface, T.COAT, [(x - 10, y - 12), (x + 10, y - 12), (x + 7 + lx, y - 34), (x - 7 + lx, y - 34)])
    pygame.draw.line(surface, T.INK, (x + lx, y - 33), (x, y - 13), 1)
    hx, hy = x + lx * 2, y - 40
    pygame.draw.circle(surface, T.SKIN, (hx, hy), 6)
    pygame.draw.polygon(surface, T.BEARD, [(hx - 5, hy + 1), (hx + 5, hy + 1), (hx + 1, hy + 12)])
    pygame.draw.ellipse(surface, T.INK, (hx - 10, hy - 7, 20, 5))
    pygame.draw.rect(surface, T.INK, (hx - 5, hy - 13, 10, 8), border_top_left_radius=3, border_top_right_radius=3)


CROWD_COLOURS = [(92, 74, 60), (70, 76, 84), (112, 88, 70), (84, 64, 70), (66, 70, 58), (104, 96, 80)]


def spectator(surface, feet, index, lean=0.0):
    rng = random.Random(index)
    x, y = feet
    lx = int(lean * 2)
    coat = CROWD_COLOURS[index % len(CROWD_COLOURS)]
    pygame.draw.rect(surface, coat, (x - 6 + lx, y - 22, 12, 22), border_top_left_radius=4, border_top_right_radius=4)
    hx, hy = x + lx * 2, y - 27
    pygame.draw.circle(surface, T.SKIN, (hx, hy), 5)
    if rng.random() < 0.5:   # bowler
        pygame.draw.ellipse(surface, T.INK, (hx - 7, hy - 5, 14, 4))
        pygame.draw.ellipse(surface, T.INK, (hx - 4, hy - 10, 8, 7))
    else:                    # bonnet
        pygame.draw.arc(surface, (150, 120, 96), (hx - 7, hy - 8, 14, 14), 0.2, math.pi - 0.2, 3)


def carrot(surface, center, size=1.0):
    x, y = center
    s = size
    pygame.draw.polygon(surface, T.CARROT, [(x - 5 * s, y - 6 * s), (x + 5 * s, y - 6 * s), (x, y + 10 * s)])
    for i in range(3):
        pygame.draw.line(surface, (160, 76, 30), (x - 3 * s + i * 2, y - 2 * s + i * 3), (x - 1 * s + i * 2, y - 2 * s + i * 3), 1)
    for dx in (-3, 0, 3):
        pygame.draw.line(surface, T.LEAF, (x, y - 6 * s), (x + dx * s, y - 12 * s), 2)


def door(surface, rect: pygame.Rect, numeral: str, font, is_open=False, contents=None, outline=None):
    """A stable door set into the wall. contents: None, 'carrot' or 'empty' when open."""
    pygame.draw.rect(surface, T.WALL_DARK, rect.inflate(6, 0))
    inner = rect.inflate(-4, -4)
    if is_open:
        pygame.draw.rect(surface, T.FILM, inner)
        pygame.draw.rect(surface, T.HAY_DARK, (inner.x, inner.bottom - 6, inner.width, 6))
        if contents == "carrot":
            carrot(surface, (inner.centerx, inner.centery), 0.9)
    else:
        pygame.draw.rect(surface, T.WOOD, inner)
        for i in range(1, 6):
            x = inner.x + i * inner.width // 6
            pygame.draw.line(surface, T.WOOD_DARK, (x, inner.y), (x, inner.bottom), 1)
        pygame.draw.line(surface, T.WOOD_DARK, inner.topleft, inner.bottomright, 2)
        plaque = pygame.Rect(0, 0, 26, 16)
        plaque.center = inner.center
        pygame.draw.rect(surface, T.PAPER, plaque)
        pygame.draw.rect(surface, T.INK, plaque, 1)
        img = font.render(numeral, True, T.INK)
        surface.blit(img, img.get_rect(center=plaque.center))
    if outline:
        pygame.draw.rect(surface, outline, rect.inflate(8, 4), 3)


def floor(surface, rect: pygame.Rect, seed: int):
    rng = random.Random(seed)
    pygame.draw.rect(surface, T.GROUND if seed % 2 else T.GROUND_ALT, rect)
    half = TILE // 2
    for oy in (0, half):
        shift = rng.randint(-4, 4)
        for ox in (0, half):
            stone = pygame.Rect(rect.x + ox + shift // 2, rect.y + oy, half - 2, half - 2)
            shade = rng.randint(-8, 8)
            c = tuple(max(0, min(255, v + shade)) for v in T.GROUND)
            pygame.draw.rect(surface, c, stone, border_radius=4)
    pygame.draw.rect(surface, T.GROUT, rect, 1)


def wall(surface, rect: pygame.Rect, seed: int):
    pygame.draw.rect(surface, T.WALL, rect)
    rng = random.Random(seed)
    for row in range(3):
        y = rect.y + row * rect.height // 3
        pygame.draw.line(surface, T.WALL_DARK, (rect.x, y), (rect.right, y), 1)
        off = (row % 2) * rect.width // 2 + rng.randint(-2, 2)
        pygame.draw.line(surface, T.WALL_DARK, (rect.x + off, y), (rect.x + off, y + rect.height // 3), 1)


def hay(surface, rect: pygame.Rect):
    r = rect.inflate(-4, -8)
    pygame.draw.rect(surface, T.HAY, r, border_radius=5)
    for i in range(1, 4):
        y = r.y + i * r.height // 4
        pygame.draw.line(surface, T.HAY_DARK, (r.x + 3, y), (r.right - 3, y), 1)
    pygame.draw.line(surface, T.WOOD_DARK, (r.centerx, r.y), (r.centerx, r.bottom), 2)


def trough(surface, rect: pygame.Rect):
    r = rect.inflate(0, -10)
    pygame.draw.rect(surface, T.STONE, r)
    pygame.draw.rect(surface, T.WATER, r.inflate(-6, -6))
    pygame.draw.rect(surface, T.WALL_DARK, r, 1)


def cart(surface, rect: pygame.Rect):
    body = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, rect.height - 12)
    pygame.draw.rect(surface, T.WOOD, body)
    for i in range(1, 4):
        pygame.draw.line(surface, T.WOOD_DARK, (body.x, body.y + i * 5), (body.right, body.y + i * 5), 1)
    for cx in (rect.x + 14, rect.right - 14):
        pygame.draw.circle(surface, T.WOOD_DARK, (cx, rect.bottom - 8), 9, 3)
        pygame.draw.circle(surface, T.WOOD_DARK, (cx, rect.bottom - 8), 2)


def fence(surface, rect: pygame.Rect):
    cx = rect.centerx
    pygame.draw.line(surface, T.WOOD, (cx - 4, rect.y), (cx - 4, rect.bottom), 3)
    pygame.draw.line(surface, T.WOOD, (cx + 4, rect.y), (cx + 4, rect.bottom), 3)
    pygame.draw.rect(surface, T.WOOD_DARK, (cx - 6, rect.y + rect.height // 2 - 3, 12, 6))


def screen(surface, rect: pygame.Rect):
    """A folding cloth screen, like the ones Pfungst used to hide the questioner."""
    r = rect.inflate(-6, 0)
    pygame.draw.rect(surface, (136, 82, 58), r)
    for i in range(5):
        panel = pygame.Rect(r.x, r.y + i * r.height // 5, r.width, r.height // 5)
        pygame.draw.rect(surface, (112, 64, 44), panel.inflate(-8, -8), 1)
        pygame.draw.line(surface, T.WOOD_DARK, panel.topleft, panel.topright, 3)
    pygame.draw.rect(surface, T.WOOD_DARK, r, 3)
