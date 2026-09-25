"""The game's own screens, run by the same StateMachine class that runs Hans.

    TITLE -> LOADING -> INTRO (case intertitle) -> LAB (investigate, verdict, proof) -> RESULT -> LOADING ...
"""

import math

import pygame

from game.config import HEADER_H, ARENA_W, FOOTER_Y, HEIGHT, CUES, FAST_FORWARD
from game.ai.state_machine import State
from game.ui import theme as T
from game.ui.panel import cycle

ENTER_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
TUTORIAL = [
    "Stumpf: start with a plain trial. Watch where Hans goes first.",
    "Stumpf: now change one thing. What if von Osten doesn't know?",
    "Stumpf: compare trials in EVIDENCE (Tab), or ask me (H).",
]


def _key(event, *keys) -> bool:
    return event.type == pygame.KEYDOWN and event.key in keys


class Scene(State):
    def draw(self, game, surface):
        pass


class Title(Scene):
    name = "TITLE"

    def enter(self, game):
        game.audio.crowd(False)
        game.demo = False

    def on_event(self, game, event) -> bool:
        if _key(event, *ENTER_KEYS):
            game.load_case(game.casebook.next_case)
        elif _key(event, pygame.K_n) and game.casebook.next_case > 1:
            game.casebook.restart()
            game.load_case(1)
        elif _key(event, pygame.K_a):
            game.demo = True
            game.load_case(max(2, game.casebook.next_case), autopilot=True)
        elif _key(event, pygame.K_h):
            game.help_open = True
        elif _key(event, pygame.K_ESCAPE):
            game.running = False
        else:
            return False
        return True

    def draw(self, game, surface):
        game.cards.title(surface, game.casebook)


class Loading(Scene):
    """Shows a card for one frame, then generates the case (training Hans takes a moment)."""
    name = "LOADING"

    def enter(self, game):
        game.loading_drawn = False

    def update(self, game, dt):
        if game.loading_drawn:
            game.start_case(game.pending_case)
            game.scenes.change(INTRO)

    def draw(self, game, surface):
        game.cards.loading(surface, "Preparing the case...")
        game.loading_drawn = True


class Intro(Scene):
    name = "INTRO"

    def on_event(self, game, event) -> bool:
        if _key(event, *ENTER_KEYS) or event.type == pygame.MOUSEBUTTONDOWN:
            game.scenes.change(LAB)
            if game.pending_autopilot:
                game.inv.start_autopilot()
                game.panel.tab = "stumpf"
            return True
        if _key(event, pygame.K_ESCAPE):
            game.scenes.change(TITLE)
            return True
        return False

    def draw(self, game, surface):
        case = game.inv.case
        footer = "Press Enter to watch Professor Stumpf" if game.pending_autopilot else "Press Enter"
        game.cards.intertitle(surface, case.title, case.intro, footer)


