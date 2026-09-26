"""The Game object: owns the window, sound, drawing and the best score, and runs the loop."""

from pathlib import Path
import os
import random

import pygame

from game.config import WIDTH, HEIGHT, FPS, TITLE
from game.ai.fsm import StateMachine
from game.audio import Audio
from game.run import Run
from game.save import Best, DEFAULT_PATH
from game.scenes import TITLE as TITLE_SCENE, PLAY
from game.ui import style
from game.ui.fx import FX
from game.ui.render import Renderer
from game.ui.screens import Screens


def _icon() -> pygame.Surface:
    """The player's cyan chevron."""
    icon = pygame.Surface((32, 32), pygame.SRCALPHA)
    pts = [(28, 16), (6, 5), (12, 16), (6, 27)]
    pygame.draw.polygon(icon, (14, 50, 64), pts)
    pygame.draw.polygon(icon, (90, 235, 255), pts, 3)
    return icon


class Game:
    def __init__(self, seed: int | None = None, start_floor: int = 1, start_room: int = 1, xray: bool = False,
                 save_path: Path | None = DEFAULT_PATH, sound: bool = True):
        pygame.init()
        style.reset()
        pygame.display.set_caption(TITLE)
        pygame.display.set_icon(_icon())
        flags = 0 if os.environ.get("SDL_VIDEODRIVER") == "dummy" else pygame.SCALED | pygame.RESIZABLE
        try:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags, vsync=1)
        except pygame.error:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.clock_time = 0.0
        self.seed = seed
        self.rng = random.Random(seed)
        self.start_floor = start_floor
        self.start_room = start_room
        self.renderer = Renderer()
        self.screens = Screens()
        self.fx = FX()
        self.demo_fx = FX(9)
        self.audio = Audio(sound)
        self.best = Best(save_path)
        self.new_best = False
        self.run: Run | None = None
        self.demo: Run | None = None
        self.seen_room = None
        self.xray = xray
        self.paused = False
        self.dash_queued = False
        self.moved = False
        self.banner = ("", "")
        self.banner_time = 99.0
        self.fade = 1.0
        self.end_time = 0.0
        self.hovered = None
        self.aim_px = (WIDTH / 2, HEIGHT / 2)
        self.syncing = False
        self.hack_queued = None
        self.argus_time = 99.0
        self.story_seen = False
        self.story_page = 0
        self.story_time = 0.0
        self.scripted = None               # tests: a function(run) -> (move, aim, firing, dash)
        self.running = True
        self.scenes = StateMachine(self, TITLE_SCENE)

    def new_run(self):
        seed = self.rng.randrange(10 ** 9) if self.seed is None else self.seed
        self.run = Run(seed, self.start_floor, self.start_room)
        self.seen_room = None
        self.new_best = False
        self.fx.clear()

    def handle(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_TAB, pygame.K_x):
            self.xray = not self.xray
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            self.audio.toggle_mute()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        elif event.type == pygame.WINDOWFOCUSLOST and self.scenes.current is PLAY and self.scripted is None:
            self.paused = True
        else:
            self.scenes.handle(event)

    def tick(self, dt: float):
        for event in pygame.event.get():
            self.handle(event)
        self.clock_time += dt
        self.scenes.update(dt)
        self.scenes.current.draw(self, self.screen)
        pygame.display.flip()

    def run_loop(self, max_frames: int | None = None, fixed_dt: float | None = None, on_frame=None):
        frames = 0
        while self.running:
            dt = self.clock.tick(FPS) / 1000 if fixed_dt is None else fixed_dt
            self.tick(min(dt, 1 / 30))
            frames += 1
            if on_frame is not None:
                on_frame(self, frames)
            if max_frames is not None and frames >= max_frames:
                break
        pygame.quit()
