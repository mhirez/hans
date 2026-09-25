"""One attempt at a level: Hans, von Osten, the scientists, the objectives, winning and getting caught.

Pure logic (no pygame): the scene feeds in the arrow keys and draws the result.
Each attempt hides the carrot behind a random door, so the hint always matters.
"""

import math
import random

from game.config import (WRONG_DOOR_NOISE, TAP_REACH, ALERT_RADIUS, CATCH_DISTANCE, ASSIST_SLOWDOWN, ASSIST_CALM)
from game.ai.owner import Owner
from game.ai.perception import Noise
from game.ai.scientist import Scientist
from game.entities.hans import Hans
from game.level import Level, Door, distance
from game.levels import LevelSpec

FACINGS = {">": 0.0, "v": math.pi / 2, "<": math.pi, "^": -math.pi / 2,
           "e": -math.pi / 4, "q": -3 * math.pi / 4, "z": 3 * math.pi / 4, "c": math.pi / 4}
NAMES = ["Dr. Stumpf", "Dr. Pfungst", "Prof. Nagel", "Dr. Heck", "Count Otto", "Major Keller"]


class Play:
    def __init__(self, number: int, spec: LevelSpec, rng: random.Random, assist: int = 0):
        self.number = number
        self.spec = spec
        self.level = Level(list(spec.map))
        self.rng = rng
        self.assist = assist
        self.carrot: Door = rng.choice(self.level.doors)
        self.hans = Hans(self.level.start)
        self.owner = Owner(self.level, self.carrot)
        self.scientists: list[Scientist] = []
        for i, route in enumerate(spec.scientists):
            watch = self.level.owner_stops[0] if route.endswith("o") else None
            route = route.rstrip("o")
            facing = FACINGS.get(route[-1])
            digits = route.rstrip("<>^vqezc")
            points = [self.level.waypoints[d] for d in digits]
            self.scientists.append(Scientist(self.level, points, NAMES[i % len(NAMES)], facing,
                                             calm=1 - ASSIST_CALM * assist, slow=1 - ASSIST_SLOWDOWN * assist,
                                             watch=watch))
        self.state = "playing"            # playing, won, caught
        self.time = 0.0
        self.hint_known = False
        self.opened: set[int] = set()     # wrong doors already tapped
        self.seen_count = 0               # times a scientist became suspicious
        self.chased = False
        self.caught_by: Scientist | None = None
        self.noises: list[tuple[Noise, float]] = []    # recent noises and their age, for drawing
        self.events: list[str] = []       # for sound: hint, hmm, alert, tap, wrong, won, caught, step, trot
        self.toast = ""
        self.toast_time = 0.0
        self.tip_index = 0
        self._first = {"hmm": True, "alert": True}
        if assist:
            self.say("The scientists look tired tonight.")

    # --- queries for the HUD and the tutorial --------------------------------------------
    @property
    def tip(self):
        tips = self.spec.tips
        return tips[self.tip_index] if self.tip_index < len(tips) else None

    def tip_text(self) -> str:
        return self.tip.text.format(door=self.carrot.name) if self.tip else ""

    def door_in_reach(self) -> Door | None:
        near = [d for d in self.level.doors if distance(self.hans.pos, d.front) <= TAP_REACH]
        return min(near, key=lambda d: distance(self.hans.pos, d.front)) if near else None

    def near_carrot(self) -> bool:
        return distance(self.hans.pos, self.carrot.front) <= TAP_REACH

    @property
    def chased_now(self) -> bool:
        return any(s.state == "CHASE" for s in self.scientists)

    @property
    def stars(self) -> int:
        return 3 if self.seen_count == 0 else 2 if not self.chased else 1

    def say(self, text: str):
        self.toast, self.toast_time = text, 3.0

    # --- actions -------------------------------------------------------------------------
    def tap(self) -> bool:
        if self.state != "playing":
            return False
        door = self.door_in_reach()
        if door is None:
            self.say("Walk right up to a door first.")
            return False
        if door.index in self.opened:
            return False
        if self.chased_now:
            self.say("Not while you're being chased! Lose him first.")
            return False
        self.events.append("tap")
        if door is self.carrot:
            self.state = "won"
            self.events.append("won")
            self._advance_tips()
            return True
        self.opened.add(door.index)
        self.events.append("wrong")
        self.say(f"Door {door.name} is empty! Everyone heard that. Hide!")
        self._noise(Noise(door.front, WRONG_DOOR_NOISE, "door"))
        return False

    # --- simulation ----------------------------------------------------------------------
    def update(self, dt: float, move: tuple[float, float], trot: bool):
        self.toast_time = max(0.0, self.toast_time - dt)
        self.noises = [(n, age + dt) for n, age in self.noises if age + dt < 0.8]
        if self.state != "playing":
            return
        self.time += dt

        for noise in self.hans.update(dt, move, trot, self.level):
            self._noise(noise)
        self.events.extend("trot" if loud else "step" for loud in self.hans.steps)

        self.owner.update(dt, self.hans)
        if "hint" in self.owner.drain_events():
            self.hint_known = True
            self.events.append("hint")
            self.say(f"Von Osten nods toward door {self.carrot.name}!")

        for s in self.scientists:
            s.update(dt, self.hans)
            for e in s.drain_events():
                self.events.append(e)
                if e == "hmm":
                    self.seen_count += 1
                    if self._first["hmm"]:
                        self._first["hmm"] = False
                        self.say("? He's suspicious. Get out of his light!")
                elif e == "alert":
                    self.chased = True
                    if self._first["alert"]:
                        self._first["alert"] = False
                        self.say("! He's seen you! Trot away (SHIFT) and hide!")
                    for other in self.scientists:
                        if other is not s and distance(other.pos, s.pos) <= ALERT_RADIUS:
                            other.alert(self.hans.pos)
            if distance(s.pos, self.hans.pos) <= CATCH_DISTANCE and (s.state == "CHASE" or s.sees_hans):
                self.state = "caught"
                self.caught_by = s
                self.events.append("caught")
                return

        self._advance_tips()

    def _advance_tips(self):
        while self.tip and self.tip.done(self):
            self.tip_index += 1

    def _noise(self, noise: Noise):
        self.noises.append((noise, 0.0))
        for s in self.scientists:
            s.hear(noise)

    def drain_events(self) -> list[str]:
        events, self.events = self.events, []
        return events
