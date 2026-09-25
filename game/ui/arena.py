"""Draws the courtyard, its people and Hans, plus the X-Ray markup on top."""

import math

import pygame

from game.config import TILE, ARENA_X, ARENA_Y, ARENA_W, ARENA_H, ROMAN, SCENT_RANGE
from game.ui import sprites, theme as T
from game.ui.theme import dashed_line
from game.world import Tile, SCREEN_TILES, CROWD_SLOTS, World


def px(p) -> tuple[int, int]:
    return int(ARENA_X + p[0] * TILE), int(ARENA_Y + p[1] * TILE)


def tile_rect(c, r) -> pygame.Rect:
    return pygame.Rect(ARENA_X + c * TILE, ARENA_Y + r * TILE, TILE, TILE)


class ArenaView:
    def __init__(self, theme: T.Theme, world: World):
        self.theme = theme
        self.rect = pygame.Rect(ARENA_X, ARENA_Y, ARENA_W, ARENA_H)
        self.static = self._render_static(world)
        self.overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)

    def _render_static(self, world: World) -> pygame.Surface:
        s = pygame.Surface((ARENA_W + ARENA_X, ARENA_H + ARENA_Y))
        if pygame.display.get_surface() is not None:
            s = s.convert()
        for r in range(world.rows):
            for c in range(world.cols):
                rect = tile_rect(c, r)
                t = world.base[r][c]
                if t == Tile.WALL:
                    sprites.wall(s, rect, c * 31 + r)
                else:
                    sprites.floor(s, rect, c * 17 + r * 7)
        for r in range(world.rows):
            for c in range(world.cols):
                t, rect = world.base[r][c], tile_rect(c, r)
                if t == Tile.HAY:
                    sprites.hay(s, rect)
                elif t == Tile.TROUGH:
                    sprites.trough(s, rect)
                elif t == Tile.FENCE:
                    sprites.fence(s, rect)
        cart_tiles = [(c, r) for r in range(world.rows) for c in range(world.cols) if world.base[r][c] == Tile.CART]
        if cart_tiles:
            first, last = tile_rect(*cart_tiles[0]), tile_rect(*cart_tiles[-1])
            sprites.cart(s, first.union(last))
        return s

    def door_rect(self, door) -> pygame.Rect:
        return pygame.Rect(ARENA_X + door.left * TILE, ARENA_Y, TILE * 2, TILE)

    # --- main draw -------------------------------------------------------------------
    def draw(self, surface, world: World, hans, trial, xray: bool, blinkers: bool = False):
        surface.blit(self.static, self.rect.topleft, self.rect)
        numeral_font = self.theme.display(13, bold=True)
        outcome = hans.outcome if hans is not None else None
        for d in world.doors:
            is_open, contents, outline = False, None, None
            if outcome is not None:
                if d.index == outcome.carrot:
                    is_open, contents = True, "carrot"
                elif d.index == outcome.choice:
                    is_open, contents = True, "empty"
                if d.index == outcome.choice:
                    outline = T.GREEN if outcome.success else T.RED
            sprites.door(surface, self.door_rect(d), d.name, numeral_font, is_open, contents, outline)

        if world.screen_up:
            top, bottom = tile_rect(*SCREEN_TILES[0]), tile_rect(*SCREEN_TILES[-1])
            sprites.screen(surface, top.union(bottom))

        figures = []   # sort by feet y so nearer figures overlap farther ones
        if world.owner_present:
            lean = 0.0
            if trial is not None and trial.owner_door is not None:
                lean = max(-1.0, min(1.0, (world.doors[trial.owner_door].center_x - world.owner_pos[0]) / 4))
            figures.append((world.owner_pos[1], lambda l=lean: sprites.von_osten(surface, px(world.owner_pos), l)))
        if world.crowd_present:
            lean = -0.5
            if trial is not None and trial.crowd_door is not None:
                lean = max(-1.0, (world.doors[trial.crowd_door].center_x - 19.5) / 8)
            for i, slot in enumerate(CROWD_SLOTS):
                figures.append((slot[1], lambda i=i, slot=slot, l=lean: sprites.spectator(surface, px(slot), i, l)))
        if hans is not None:
            figures.append((hans.pos[1], lambda: self._draw_hans(surface, hans, blinkers)))
        for _, draw in sorted(figures, key=lambda f: f[0]):
            draw()

        if xray and hans is not None:
            self._draw_xray(surface, world, hans, trial)
        self.theme.film_overlay(surface, self.rect)

    def _draw_hans(self, surface, hans, blinkers):
        state = hans.state
        moving = hans.moving
        target = hans.target
        head = "down" if (state == "INVESTIGATING" and target is not None and target.cue == "scent"
                          and not hans.waypoints) else "up"
        facing = hans.facing
        if state == "OBSERVING":   # a visible tell: Hans turns toward what he is reading most
            focus = self._strongest_source(hans)
            if focus is not None:
                facing = 1 if focus[0] > hans.pos[0] else -1
        tap_up = hans.tapping and hans.tap_timer < 0.18
        sprites.hans(surface, px((hans.pos[0], hans.pos[1] + 0.35)), facing, hans.walk_phase, moving, head, tap_up,
                     blinkers)

    @staticmethod
    def _strongest_source(hans):
        best, best_e = None, 0.05
        for sid, r in hans.mind.readings.items():
            e = abs(r.evidence) * hans.beliefs.weight(r.cue) * (1 if r.polarity > 0 else 0.5)
            if e > best_e:
                src = hans.world.source(sid)
                if src is not None:
                    best, best_e = src.pos, e
        return best

    # --- X-Ray: Pfungst's red-pencil and blue-ink markup -----------------------------
    def _draw_xray(self, surface, world, hans, trial):
        ov = self.overlay
        ov.fill((0, 0, 0, 0))
        off = (-ARENA_X, -ARENA_Y)

        def o(p):
            x, y = px(p)
            return x + off[0], y + off[1]

        if hans.search is not None and hans.waypoints:
            for (c, r) in hans.search.explored:
                pygame.draw.circle(ov, (*T.BLUE, 70), o((c + 0.5, r + 0.5)), 2)
            pts = [o(hans.pos)] + [o(w) for w in hans.waypoints]
            for a, b in zip(pts, pts[1:]):
                dashed_line(ov, (*T.RED, 220), a, b, 7, 5, 2)
            pygame.draw.circle(ov, (*T.RED, 220), pts[-1], 6, 2)

        hx, hy = hans.pos
        pygame.draw.circle(ov, (*T.BLUE, 110), o(hans.pos), int(SCENT_RANGE * TILE), 1)

        if world.owner_present:
            eye = (hx + 0.4 * hans.facing, hy - 0.9)
            head = (world.owner_pos[0], world.owner_pos[1] - 1.2)
            if world.line_of_sight(hans.pos, world.owner_pos) and not (trial and trial.blinkers):
                pygame.draw.line(ov, (*T.BLUE, 170), o(eye), o(head), 2)
            else:
                dashed_line(ov, (*T.RED, 170), o(eye), o(head), 4, 6, 2)
                mx, my = o(((eye[0] + head[0]) / 2, (eye[1] + head[1]) / 2))
                pygame.draw.line(ov, (*T.RED, 230), (mx - 6, my - 6), (mx + 6, my + 6), 3)
                pygame.draw.line(ov, (*T.RED, 230), (mx - 6, my + 6), (mx + 6, my - 6), 3)

        if trial is not None:   # ground truth the scientist knows but Hans does not
            if trial.owner_door is not None and world.owner_present:
                d = world.doors[trial.owner_door]
                dashed_line(ov, (*T.INK_SOFT, 120), o((world.owner_pos[0], world.owner_pos[1] - 1.2)),
                            o((d.center_x, 1.0)), 3, 6, 1)
            if trial.crowd_door is not None and world.crowd_present:
                d = world.doors[trial.crowd_door]
                dashed_line(ov, (*T.INK_SOFT, 120), o((19.2, 6.0)), o((d.center_x + 0.4, 1.0)), 3, 6, 1)

        surface.blit(ov, self.rect.topleft)

        small = self.theme.type(12)
        if trial is not None and hans.outcome is None:
            sprites.carrot(surface, px((world.doors[trial.carrot].center_x + 0.75, 0.55)), 0.7)
            if trial.decoy_door is not None:
                d = world.doors[trial.decoy_door]
                for i in range(3):
                    x, y = px((d.center_x - 0.3 + i * 0.3, 1.1))
                    pygame.draw.arc(surface, T.RED, (x - 3, y - 8, 6, 10), 1.5, 4.7, 1)

        belief = hans.mind.belief()
        for d in hans.world.doors:
            p = belief[d.index]
            x, y = px((d.center_x, 2.05))
            back = pygame.Rect(x - 30, y, 60, 7)
            pygame.draw.rect(surface, T.PAPER_DARK, back)
            pygame.draw.rect(surface, T.GREEN, (back.x, back.y, int(back.width * p), back.height))
            pygame.draw.rect(surface, T.INK_SOFT, back, 1)
            self.theme.text(surface, f"{p:.0%}", small, T.INK, (x, y + 9), "midtop")

        for sid, r in hans.mind.readings.items():
            src = world.source(sid)
            if src is None:
                continue
            label = f"{ROMAN[r.door]}{'+' if r.polarity > 0 else '-'} {r.clarity:.2f}"
            anchor = px((src.pos[0], src.pos[1] - (1.9 if src.cue != "scent" else -0.6)))
            tag = small.render(label, True, T.RED if r.misread else T.BLUE)
            box = tag.get_rect(center=anchor).inflate(6, 2)
            pygame.draw.rect(surface, T.PAPER, box)
            pygame.draw.rect(surface, T.BLUE, box, 1)
            surface.blit(tag, tag.get_rect(center=anchor))

        label = small.render(hans.state, True, T.PAPER)
        box = label.get_rect(midbottom=px((hx, hy - 1.35))).inflate(8, 4)
        if box.top < self.rect.top + 2:      # near the doors: put the label under Hans instead
            box.top = px((hx, hy + 0.5))[1]
        pygame.draw.rect(surface, T.INK, box, border_radius=3)
        surface.blit(label, label.get_rect(center=box.center))
        if hans.state in ("OBSERVING", "INVESTIGATING"):
            frac = max(0.0, hans.patience / hans.temperament.patience)
            ring = pygame.Rect(0, 0, 16, 16)
            ring.midleft = (box.right + 4, box.centery)
            pygame.draw.arc(surface, T.RED, ring, math.pi / 2, math.pi / 2 + frac * 2 * math.pi, 3)
