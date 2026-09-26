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


def screen(surface, rect: pygame.Rect):
    """A folding cloth screen, like the ones Pfungst used to hide the questioner."""
    r = rect.inflate(-6, 0)
    pygame.draw.rect(surface, (136, 82, 58), r)
    for i in range(5):
        panel = pygame.Rect(r.x, r.y + i * r.height // 5, r.width, r.height // 5)
        pygame.draw.rect(surface, (112, 64, 44), panel.inflate(-8, -8), 1)
        pygame.draw.line(surface, T.WOOD_DARK, panel.topleft, panel.topright, 3)
    pygame.draw.rect(surface, T.WOOD_DARK, r, 3)


SCIENTIST_COATS = [(64, 58, 70), (78, 62, 52), (56, 66, 62), (84, 72, 60)]


def _side(facing: float) -> int:
    return 1 if math.cos(facing) >= 0 else -1


def scientist(surface, feet, facing: float, walk_phase=0.0, moving=False, index=0, windup=0.0):
    """A scientist of the Commission: long coat, bowler hat, butterfly net. windup 0..1 raises the net."""
    x, y = feet
    coat = (38, 62, 46) if index == 99 else SCIENTIST_COATS[index % len(SCIENTIST_COATS)]   # 99: Pfungst
    swing = math.sin(walk_phase) * 3 if moving else 0
    side = _side(facing)
    pygame.draw.line(surface, T.INK, (x - 4, y - 14), (x - 4 + swing, y), 3)
    pygame.draw.line(surface, T.INK, (x + 4, y - 14), (x + 4 - swing, y), 3)
    pygame.draw.polygon(surface, coat, [(x - 11, y - 11), (x + 11, y - 11), (x + 8, y - 36), (x - 8, y - 36)])
    pygame.draw.line(surface, T.INK, (x, y - 35), (x, y - 12), 1)
    hx, hy = x + side * 2, y - 42
    pygame.draw.circle(surface, T.SKIN, (hx, hy), 7)
    pygame.draw.circle(surface, T.INK, (hx + side * 3, hy - 1), 1)
    pygame.draw.ellipse(surface, T.INK, (hx - 10, hy - 7, 20, 5))
    pygame.draw.ellipse(surface, T.INK, (hx - 6, hy - 14, 12, 10))
    # the net: a pole from his hands, raised overhead as he winds up
    a = math.radians(-30 - 100 * windup)
    hand = (x + side * 8, y - 26)
    tip = (hand[0] + side * math.cos(a) * 30, hand[1] + math.sin(a) * 30)
    pygame.draw.line(surface, T.WOOD_DARK, hand, tip, 3)
    pygame.draw.circle(surface, T.PAPER, (int(tip[0]), int(tip[1])), 9)
    pygame.draw.circle(surface, T.INK, (int(tip[0]), int(tip[1])), 9, 2)
    for i in (-4, 0, 4):
        pygame.draw.line(surface, T.INK_FAINT, (tip[0] + i, tip[1] - 7), (tip[0] + i, tip[1] + 7), 1)


def stableboy(surface, feet, facing: float, walk_phase=0.0, moving=False, windup=0.0, t=0.0):
    """A stable boy: flat cap, waistcoat, a coil of rope; spins a loop overhead before throwing."""
    x, y = feet
    swing = math.sin(walk_phase) * 3 if moving else 0
    side = _side(facing)
    pygame.draw.line(surface, (70, 60, 50), (x - 3, y - 12), (x - 3 + swing, y), 3)
    pygame.draw.line(surface, (70, 60, 50), (x + 3, y - 12), (x + 3 - swing, y), 3)
    pygame.draw.rect(surface, (176, 150, 110), (x - 7, y - 30, 14, 19), border_radius=3)
    pygame.draw.rect(surface, (96, 70, 48), (x - 7, y - 30, 14, 12), border_radius=3)
    hx, hy = x + side, y - 36
    pygame.draw.circle(surface, T.SKIN, (hx, hy), 6)
    pygame.draw.circle(surface, T.INK, (hx + side * 3, hy - 1), 1)
    pygame.draw.ellipse(surface, (90, 80, 70), (hx - 8 + side * 2, hy - 8, 14, 6))
    pygame.draw.circle(surface, T.HAY_DARK, (x - side * 7, y - 20), 5, 2)          # rope coil at his hip
    if windup > 0:
        a = t * 14
        cx, cy = hx, hy - 16
        pygame.draw.ellipse(surface, T.HAY_DARK, (cx - 14 + math.cos(a) * 3, cy - 5, 28, 10), 2)
        pygame.draw.line(surface, T.HAY_DARK, (x + side * 5, y - 28), (cx + math.cos(a) * 12, cy), 2)


def dog(surface, feet, facing: float, walk_phase=0.0, moving=False, crouch=0.0):
    """A guard dog, side-on. crouch 0..1 lowers him before a pounce."""
    x, y = feet
    side = _side(facing)
    body_y = y - 16 + int(4 * crouch)
    for i, lx in enumerate((-9, -5, 6, 10)):
        swing = math.sin(walk_phase * 1.4 + i * math.pi / 2) * 3 if moving else 0
        pygame.draw.line(surface, (60, 44, 32), (x + side * lx, body_y + 4), (x + side * lx + swing, y), 3)
    pygame.draw.ellipse(surface, (92, 66, 44), (x - 14, body_y - 5, 28, 12))
    hx = x + side * 15
    pygame.draw.ellipse(surface, (92, 66, 44), (hx - 7, body_y - 11, 14, 11))
    pygame.draw.polygon(surface, (92, 66, 44), [(hx + side * 4, body_y - 6), (hx + side * 11, body_y - 3),
                                                (hx + side * 4, body_y)])
    pygame.draw.polygon(surface, (50, 36, 26), [(hx - side * 2, body_y - 10), (hx - side * 5, body_y - 16),
                                                (hx + side, body_y - 10)])
    pygame.draw.circle(surface, T.INK, (hx + side * 3, body_y - 7), 1)
    wag = math.sin(walk_phase * 2) * 4
    pygame.draw.line(surface, (60, 44, 32), (x - side * 13, body_y - 2), (x - side * 20, body_y - 8 + wag), 3)


def sugar(surface, center, t=0.0):
    x, y = center
    pygame.draw.rect(surface, (250, 248, 240), (x - 8, y - 8, 16, 16), border_radius=3)
    pygame.draw.rect(surface, T.INK_SOFT, (x - 8, y - 8, 16, 16), 1, border_radius=3)
    for k in range(3):
        a = t * 2 + k * 2.1
        sx, sy = x + math.cos(a) * 14, y + math.sin(a) * 14
        pygame.draw.line(surface, (255, 240, 180), (sx - 3, sy), (sx + 3, sy), 1)
        pygame.draw.line(surface, (255, 240, 180), (sx, sy - 3), (sx, sy + 3), 1)


def horseshoe(surface, center, t=0.0):
    x, y = center
    glow = 16 + 3 * math.sin(t * 6)
    halo = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.circle(halo, (255, 214, 90, 70), (32, 32), int(glow))
    surface.blit(halo, (x - 32, y - 32))
    pygame.draw.arc(surface, (226, 176, 50), (x - 10, y - 11, 20, 22), math.pi * 0.0, math.pi * 1.0, 5)
    pygame.draw.line(surface, (226, 176, 50), (x - 8, y), (x - 8, y + 9), 5)
    pygame.draw.line(surface, (226, 176, 50), (x + 8, y), (x + 8, y + 9), 5)


def coffee(surface, center, t=0.0):
    x, y = center
    pygame.draw.rect(surface, (246, 240, 228), (x - 7, y - 4, 14, 12), border_radius=3)
    pygame.draw.rect(surface, T.INK_SOFT, (x - 7, y - 4, 14, 12), 1, border_radius=3)
    pygame.draw.circle(surface, T.INK_SOFT, (x + 9, y + 1), 4, 1)
    pygame.draw.rect(surface, (90, 58, 36), (x - 5, y - 3, 10, 3))
    for k in (-3, 2):
        pygame.draw.arc(surface, T.INK_FAINT, (x + k - 2, y - 14 + 2 * math.sin(t * 3 + k), 5, 9), 1.5, 4.7, 1)


def stars(surface, center, t):
    x, y = center
    for k in range(3):
        a = t * 5 + k * 2.1
        sx, sy = x + math.cos(a) * 12, y + math.sin(a) * 4
        pygame.draw.polygon(surface, (240, 200, 60), [(sx, sy - 4), (sx + 1.5, sy - 1), (sx + 4, sy), (sx + 1.5, sy + 1),
                                                      (sx, sy + 4), (sx - 1.5, sy + 1), (sx - 4, sy), (sx - 1.5, sy - 1)])


def heart(surface, center, size, filled):
    x, y = center
    colour = T.RED if filled else T.PAPER_DARK
    r = size // 2
    pygame.draw.circle(surface, colour, (x - r // 2 - 1, y - r // 3), r // 2 + 1)
    pygame.draw.circle(surface, colour, (x + r // 2 + 1, y - r // 3), r // 2 + 1)
    pygame.draw.polygon(surface, colour, [(x - r, y - r // 4), (x + r, y - r // 4), (x, y + r)])
    pygame.draw.circle(surface, T.INK, (x - r // 2 - 1, y - r // 3), r // 2 + 1, 1)
    pygame.draw.circle(surface, T.INK, (x + r // 2 + 1, y - r // 3), r // 2 + 1, 1)


def gravel(surface, rect: pygame.Rect, seed: int):
    rng = random.Random(seed)
    pygame.draw.rect(surface, (176, 162, 136), rect)
    for _ in range(26):
        c = rng.choice([(140, 128, 108), (200, 188, 164), (120, 110, 94)])
        pygame.draw.circle(surface, c, (rect.x + rng.randrange(rect.width), rect.y + rng.randrange(rect.height)),
                           rng.choice((1, 1, 2)))


def bubble(surface, center, char: str, font, fill, progress: float | None = None):
    """The ? / ! over a scientist's head, with an optional ring showing how suspicious he is."""
    x, y = center
    pygame.draw.circle(surface, fill, (x, y), 13)
    pygame.draw.circle(surface, T.INK, (x, y), 13, 2)
    pygame.draw.polygon(surface, fill, [(x - 4, y + 11), (x + 4, y + 11), (x, y + 18)])
    img = font.render(char, True, T.INK)
    surface.blit(img, img.get_rect(center=(x, y + 1)))
    if progress is not None:
        pygame.draw.arc(surface, T.RED, (x - 18, y - 18, 36, 36), math.pi / 2,
                        math.pi / 2 + max(0.01, progress) * 2 * math.pi, 4)
