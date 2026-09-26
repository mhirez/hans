"""AI VIEW (press TAB): see exactly what every enemy knows, wants and plans.

For every enemy: its sight cone, whether it can see you (solid line) or only remembers where
you were (dashed line to a red X, with how old that memory is), its A* path, where it's going
on purpose, its state, and its utility scores as bars (the winner is highlighted).
Hover the mouse over an enemy to see the tactical map it last scored (cover, firing, flank
or escape spots) as a heat map. The panel shows the squad's attack tokens and flanker.
"""

import math

import pygame

from game.config import TILE, VIEW_HALF_ANGLE, ALERT_HALF_ANGLE
from game.geometry import distance
from game.room import COLOURS
from game.ui import style as S


def px(p):
    return p[0] * TILE, p[1] * TILE


def draw(surface, room, mouse, t: float, director=None):
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    focus = None
    if room.enemies:
        m = (mouse[0] / TILE, mouse[1] / TILE)
        nearest = min(room.enemies, key=lambda e: distance(e.pos, m))
        if distance(nearest.pos, m) < 2.5:
            focus = nearest
    if focus is not None:
        _heatmap(layer, room, focus)
    for e in room.enemies:
        if not e.alert or e is focus:
            _cone(layer, room, e)
        _knowledge(layer, room, e, t)
    surface.blit(layer, (0, 0))
    placed: list[pygame.Rect] = []
    for e in room.enemies:
        _card(surface, room, e, e is focus, placed)
    _panel(surface, room, focus, director)


def _cone(layer, room, e):
    x, y = px(e.pos)
    half = ALERT_HALF_ANGLE if e.alert else VIEW_HALF_ANGLE
    reach = e.view_range * (1.2 if e.alert else 1.0)
    pts = [(x, y)]
    for i in range(21):
        a = e.facing - half + 2 * half * i / 20
        d = room.grid.raycast(e.pos, a, reach)
        pts.append((x + math.cos(a) * d * TILE, y + math.sin(a) * d * TILE))
    pygame.draw.lines(layer, (*COLOURS[e.kind], 90), True, pts, 1)


def _knowledge(layer, room, e, t):
    colour = COLOURS[e.kind]
    x, y = px(e.pos)
    s = e.senses
    if s.sees:
        pygame.draw.line(layer, (120, 255, 160, 170), (x, y), px(room.player.pos), 1)
    elif e.alert and s.last_known is not None:
        lx, ly = px(s.last_known)
        S.dashed(layer, (255, 90, 90, 190), (x, y), (lx, ly), 6, 6, 1)
        pygame.draw.line(layer, (255, 90, 90, 230), (lx - 7, ly - 7), (lx + 7, ly + 7), 3)
        pygame.draw.line(layer, (255, 90, 90, 230), (lx - 7, ly + 7), (lx + 7, ly - 7), 3)
        S.text(layer, f"{s.age(room.time):.1f}s ago", S.mono(11, True), (255, 150, 150), (lx + 10, ly - 8))
    if e.path:
        pts = [(x, y)] + [px(p) for p in e.path]
        for a, b in zip(pts, pts[1:]):
            S.dashed(layer, (*colour, 200), a, b, 4, 5, 2)
    if e.spot is not None and e.alert:
        sx, sy = px(e.spot)
        pygame.draw.polygon(layer, (*colour, 220), [(sx, sy - 8), (sx + 8, sy), (sx, sy + 8), (sx - 8, sy)], 2)


