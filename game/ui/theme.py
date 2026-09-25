"""The 1904 look: sepia palette, period typefaces, film grain and silent-film intertitles.

X-Ray annotations are drawn in 'red pencil' and 'blue ink', as if Pfungst marked up the scene.
"""

import random

import pygame

from game.config import WIDTH, HEIGHT

PAPER = (236, 224, 197)
PAPER_DARK = (218, 202, 168)
PAPER_EDGE = (196, 176, 138)
INK = (46, 34, 24)
INK_SOFT = (104, 86, 64)
INK_FAINT = (150, 132, 106)
FILM = (26, 20, 14)
FILM_TEXT = (232, 220, 192)

GROUND = (198, 176, 138)
GROUND_ALT = (190, 167, 128)
GROUT = (170, 148, 110)
WALL = (128, 100, 72)
WALL_DARK = (100, 78, 55)
WOOD = (104, 70, 42)
WOOD_DARK = (74, 50, 30)
HAY = (208, 174, 98)
HAY_DARK = (172, 138, 66)
WATER = (122, 134, 128)
STONE = (150, 138, 118)

HORSE = (124, 80, 46)
HORSE_DARK = (86, 54, 31)
MANE = (54, 36, 22)
SKIN = (222, 190, 160)
COAT = (58, 50, 46)
BEARD = (238, 232, 220)
CARROT = (200, 100, 40)
LEAF = (96, 116, 60)

RED = (150, 44, 26)          # red pencil: paths, wrong, warnings
BLUE = (52, 80, 118)         # blue ink: perception, sight lines
GREEN = (70, 104, 54)        # correct
GOLD = (176, 138, 70)

SERIF = "baskerville,hoeflertext,georgia,palatino,timesnewroman"
DISPLAY = "bigcaslon,didot,bodoni72,baskerville,georgia,timesnewroman"
TYPE = "americantypewriter,couriernew,courier,menlo,monospace"


class Theme:
    def __init__(self, seed: int = 7):
        self._fonts: dict[tuple, pygame.font.Font] = {}
        rng = random.Random(seed)
        self.grain = [self._make_grain(rng) for _ in range(4)]
        self.vignette = self._make_vignette()
        if pygame.display.get_surface() is not None:     # faster blits once a window exists
            self.grain = [g.convert_alpha() for g in self.grain]
            self.vignette = self.vignette.convert_alpha()
        self.frame = 0

    # --- fonts ---------------------------------------------------------------------------
    def font(self, size: int, family: str = SERIF, bold: bool = False, italic: bool = False) -> pygame.font.Font:
        key = (size, family, bold, italic)
        if key not in self._fonts:
            self._fonts[key] = pygame.font.SysFont(family, size, bold=bold, italic=italic)
        return self._fonts[key]

    def serif(self, size, bold=False, italic=False):
        return self.font(size, SERIF, bold, italic)

    def display(self, size, bold=False):
        return self.font(size, DISPLAY, bold)

    def type(self, size, bold=False):
        return self.font(size, TYPE, bold)

    # --- film effects ----------------------------------------------------------------
    @staticmethod
    def _make_grain(rng: random.Random) -> pygame.Surface:
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for _ in range(2600):
            shade = rng.randint(0, 60)
            s.fill((shade, shade * 0.8, shade * 0.6, rng.randint(14, 34)),
                   (rng.randrange(WIDTH), rng.randrange(HEIGHT), rng.choice((1, 1, 2)), rng.choice((1, 1, 2))))
        for _ in range(3):   # the odd vertical scratch
            x = rng.randrange(WIDTH)
            pygame.draw.line(s, (40, 30, 20, 18), (x, 0), (x + rng.randint(-6, 6), HEIGHT))
        return s

    @staticmethod
    def _make_vignette() -> pygame.Surface:
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        steps = 26
        for i in range(steps):
            alpha = int(90 * (1 - i / steps) ** 2.2)
            inset = i * 10
            pygame.draw.rect(s, (20, 12, 6, alpha), (inset - 260, inset - 260, WIDTH + 520 - 2 * inset,
                                                     HEIGHT + 520 - 2 * inset), width=12, border_radius=260)
        return s

    def film_overlay(self, surface: pygame.Surface, area: pygame.Rect | None = None):
        self.frame += 1
        grain = self.grain[(self.frame // 4) % len(self.grain)]
        if area is None:
            surface.blit(grain, (0, 0))
            surface.blit(self.vignette, (0, 0))
        else:
            surface.blit(grain, area.topleft, area)

    # --- drawing helpers -------------------------------------------------------------
    def text(self, surface, text, font, color, pos, anchor="topleft", max_width=None) -> pygame.Rect:
        if max_width is not None and font.size(text)[0] > max_width:
            while text and font.size(text + "...")[0] > max_width:
                text = text[:-1]
            text += "..."
        img = font.render(text, True, color)
        rect = img.get_rect(**{anchor: pos})
        surface.blit(img, rect)
        return rect

    def spaced(self, surface, text, font, color, pos, spacing=2, anchor="topleft") -> pygame.Rect:
        """Letter-spaced small caps look for headings."""
        glyphs = [font.render(ch, True, color) for ch in text]
        width = sum(g.get_width() for g in glyphs) + spacing * (len(glyphs) - 1)
        rect = pygame.Rect(0, 0, width, font.get_height())
        setattr(rect, anchor, pos)
        x = rect.x
        for g in glyphs:
            surface.blit(g, (x, rect.y))
            x += g.get_width() + spacing
        return rect

    def wrap(self, text, font, width) -> list[str]:
        words, lines, line = text.split(), [], ""
        for w in words:
            trial = f"{line} {w}".strip()
            if font.size(trial)[0] <= width:
                line = trial
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        return lines

    def ornate_border(self, surface, rect: pygame.Rect, color, inset=10):
        pygame.draw.rect(surface, color, rect, 2)
        inner = rect.inflate(-inset * 2, -inset * 2)
        pygame.draw.rect(surface, color, inner, 1)
        for cx, cy in (inner.topleft, inner.topright, inner.bottomleft, inner.bottomright):
            pygame.draw.circle(surface, color, (cx, cy), 4, 1)
            pygame.draw.circle(surface, color, (cx, cy), 1)
        mid = rect.centerx
        for y in (rect.top + inset // 2, rect.bottom - inset // 2):
            pygame.draw.line(surface, color, (mid - 40, y), (mid + 40, y), 1)
            pygame.draw.polygon(surface, color, [(mid - 5, y), (mid, y - 4), (mid + 5, y), (mid, y + 4)])

    def bar(self, surface, rect: pygame.Rect, value: float, color, back=PAPER_DARK, border=INK_SOFT):
        pygame.draw.rect(surface, back, rect)
        fill = rect.copy()
        fill.width = max(0, int(rect.width * max(0.0, min(1.0, value))))
        pygame.draw.rect(surface, color, fill)
        pygame.draw.rect(surface, border, rect, 1)

    def rule(self, surface, x1, x2, y, color=INK_SOFT):
        pygame.draw.line(surface, color, (x1, y), (x2, y), 1)
        pygame.draw.line(surface, color, (x1, y + 3), (x2, y + 3), 1)


def dashed_line(surface, color, a, b, dash=6, gap=4, width=2):
    ax, ay = a
    bx, by = b
    length = max(1.0, ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5)
    dx, dy = (bx - ax) / length, (by - ay) / length
    d = 0.0
    while d < length:
        e = min(d + dash, length)
        pygame.draw.line(surface, color, (ax + dx * d, ay + dy * d), (ax + dx * e, ay + dy * e), width)
        d = e + gap
