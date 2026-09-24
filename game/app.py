"""The Game object: owns the window, the shared world and views, and runs the loop."""

import random

import pygame

from game.config import WIDTH, HEIGHT, FPS, TITLE, FAST_FORWARD
from game.ai.state_machine import StateMachine
from game.case import make_case
from game.investigation import Investigation
from game.log import ExperimentLog
from game.scenes import TITLE as TITLE_SCENE, LAB
from game.ui.arena import ArenaView
from game.ui.cards import Cards
from game.ui.panel import Panel
from game.ui.theme import Theme
from game.world import World


class Game:
    def __init__(self, seed: int | None = None, xray: bool = False, log_dir: str | None = "logs",
                 start_case: int = 1):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.seed = seed if seed is not None else random.randrange(1_000_000)
        self.rng = random.Random(self.seed)
        self.theme = Theme()
        self.world = World()
        self.arena = ArenaView(self.theme, self.world)
        self.panel = Panel(self.theme)
        self.cards = Cards(self.theme)
        self.log = ExperimentLog(log_dir) if log_dir is not None else None
        self.xray = xray
        self.fast = False
        self.running = True
        self.mouse = (0, 0)
        self.case_number = start_case
        self.inv: Investigation | None = None
        self.scenes = StateMachine(self, TITLE_SCENE)

    def start_case(self, number: int):
        self.inv = Investigation(make_case(number, self.rng), self.world, self.rng, self.log)

    def handle(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_x:
            self.xray = not self.xray
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            self.fast = not self.fast
        else:
            self.scenes.handle(event)

    def tick(self, dt: float):
        for event in pygame.event.get():
            self.handle(event)
        steps = FAST_FORWARD if (self.fast and self.scenes.current is LAB) else 1
        for _ in range(steps):
            self.scenes.update(dt)
        self.scenes.current.draw(self, self.screen)
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
