"""Hans the agent: a mind (beliefs, readings, decisions), a body (position, A* walking)
and an FSM that decides which of those to use each frame."""

from dataclasses import dataclass
import math
import random

from game.config import HANS_SPEED, PATIENCE, CROWD_PATIENCE_DRAIN, PASSIVE_SENSE_INTERVAL
from game.ai.beliefs import BeliefModel
from game.ai.hans_states import WAITING
from game.ai.mind import HansMind
from game.ai.pathfinding import astar, SearchResult
from game.ai.perception import Senses
from game.ai.state_machine import StateMachine
from game.ai.utility import Decision
from game.world import World, START, Point, tile_of, center


@dataclass(frozen=True)
class Outcome:
    decision: Decision
    carrot: int
    deltas: dict[str, float]

    @property
    def choice(self) -> int:
        return self.decision.choice

    @property
    def success(self) -> bool:
        return self.decision.choice == self.carrot


def travel_times(world: World, pos: Point, sources) -> dict[str, float]:
    """Walking time to each source's study tile, from real A* path costs (None = unreachable)."""
    times = {}
    for s in sources:
        result = astar(tile_of(pos), s.observe_tile, world.walkable)
        times[s.id] = None if result.path is None else result.cost / HANS_SPEED
    return times


class Hans:
    def __init__(self, world: World, rng: random.Random, beliefs: BeliefModel | None = None):
        self.world = world
        self.rng = rng
        self.mind = HansMind(beliefs, rng)
        self.pos: Point = START
        self.facing = -1
        self.walk_phase = 0.0
        self.waypoints: list[Point] = []
        self.search: SearchResult | None = None
        self.senses: Senses | None = None
        self.patience = PATIENCE
        self.sense_timer = 0.0
        self.first_look = True
        self.target = None
        self.route_failed = False
        self.study_left = 0.0
        self.tapping = False
        self.taps_done = 0
        self.tap_timer = 0.0
        self.outcome: Outcome | None = None
        self.caption = ""
        self.done = False
        self.fsm = StateMachine(self, WAITING)

    @property
    def beliefs(self) -> BeliefModel:
        return self.mind.beliefs

    @property
    def state(self) -> str:
        return self.fsm.name

    # --- commands from the game ------------------------------------------------------
    def begin_trial(self, senses: Senses):
        self.senses = senses
        self.pos = START
        self.facing = -1
        self.waypoints = []
        self.search = None
        self.patience = PATIENCE
        self.sense_timer = 0.0
        self.first_look = True
        self.outcome = None
        self.done = False
        self.mind.start_trial()
        self.mind.perceive(senses, self.pos)
        if self.fsm.current is not WAITING:
            self.fsm.change(WAITING)
        self.fsm.handle("start")

    def update(self, dt: float):
        self.fsm.update(dt)

    # --- helpers the states use ------------------------------------------------------
    def drain_patience(self, dt: float):
        self.patience -= dt * (CROWD_PATIENCE_DRAIN if self.senses.crowd_audible else 1.0)

    def sense(self, dt: float):
        self.sense_timer += dt
        if self.sense_timer >= PASSIVE_SENSE_INTERVAL:
            self.sense_timer = 0.0
            self.mind.perceive(self.senses, self.pos)

    def travel_times(self) -> dict[str, float]:
        return travel_times(self.world, self.pos, self.senses.sources())

    def walk_to(self, tile, final: Point | None = None) -> bool:
        self.search = astar(tile_of(self.pos), tile, self.world.walkable)
        if self.search.path is None:
            self.waypoints = []
            return False
        self.waypoints = [center(t) for t in self.search.path[1:]]
        if final is not None:
            self.waypoints.append(final)
        return True

    def step(self, dt: float) -> bool:
        """Follow the current waypoints. Returns True once there are none left."""
        budget = HANS_SPEED * dt
        while self.waypoints and budget > 0:
            tx, ty = self.waypoints[0]
            dx, dy = tx - self.pos[0], ty - self.pos[1]
            dist = math.hypot(dx, dy)
            if abs(dx) > 1e-3:
                self.facing = 1 if dx > 0 else -1
            if dist <= budget:
                self.pos = (tx, ty)
                self.waypoints.pop(0)
                budget -= dist
            else:
                self.pos = (self.pos[0] + dx / dist * budget, self.pos[1] + dy / dist * budget)
                budget = 0
            self.walk_phase += dt * 10
        return not self.waypoints

    def face(self, point: Point):
        if abs(point[0] - self.pos[0]) > 0.05:
            self.facing = 1 if point[0] > self.pos[0] else -1

    def finish_trial(self, carrot: int):
        deltas = self.mind.learn(carrot)
        self.outcome = Outcome(self.mind.decision, carrot, deltas)
