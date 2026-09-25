"""The game's screens, run by the same StateMachine class that runs the scientists.

    TITLE -> INTRO (night intertitle) -> PLAY -> WON -> INTRO (next night) ... -> FINALE
                                            \\-> CAUGHT -> PLAY (try again)
"""

import pygame

from game.ai.ghost import Ghost
from game.ai.state_machine import State
from game.levels import LEVELS

ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
SOUNDS = {"step": "step", "trot": "trot", "tap": "tap", "hmm": "hmm", "alert": "alert", "hint": "hint",
          "wrong": "wrong", "won": "won", "caught": "caught"}


def pressed(event, *keys) -> bool:
    return event.type == pygame.KEYDOWN and event.key in keys


class Scene(State):
    def draw(self, game, surface):
        pass


class Title(Scene):
    name = "TITLE"

    def on_event(self, game, event) -> bool:
        if pressed(event, *ENTER):
            game.demo = False
            game.start_night(game.selected)
        elif pressed(event, pygame.K_d):
            game.demo = True
            game.start_night(game.selected)
        elif pressed(event, pygame.K_LEFT, pygame.K_a):
            game.selected = max(0, game.selected - 1)
            game.audio.play("click")
        elif pressed(event, pygame.K_RIGHT):
            game.selected = min(game.progress.unlocked, game.selected + 1)
            game.audio.play("click")
        elif pressed(event, pygame.K_h):
            game.help_open = True
        elif pressed(event, pygame.K_ESCAPE):
            game.running = False
        else:
            return False
        return True

    def draw(self, game, surface):
        game.cards.title(surface, LEVELS, game.selected, game.progress)


class Intro(Scene):
    name = "INTRO"

    def on_event(self, game, event) -> bool:
        if pressed(event, *ENTER) or event.type == pygame.MOUSEBUTTONDOWN:
            game.new_attempt()
            game.scenes.change(PLAY)
        elif pressed(event, pygame.K_ESCAPE):
            game.scenes.change(TITLE)
        else:
            return False
        return True

    def draw(self, game, surface):
        spec = LEVELS[game.night]
        footer = "Press Enter to watch the AI play" if game.demo else "Press Enter"
        game.cards.intertitle(surface, f"Night {game.night}: {spec.name}", spec.intro, footer)


class Play(Scene):
    name = "PLAY"

    def enter(self, game):
        game.paused = False
        game.end_timer = 0.0
        game.ghost = Ghost() if game.demo else None

    def update(self, game, dt):
        play = game.play
        if game.paused:
            return
        keys = pygame.key.get_pressed()
        move = ((keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a]),
                (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w]))
        trot = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        if game.ghost is not None and move != (0, 0):
            game.ghost = None                         # the player takes over
            game.demo = False
        if game.ghost is not None:
            move, trot, tap = game.ghost.act(play)
            if tap:
                play.tap()
        if game.scripted_move is not None:           # tests drive Hans directly
            move, trot = game.scripted_move, game.scripted_trot
        play.update(dt, move, trot)
        for e in play.drain_events():
            game.audio.play(SOUNDS.get(e, e))
            if e in ("won", "wrong"):
                game.audio.play("open")
        if play.state != "playing":
            game.end_timer += dt
            if game.end_timer > (0.9 if play.state == "won" else 0.7):
                game.scenes.change(WON if play.state == "won" else CAUGHT)

    def on_event(self, game, event) -> bool:
        if event.type != pygame.KEYDOWN:
            return False
        if game.paused:
            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_p):
                game.paused = False
            elif event.key == pygame.K_r:
                game.new_attempt()
                game.paused = False
            elif event.key == pygame.K_q:
                game.scenes.change(TITLE)
            return True
        if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e):
            game.play.tap()
        elif event.key in (pygame.K_ESCAPE, pygame.K_p):
            game.paused = True
        elif event.key == pygame.K_r:
            game.new_attempt()
        else:
            return False
        return True

    def draw(self, game, surface):
        banner = None
        if game.ghost is not None:
            banner = f"AI DEMO   the ghost is: {game.ghost.mode}      (arrow keys: take over)"
        game.view.draw(surface, game.play, game.xray, game.clock_time, banner)
        if game.paused:
            game.cards.pause(surface)


class Won(Scene):
    name = "WON"

    def enter(self, game):
        game.fails = 0
        if not game.demo:
            game.progress.record(game.night, game.play.stars, len(LEVELS) - 1)

    def on_event(self, game, event) -> bool:
        if pressed(event, *ENTER):
            if game.night + 1 < len(LEVELS):
                game.start_night(game.night + 1)
            else:
                game.scenes.change(FINALE)
        elif pressed(event, pygame.K_r):
            game.new_attempt()
            game.scenes.change(PLAY)
        elif pressed(event, pygame.K_ESCAPE):
            game.scenes.change(TITLE)
        else:
            return False
        return True

    def draw(self, game, surface):
        game.view.draw(surface, game.play, game.xray, game.clock_time)
        game.cards.won(surface, game.play, game.night + 1 >= len(LEVELS))


class Caught(Scene):
    name = "CAUGHT"

    def enter(self, game):
        if not game.demo:
            game.fails += 1

    def on_event(self, game, event) -> bool:
        if pressed(event, *ENTER) or pressed(event, pygame.K_r):
            game.new_attempt()
            game.scenes.change(PLAY)
        elif pressed(event, pygame.K_ESCAPE):
            game.scenes.change(TITLE)
        else:
            return False
        return True

    def draw(self, game, surface):
        game.view.draw(surface, game.play, game.xray, game.clock_time)
        game.cards.caught(surface, game.play, game.fails - 1)


class Finale(Scene):
    name = "FINALE"

    def on_event(self, game, event) -> bool:
        if pressed(event, *ENTER, pygame.K_ESCAPE):
            game.scenes.change(TITLE)
            return True
        return False

    def draw(self, game, surface):
        game.cards.finale(surface, sum(game.progress.stars.values()), 3 * len(LEVELS))


TITLE, INTRO, PLAY, WON, CAUGHT, FINALE = Title(), Intro(), Play(), Won(), Caught(), Finale()
