"""Full screens and overlays: title, pause, upgrade choice, game over, escape."""

import math

import pygame

from game.config import WIDTH, HEIGHT, TITLE
from game.ui import style as S

NAMES = {"grunt": "a SENTRY", "charger": "a HOUND", "sniper": "a LENS", "medic": "a MENDER",
         "warden": "THE WARDEN", None: "the facility"}


def dim(surface, alpha: int = 170):
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((4, 6, 12, alpha))
    surface.blit(veil, (0, 0))


def glowing_title(text: str, size: int, colour, spacing: int) -> pygame.Surface:
    f = S.display(size)
    probe = pygame.Surface((10, 10), pygame.SRCALPHA)
    rect = S.spaced(probe, text, f, colour, (0, 0), spacing, "topleft")
    w, h = rect.width + 80, rect.height + 60
    base = pygame.Surface((w, h))
    base.fill((0, 0, 0))
    S.spaced(base, text, f, colour, (w // 2, h // 2), spacing, "center")
    out = pygame.Surface((w, h))
    out.fill((0, 0, 0))
    out.blit(S.blur(base, 6), (0, 0), special_flags=pygame.BLEND_ADD)
    out.blit(S.blur(base, 3), (0, 0), special_flags=pygame.BLEND_ADD)
    S.spaced(out, text, f, S.WHITE, (w // 2, h // 2), spacing, "center")
    return out


def _stat(surface, label, value, center, colour=S.WHITE):
    S.text(surface, value, S.display(40), colour, center, "center")
    S.text(surface, label, S.font(15, S.UI, True), S.DIM, (center[0], center[1] + 32), "center")


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


class Screens:
    def __init__(self):
        self._title = None

    def title(self, surface, t: float, best):
        dim(surface, 175)
        if self._title is None:
            self._title = glowing_title(TITLE, 132, S.PLAYER, 18)
        rect = self._title.get_rect(center=(WIDTH // 2, 200))
        surface.blit(self._title, rect, special_flags=pygame.BLEND_ADD)
        S.text(surface, "Break out of the facility, room by room. The security AI is watching.",
               S.font(24, S.UI, True), S.DIM, (WIDTH // 2, 296), "center")
        pulse = 0.55 + 0.45 * math.sin(t * 4)
        S.spaced(surface, "PRESS ENTER", S.display(34), S.mix(S.BG, S.WHITE, pulse), (WIDTH // 2, 392), 6)
        items = [("W A S D", "move"), ("MOUSE", "aim"), ("CLICK", "shoot"), ("SPACE", "dash")]
        x = WIDTH // 2 - 330
        for key, what in items:
            box = S.keycap(surface, key, (x + 50, 488), S.WHITE, 16)
            S.text(surface, what, S.font(18, S.UI, True), S.DIM, (box.centerx, box.bottom + 16), "center")
            x += 220
        if best.score:
            S.text(surface, f"BEST  {best.score:07d}   ·   {best.label()}", S.font(18, S.UI, True), S.GOLD,
                   (WIDTH // 2, 588), "center")
        S.text(surface, "TAB  AI view      M  mute      F11  full screen      ESC  quit",
               S.font(15, S.UI, True), S.FAINT, (WIDTH // 2, HEIGHT - 34), "center")

    def pause(self, surface):
        dim(surface, 170)
        S.spaced(surface, "PAUSED", S.display(72), S.WHITE, (WIDTH // 2, HEIGHT // 2 - 40), 12)
        S.text(surface, "ESC  resume        R  restart        Q  quit to title", S.font(20, S.UI, True), S.DIM,
               (WIDTH // 2, HEIGHT // 2 + 40), "center")

    def upgrade(self, surface, run, mouse, t: float) -> int | None:
        """Draws the three cards; returns the index under the mouse (or None)."""
        dim(surface, 200)
        S.spaced(surface, f"FLOOR {run.floor} SECURED", S.display(60), S.GOOD, (WIDTH // 2, 132), 10)
        S.text(surface, "Choose an upgrade", S.font(24, S.UI, True), S.DIM, (WIDTH // 2, 190), "center")
        hovered = None
        for i, up in enumerate(run.offers):
            cx = WIDTH // 2 + (i - 1) * 360
            card = pygame.Rect(0, 0, 320, 260)
            card.center = (cx, 380)
            over = card.collidepoint(mouse)
            if over:
                hovered = i
                card.y -= 6
            panel = pygame.Surface(card.size, pygame.SRCALPHA)
            panel.fill((14, 20, 36, 240))
            surface.blit(panel, card.topleft)
            edge = S.PLAYER if over else S.scale(S.PLAYER, 0.45)
            pygame.draw.rect(surface, edge, card, 3 if over else 2, border_radius=10)
            if over:
                S.add_glow(surface, card.center, 170, S.scale(S.PLAYER, 0.18))
            S.text(surface, up.icon, S.display(56), S.PLAYER, (card.centerx, card.y + 64), "center")
            S.text(surface, up.name, S.display(30), S.WHITE, (card.centerx, card.y + 136), "center")
            S.text(surface, up.text, S.font(18, S.UI, True), S.DIM, (card.centerx, card.y + 178), "center")
            S.keycap(surface, str(i + 1), (card.centerx, card.bottom - 30), S.WHITE, 15)
        return hovered

    def game_over(self, surface, run, best, new_best: bool, t: float):
        dim(surface, 205)
        S.spaced(surface, "TERMINATED", S.display(86), S.DANGER, (WIDTH // 2, 150), 12)
        S.text(surface, f"Taken down by {NAMES.get(run.killer, 'the facility')} on floor {run.floor}, "
                        f"room {run.index + 1}.", S.font(22, S.UI, True), S.DIM, (WIDTH // 2, 226), "center")
        self._stats(surface, run, best, new_best)
        S.text(surface, "ENTER  try again          ESC  title", S.font(22, S.UI, True), S.WHITE,
               (WIDTH // 2, HEIGHT - 110), "center")

    def victory(self, surface, run, best, new_best: bool, t: float):
        dim(surface, 205)
        S.spaced(surface, "YOU ESCAPED", S.display(86), S.GOOD, (WIDTH // 2, 150), 12)
        S.text(surface, "The Warden is scrap. The facility is behind you.", S.font(22, S.UI, True), S.DIM,
               (WIDTH // 2, 226), "center")
        self._stats(surface, run, best, new_best)
        S.text(surface, "ENTER  play again          ESC  title", S.font(22, S.UI, True), S.WHITE,
               (WIDTH // 2, HEIGHT - 110), "center")

    def _stats(self, surface, run, best, new_best):
        y = 350
        stats = [("SCORE", f"{run.score:07d}"), ("ROOMS CLEARED", str(run.rooms_cleared)),
                 ("KILLS", str(run.kills)), ("TIME", _fmt_time(run.time))]
        for i, (label, value) in enumerate(stats):
            _stat(surface, label, value, (WIDTH // 2 + (i - 1.5) * 250, y))
        S.text(surface, "NEW BEST!" if new_best else f"best {best.score:07d}", S.font(22, S.UI, True),
               S.GOLD if new_best else S.DIM, (WIDTH // 2, y + 90), "center")
