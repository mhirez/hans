"""The heads-up display: health, dash, where you are, hostiles left, score, boss bar, banners."""

import math

import pygame

from game.config import WIDTH, HEIGHT, ROOMS_PER_FLOOR, DASH_TIME
from game.ui import style as S

BAR_H = 40


def hexagon(surface, center, r, colour, width=0):
    pygame.draw.polygon(surface, colour, S.polygon(center, r, 6, math.pi / 6), width)


def draw(surface, run, t: float, xray: bool):
    room, p = run.room, run.player
    strip = pygame.Surface((WIDTH, BAR_H), pygame.SRCALPHA)
    strip.fill((6, 8, 14, 215))
    surface.blit(strip, (0, 0))
    pygame.draw.line(surface, (40, 60, 100), (0, BAR_H), (WIDTH, BAR_H), 1)

    low = p.hp <= 2
    for i in range(p.stats.max_hp):
        c = (22 + i * 25, 20)
        if i < p.hp:
            colour = S.mix(S.DANGER, S.WHITE, 0.3 * (1 + math.sin(t * 10))) if low else S.PLAYER
            S.add_glow(surface, c, 16, S.scale(colour, 0.35))
            hexagon(surface, c, 10, colour)
        else:
            hexagon(surface, c, 10, S.FAINT, 2)
    x = 22 + p.stats.max_hp * 25 + 12
    S.text(surface, "DASH", S.font(13, S.UI, True), S.DIM, (x, 6))
    bar = pygame.Rect(x, 24, 64, 6)
    ready = 1 - p.dash_ready / max(0.01, p.stats.dash_cooldown + DASH_TIME)
    pygame.draw.rect(surface, (30, 36, 56), bar)
    pygame.draw.rect(surface, S.PLAYER if p.dash_ready <= 0 else S.DIM, (bar.x, bar.y, int(bar.w * min(1, ready)), bar.h))

    where = f"FLOOR {run.floor}   ·   ROOM {run.index + 1} / {ROOMS_PER_FLOOR}"
    if room.plan.kind == "lockdown":
        where += "   ·   LOCKDOWN"
    elif room.plan.kind == "boss":
        where = f"FLOOR {run.floor}   ·   THE CORE"
    S.text(surface, where, S.display(22), S.WHITE, (WIDTH // 2, BAR_H // 2 + 1), "center")
    n = room.hostiles
    if room.state == "fight":
        S.text(surface, f"{n} HOSTILE{'S' if n != 1 else ''}", S.font(15, S.UI, True), S.DANGER,
               (WIDTH // 2 + 230, BAR_H // 2 + 1), "midleft")
    else:
        S.text(surface, "EXIT OPEN  >>", S.font(15, S.UI, True), S.GOOD, (WIDTH // 2 + 230, BAR_H // 2 + 1), "midleft")
    S.text(surface, f"{run.total_score:07d}", S.display(24), S.WHITE, (WIDTH - 16, BAR_H // 2 + 1), "midright")
    if xray:
        S.text(surface, "AI VIEW", S.font(14, S.UI, True), S.GOLD, (WIDTH - 130, BAR_H // 2 + 1), "midright")

    boss = room.boss
    if boss is not None and not boss.dead:
        w = 620
        box = pygame.Rect((WIDTH - w) // 2, HEIGHT - 26, w, 10)
        S.text(surface, "THE WARDEN", S.display(20), S.GOLD, (box.centerx, box.y - 4), "midbottom")
        pygame.draw.rect(surface, (40, 30, 20), box)
        pygame.draw.rect(surface, S.GOLD, (box.x, box.y, int(w * boss.health), box.h))
        for f in (0.33, 0.66):
            pygame.draw.line(surface, S.BG, (box.x + int(w * f), box.y), (box.x + int(w * f), box.bottom), 2)
        pygame.draw.rect(surface, S.scale(S.GOLD, 0.6), box, 1)


def banner(surface, title: str, subtitle: str, alpha: float, colour=S.WHITE):
    if alpha <= 0:
        return
    a = int(255 * min(1.0, alpha))
    band = pygame.Surface((WIDTH, 120), pygame.SRCALPHA)
    band.fill((4, 6, 12, int(170 * min(1.0, alpha))))
    y = HEIGHT // 2 - 60
    surface.blit(band, (0, y))
    pygame.draw.line(surface, S.scale(colour, 0.5 * min(1, alpha)), (0, y), (WIDTH, y), 1)
    pygame.draw.line(surface, S.scale(colour, 0.5 * min(1, alpha)), (0, y + 119), (WIDTH, y + 119), 1)
    S.spaced(surface, title, S.display(58), colour, (WIDTH // 2, y + 46), 8, "center", a)
    if subtitle:
        S.text(surface, subtitle, S.font(22, S.UI, True), S.DIM, (WIDTH // 2, y + 94), "center", a)


def controls_hint(surface, alpha: float):
    if alpha <= 0:
        return
    y = HEIGHT - 34
    items = [("W A S D", "move"), ("MOUSE", "aim"), ("CLICK", "shoot"), ("SPACE", "dash"), ("TAB", "AI view")]
    layer = pygame.Surface((WIDTH, 60), pygame.SRCALPHA)
    x = WIDTH // 2 - 430
    for key, what in items:
        box = S.keycap(layer, key, (x + 60, 30), S.WHITE, 15)
        S.text(layer, what, S.font(17, S.UI, True), S.DIM, (box.right + 10, 30), "midleft")
        x += 185
    layer.set_alpha(int(255 * min(1.0, alpha)))
    surface.blit(layer, (0, y - 30))


def crosshair(surface, pos, t: float, colour=S.PLAYER):
    x, y = int(pos[0]), int(pos[1])
    pygame.draw.circle(surface, colour, (x, y), 9, 2)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        pygame.draw.line(surface, colour, (x + dx * 13, y + dy * 13), (x + dx * 19, y + dy * 19), 2)
    pygame.draw.circle(surface, S.WHITE, (x, y), 2)
