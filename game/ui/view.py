"""Draws a Play: the moonlit courtyard, lantern light, everyone in it, the objective bar,
the tutorial arrow, and (press X) the AI X-Ray."""

import math

import pygame

from game.config import WIDTH, TILE, HUD_H, PLAY_Y, PLAY_H, HINT_RADIUS, VIEW_RANGE, VIEW_HALF_ANGLE
from game.ai.perception import cone
from game.level import Level, distance
from game.ui import sprites, theme as T
from game.ui.theme import dashed_line

NIGHT = (104, 100, 128)          # multiply: moonlit sepia
LAMP = (255, 196, 110, 38)
ALARM = (255, 90, 60, 50)


class PlayView:
    def __init__(self, theme: T.Theme):
        self.theme = theme
        self._level_id = None
        self.day = self.night = None
        self.mask = None

    # --- layout --------------------------------------------------------------------------
    def origin(self, level: Level) -> tuple[int, int]:
        return (WIDTH - level.cols * TILE) // 2, PLAY_Y + (PLAY_H - level.rows * TILE) // 2

    def px(self, level: Level, p) -> tuple[int, int]:
        ox, oy = self.origin(level)
        return int(ox + p[0] * TILE), int(oy + p[1] * TILE)

    def _prepare(self, level: Level):
        if self._level_id == id(level):
            return
        self._level_id = id(level)
        w, h = level.cols * TILE, level.rows * TILE
        day = pygame.Surface((w, h))
        for r in range(level.rows):
            for c in range(level.cols):
                rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                ch = level.at(c, r)
                if ch in "#D":
                    sprites.wall(day, rect, c * 31 + r)
                elif ch == "g":
                    sprites.gravel(day, rect, c * 13 + r * 7)
                else:
                    sprites.floor(day, rect, c * 17 + r * 7)
        for r in range(level.rows):
            for c in range(level.cols):
                rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                ch = level.at(c, r)
                if ch == "h":
                    sprites.hay(day, rect)
                elif ch == "t":
                    sprites.trough(day, rect)
                elif ch == "s":
                    sprites.screen(day, rect)
                elif ch == "c" and level.at(c - 1, r) != "c":
                    run = 1
                    while level.at(c + run, r) == "c":
                        run += 1
                    sprites.cart(day, pygame.Rect(rect.x, rect.y, TILE * run, TILE))
        # an alpha copy, so BLEND_RGBA_MULT can cut it down to the lantern cones each frame
        self.day = day.convert_alpha() if pygame.display.get_surface() else self._alpha(day)
        self.night = day.copy()
        self.night.fill(NIGHT, special_flags=pygame.BLEND_MULT)
        self.mask = pygame.Surface((w, h), pygame.SRCALPHA)

    @staticmethod
    def _alpha(surface):
        out = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        out.blit(surface, (0, 0))
        return out

    # --- main ----------------------------------------------------------------------------
    def draw(self, surface, play, xray: bool, t: float, banner: str | None = None):
        level = play.level
        self._prepare(level)
        ox, oy = self.origin(level)
        surface.fill(T.FILM)
        surface.blit(self.night, (ox, oy))
        self._lanterns(surface, play, ox, oy)
        self._doors(surface, play, t)
        self._owner_circle(surface, play, t)
        self._noises(surface, play)
        self._figures(surface, play, t)
        if xray:
            self._xray(surface, play)
        self._hud(surface, play, xray)
        top = self._banner(surface, banner) if banner else self._tip(surface, play, t)
        self._toast(surface, play, top)
        self.theme.film_overlay(surface)

    def _lanterns(self, surface, play, ox, oy):
        level = play.level
        polys = []
        self.mask.fill((0, 0, 0, 0))
        for s in play.scientists:
            pts = [(x * TILE, y * TILE) for x, y in cone(level, s.pos, s.angle, VIEW_RANGE, VIEW_HALF_ANGLE)]
            polys.append((s, pts))
            pygame.draw.polygon(self.mask, (255, 255, 255, 255), pts)
        lit = self.day.copy()
        lit.blit(self.mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(lit, (ox, oy))
        glow = pygame.Surface(self.mask.get_size(), pygame.SRCALPHA)
        for s, pts in polys:
            pygame.draw.polygon(glow, ALARM if s.state == "CHASE" else LAMP, pts)
        surface.blit(glow, (ox, oy))

    def _doors(self, surface, play, t):
        font = self.theme.display(13, bold=True)
        pulse = 0.5 + 0.5 * math.sin(t * 5)
        for d in play.level.doors:
            x, y = self.px(play.level, d.tile)
            rect = pygame.Rect(x, y, TILE, TILE)
            won = play.state == "won" and d is play.carrot
            opened = d.index in play.opened
            outline = None
            if play.hint_known and d is play.carrot and not won:
                outline = (255, int(170 + 60 * pulse), 60)
            sprites.door(surface, rect.inflate(-4, 0), d.name, font, won or opened, "carrot" if won else "empty",
                         outline)
            if play.hint_known and d is play.carrot and not won:
                pygame.draw.rect(surface, outline, rect.inflate(10 + 6 * pulse, 10 + 6 * pulse), 2, border_radius=6)
        door = play.door_in_reach()
        if door is not None and play.state == "playing" and door.index not in play.opened:
            fx, fy = self.px(play.level, door.front)
            self._key_cap(surface, "SPACE", (fx, fy + 30))

    def _key_cap(self, surface, label, center):
        font = self.theme.type(13, bold=True)
        img = font.render(label, True, T.INK)
        box = img.get_rect(center=center).inflate(14, 8)
        pygame.draw.rect(surface, T.PAPER, box, border_radius=4)
        pygame.draw.rect(surface, T.INK, box, 2, border_radius=4)
        surface.blit(img, img.get_rect(center=box.center))

    def _owner_circle(self, surface, play, t):
        o = play.owner
        cx, cy = self.px(play.level, o.pos)
        radius = int(HINT_RADIUS * TILE)
        ring = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        c = radius + 4
        colour = (255, 214, 120)
        pygame.draw.circle(ring, (*colour, 26 if o.state != "WALKING" else 10), (c, c), radius)
        for i in range(36):
            if i % 2 == 0:
                a0, a1 = i / 36 * 2 * math.pi + t * 0.3, (i + 1) / 36 * 2 * math.pi + t * 0.3
                pygame.draw.arc(ring, (*colour, 200 if o.state != "WALKING" else 70),
                                (4, 4, radius * 2, radius * 2), a0, a1, 2)
        surface.blit(ring, (cx - c, cy - c))
        if 0 < o.progress < 1 and not play.hint_known:
            pygame.draw.arc(surface, T.GREEN, (cx - 26, cy - 92, 52, 52), math.pi / 2,
                            math.pi / 2 + o.progress * 2 * math.pi, 6)
        if play.hint_known and o.nodding:
            fx, fy = self.px(play.level, play.carrot.front)
            dashed_line(surface, (255, 214, 120), (cx, cy - 40), (fx, fy), 6, 6, 2)

    def _noises(self, surface, play):
        for noise, age in play.noises:
            frac = age / 0.8
            r = int(noise.radius * TILE * min(1.0, frac * 1.6))
            if r < 4:
                continue
            alpha = int(200 * (1 - frac))
            ring = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring, (240, 230, 210, alpha), (r + 2, r + 2), r, 2)
            x, y = self.px(play.level, noise.pos)
            surface.blit(ring, (x - r - 2, y - r - 2))

    def _figures(self, surface, play, t):
        level = play.level
        figures = []
        o = play.owner
        lean = 0.0
        if o.nodding:
            direction = 1 if play.carrot.front[0] > o.pos[0] else -1
            lean = direction * (0.5 + 0.5 * math.sin(t * 9))
        figures.append((o.pos[1], lambda: sprites.von_osten(surface, self.px(level, (o.pos[0], o.pos[1] + 0.35)), lean)))
        for i, s in enumerate(play.scientists):
            figures.append((s.pos[1], lambda s=s, i=i: sprites.scientist(
                surface, self.px(level, (s.pos[0], s.pos[1] + 0.35)), s.angle, s.walk_phase, s.moving, i,
                s.state == "CHASE")))
        h = play.hans
        tap_up = play.state == "won"
        figures.append((h.pos[1], lambda: sprites.hans(surface, self.px(level, (h.pos[0], h.pos[1] + 0.4)), h.facing,
                                                       h.walk_phase, h.moving, "up", tap_up)))
        for _, draw in sorted(figures, key=lambda f: f[0]):
            draw()
        font = self.theme.display(20, bold=True)
        for s in play.scientists:
            icon = s.icon
            if icon:
                x, y = self.px(level, s.pos)
                fill = T.RED if icon == "!" else (236, 190, 70)
                progress = s.suspicion if s.state == "SUSPICIOUS" else None
                sprites.bubble(surface, (x, y - 72), icon, font, fill, progress)

    # --- X-Ray ---------------------------------------------------------------------------
    def _xray(self, surface, play):
        level, th = play.level, self.theme
        small = th.type(12, bold=True)
        for s in play.scientists:
            pts = [self.px(level, p) for p in s.route]
            if len(pts) > 1:
                for a, b in zip(pts, pts[1:] + pts[:1]):
                    dashed_line(surface, T.BLUE, a, b, 3, 7, 2)
            if s.path:
                for c, r in s.explored:
                    pygame.draw.circle(surface, (120, 150, 200), self.px(level, (c + 0.5, r + 0.5)), 2)
                path = [self.px(level, s.pos)] + [self.px(level, p) for p in s.path]
                for a, b in zip(path, path[1:]):
                    dashed_line(surface, T.RED, a, b, 7, 5, 3)
            if s.last_seen is not None and s.state in ("SUSPICIOUS", "INVESTIGATE", "CHASE"):
                x, y = self.px(level, s.last_seen)
                pygame.draw.line(surface, T.RED, (x - 7, y - 7), (x + 7, y + 7), 3)
                pygame.draw.line(surface, T.RED, (x - 7, y + 7), (x + 7, y - 7), 3)
            x, y = self.px(level, s.pos)
            self._label(surface, f"{s.state} {s.suspicion:.0%}", (x, y + 26), small)
        o = play.owner
        x, y = self.px(level, o.pos)
        self._label(surface, f"{o.state} {o.progress:.0%}", (x, y + 26), small)

    def _label(self, surface, text, center, font):
        img = font.render(text, True, T.PAPER)
        box = img.get_rect(center=center).inflate(8, 4)
        pygame.draw.rect(surface, T.INK, box, border_radius=3)
        surface.blit(img, img.get_rect(center=box.center))

    # --- HUD, tips, toasts ---------------------------------------------------------------
    def _hud(self, surface, play, xray):
        th = self.theme
        pygame.draw.rect(surface, T.PAPER, (0, 0, WIDTH, HUD_H))
        pygame.draw.line(surface, T.INK, (0, HUD_H - 2), (WIDTH, HUD_H - 2), 2)
        logo = th.spaced(surface, "HANS", th.display(26, bold=True), T.INK, (16, 11), 5)
        th.text(surface, f"Night {play.number}: {play.spec.name}", th.serif(17, italic=True), T.INK_SOFT,
                (logo.right + 14, 17))
        x = 470
        steps = [(play.hint_known, "Catch von Osten's nod" if not play.hint_known
                  else f"Von Osten nodded: door {play.carrot.name}"),
                 (play.state == "won", "Lose him first! (hide in the dark)" if play.chased_now
                  else f"Tap door {play.carrot.name} with SPACE" if play.hint_known else "Tap the carrot door")]
        for i, (done, text) in enumerate(steps):
            box = pygame.Rect(x, 16, 22, 22)
            pygame.draw.rect(surface, T.GREEN if done else T.PAPER, box, border_radius=4)
            pygame.draw.rect(surface, T.INK, box, 2, border_radius=4)
            if done:
                pygame.draw.lines(surface, T.PAPER, False, [(x + 5, 27), (x + 10, 32), (x + 17, 21)], 3)
            else:
                th.text(surface, str(i + 1), th.type(13, bold=True), T.INK, box.center, "center")
            r = th.text(surface, text, th.serif(17, bold=not done), T.INK if not done else T.INK_SOFT, (x + 30, 17))
            x = r.right + 26
        tags = [f"{int(play.time) // 60}:{int(play.time) % 60:02d}", f"seen {play.seen_count}"]
        th.text(surface, "    ".join(tags), th.type(14, bold=True), T.INK, (WIDTH - 16, 13), "topright")
        th.text(surface, "SHIFT trot   SPACE tap   Esc menu" + ("   X-RAY" if xray else ""), th.type(11),
                T.RED if xray else T.INK_SOFT, (WIDTH - 16, 33), "topright")

    def _target_pos(self, play, target):
        level = play.level
        if target == "hans":
            return self.px(level, play.hans.pos), 70
        if target == "owner":
            return self.px(level, play.owner.pos), 78
        if target == "door":
            return self.px(level, (play.carrot.tile[0] + 0.5, play.carrot.tile[1] + 0.5)), -10
        if target == "scientist" and play.scientists:
            s = min(play.scientists, key=lambda s: distance(s.pos, play.hans.pos))
            return self.px(level, s.pos), 78
        return None, 0

    def _banner(self, surface, text) -> int:
        th = self.theme
        img = th.serif(21, bold=True).render(text, True, T.PAPER)
        box = img.get_rect(midbottom=(WIDTH // 2, PLAY_Y + PLAY_H - 12)).inflate(30, 16)
        pygame.draw.rect(surface, T.GREEN, box, border_radius=6)
        pygame.draw.rect(surface, T.INK, box, 2, border_radius=6)
        surface.blit(img, img.get_rect(center=box.center))
        return box.top

    def _tip(self, surface, play, t) -> int:
        """The tutorial banner and its bouncing arrow. Returns the banner's top edge."""
        text = play.tip_text()
        if not text or play.state != "playing":
            return PLAY_Y + PLAY_H - 12
        th = self.theme
        font = th.serif(22, bold=True)
        lines = th.wrap(text, font, 860)
        height = 22 + 30 * len(lines)
        box = pygame.Rect(0, 0, 920, height)
        box.midbottom = (WIDTH // 2, PLAY_Y + PLAY_H - 12)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((*T.PAPER, 235))
        surface.blit(panel, box.topleft)
        pygame.draw.rect(surface, T.RED, box, 3, border_radius=6)
        for i, line in enumerate(lines):
            th.text(surface, line, font, T.INK, (box.centerx, box.y + 12 + 30 * i), "midtop")
        pos, lift = self._target_pos(play, play.tip.target)
        if pos is not None:
            bob = int(6 * math.sin(t * 6))
            x, y = pos[0], pos[1] - lift + bob
            if play.tip.target == "door":
                y = pos[1] + 44 + bob
                pygame.draw.polygon(surface, T.RED, [(x - 14, y + 18), (x + 14, y + 18), (x, y)])
            else:
                pygame.draw.polygon(surface, T.RED, [(x - 14, y - 18), (x + 14, y - 18), (x, y)])
        return box.top

    def _toast(self, surface, play, above: int):
        if play.toast_time <= 0:
            return
        th = self.theme
        img = th.serif(26, bold=True).render(play.toast, True, T.PAPER)
        box = img.get_rect(midbottom=(WIDTH // 2, above - 12)).inflate(28, 14)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((20, 14, 8, int(210 * min(1.0, play.toast_time))))
        surface.blit(panel, box.topleft)
        img.set_alpha(int(255 * min(1.0, play.toast_time)))
        surface.blit(img, img.get_rect(center=box.center))
