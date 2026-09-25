"""The Game object: owns the window, the views and the progress, and runs the loop."""

from pathlib import Path
import os
import random

import pygame

from game.config import WIDTH, HEIGHT, FPS, TITLE, ASSIST_AFTER, ASSIST_MAX
from game.ai.state_machine import StateMachine
from game.audio import Audio
from game.levels import LEVELS
from game.play import Play
from game.save import Progress, DEFAULT_PATH
from game.scenes import TITLE as TITLE_SCENE, INTRO
from game.ui.cards import Cards
from game.ui.theme import Theme
from game.ui.view import PlayView


class Game:
    def __init__(self, seed: int | None = None, xray: bool = False, night: int | None = None,
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
        self.view = PlayView(self.theme)
        self.cards = Cards(self.theme)
        self.audio = Audio(sound)
        self.progress = Progress(save_path)
        if night is not None:
            self.progress.unlocked = max(self.progress.unlocked, min(night, len(LEVELS) - 1))
        self.selected = min(self.progress.unlocked, night if night is not None else self.progress.unlocked)
        self.night = self.selected
        self.play: Play | None = None
        self.fails = 0
        self.xray = xray
        self.paused = False
        self.help_open = False
        self.end_timer = 0.0
        self.scripted_move = None      # set by tests to drive Hans without a keyboard
        self.scripted_trot = False
        self.demo = False              # the AI ghost plays (title screen: D)
        self.ghost = None
        self.running = True
        self.scenes = StateMachine(self, TITLE_SCENE)

    def start_night(self, night: int):
        if night != self.night:
            self.fails = 0
        self.night = self.selected = night
        self.scenes.change(INTRO)

    def new_attempt(self):
        assist = min(ASSIST_MAX, self.fails // ASSIST_AFTER)
        self.play = Play(self.night, LEVELS[self.night], self.rng, assist)

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
