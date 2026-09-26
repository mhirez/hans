"""Draws a room: the neon facility, doors, enemies, their warnings, the player and bullets.

The warning language is the same for every enemy, so it's learned once:
  - a thin line/band in the enemy's colour shows WHERE the attack will go, and it follows you;
  - it flashes WHITE and stops following for the last 0.25 s (locked: now move!);
  - a ring closing in on the enemy shows WHEN.
Calm enemies show their sight cone (white -> yellow -> red as they grow suspicious); once
they're alert the cones disappear to keep the fight readable.
"""

import math
import random

import pygame

from game.ai.charger import CHARGE_DIST
from game.ai.grunt import FAN
from game.config import TILE, WIDTH, HEIGHT, VIEW_HALF_ANGLE
from game.room import COLOURS
from game.rooms import ENTRY, EXIT
from game.ui import style as S


def px(p) -> tuple[float, float]:
    return p[0] * TILE, p[1] * TILE


class Renderer:
    def __init__(self):
        self._bg_for = None
        self.bg: pygame.Surface | None = None
        self.leds: list = []
        self.overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    # --- the static room ---------------------------------------------------------------------
    def background(self, room) -> pygame.Surface:
        if self._bg_for is not room:
            self.bg, self.leds = build_background(room.grid, room.plan.floor * 100 + room.plan.index)
            self._bg_for = room
        return self.bg

    def _leds(self, surface, t, off):
        """Status lights on the server racks: some steady, some blinking."""
        for x, y, colour, rate, phase in self.leds:
            on = rate == 0 or math.sin(t * rate + phase) > 0
            pygame.draw.rect(surface, colour if on else S.scale(colour, 0.25), (x + off[0], y + off[1], 3, 2))

    # --- the frame ---------------------------------------------------------------------------
    def draw(self, surface, room, fx, t: float, off=(0, 0)):
        ox, oy = off
        surface.fill(S.BG)
        surface.blit(self.background(room), off)
        self._leds(surface, t, off)
        self._doors(surface, room, t, off)
        fx.draw_under(surface, off)
        self._pickups(surface, room, t, off)

        self.overlay.fill((0, 0, 0, 0))
        for e in room.enemies:
            if not e.alert and e.kind != "warden":
                self._cone(self.overlay, room, e, off)
        for e in room.enemies:
            self._telegraph(self.overlay, surface, room, e, t, off)
        surface.blit(self.overlay, (0, 0))

        for e in room.enemies:
            beam = getattr(e, "beam", None)
            if beam is not None and not beam.dead:
                self._heal_beam(surface, e, beam, t, off)
        for e in room.enemies:
            self._enemy(surface, e, t, off)
        self._player(surface, room.player, t, off)
        self._bullets(surface, room, off)
        fx.draw(surface, off)
        for e in room.enemies:
            self._icon(surface, e, off)

    # --- pieces ------------------------------------------------------------------------------
    def _doors(self, surface, room, t, off):
        for tiles, is_exit in ((ENTRY, False), (EXIT, True)):
            locked = room.grid.at(*tiles[0]) == "D"
            x0, y0 = tiles[0][0] * TILE + off[0], tiles[0][1] * TILE + off[1]
            rect = pygame.Rect(x0, y0, TILE, TILE * len(tiles))
            if locked:
                pygame.draw.rect(surface, (40, 14, 24), rect)
                for i in range(4):
                    y = rect.y + 8 + i * (rect.height - 16) // 3
                    pygame.draw.line(surface, S.LOCKED, (rect.x + 6, y), (rect.right - 6, y), 3)
                S.add_glow(surface, rect.center, TILE, S.scale(S.LOCKED, 0.35))
            else:
                pygame.draw.rect(surface, (6, 20, 16), rect)
                S.add_glow(surface, rect.center, int(TILE * 1.6), S.scale(S.GOOD, 0.5 + 0.2 * math.sin(t * 5)))
                if is_exit:
                    for k in range(3):
                        phase = (t * 1.6 + k / 3) % 1
                        x = rect.x - TILE * 2.4 + phase * TILE * 2.2
                        c = S.scale(S.GOOD, math.sin(phase * math.pi))
                        cy = rect.centery
                        pygame.draw.lines(surface, c, False, [(x, cy - 12), (x + 11, cy), (x, cy + 12)], 4)

    def _pickups(self, surface, room, t, off):
        for k in room.pickups:
            x, y = px(k.pos)
            x, y = x + off[0], y + off[1] + math.sin(t * 5 + k.pos[0]) * 3
            S.add_glow(surface, (x, y), 22, S.scale(S.GOOD, 0.7))
            pygame.draw.circle(surface, (10, 40, 26), (int(x), int(y)), 9)
            pygame.draw.circle(surface, S.GOOD, (int(x), int(y)), 9, 2)
            pygame.draw.line(surface, S.WHITE, (x - 4, y), (x + 4, y), 2)
            pygame.draw.line(surface, S.WHITE, (x, y - 4), (x, y + 4), 2)

    def _cone(self, overlay, room, e, off):
        x, y = px(e.pos)
        s = e.senses.suspicion
        colour = S.mix((255, 255, 255), (255, 220, 60), min(1, s * 2)) if s < 0.5 else \
            S.mix((255, 220, 60), S.DANGER, (s - 0.5) * 2)
        pts = [(x + off[0], y + off[1])]
        n = 14
        for i in range(n + 1):
            a = e.facing - VIEW_HALF_ANGLE + 2 * VIEW_HALF_ANGLE * i / n
            d = room.grid.raycast(e.pos, a, e.view_range)
            pts.append((x + off[0] + math.cos(a) * d * TILE, y + off[1] + math.sin(a) * d * TILE))
        pygame.draw.polygon(overlay, (*colour, int(22 + 40 * s)), pts)
        pygame.draw.lines(overlay, (*colour, int(40 + 90 * s)), True, pts, 1)

    def _telegraph(self, overlay, surface, room, e, t, off):
        if e.windup <= 0 and e.state not in ("SWEEP",):
            return
        x, y = px(e.pos)
        x, y = x + off[0], y + off[1]
        colour = room.colour(e)
        k = e.windup
        live = S.WHITE if e.locked else colour
        alpha = 230 if e.locked else int(70 + 150 * k)
        width = 3 if e.locked else 2
        grid = room.grid
        kind = e.kind
        if kind == "grunt" and e.state == "AIM":
            for i in (-1, 0, 1):
                a = e.aim + i * getattr(e, "fan", FAN)
                d = min(14.0, grid.raycast(e.pos, a, 14.0))
                end = (x + math.cos(a) * d * TILE, y + math.sin(a) * d * TILE)
                pygame.draw.line(overlay, (*live, alpha if i == 0 else alpha // 2), (x, y), end, width if i == 0 else 1)
        elif kind == "charger" and e.state == "WINDUP":
            self._band(overlay, (x, y), e.aim, e.charge_len * TILE, e.radius * TILE, live, alpha)
            if e.charge_len < CHARGE_DIST - 0.05:                      # it will hit a wall: show the impact
                ex, ey = x + math.cos(e.aim) * (e.charge_len + e.radius) * TILE, y + math.sin(e.aim) * (e.charge_len + e.radius) * TILE
                pygame.draw.circle(overlay, (*live, alpha), (int(ex), int(ey)), 7, 2)
        elif kind == "sniper" and e.state == "AIM":
            end = (x + math.cos(e.aim) * e.laser_len * TILE, y + math.sin(e.aim) * e.laser_len * TILE)
            pulse = 0.6 + 0.4 * math.sin(t * 30)
            pygame.draw.line(overlay, (*live, int(alpha * (1 if e.locked else pulse))), (x, y), end, 3 if e.locked else 1)
            S.add_glow(surface, end, 14 if e.locked else 9, S.scale(live, 0.8))
        elif kind == "warden":
            self._warden_telegraph(overlay, surface, room, e, (x, y), live, alpha, t)
        # the "when": a ring closing in on the enemy
        if e.windup > 0 and e.state in ("AIM", "WINDUP"):
            r = e.radius * TILE * (1.1 + 1.6 * (1 - k))
            pygame.draw.circle(overlay, (*live, alpha), (int(x), int(y)), int(r), 2 if not e.locked else 3)

    def _band(self, overlay, origin, angle, length, half, colour, alpha):
        x, y = origin
        dx, dy = math.cos(angle), math.sin(angle)
        nx, ny = -dy * half, dx * half
        pts = [(x + nx, y + ny), (x + dx * length + nx, y + dy * length + ny),
               (x + dx * length - nx, y + dy * length - ny), (x - nx, y - ny)]
        pygame.draw.polygon(overlay, (*colour, alpha // 3), pts)
        pygame.draw.polygon(overlay, (*colour, alpha), pts, 2)

    def _warden_telegraph(self, overlay, surface, room, w, pos, live, alpha, t):
        x, y = pos
        if w.state == "SWEEP":
            end = (x + math.cos(w.aim) * w.beam_len * TILE, y + math.sin(w.aim) * w.beam_len * TILE)
            pygame.draw.line(overlay, (255, 230, 150, 120), pos, end, 18)
            pygame.draw.line(surface, S.WHITE, pos, end, 5)
            S.add_glow(surface, end, 26, S.GOLD)
            return
        if w.state != "WINDUP":
            return
        attack = w.attack
        if attack == "volley":
            for i in range(7):
                a = w.aim + math.radians(-30 + 10 * i)
                d = min(12.0, room.grid.raycast(w.pos, a, 12.0))
                pygame.draw.line(overlay, (*live, alpha // 2), pos, (x + math.cos(a) * d * TILE, y + math.sin(a) * d * TILE), 1)
        elif attack == "ring":
            r = w.radius * TILE + w.windup * TILE * 3
            pygame.draw.circle(overlay, (*live, alpha), (int(x), int(y)), int(r), 3)
        elif attack == "sweep":
            start = w.sweep_from if w.locked else w.aim - w.sweep_dir * math.radians(60)
            pts = [pos]
            for i in range(13):
                a = start + w.sweep_dir * math.radians(120) * i / 12
                d = min(20.0, room.grid.raycast(w.pos, a, 20.0))
                pts.append((x + math.cos(a) * d * TILE, y + math.sin(a) * d * TILE))
            pygame.draw.polygon(overlay, (*live, alpha // 4), pts)
            pygame.draw.lines(overlay, (*live, alpha), True, pts, 2)
        elif attack == "charge":
            self._band(overlay, pos, w.aim, w.beam_len * TILE, w.radius * TILE, live, alpha)

    def _heal_beam(self, surface, m, target, t, off):
        a = (px(m.pos)[0] + off[0], px(m.pos)[1] + off[1])
        b = (px(target.pos)[0] + off[0], px(target.pos)[1] + off[1])
        pygame.draw.line(surface, S.scale(S.GOOD, 0.5), a, b, 5)
        pygame.draw.line(surface, S.GOOD, a, b, 2)
        for k in range(3):
            f = (t * 1.8 + k / 3) % 1
            p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            S.add_glow(surface, p, 10, S.GOOD)
        S.add_glow(surface, b, 26, S.scale(S.GOOD, 0.6))

    def _enemy(self, surface, e, t, off):
        x, y = px(e.pos)
        if e.state == "WINDUP" and e.kind == "charger" and not e.locked:
            x += math.sin(t * 90) * 2
        x, y = x + off[0], y + off[1]
        colour = e.room.colour(e)
        r = e.radius * TILE * (1.18 if e.kind != "warden" else 1.0) * (0.82 if e.crouch else 1.0)
        S.add_glow(surface, (x, y), int(r * 2.4), S.scale(colour, 0.32 if e.alert else 0.18))
        fill = S.WHITE if e.flash > 0 else S.scale(colour, 0.22)
        edge = S.WHITE if e.flash > 0 else colour
        a = e.facing
        if e.kind == "grunt":
            body = S.polygon((x, y), r * 1.15, 4, a + math.pi / 4)
            pygame.draw.polygon(surface, fill, body)
            pygame.draw.polygon(surface, edge, body, 2)
            pygame.draw.line(surface, edge, (x, y), (x + math.cos(a) * r * 1.5, y + math.sin(a) * r * 1.5), 4)
            vx, vy = x + math.cos(a) * r * 0.45, y + math.sin(a) * r * 0.45
            pygame.draw.line(surface, S.WHITE, (vx - math.sin(a) * r * 0.45, vy + math.cos(a) * r * 0.45),
                             (vx + math.sin(a) * r * 0.45, vy - math.cos(a) * r * 0.45), 3)
        elif e.kind == "charger":
            tip = (x + math.cos(a) * r * 1.5, y + math.sin(a) * r * 1.5)
            left = (x + math.cos(a + 2.4) * r * 1.1, y + math.sin(a + 2.4) * r * 1.1)
            right = (x + math.cos(a - 2.4) * r * 1.1, y + math.sin(a - 2.4) * r * 1.1)
            back = (x - math.cos(a) * r * 0.4, y - math.sin(a) * r * 0.4)
            pygame.draw.polygon(surface, fill, [tip, left, back, right])
            pygame.draw.polygon(surface, edge, [tip, left, back, right], 2)
            pygame.draw.circle(surface, S.WHITE, (int(x + math.cos(a) * r * 0.5), int(y + math.sin(a) * r * 0.5)), 3)
        elif e.kind == "sniper":
            pts = [(x + math.cos(a) * r * 1.4, y + math.sin(a) * r * 1.4),
                   (x + math.cos(a + math.pi / 2) * r * 0.85, y + math.sin(a + math.pi / 2) * r * 0.85),
                   (x - math.cos(a) * r * 1.0, y - math.sin(a) * r * 1.0),
                   (x + math.cos(a - math.pi / 2) * r * 0.85, y + math.sin(a - math.pi / 2) * r * 0.85)]
            pygame.draw.line(surface, edge, (x, y), (x + math.cos(a) * r * 2.3, y + math.sin(a) * r * 2.3), 3)
            pygame.draw.polygon(surface, fill, pts)
            pygame.draw.polygon(surface, edge, pts, 2)
            lens = (x + math.cos(a) * r * 0.6, y + math.sin(a) * r * 0.6)
            S.add_glow(surface, lens, 10, colour)
            pygame.draw.circle(surface, S.WHITE, (int(lens[0]), int(lens[1])), 3)
        elif e.kind == "medic":
            pygame.draw.circle(surface, fill, (int(x), int(y)), int(r))
            pygame.draw.circle(surface, edge, (int(x), int(y)), int(r), 2)
            pygame.draw.line(surface, S.WHITE, (x - r * 0.5, y), (x + r * 0.5, y), 3)
            pygame.draw.line(surface, S.WHITE, (x, y - r * 0.5), (x, y + r * 0.5), 3)
            orb = (x + math.cos(t * 4 + e.uid) * r * 1.5, y + math.sin(t * 4 + e.uid) * r * 1.5)
            pygame.draw.circle(surface, colour, (int(orb[0]), int(orb[1])), 3)
        elif e.kind == "warden":
            self._warden(surface, e, (x, y), r, fill, edge, colour, t)
        if e.state == "STUNNED":
            for i in range(3):
                b = t * 6 + i * 2 * math.pi / 3
                pygame.draw.circle(surface, S.WHITE, (int(x + math.cos(b) * r), int(y - r * 1.3 + math.sin(b) * r * 0.35)), 3)
        if e.firewall > 0:                                   # ARGUS's firewall: shoot it off first
            ring = S.polygon((x, y), r * 1.75, 6, t * 0.8)
            pygame.draw.polygon(surface, S.scale((170, 210, 255), 0.7 + 0.3 * math.sin(t * 6)), ring, 2)
        if e.side == "player":                                # rewritten: how long it's yours for
            left = max(0.0, e.turned_until - e.room.time) / e.room.player.stats.rewrite_time
            rect = pygame.Rect(0, 0, int(r * 3.2), int(r * 3.2))
            rect.center = (int(x), int(y))
            pygame.draw.arc(surface, S.PLAYER, rect, math.pi / 2, math.pi / 2 + 2 * math.pi * left, 2)
            pygame.draw.polygon(surface, S.WHITE, S.polygon((x + r * 1.2, y - r * 1.2), 4, 4, 0))
        if e.hp < e.max_hp and e.kind != "warden":
            w = int(r * 2.2)
            bar = pygame.Rect(int(x - w / 2), int(y + r + 7), w, 4)
            pygame.draw.rect(surface, (30, 30, 44), bar)
            pygame.draw.rect(surface, colour, (bar.x, bar.y, int(bar.w * e.health), bar.h))

    def _warden(self, surface, w, pos, r, fill, edge, colour, t):
        x, y = pos
        core = {1: S.GOLD, 2: (255, 150, 40), 3: (255, 70, 60)}[w.phase]
        outer = S.polygon(pos, r * 1.15, 8, w.spin * 0.3)
        pygame.draw.polygon(surface, fill, outer)
        pygame.draw.polygon(surface, edge, outer, 3)
        inner = S.polygon(pos, r * 0.78, 6, -w.spin)
        pygame.draw.polygon(surface, S.scale(core, 0.25), inner)
        pygame.draw.polygon(surface, core, inner, 2)
        S.add_glow(surface, pos, int(r * 1.3), S.scale(core, 0.6 + 0.2 * math.sin(t * 8)))
        blink = 1.0 if (t * 0.7) % 4 > 0.12 else 0.15                  # the eye: it looks at you
        eye = pygame.Rect(0, 0, int(r * 1.15), max(2, int(r * 0.62 * blink)))
        eye.center = (int(x), int(y))
        pygame.draw.ellipse(surface, (235, 235, 225), eye)
        pupil = (int(x + math.cos(w.facing) * r * 0.22), int(y + math.sin(w.facing) * r * 0.12))
        if blink > 0.5:
            pygame.draw.circle(surface, core, pupil, int(r * 0.24))
            pygame.draw.circle(surface, (10, 10, 14), pupil, int(r * 0.12))
        pygame.draw.ellipse(surface, core, eye, 2)
        if w.shield > 0:
            pygame.draw.circle(surface, S.scale(S.PLAYER, 0.6 + 0.4 * math.sin(t * 20)), (int(x), int(y)), int(r * 1.5), 2)

    def _icon(self, surface, e, off):
        if not e.icon:
            return
        x, y = px(e.pos)
        k = 1 + 0.6 * math.exp(-e.icon_age * 12)
        colour = S.DANGER if e.icon == "!" else (255, 230, 90)
        img = S.display(int(26 * k)).render(e.icon, True, colour)
        rect = img.get_rect(midbottom=(int(x + off[0]), int(y + off[1] - e.radius * TILE - 6)))
        S.add_glow(surface, rect.center, 18, S.scale(colour, 0.5))
        surface.blit(img, rect)

    def _player(self, surface, p, t, off):
        for pos, life in p.trail:
            x, y = px(pos)
            S.add_glow(surface, (x + off[0], y + off[1]), int(p.radius * TILE * 2.2), S.scale(S.PLAYER, life * 2.4))
        if p.invulnerable > 0 and not p.dashing and int(t * 16) % 2 == 0:
            return
        # the data scientist, from above: lab-coat shoulders, hair, both arms out to a pistol
        x, y = px(p.pos)
        a = p.aim
        back = p.recoil * 3
        x, y = x + off[0] - math.cos(a) * back, y + off[1] - math.sin(a) * back
        r = p.radius * TILE * 1.3
        edge = S.WHITE if p.hurt_flash > 0.25 else S.PLAYER
        S.add_glow(surface, (x, y), int(r * 2.8), S.scale(S.PLAYER, 0.4))
        ca, sa = math.cos(a), math.sin(a)

        def at(along, across):                     # a point in the body's own frame
            return x + ca * along - sa * across, y + sa * along + ca * across

        for side in (-1, 1):                                                        # arms
            pygame.draw.line(surface, (196, 210, 222), at(0.0, side * r * 0.72), at(r * 0.95, side * r * 0.12), 6)
        pygame.draw.line(surface, (26, 30, 42), at(r * 0.8, 0), at(r * 1.65, 0), 6)  # pistol
        pygame.draw.circle(surface, edge, [int(v) for v in at(r * 1.65, 0)], 2)
        body = []
        for k in range(24):
            t = 2 * math.pi * k / 24
            c, s_ = math.cos(t), math.sin(t)
            body.append(at(math.copysign(abs(c) ** 0.6, c) * r * 0.42, math.copysign(abs(s_) ** 0.6, s_) * r * 0.95))
        pygame.draw.polygon(surface, (214, 228, 238), body)                         # lab-coat shoulders
        pygame.draw.polygon(surface, edge, body, 2)
        head = [int(v) for v in at(r * 0.05, 0)]
        pygame.draw.circle(surface, (52, 40, 34), head, int(r * 0.42))              # hair
        pygame.draw.circle(surface, (20, 16, 14), head, int(r * 0.42), 1)

    def _bullets(self, surface, room, off):
        for b in room.bullets:
            x, y = px(b.pos)
            x, y = x + off[0], y + off[1]
            speed = math.hypot(*b.vel) or 1
            dx, dy = b.vel[0] / speed, b.vel[1] / speed
            if b.owner is room.player:
                tail = (x - dx * 14, y - dy * 14)
                S.add_glow(surface, (x, y), 12, S.scale(S.PLAYER, 0.6))
                pygame.draw.line(surface, S.PLAYER, tail, (x, y), 4)
                pygame.draw.line(surface, S.WHITE, (x - dx * 7, y - dy * 7), (x, y), 2)
                continue
            colour = S.PLAYER if b.side == "player" else COLOURS.get(getattr(b.owner, "kind", ""), S.DANGER)
            if b.heavy:
                tail = (x - dx * 34, y - dy * 34)
                S.add_glow(surface, (x, y), 18, colour)
                pygame.draw.line(surface, colour, tail, (x, y), 5)
                pygame.draw.line(surface, S.WHITE, (x - dx * 18, y - dy * 18), (x, y), 2)
            else:
                rr = int(b.radius * TILE)
                S.add_glow(surface, (x, y), rr * 3, S.scale(colour, 0.8))
                pygame.draw.circle(surface, colour, (int(x), int(y)), rr)
                pygame.draw.circle(surface, S.WHITE, (int(x), int(y)), max(2, rr - 3))


def build_background(grid, seed: int) -> tuple[pygame.Surface, list]:
    rng = random.Random(seed)
    leds = []
    surf = pygame.Surface((WIDTH, HEIGHT))
    surf.fill(S.BG)
    edges = pygame.Surface((WIDTH, HEIGHT))
    edges.fill((0, 0, 0))
    for r in range(grid.rows):
        for c in range(grid.cols):
            rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
            ch = grid.at(c, r)
            if ch == ".":
                pygame.draw.rect(surf, S.FLOOR if (c + r) % 2 else S.FLOOR_ALT, rect)
                pygame.draw.rect(surf, S.GRID, rect, 1)
                if rng.random() < 0.06:
                    for cx, cy in ((4, 4), (TILE - 5, 4), (4, TILE - 5), (TILE - 5, TILE - 5)):
                        pygame.draw.circle(surf, S.GRID, (rect.x + cx, rect.y + cy), 2)
            elif ch == "X":                                            # a server rack, seen from above
                pygame.draw.rect(surf, S.COVER, rect)
                inner = rect.inflate(-6, -6)
                pygame.draw.rect(surf, S.COVER_TOP, inner)
                for k in range(inner.y + 4, inner.bottom - 2, 6):
                    pygame.draw.line(surf, (40, 46, 76), (inner.x + 3, k), (inner.right - 12, k), 1)
                    colour = rng.choice(((80, 255, 160), (90, 235, 255), (255, 200, 80), (80, 255, 160)))
                    rate = rng.choice((0, 0, 0, 3.0, 7.0, 13.0))
                    leds.append((inner.right - 9, k - 1, colour, rate, rng.uniform(0, 6.3)))
            else:
                pygame.draw.rect(surf, S.WALL, rect)
                if (c + r) % 3 == 0:
                    pygame.draw.line(surf, (26, 31, 52), rect.topleft, rect.bottomright, 1)
    for r in range(grid.rows):
        for c in range(grid.cols):
            ch = grid.at(c, r)
            if ch not in "#X":
                continue
            colour = S.WALL_EDGE if ch == "#" else S.COVER_EDGE
            x0, y0, x1, y1 = c * TILE, r * TILE, (c + 1) * TILE - 1, (r + 1) * TILE - 1
            for dc, dr, a, b in ((1, 0, (x1, y0), (x1, y1)), (-1, 0, (x0, y0), (x0, y1)),
                                 (0, 1, (x0, y1), (x1, y1)), (0, -1, (x0, y0), (x1, y0))):
                n = grid.at(c + dc, r + dr)
                if n in ".D" and 0 <= c + dc < grid.cols and 0 <= r + dr < grid.rows:
                    pygame.draw.line(surf, colour, a, b, 2)
                    pygame.draw.line(edges, colour, a, b, 5)
    glow = S.blur(edges, 4)
    surf.blit(glow, (0, 0), special_flags=pygame.BLEND_ADD)
    surf.blit(glow, (0, 0), special_flags=pygame.BLEND_ADD)
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(24):
        pygame.draw.rect(shade, (0, 0, 0, int(90 * (1 - i / 24) ** 2)), (i * 3, i * 3, WIDTH - i * 6, HEIGHT - i * 6), 3)
    surf.blit(shade, (0, 0))
    return (surf.convert() if pygame.display.get_surface() else surf), leds

