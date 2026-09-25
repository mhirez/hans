"""The game's screens, run by the same StateMachine class that runs the enemies.

    TITLE -> PLAY -> OVER -> PLAY (again) ...
"""

import math

import pygame

from game.ai.state_machine import State

ENTER = (pygame.K_RETURN, pygame.K_KP_ENTER)
SOUNDS = {"kick": "kick", "ko": "ko", "hurt": "hurt", "tangled": "whoosh", "throw": "whoosh",
          "scientist:swing": "whoosh", "bark": "bark", "dog:growl": "growl", "shout": "hmm", "crunch": "crunch",
          "heal": "bell", "power": "fanfare", "wave_clear": "fanfare", "game_over": "caught", "door": "creak",
          "slurp": "slurp"}


def pressed(event, *keys) -> bool:
    return event.type == pygame.KEYDOWN and event.key in keys


class Scene(State):
    def draw(self, game, surface):
        pass


class Title(Scene):
    name = "TITLE"

    def on_event(self, game, event) -> bool:
        if pressed(event, *ENTER, pygame.K_SPACE):
            game.new_match()
            game.scenes.change(PLAY)
        elif pressed(event, pygame.K_h):
            game.help_open = True
        elif pressed(event, pygame.K_ESCAPE):
            game.running = False
        else:
            return False
        return True

    def draw(self, game, surface):
        game.cards.title(surface, game.best.score, game.best.wave)


class Play(Scene):
    name = "PLAY"

    def enter(self, game):
        game.paused = False
        game.kick_queued = False
        game.step_phase = 0

    def update(self, game, dt):
        m = game.match
        if game.paused:
            return
        keys = pygame.key.get_pressed()
        move = ((keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a]),
                (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w]))
        gallop = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        if game.scripted is not None:                   # tests drive Hans without a keyboard
            move, gallop, kick = game.scripted(m)
            game.kick_queued = game.kick_queued or kick
        m.update(dt, move, gallop, game.kick_queued)
        game.kick_queued = False
        for e in m.drain_events():
            if e in SOUNDS:
                game.audio.play(SOUNDS[e])
        h = m.hans
        if h.moving:
            phase = int(h.walk_phase / math.pi)
            if phase != game.step_phase:
                game.step_phase = phase
                game.audio.play("trot" if h.galloping else "step")
        if m.state == "over" and m.state_time > 1.2:
            game.new_best = game.best.record(m.score, m.wave.number)
            game.scenes.change(OVER)

    def on_event(self, game, event) -> bool:
        if event.type != pygame.KEYDOWN:
            return False
        if game.paused:
            if event.key in (*ENTER, pygame.K_p, pygame.K_ESCAPE):
                game.paused = False
            elif event.key == pygame.K_r:
                game.new_match()
                game.paused = False
            elif event.key == pygame.K_q:
                game.scenes.change(TITLE)
            return True
        if event.key == pygame.K_SPACE:
            game.kick_queued = True
        elif event.key in (pygame.K_p, pygame.K_ESCAPE):
            game.paused = True
        else:
            return False
        return True

    def draw(self, game, surface):
        m = game.match
        banner = None
        if m.state == "cleared":
            banner = (f"WAVE {m.wave.number} CLEARED", "Get ready...", "")
        elif m.state == "playing" and m.clock < 3.2:
            first, second = m.wave.intro
            if m.wave.number == 1:
                banner = ("WAVE 1", first, "ARROWS run    SHIFT gallop    SPACE kick")
            else:
                banner = (f"WAVE {m.wave.number}", first, second)
        game.view.draw(surface, m, game.xray, game.clock_time, banner)
        if game.paused:
            game.cards.pause(surface)


class Over(Scene):
    name = "OVER"

    def on_event(self, game, event) -> bool:
        if pressed(event, *ENTER, pygame.K_SPACE, pygame.K_r):
            game.new_match()
            game.scenes.change(PLAY)
        elif pressed(event, pygame.K_ESCAPE):
            game.scenes.change(TITLE)
        else:
            return False
        return True

    def draw(self, game, surface):
        game.view.draw(surface, game.match, game.xray, game.clock_time)
        game.cards.game_over(surface, game.match, game.best.score, game.new_best)


TITLE, PLAY, OVER = Title(), Play(), Over()
