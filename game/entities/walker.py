"""A body that walks along A* paths and turns smoothly: shared by the scientists and von Osten."""

import math

from game.config import TURN_SPEED
from game.level import Level, Point, tile_of, center, angle_to, angle_diff


class Walker:
    def __init__(self, level: Level, pos: Point, angle: float = math.pi / 2):
        self.level = level
        self.pos = pos
        self.angle = angle
        self.path: list[Point] = []
        self.explored: set = set()        # last A* closed set, for the X-Ray
        self.walk_phase = 0.0

    @property
    def moving(self) -> bool:
        return bool(self.path)

    def go_to(self, target: Point) -> bool:
        goal = self.level.nearest_walkable(tile_of(target))
        search = self.level.route(tile_of(self.pos), goal)
        self.explored = search.explored
        if search.path is None:
            self.path = []
            return False
        self.path = [center(t) for t in search.path[1:]]
        if self.level.walkable(*tile_of(target)) and self.path:
            self.path[-1] = target
        return True

    def walk(self, dt: float, speed: float) -> bool:
        """Follow the path. Returns True when there is nothing left to walk."""
        budget = speed * dt
        while self.path and budget > 0:
            tx, ty = self.path[0]
            dx, dy = tx - self.pos[0], ty - self.pos[1]
            dist = math.hypot(dx, dy)
            if dist > 1e-6:
                self.turn_toward(math.atan2(dy, dx), dt)
            if dist <= budget:
                self.pos = (tx, ty)
                self.path.pop(0)
                budget -= dist
            else:
                self.pos = (self.pos[0] + dx / dist * budget, self.pos[1] + dy / dist * budget)
                budget = 0
        if self.path:
            self.walk_phase += dt * speed * 3
        return not self.path

    def turn_toward(self, target_angle: float, dt: float, speed: float = TURN_SPEED):
        diff = angle_diff(self.angle, target_angle)
        step = speed * dt
        self.angle += max(-step, min(step, diff))

    def face(self, point: Point, dt: float):
        self.turn_toward(angle_to(self.pos, point), dt)