class Lab(Scene):
    name = "LAB"

    def enter(self, game):
        game.step_phase = 0
        game.seen_entries = len(game.inv.entries)

    def exit(self, game):
        game.audio.crowd(False)
        game.paused = False

    def update(self, game, dt):
        inv = game.inv
        if game.paused:
            return
        if game.xray and inv.stage != "done":
            inv.xray_used = True
        inv.update(dt)
        self._sounds(game)
        if inv.stage == "investigate" and not inv.running and inv.trials_left == 0:
            inv.stage = "verdict"
        if inv.stage == "done" and not inv.running:
            game.scenes.change(RESULT)

    @staticmethod
    def _sounds(game):
        inv, hans, audio = game.inv, game.inv.hans, game.audio
        for event in hans.drain_events():
            audio.play(event)
        if hans.moving:
            phase = int(hans.walk_phase / math.pi)
            if phase != game.step_phase:
                game.step_phase = phase
                audio.play("clop")
        if len(inv.entries) != game.seen_entries:
            game.seen_entries = len(inv.entries)
            audio.play("page")
        audio.crowd(game.world.crowd_present)

    # --- input -----------------------------------------------------------------------
    def on_event(self, game, event) -> bool:
        inv = game.inv
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._click(game, event)
        if event.type != pygame.KEYDOWN:
            return False
        key = event.key
        if key == pygame.K_p:
            game.paused = not game.paused
            return True
        if game.paused:
            return True
        if key == pygame.K_s:
            if inv.autopilot:
                inv.stop_autopilot()
            else:
                inv.start_autopilot()
                game.panel.tab = "stumpf"
            return True
        if key == pygame.K_TAB:
            game.panel.next_tab()
            return True
        if key == pygame.K_ESCAPE and inv.stage != "verdict":
            game.scenes.change(TITLE)
            return True
        if inv.autopilot:
            return False
        if inv.stage == "verdict":
            if pygame.K_1 <= key <= pygame.K_3:
                inv.give_verdict(CUES[key - pygame.K_1])
                game.audio.play("click")
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
        elif key == pygame.K_h:
            if inv.ask_stumpf():
                game.panel.tab = "stumpf"
        elif key == pygame.K_a:
            if inv.apply_advice():
                game.audio.play("click")
        elif pygame.K_0 <= key <= pygame.K_9:
            self._cycle(game, game.panel.field_for_key(str(key - pygame.K_0)),
                        -1 if event.mod & pygame.KMOD_SHIFT else 1)
        else:
            return False
        return True

    def _click(self, game, event) -> bool:
        inv, panel = game.inv, game.panel
        tab = panel.tab_at(event.pos)
        if tab is not None and not game.xray:
            panel.tab = tab
            return True
        if game.paused or inv.autopilot:
            return False
        if inv.stage == "verdict":
            for cue, rect in game.cards.verdict_rects.items():
                if rect.collidepoint(event.pos):
                    inv.give_verdict(cue)
                    game.audio.play("click")
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
        game.audio.play("click")

    # --- drawing ---------------------------------------------------------------------
    def draw(self, game, surface):
        inv, th = game.inv, game.theme
        blinkers = inv.trial.blinkers if inv.trial is not None else inv.setup.blinkers
        game.arena.draw(surface, game.world, inv.hans, inv.trial, game.xray, blinkers)
        self._header(game, surface)
        self._footer(game, surface)
        game.panel.draw(surface, inv, inv.hans, game.xray, game.mouse)
        surface.blit(th.vignette, (0, 0))
        if inv.stage == "verdict":
            game.cards.verdict(surface, game.mouse, inv.trials_left)
        elif inv.stage == "proof_intro":
            game.cards.proof_intro(surface, inv.verdict)
        if game.paused:
            game.cards.pause(surface)

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
        if inv.autopilot:
            tags.append(("STUMPF", T.GREEN))
        if game.fast:
            tags.append((f">> x{FAST_FORWARD}", T.BLUE))
        if game.audio.muted:
            tags.append(("MUTED", T.INK_SOFT))
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
        caption, colour = inv.hans.caption, T.INK
        tip = None if inv.running else game.panel.tooltip(inv, game.mouse)
        if inv.autopilot and not inv.running:
            caption, colour = inv.pilot.caption, T.GREEN
        elif tip:
            caption, colour = tip, T.BLUE
        elif not inv.running and inv.stage == "investigate" and inv.case.number == 1 and len(inv.entries) < len(TUTORIAL):
            caption, colour = TUTORIAL[len(inv.entries)], T.RED
        elif not inv.running and not inv.entries and inv.stage == "investigate":
            caption = "Set up your first experiment on the right, then press Enter."
        elif not inv.running and inv.stage == "proof":
            caption = inv.proof_problem() or "Ready. Run the Commission's test."
        th.text(surface, caption, th.serif(17, italic=True), colour, (16, FOOTER_Y + 16), max_width=ARENA_W - 186)
        th.text(surface, "F1 help   P pause   Esc menu", th.type(12), T.INK_SOFT, (ARENA_W - 14, FOOTER_Y + 21), "topright")


class Result(Scene):
    name = "RESULT"

    def enter(self, game):
        if not game.inv.autopilot:
            game.casebook.record(game.inv)

    def on_event(self, game, event) -> bool:
        if _key(event, *ENTER_KEYS):
            if game.demo:
                game.scenes.change(TITLE)
            else:
                game.load_case(game.casebook.next_case)
        elif _key(event, pygame.K_ESCAPE):
            game.scenes.change(TITLE)
        else:
            return False
        return True

    def draw(self, game, surface):
        game.cards.result(surface, game.inv)


TITLE, LOADING, INTRO, LAB, RESULT = Title(), Loading(), Intro(), Lab(), Result()
