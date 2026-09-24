"""The game's own screens, run by the same StateMachine class that runs Hans.

    TITLE -> INTRO (case intertitle) -> LAB (investigate, verdict, proof) -> RESULT -> INTRO ...
"""

import pygame

from game.config import (WIDTH, HEADER_H, ARENA_W, FOOTER_Y, HEIGHT, CUES, FAST_FORWARD)
from game.ai.state_machine import State
from game.ui import theme as T
from game.ui.panel import cycle

ENTER_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


class Scene(State):
    def draw(self, game, surface):
        pass


class Title(Scene):
    name = "TITLE"

    def on_event(self, game, event) -> bool:
        if event.type == pygame.KEYDOWN and event.key in ENTER_KEYS:
            game.start_case(game.case_number)
            game.scenes.change(INTRO)
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            game.running = False
            return True
        return False

    def draw(self, game, surface):
        game.cards.title(surface)


class Intro(Scene):
    name = "INTRO"

    def on_event(self, game, event) -> bool:
        if event.type == pygame.KEYDOWN and event.key in ENTER_KEYS:
            game.scenes.change(LAB)
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            game.scenes.change(TITLE)
            return True
        return False

    def draw(self, game, surface):
        case = game.inv.case
        game.cards.intertitle(surface, case.title, case.intro)


class Lab(Scene):
    name = "LAB"

    def update(self, game, dt):
        inv = game.inv
        if game.xray and inv.stage != "done":
            inv.xray_used = True
        inv.update(dt)
        if inv.stage == "investigate" and not inv.running and inv.trials_left == 0:
            inv.stage = "verdict"
        if inv.stage == "done" and not inv.running:
            game.scenes.change(RESULT)

    def on_event(self, game, event) -> bool:
        inv = game.inv
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._click(game, event)
        if event.type != pygame.KEYDOWN:
            return False
        key = event.key
        if inv.stage == "verdict":
            if pygame.K_1 <= key <= pygame.K_3:
                inv.give_verdict(CUES[key - pygame.K_1])
            elif key == pygame.K_ESCAPE:
                inv.cancel_verdict()
            return True
        if inv.stage == "proof_intro":
            if key in ENTER_KEYS:
                inv.begin_proof()
            return True
        if key in ENTER_KEYS:
            inv.run()
        elif key == pygame.K_v:
            inv.open_verdict()
        elif key == pygame.K_ESCAPE:
            game.scenes.change(TITLE)
        elif pygame.K_0 <= key <= pygame.K_9:
            self._cycle(game, game.panel.field_for_key(str(key - pygame.K_0)),
                        -1 if event.mod & pygame.KMOD_SHIFT else 1)
        else:
            return False
        return True

    def _click(self, game, event) -> bool:
        inv, panel = game.inv, game.panel
        if inv.stage == "verdict":
            for cue, rect in game.cards.verdict_rects.items():
                if rect.collidepoint(event.pos):
                    inv.give_verdict(cue)
            return True
        if inv.stage == "proof_intro":
            inv.begin_proof()
            return True
        if panel.run_rect.collidepoint(event.pos):
            inv.run()
        elif panel.verdict_rect.collidepoint(event.pos):
            inv.open_verdict()
        else:
            field = panel.field_at(event.pos)
            if field is None:
                return False
            self._cycle(game, field, -1 if event.button == 3 else 1)
        return True

    @staticmethod
    def _cycle(game, field, step):
        inv = game.inv
        if field is None or inv.running or inv.stage not in ("investigate", "proof") or not field.enabled(inv):
            return
        cycle(field, inv, step)
        inv.preview()

    def draw(self, game, surface):
        inv, th = game.inv, game.theme
        hans = inv.hans
        blinkers = inv.trial.blinkers if inv.trial is not None else inv.setup.blinkers
        game.arena.draw(surface, game.world, hans, inv.trial, game.xray, blinkers)
        self._header(game, surface)
        self._footer(game, surface)
        game.panel.draw(surface, inv, hans, game.xray, game.mouse)
        surface.blit(th.vignette, (0, 0))
        if inv.stage == "verdict":
            game.cards.verdict(surface, game.mouse, inv.trials_left)
        elif inv.stage == "proof_intro":
            game.cards.proof_intro(surface, inv.verdict)

    @staticmethod
    def _header(game, surface):
        th, inv = game.theme, game.inv
        pygame.draw.rect(surface, T.PAPER_DARK, (0, 0, ARENA_W, HEADER_H))
        pygame.draw.line(surface, T.INK, (0, HEADER_H - 2), (ARENA_W, HEADER_H - 2), 2)
        logo = th.spaced(surface, "HANS", th.display(30, bold=True), T.INK, (16, 9), 6)
        th.text(surface, inv.case.title, th.serif(19, italic=True), T.INK_SOFT, (logo.right + 18, 17))
        if inv.stage in ("proof", "proof_intro", "done"):
            right = "The Commission's test"
        else:
            right = f"Trials left {inv.trials_left} / {inv.case.budget}"
        r = th.text(surface, right, th.serif(18, bold=True), T.INK, (ARENA_W - 16, 17), "topright")
        tags = []
        if game.xray:
            tags.append(("X-RAY", T.RED))
        if game.fast:
            tags.append((f">> x{FAST_FORWARD}", T.BLUE))
        x = r.left - 14
        for label, colour in tags:
            img = th.type(12, bold=True).render(label, True, T.PAPER)
            box = img.get_rect(topright=(x, 19)).inflate(10, 6)
            pygame.draw.rect(surface, colour, box, border_radius=3)
            surface.blit(img, img.get_rect(center=box.center))
            x = box.left - 8

    @staticmethod
    def _footer(game, surface):
        th, inv = game.theme, game.inv
        pygame.draw.rect(surface, T.PAPER_DARK, (0, FOOTER_Y, ARENA_W, HEIGHT - FOOTER_Y))
        pygame.draw.line(surface, T.INK, (0, FOOTER_Y), (ARENA_W, FOOTER_Y), 2)
        caption = inv.hans.caption
        if not inv.running and not inv.entries and inv.stage == "investigate":
            caption = "Set up your first experiment on the right, then press Enter."
        elif not inv.running and inv.stage == "proof":
            caption = "Choose the conditions and your prediction, then run the test."
        th.text(surface, caption, th.serif(19, italic=True), T.INK, (16, FOOTER_Y + 14), max_width=ARENA_W - 260)
        th.text(surface, "X x-ray   F fast   V verdict   Esc menu", th.type(12), T.INK_SOFT,
                (ARENA_W - 14, FOOTER_Y + 20), "topright")


class Result(Scene):
    name = "RESULT"

    def on_event(self, game, event) -> bool:
        if event.type != pygame.KEYDOWN:
            return False
        if event.key in ENTER_KEYS:
            game.case_number += 1
            game.start_case(game.case_number)
            game.scenes.change(INTRO)
        elif event.key == pygame.K_ESCAPE:
            game.running = False
        return True

    def draw(self, game, surface):
        game.cards.result(surface, game.inv, game.inv.hans.beliefs)


TITLE, INTRO, LAB, RESULT = Title(), Intro(), Lab(), Result()
