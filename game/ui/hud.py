"""The heads-up display: health, dash, where you are, hostiles left, score, boss bar, banners."""

import math

import pygame

from game.config import WIDTH, HEIGHT, DASH_TIME
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
    x += 84
    S.text(surface, "DEBUG", S.font(13, S.UI, True), S.DIM, (x, 6))
    bar = pygame.Rect(x, 24, 64, 6)
    pygame.draw.rect(surface, (30, 36, 56), bar)
    pygame.draw.rect(surface, (120, 200, 255), (bar.x, bar.y, int(bar.w * p.sync), bar.h))
    x += 84
    S.text(surface, "OVERRIDE", S.font(13, S.UI, True), S.DIM, (x, 6))
    for i in range(p.stats.max_charges):
        c = (x + 7 + i * 17, 28)
        if i < p.charges:
            S.add_glow(surface, c, 12, S.scale(S.PLAYER, 0.5))
            pygame.draw.polygon(surface, S.PLAYER, S.polygon(c, 6, 4, math.pi / 4))
        else:
            pygame.draw.polygon(surface, S.FAINT, S.polygon(c, 6, 4, math.pi / 4), 1)

    where = f"{room.plan.floor_name} · {room.plan.name}"
    S.text(surface, where, S.display(22), S.WHITE, (WIDTH // 2 + 50, BAR_H // 2 + 1), "center")
    n = room.hostiles
    if room.state == "fight":
        S.text(surface, f"{n} ROBOT{'S' if n != 1 else ''}", S.font(15, S.UI, True), S.DANGER,
               (WIDTH // 2 + 235, BAR_H // 2 + 1), "midleft")
    else:
        S.text(surface, "EXIT OPEN  >>", S.font(15, S.UI, True), S.GOOD, (WIDTH // 2 + 235, BAR_H // 2 + 1), "midleft")
    up = run.upload                                  # ARGUS copying itself out: a line creeping across
    colour = S.mix(S.GOLD, S.DANGER, up)
    pygame.draw.rect(surface, (40, 30, 20), (0, BAR_H, WIDTH, 3))
    pygame.draw.rect(surface, colour, (0, BAR_H, int(WIDTH * up), 3))
    S.text(surface, f"ARGUS UPLOAD {int(up * 100)}%", S.font(13, S.UI, True), colour, (WIDTH - 16, BAR_H + 6), "topright")
    S.text(surface, f"{run.total_score:07d}", S.display(24), S.WHITE, (WIDTH - 16, BAR_H // 2 + 1), "midright")
    if xray:
        S.text(surface, "AI VIEW", S.font(14, S.UI, True), S.GOLD, (WIDTH - 130, BAR_H // 2 + 1), "midright")

    boss = room.boss
    if boss is not None and not boss.dead:
        w = 620
        box = pygame.Rect((WIDTH - w) // 2, HEIGHT - 26, w, 10)
        S.text(surface, "ARGUS", S.display(20), S.GOLD, (box.centerx, box.y - 4), "midbottom")
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
    items = [("W A S D", "move"), ("CLICK", "shoot"), ("SPACE", "dash"), ("RIGHT CLICK", "hold: debug"),
             ("TAB", "AI view")]
    layer = pygame.Surface((WIDTH, 60), pygame.SRCALPHA)
    x = WIDTH // 2 - 520
    for key, what in items:
        box = S.keycap(layer, key, (x + 60, 30), S.WHITE, 15)
        S.text(layer, what, S.font(17, S.UI, True), S.DIM, (box.right + 10, 30), "midleft")
        x += 215
    layer.set_alpha(int(255 * min(1.0, alpha)))
    surface.blit(layer, (0, y - 30))


def argus_line(surface, line: str, t: float):
    """ARGUS speaks as you enter a room: typed out, held, then gone."""
    if not line or t > 6.0 or t < 0.9:
        return
    t -= 0.9
    shown = line[: int(t * 38)]
    alpha = min(1.0, (5.1 - t) * 1.5)
    if alpha <= 0 or not shown:
        return
    f = S.font(20, S.UI, True)
    label = S.font(14, S.UI, True).render("ARGUS", True, S.GOLD)
    img = f.render(shown, True, (255, 236, 200))
    w = max(420, img.get_width() + label.get_width() + 60)
    box = pygame.Rect(0, 0, w, 40)
    box.midtop = (WIDTH // 2, BAR_H + 14)
    panel = pygame.Surface(box.size, pygame.SRCALPHA)
    panel.fill((20, 14, 4, int(215 * alpha)))
    pygame.draw.rect(panel, (*S.GOLD, int(200 * alpha)), panel.get_rect(), 1)
    label.set_alpha(int(255 * alpha))
    img.set_alpha(int(255 * alpha))
    panel.blit(label, (14, (40 - label.get_height()) // 2))
    panel.blit(img, (28 + label.get_width(), (40 - img.get_height()) // 2))
    S.add_glow(surface, (box.x + 20, box.centery), 24, S.scale(S.GOLD, 0.4 * alpha))
    surface.blit(panel, box.topleft)


def crosshair(surface, pos, t: float, colour=S.PLAYER):
    x, y = int(pos[0]), int(pos[1])
    pygame.draw.circle(surface, colour, (x, y), 9, 2)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        pygame.draw.line(surface, colour, (x + dx * 13, y + dy * 13), (x + dx * 19, y + dy * 19), 2)
    pygame.draw.circle(surface, S.WHITE, (x, y), 2)
