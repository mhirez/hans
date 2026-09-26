"""The look: dark facility, neon edges, glowing shapes. Colours, fonts, glow sprites, text."""

import math

import pygame

BG = (8, 10, 18)
FLOOR = (13, 16, 28)
FLOOR_ALT = (15, 19, 33)
GRID = (22, 28, 46)
WALL = (19, 23, 39)
WALL_EDGE = (60, 175, 255)
COVER = (25, 29, 50)
COVER_TOP = (33, 38, 64)
COVER_EDGE = (150, 120, 255)
WHITE = (238, 242, 255)
DIM = (120, 132, 165)
FAINT = (70, 80, 110)
PLAYER = (90, 235, 255)
DANGER = (255, 70, 90)
GOOD = (80, 255, 160)
GOLD = (255, 210, 90)
LOCKED = (255, 60, 90)

DISPLAY = "dincondensed,avenirnextcondensed,futura,arialblack,arial"
UI = "avenirnextcondensed,avenirnext,futura,helveticaneue,arial"
MONO = "menlo,monaco,couriernew,monospace"

_fonts: dict = {}
_glows: dict = {}


def reset():
    """Forget cached fonts (they die with pygame.quit(); a new Game starts fresh)."""
    _fonts.clear()


def font(size: int, family: str = UI, bold: bool = False) -> pygame.font.Font:
    key = (size, family, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont(family, size, bold=bold)
    return _fonts[key]


def display(size: int) -> pygame.font.Font:
    return font(size, DISPLAY, True)


def mono(size: int, bold: bool = False) -> pygame.font.Font:
    return font(size, MONO, bold)


def text(surface, s: str, f: pygame.font.Font, colour, pos, anchor: str = "topleft", alpha: int = 255):
    img = f.render(s, True, colour)
    if alpha < 255:
        img.set_alpha(alpha)
    rect = img.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    surface.blit(img, rect)
    return rect


def spaced(surface, s: str, f: pygame.font.Font, colour, pos, spacing: int, anchor: str = "center", alpha=255):
    """Letter-spaced text (for titles)."""
    imgs = [f.render(ch, True, colour) for ch in s]
    width = sum(i.get_width() for i in imgs) + spacing * (len(imgs) - 1)
    height = max(i.get_height() for i in imgs)
    strip = pygame.Surface((width, height), pygame.SRCALPHA)
    x = 0
    for img in imgs:
        strip.blit(img, (x, 0))
        x += img.get_width() + spacing
    if alpha < 255:
        strip.set_alpha(alpha)
    rect = strip.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
    surface.blit(strip, rect)
    return rect


def glow(radius: int, colour, strength: float = 1.0) -> pygame.Surface:
    """A soft radial light, for additive blending (special_flags=pygame.BLEND_ADD)."""
    radius = max(2, int(radius))
    key = (radius, colour, round(strength, 2))
    if key not in _glows:
        surf = pygame.Surface((radius * 2, radius * 2))
        surf.fill((0, 0, 0))
        for r in range(radius, 0, -1):
            k = (1 - r / radius) ** 2 * strength
            pygame.draw.circle(surf, tuple(min(255, int(c * k)) for c in colour), (radius, radius), r)
        _glows[key] = surf
    return _glows[key]


def add_glow(surface, pos, radius: int, colour, strength: float = 1.0):
    g = glow(radius, colour, strength)
    surface.blit(g, (int(pos[0]) - g.get_width() // 2, int(pos[1]) - g.get_height() // 2),
                 special_flags=pygame.BLEND_ADD)


def blur(surface: pygame.Surface, factor: int = 4) -> pygame.Surface:
    w, h = surface.get_size()
    small = pygame.transform.smoothscale(surface, (max(1, w // factor), max(1, h // factor)))
    small = pygame.transform.smoothscale(small, (max(1, w // (factor * 2)), max(1, h // (factor * 2))))
    return pygame.transform.smoothscale(small, (w, h))


def mix(a, b, t: float):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def scale(c, k: float):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def polygon(center, radius: float, sides: int, angle: float):
    return [(center[0] + math.cos(angle + 2 * math.pi * i / sides) * radius,
             center[1] + math.sin(angle + 2 * math.pi * i / sides) * radius) for i in range(sides)]


def dashed(surface, colour, a, b, dash: int = 8, gap: int = 6, width: int = 2):
    length = math.dist(a, b)
    if length < 1:
        return
    dx, dy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    d = 0.0
    while d < length:
        e = min(length, d + dash)
        pygame.draw.line(surface, colour, (a[0] + dx * d, a[1] + dy * d), (a[0] + dx * e, a[1] + dy * e), width)
        d += dash + gap


def keycap(surface, label: str, center, colour=WHITE, size: int = 18):
    f = mono(size, True)
    img = f.render(label, True, colour)
    box = img.get_rect(center=(int(center[0]), int(center[1]))).inflate(22, 12)
    pygame.draw.rect(surface, (20, 26, 44), box, border_radius=6)
    pygame.draw.rect(surface, scale(colour, 0.7), box, 2, border_radius=6)
    surface.blit(img, img.get_rect(center=box.center))
    return box
