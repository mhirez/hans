"""The Game object: owns the window, the shared world and views, and runs the loop."""

from pathlib import Path
import os
import random

import pygame

from game.config import WIDTH, HEIGHT, FPS, TITLE, FAST_FORWARD
from game.ai.state_machine import StateMachine
from game.audio import Audio
from game.case import make_case
from game.investigation import Investigation
from game.log import ExperimentLog
from game.save import Casebook, DEFAULT_PATH
from game.scenes import TITLE as TITLE_SCENE, LOADING, LAB
from game.ui.arena import ArenaView
from game.ui.cards import Cards
from game.ui.panel import Panel
from game.ui.theme import Theme
from game.world import World

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Game:
    def __init__(self, seed: int | None = None, xray: bool = False, log_dir: str | Path | None = PROJECT_ROOT / "logs",
                 start_case: int | None = None, save_path: Path | None = DEFAULT_PATH, sound: bool = True):
        pygame.init()
        pygame.display.set_caption(TITLE)
        # SCALED keeps the 1280x720 layout crisp in any window size, and allows full screen
        flags = 0 if os.environ.get("SDL_VIDEODRIVER") == "dummy" else pygame.SCALED | pygame.RESIZABLE
        try:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self.rng = random.Random(self.seed)
        self.theme = Theme()
        self.world = World()
        self.arena = ArenaView(self.theme, self.world)
        self.panel = Panel(self.theme)
        self.cards = Cards(self.theme)
        self.audio = Audio(sound)
        self.casebook = Casebook(save_path)
        if start_case is not None:
            self.casebook.next_case = start_case
        self.log = ExperimentLog(log_dir) if log_dir is not None else None
        self.xray = xray
        self.fast = False
        self.paused = False
        self.help_open = False
        self.demo = False
        self.running = True
        self.mouse = (0, 0)
        self.inv: Investigation | None = None
        self.pending_case = 1
        self.pending_autopilot = False
        self.loading_drawn = False
        self.step_phase = 0
        self.seen_entries = 0
        self.scenes = StateMachine(self, TITLE_SCENE)

    def load_case(self, number: int, autopilot: bool = False):
        self.pending_case, self.pending_autopilot = number, autopilot
        self.scenes.change(LOADING)

    def start_case(self, number: int):
        self.inv = Investigation(make_case(number, self.rng), self.world, self.rng, self.log)
        self.panel.tab = "notebook"

    def handle(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            self.mouse = event.pos
            if event.type == pygame.MOUSEBUTTONDOWN and self.help_open:
                self.help_open = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.scenes.handle(event)
        elif event.type != pygame.KEYDOWN:
            return
        elif self.help_open:
            self.help_open = False
        elif event.key in (pygame.K_F1, pygame.K_QUESTION) or (event.key == pygame.K_SLASH and event.mod & pygame.KMOD_SHIFT):
            self.help_open = True
        elif event.key == pygame.K_x:
            self.xray = not self.xray
        elif event.key == pygame.K_f:
            self.fast = not self.fast
        elif event.key == pygame.K_m:
            self.audio.toggle_mute()
        elif event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        else:
            self.scenes.handle(event)

    def tick(self, dt: float):
        for event in pygame.event.get():
            self.handle(event)
        if not self.help_open:
            steps = FAST_FORWARD if (self.fast and self.scenes.current is LAB) else 1
            for _ in range(steps):
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
