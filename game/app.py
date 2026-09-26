"""The Game object: owns the window, the views and the best score, and runs the loop."""

from pathlib import Path
import os
import random

import pygame

from game.config import WIDTH, HEIGHT, FPS, TITLE
from game.ai.state_machine import StateMachine
from game.audio import Audio
from game.match import Match
from game.save import Best, DEFAULT_PATH
from game.scenes import TITLE as TITLE_SCENE
from game.ui.cards import Cards
from game.ui.theme import Theme
from game.ui.view import MatchView


class Game:
    def __init__(self, seed: int | None = None, xray: bool = False, start_wave: int = 1,
                 save_path: Path | None = DEFAULT_PATH, sound: bool = True):
        pygame.init()
        pygame.display.set_caption(TITLE)
        # SCALED keeps the 1280x720 layout crisp in any window size, and allows full screen
        flags = 0 if os.environ.get("SDL_VIDEODRIVER") == "dummy" else pygame.SCALED | pygame.RESIZABLE
        try:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.clock_time = 0.0
        self.rng = random.Random(seed)
        self.theme = Theme()
        self.view = MatchView(self.theme)
        self.cards = Cards(self.theme)
        self.audio = Audio(sound)
        self.best = Best(save_path)
        self.new_best = False
        self.start_wave = start_wave
        self.match: Match | None = None
        self.xray = xray
        self.paused = False
        self.help_open = False
        self.kick_queued = False
        self.step_phase = 0
        self.scripted = None           # tests: a function(match) -> (move, gallop, kick)
        self.story_seen = False        # the silent-film intro plays before the first game only
        self.story_page = 0
        self.running = True
        self.scenes = StateMachine(self, TITLE_SCENE)

    def new_match(self):
        self.match = Match(self.rng, self.start_wave)
        self.new_best = False

    def handle(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif self.help_open and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.help_open = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.help_open = True
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_x:
            self.xray = not self.xray
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            self.audio.toggle_mute()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        else:
            self.scenes.handle(event)

    def tick(self, dt: float):
        for event in pygame.event.get():
            self.handle(event)
        self.clock_time += dt
        if not self.help_open:
            self.scenes.update(dt)
        self.scenes.current.draw(self, self.screen)
        if self.help_open:
            self.cards.help(self.screen)
        pygame.display.flip()

    def run(self, max_frames: int | None = None, fixed_dt: float | None = None, on_frame=None):
        frames = 0
        while self.running:
            dt = self.clock.tick(FPS) / 1000 if fixed_dt is None else fixed_dt
            self.tick(min(dt, 0.05))
            frames += 1
            if on_frame is not None:
                on_frame(self, frames)
            if max_frames is not None and frames >= max_frames:
                break
        pygame.quit()
