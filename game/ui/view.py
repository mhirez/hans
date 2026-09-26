"""Draws a Match: the courtyard, Hans, the enemies and their warning signs, items, the HUD,
the wave banner, and (press X) the AI X-Ray."""

import math

import pygame

from game.config import (WIDTH, HEIGHT, TILE, HUD_H, HEARTS, STAMINA, KICK_RADIUS, NET_REACH, VIEW_RANGE,
                         VIEW_HALF_ANGLE, DOG_POUNCE_DISTANCE, LASSO_RANGE)
from game.ai.dog import POUNCE
from game.ai.perception import cone
from game.ai.scientist import SWING
from game.ai.stableboy import THROW
from game.level import angle_to
from game.ui import sprites, theme as T
from game.ui.theme import dashed_line

KIND_NAMES = {"scientist": "scientist", "stableboy": "stable boy", "dog": "dog"}
TACTIC_NAMES = {"wary": "jump back from kicks", "intercept": "cut you off", "sweep": "check behind hay",
                "guard": "guard the carrots"}


class MatchView:
    def __init__(self, theme: T.Theme):
        self.theme = theme
        self._level_id = None
        self.ground = None

    def origin(self, level) -> tuple[int, int]:
        return (WIDTH - level.cols * TILE) // 2, HUD_H + (HEIGHT - HUD_H - level.rows * TILE) // 2

    def px(self, level, p) -> tuple[int, int]:
        ox, oy = self.origin(level)
        return int(ox + p[0] * TILE), int(oy + p[1] * TILE)

    def _prepare(self, level):
        if self._level_id == id(level):
            return
        self._level_id = id(level)
        w, h = level.cols * TILE, level.rows * TILE
        g = pygame.Surface((w, h))
        for r in range(level.rows):
            for c in range(level.cols):
                rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                if level.at(c, r) in "#D":
                    sprites.wall(g, rect, c * 31 + r)
                else:
                    sprites.floor(g, rect, c * 17 + r * 7)
        font = self.theme.display(12, bold=True)
        for r in range(level.rows):
            for c in range(level.cols):
                rect = pygame.Rect(c * TILE, r * TILE, TILE, TILE)
                ch = level.at(c, r)
                if ch == "h":
                    sprites.hay(g, rect)
                elif ch == "t":
                    sprites.trough(g, rect)
                elif ch == "D":
                    sprites.door(g, rect.inflate(-4, -4), "", font)
                elif ch == "c" and level.at(c - 1, r) != "c":
                    run = 1
                    while level.at(c + run, r) == "c":
                        run += 1
                    sprites.cart(g, pygame.Rect(rect.x, rect.y, TILE * run, TILE))
        self.ground = g.convert() if pygame.display.get_surface() else g

    # --- main --------------------------------------------------------------------------
    def draw(self, surface, match, xray: bool, t: float, banner=None):
        level = match.level
        self._prepare(level)
        surface.fill(T.FILM)
        surface.blit(self.ground, self.origin(level))
        self._prints(surface, match)
        if xray:
            self._cones(surface, match)
        self._items(surface, match, t)
        self._warnings(surface, match)
        self._figures(surface, match, t)
        self._lassos(surface, match)
        self._effects(surface, match)
        self._speech(surface, match)
        if xray:
            self._xray(surface, match)
            self._commission_panel(surface, match)
        self._hud(surface, match, xray)
        self._learned(surface, match)
        if banner:
            self._banner(surface, *banner)
        self._toast(surface, match)
        self.theme.film_overlay(surface)

    # --- things on the ground ----------------------------------------------------------
    def _prints(self, surface, match):
        """Hans's hoofprints: fading, and what the dogs follow."""
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for p in match.prints:
            x, y = self.px(match.level, p.pos)
            alpha = int(110 * (1 - p.age / 14.0))
            if alpha <= 0:
                continue
            pygame.draw.arc(layer, (90, 66, 40, alpha), (x - 5, y + 6, 10, 9), 0, math.pi, 2)
        surface.blit(layer, (0, 0))

    def _items(self, surface, match, t):
        for item in match.items:
            x, y = self.px(match.level, item.pos)
            bob = int(3 * math.sin(t * 4 + item.uid))
            if item.kind == "carrot":
                pygame.draw.ellipse(surface, (150, 128, 96), (x - 12, y + 12, 24, 7))
                sprites.carrot(surface, (x, y + bob), 1.7)
            elif item.kind == "sugar":
                sprites.sugar(surface, (x, y + bob), t)
            elif item.kind == "horseshoe":
                sprites.horseshoe(surface, (x, y + bob), t)
            elif item.kind == "coffee":
                sprites.coffee(surface, (x, y), t)

    def _warnings(self, surface, match):
        """The tells: what's about to happen, so the player can react."""
        level = match.level
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for e in match.enemies:
            x, y = self.px(level, e.pos)
            if e.fsm.current is SWING and not e.swung:
                k = SWING.progress(e)
                r = NET_REACH * TILE
                arc = [e.angle + math.radians(-80 + 160 * i / 12) for i in range(13)]
                pts = [(x, y)] + [(x + math.cos(a) * r, y + math.sin(a) * r) for a in arc]
                pygame.draw.polygon(overlay, (190, 40, 30, int(40 + 110 * k)), pts)
            elif e.fsm.current is POUNCE and e.leap is None:
                a = angle_to(e.pos, match.hans.pos)
                end = self.px(level, (e.pos[0] + math.cos(a) * DOG_POUNCE_DISTANCE,
                                      e.pos[1] + math.sin(a) * DOG_POUNCE_DISTANCE))
                dashed_line(overlay, (190, 40, 30, 200), (x, y), end, 8, 5, 4)
            elif e.fsm.current is THROW:
                a = angle_to(e.pos, match.hans.pos)
                end = self.px(level, (e.pos[0] + math.cos(a) * LASSO_RANGE, e.pos[1] + math.sin(a) * LASSO_RANGE))
                dashed_line(overlay, (190, 40, 30, int(60 + 120 * THROW.progress(e))), (x, y - 20), end, 6, 8, 2)
        surface.blit(overlay, (0, 0))

    def _figures(self, surface, match, t):
        level = match.level
        figures = []
        for i, e in enumerate(match.enemies):
            figures.append((e.pos[1], lambda e=e, i=i: self._enemy(surface, level, e, t)))
        h = match.hans
        figures.append((h.pos[1], lambda: self._hans(surface, level, h, t)))
        for _, draw in sorted(figures, key=lambda f: f[0]):
            draw()
        font = self.theme.display(20, bold=True)
        for e in match.enemies:
            x, y = self.px(level, e.pos)
            icon = e.icon
            top = y - 66
            if icon == "stars":
                sprites.stars(surface, (x, top + 20), t)
            elif icon == "nose":
                pygame.draw.circle(surface, T.PAPER, (x, top + 14), 11)
                pygame.draw.circle(surface, T.INK, (x, top + 14), 11, 2)
                pygame.draw.ellipse(surface, T.INK, (x - 4, top + 11, 8, 6))
                for k in (-1, 1):
                    pygame.draw.arc(surface, T.INK_SOFT, (x + k * 7 - 3, top + 6, 6, 8), 1.2, 5.0, 1)
            elif icon == "cup":
                pygame.draw.circle(surface, T.PAPER, (x, top), 13)
                pygame.draw.circle(surface, T.INK, (x, top), 13, 2)
                sprites.coffee(surface, (x - 1, top + 2), t)
            elif icon:
                fill = {"!": T.RED, "?": (236, 190, 70), "!!": T.PAPER}[icon]
                sprites.bubble(surface, (x, top), icon, font, fill)

    def _enemy(self, surface, level, e, t):
        x, y = self.px(level, (e.pos[0], e.pos[1] + 0.4))
        if e.state == "KO":
            fig = pygame.Surface((80, 80), pygame.SRCALPHA)
            self._draw_kind(fig, e, (40, 70), t)
            fig = pygame.transform.rotate(fig, 90 if math.cos(e.angle) < 0 else -90)
            fig.set_alpha(max(0, 255 - int(e.timer * 150)))
            surface.blit(fig, fig.get_rect(center=(x, y - 10)))
            return
        self._draw_kind(surface, e, (x, y), t)

    @staticmethod
    def _draw_kind(surface, e, feet, t):
        if e.kind == "scientist":
            sprites.scientist(surface, feet, e.angle, e.walk_phase, e.moving, e.uid, SWING.progress(e)
                              if e.fsm.current is SWING else 0.0)
        elif e.kind == "stableboy":
            sprites.stableboy(surface, feet, e.angle, e.walk_phase, e.moving,
                              THROW.progress(e) if e.fsm.current is THROW else 0.0, t)
        else:
            sprites.dog(surface, feet, e.angle, e.walk_phase, e.moving,
                        POUNCE.progress(e) if e.fsm.current is POUNCE else 0.0)

    def _hans(self, surface, level, h, t):
        x, y = self.px(level, (h.pos[0], h.pos[1] + 0.45))
        if h.powered:
            halo = pygame.Surface((110, 110), pygame.SRCALPHA)
            pygame.draw.circle(halo, (255, 214, 90, 90 + int(40 * math.sin(t * 10))), (55, 55), 42)
            surface.blit(halo, (x - 55, y - 75))
        if h.invulnerable > 0 and int(t * 16) % 2 == 0:
            return                                               # blink after being hit
        sprites.hans(surface, (x, y), h.facing, h.walk_phase, h.moving, "up", h.kick_flash > 0)
        if h.tangled:
            for k in range(3):
                pygame.draw.ellipse(surface, T.HAY_DARK, (x - 22 + k * 4, y - 34 + k * 7, 44 - k * 8, 10), 2)

    def _lassos(self, surface, match):
        for lasso in match.lassos:
            x, y = self.px(match.level, lasso.pos)
            bx, by = self.px(match.level, lasso.thrower.pos)
            pygame.draw.line(surface, T.HAY_DARK, (bx, by - 22), (x, y), 2)
            pygame.draw.circle(surface, T.HAY_DARK, (x, y), 11, 3)

    def _effects(self, surface, match):
        h = match.hans
        if h.kick_flash > 0:
            x, y = self.px(match.level, h.pos)
            r = int(KICK_RADIUS * TILE * (1.2 - h.kick_flash * 2))
            pygame.draw.circle(surface, T.PAPER, (x, y), max(4, r), 3)
        font = self.theme.display(20, bold=True)
        for p in match.popups:
            x, y = self.px(match.level, p.pos)
            img = font.render(p.text, True, (250, 230, 150))
            img.set_alpha(int(255 * (1 - p.age)))
            surface.blit(img, img.get_rect(center=(x, y - 30 - p.age * 40)))

    def _speech(self, surface, match):
        """Speech bubbles: every line is a real decision being made, said out loud."""
        font = self.theme.serif(16, italic=True, bold=True)
        hx, hy = self.px(match.level, match.hans.pos)
        hans_box = pygame.Rect(hx - 34, hy - 50, 68, 66)          # never hide the player's horse
        for b in match.barks.bubbles:
            e = b.enemy
            if e not in match.enemies:
                continue
            x, y = self.px(match.level, e.pos)
            img = font.render(b.text, True, T.INK)
            box = img.get_rect(midbottom=(x + 18, y - 82)).inflate(16, 8)
            below = box.colliderect(hans_box)
            if below:
                box = img.get_rect(midtop=(x + 18, y + 26)).inflate(16, 8)
            box.clamp_ip(pygame.Rect(4, HUD_H + 4, WIDTH - 8, HEIGHT - HUD_H - 8))
            fade = 1.0 if b.age < 1.5 else max(0.0, 1 - (b.age - 1.5) / 0.4)
            panel = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (*T.PAPER, int(240 * fade)), panel.get_rect(), border_radius=8)
            pygame.draw.rect(panel, (*T.INK, int(255 * fade)), panel.get_rect(), 2, border_radius=8)
            surface.blit(panel, box.topleft)
            if fade > 0.3:
                edge = box.top + 1 if below else box.bottom - 1
                pygame.draw.polygon(surface, T.INK, [(box.x + 12, edge), (box.x + 22, edge),
                                                     (x + 4, y + 12 if below else y - 64)])
            img.set_alpha(int(255 * fade))
            surface.blit(img, img.get_rect(center=box.center))

    def _learned(self, surface, match):
        """Always on screen: what the Commission has learned about the way you play."""
        tactics = match.commission.tactics
        if not tactics:
            return
        th = self.theme
        text = "The Commission has learned to: " + ",  ".join(TACTIC_NAMES[t] for t in tactics)
        img = th.serif(15, italic=True, bold=True).render(text, True, T.PAPER)
        box = img.get_rect(topleft=(12, HUD_H + 8)).inflate(16, 8)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((120, 30, 20, 200))
        surface.blit(panel, box.topleft)
        surface.blit(img, img.get_rect(center=box.center))

    def _commission_panel(self, surface, match):
        """X-Ray: the Commission's running tally of your habits against its thresholds."""
        from game.ai.commission import HABITS
        th = self.theme
        habits = match.commission.habits
        box = pygame.Rect(WIDTH - 300, HUD_H + 8, 288, 116)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((24, 18, 12, 210))
        surface.blit(panel, box.topleft)
        th.text(surface, "THE COMMISSION IS WATCHING YOU", th.type(11, bold=True), T.FILM_TEXT, (box.x + 10, box.y + 8))
        y = box.y + 28
        labels = {"kicks": "kicks / min", "gallop": "time galloping", "hides": "hiding by hay",
                  "greedy": "risky carrots"}
        for habit, (tactic, threshold, _) in HABITS.items():
            frac = min(1.0, habits.score(habit) / threshold)
            th.text(surface, labels[habit], th.type(11), T.FILM_TEXT, (box.x + 10, y))
            bar = pygame.Rect(box.x + 130, y + 2, 100, 9)
            th.bar(surface, bar, frac, T.RED if frac >= 1 else (226, 176, 50), back=(60, 48, 36))
            done = "learned" if match.commission.has(tactic) else ""
            th.text(surface, done, th.type(10, bold=True), T.RED, (box.right - 8, y), "topright")
            y += 21

    # --- X-Ray ---------------------------------------------------------------------------
    def _cones(self, surface, match):
        level = match.level
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for e in match.enemies:
            if e.state == "KO":
                continue
            pts = [self.px(level, p) for p in cone(level, e.pos, e.angle, VIEW_RANGE, VIEW_HALF_ANGLE, 18)]
            pygame.draw.polygon(overlay, (255, 190, 90, 38) if not e.aware else (255, 90, 60, 45), pts)
        surface.blit(overlay, (0, 0))

    def _xray(self, surface, match):
        level, th = match.level, self.theme
        small = th.type(11, bold=True)
        for e in match.enemies:
            if e.state == "KO":
                continue
            x, y = self.px(level, e.pos)
            if e.path:
                pts = [(x, y)] + [self.px(level, p) for p in e.path]
                for a, b in zip(pts, pts[1:]):
                    dashed_line(surface, T.RED, a, b, 6, 5, 2)
            if e.last_seen is not None and e.aware and not e.sees_hans:
                lx, ly = self.px(level, e.last_seen)
                pygame.draw.line(surface, T.RED, (lx - 6, ly - 6), (lx + 6, ly + 6), 3)
                pygame.draw.line(surface, T.RED, (lx - 6, ly + 6), (lx + 6, ly - 6), 3)
            if e.kind == "dog" and e.state == "SURROUND":
                sx, sy = self.px(level, e.slot)
                pygame.draw.circle(surface, T.BLUE, (sx, sy), 7, 2)
                pygame.draw.line(surface, T.BLUE, (x, y), (sx, sy), 1)
            if e.kind == "stableboy" and e.spot_target is not None and e.state == "POSITION":
                sx, sy = self.px(level, e.spot_target)
                pygame.draw.rect(surface, T.BLUE, (sx - 6, sy - 6, 12, 12), 2)
            lines = [f"{e.state}"]
            if e.scores:
                top = sorted(e.scores.items(), key=lambda kv: -kv[1])[:3]
                lines.append(" ".join(f"{k[:4]} {v:.1f}" for k, v in top))
            for i, line in enumerate(lines):
                img = small.render(line, True, T.PAPER)
                box = img.get_rect(center=(x, y + 22 + i * 14)).inflate(6, 2)
                pygame.draw.rect(surface, T.INK, box, border_radius=3)
                surface.blit(img, img.get_rect(center=box.center))

    # --- HUD, banner, toast --------------------------------------------------------------
    def _hud(self, surface, match, xray):
        th = self.theme
        h = match.hans
        pygame.draw.rect(surface, T.PAPER, (0, 0, WIDTH, HUD_H))
        pygame.draw.line(surface, T.INK, (0, HUD_H - 2), (WIDTH, HUD_H - 2), 2)
        th.spaced(surface, "HANS", th.display(26, bold=True), T.INK, (16, 14), 5)
        for i in range(HEARTS):
            sprites.heart(surface, (158 + i * 30, 30), 22, i < h.hearts)
        th.text(surface, "GALLOP", th.type(11, bold=True), T.INK_SOFT, (262, 12))
        th.bar(surface, pygame.Rect(262, 28, 110, 12), h.stamina / STAMINA,
               (226, 176, 50) if h.powered else T.BLUE)
        wave = match.wave
        th.text(surface, f"WAVE {wave.number}", th.display(22, bold=True), T.INK, (WIDTH // 2 - 40, 16), "topright")
        sprites.carrot(surface, (WIDTH // 2 - 14, 30), 1.0)
        bar = pygame.Rect(WIDTH // 2 + 2, 22, 200, 16)
        th.bar(surface, bar, match.carrots / wave.carrots, (212, 112, 44))
        th.text(surface, f"{match.carrots} / {wave.carrots}", th.type(13, bold=True), T.INK, bar.center, "center")
        th.text(surface, f"SCORE {match.score}", th.display(22, bold=True), T.INK, (WIDTH - 16, 8), "topright")
        th.text(surface, "arrows run   SHIFT gallop   SPACE kick   P pause" + ("   X-RAY" if xray else ""),
                th.type(11), T.RED if xray else T.INK_SOFT, (WIDTH - 16, 36), "topright")

    def _banner(self, surface, title, line1, line2=""):
        th = self.theme
        band = pygame.Surface((WIDTH, 150), pygame.SRCALPHA)
        band.fill((24, 18, 12, 200))
        y = HUD_H + 190
        surface.blit(band, (0, y))
        th.spaced(surface, title, th.display(42, bold=True), T.FILM_TEXT, (WIDTH // 2, y + 18), 8, "midtop")
        th.text(surface, line1, th.serif(24, italic=True), T.FILM_TEXT, (WIDTH // 2, y + 86), "center")
        if line2:
            th.text(surface, line2, th.serif(20), T.FILM_TEXT, (WIDTH // 2, y + 118), "center")

    def _toast(self, surface, match):
        if match.toast_time <= 0:
            return
        th = self.theme
        img = th.serif(26, bold=True).render(match.toast, True, T.PAPER)
        box = img.get_rect(midbottom=(WIDTH // 2, HEIGHT - 26)).inflate(28, 14)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        panel.fill((20, 14, 8, int(210 * min(1.0, match.toast_time))))
        surface.blit(panel, box.topleft)
        img.set_alpha(int(255 * min(1.0, match.toast_time)))
        surface.blit(img, img.get_rect(center=box.center))