def _heatmap(layer, room, e):
    entry = room.tactics.debug.get(e.uid)
    if not entry:
        return
    purpose, scores, best = entry
    if not scores:
        return
    lo, hi = min(scores.values()), max(scores.values())
    span = max(1e-6, hi - lo)
    for (c, r), v in scores.items():
        k = (v - lo) / span
        colour = S.mix((40, 90, 255), (255, 60, 60), k)
        pygame.draw.rect(layer, (*colour, int(40 + 110 * k)), (c * TILE + 2, r * TILE + 2, TILE - 4, TILE - 4))
    if best is not None:
        pygame.draw.rect(layer, (255, 255, 255, 255), (best[0] * TILE, best[1] * TILE, TILE, TILE), 3)
        S.text(layer, purpose.upper(), S.font(14, S.UI, True), S.WHITE, (best[0] * TILE + TILE // 2, best[1] * TILE - 4), "midbottom")


def _card(surface, room, e, focused, placed):
    colour = COLOURS[e.kind]
    x, y = px(e.pos)
    title = f"{e.name} · {e.state}"
    tags = []
    if e.uid in room.coordinator.holders:
        tags.append("TOKEN")
    if room.coordinator.flanker == e.uid:
        tags.append("FLANKER")
    if not e.alert:
        tags.append(f"suspicion {int(e.senses.suspicion * 100)}%")
    if e.firewall > 0:
        tags.append("FIREWALL")
    if e.predicts:
        tags.append("LEADS SHOTS")
    if e.side == "seven":
        tags.append("REWRITTEN")
    rows = sorted(e.scores.items(), key=lambda kv: -kv[1])[:4] if e.alert else []
    if e.alert and len(e.foe_scores) > 1:
        target = max(e.foe_scores, key=e.foe_scores.get)
        tags.append(f"target: {target}")
    f = S.font(13, S.UI, True)
    small = S.mono(11)
    width = 150
    height = 20 + (14 if tags else 0) + 14 * len(rows)
    box = pygame.Rect(0, 0, width, height)
    box.midtop = (int(x), int(y + e.radius * TILE + 16))
    box.clamp_ip(surface.get_rect().inflate(-8, -8))
    for _ in range(8):
        hit = box.collidelist(placed)
        if hit < 0:
            break
        box.y = placed[hit].bottom + 2
    placed.append(box)
    panel = pygame.Surface(box.size, pygame.SRCALPHA)
    panel.fill((6, 8, 16, 225 if focused else 190))
    surface.blit(panel, box.topleft)
    pygame.draw.rect(surface, colour if focused else S.scale(colour, 0.6), box, 1)
    S.text(surface, title, f, colour, (box.x + 6, box.y + 3))
    yy = box.y + 20
    if tags:
        S.text(surface, "  ".join(tags), small, S.GOLD, (box.x + 6, yy))
        yy += 14
    for i, (name, v) in enumerate(rows):
        chosen = name == e.action
        S.text(surface, name, small, S.WHITE if chosen else S.DIM, (box.x + 6, yy))
        bar = pygame.Rect(box.x + 74, yy + 3, int(64 * min(1.2, max(0.0, v)) / 1.2), 7)
        pygame.draw.rect(surface, colour if chosen else S.FAINT, bar)
        S.text(surface, f"{v:.2f}", small, S.WHITE if chosen else S.DIM, (box.right - 4, yy), "topright")
        yy += 14


def _focus_line(room, focus) -> str:
    if focus is None:
        return "hover an enemy: see its tactical map"
    entry = room.tactics.debug.get(focus.uid)
    if not entry:
        return f"{focus.name}: no spots scored yet"
    return f"{focus.name}: {entry[0]} map (white = best)"


def _panel(surface, room, focus, director=None):
    c = room.coordinator
    lines = [("AI VIEW", S.GOLD),
             (f"attack tokens  {len(c.holders)} / {c.slots} in use", S.WHITE),
             (f"flanker  {'#' + str(c.flanker) if c.flanker else '-'}", S.WHITE),
             ("cone = what it can see", S.DIM),
             ("solid line = sees you", S.DIM),
             ("red X = where it thinks you are", S.DIM),
             ("bars = utility scores (best wins)", S.DIM),
             (_focus_line(room, focus), S.DIM)]
    box = pygame.Rect(10, 48, 270, 12 + 18 * len(lines))
    panel = pygame.Surface(box.size, pygame.SRCALPHA)
    panel.fill((6, 8, 16, 200))
    surface.blit(panel, box.topleft)
    pygame.draw.rect(surface, S.scale(S.GOLD, 0.5), box, 1)
    for i, (s, colour) in enumerate(lines):
        S.text(surface, s, S.font(15 if i == 0 else 13, S.UI, True), colour, (box.x + 10, box.y + 6 + 18 * i))
    if director is not None:
        _director(surface, director, box.bottom + 8)


def _director(surface, d, top: int):
    """ARGUS's model of Seven, and how it scored its countermeasures for this room."""
    p = d.profile
    habits = [("far away", p.far), ("up close", p.close), ("unseen", p.hidden), ("moving", p.moving),
              ("accuracy", p.accuracy), ("rewrites/room", min(1.0, p.rewrites / 2))]
    rows = sorted(d.scores.items(), key=lambda kv: -kv[1])[:4]
    box = pygame.Rect(10, top, 270, 44 + 16 * len(habits) + 16 * len(rows))
    panel = pygame.Surface(box.size, pygame.SRCALPHA)
    panel.fill((16, 12, 4, 210))
    surface.blit(panel, box.topleft)
    pygame.draw.rect(surface, S.scale(S.GOLD, 0.6), box, 1)
    S.text(surface, "ARGUS'S MODEL OF YOU", S.font(14, S.UI, True), S.GOLD, (box.x + 10, box.y + 5))
    y = box.y + 24
    for name, v in habits:
        S.text(surface, name, S.mono(11), S.DIM, (box.x + 10, y))
        pygame.draw.rect(surface, (50, 40, 20), (box.x + 120, y + 3, 100, 7))
        pygame.draw.rect(surface, S.GOLD, (box.x + 120, y + 3, int(100 * max(0.0, min(1.0, v))), 7))
        y += 16
    S.text(surface, "countermeasures (deployed in white)", S.mono(11), S.GOLD, (box.x + 10, y + 2))
    y += 18
    for name, v in rows:
        colour = S.WHITE if name in d.deployed else S.DIM
        S.text(surface, f"{name:<11} {v:.2f}", S.mono(11, name in d.deployed), colour, (box.x + 10, y))
        y += 16
