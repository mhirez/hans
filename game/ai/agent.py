"""The shared enemy brain: body, senses, memory, movement, decision making, and the calm states.

Every enemy runs a finite state machine. The calm half is shared:

    PATROL ──hears a shot──> INVESTIGATE ──nothing there──> PATROL
      │  suspicion fills (sees you)        │ spots you
      └──────────────"!"───────────────────┴──> combat states (one set per enemy type)
    combat ──lost you for 5 s──> SEARCH ──spots you──> combat
                                   └──gives up──> PATROL
    any ──stunned──> STUNNED ──> combat

In combat each type DECIDES what to do with utility scores: every option gets a score from
0 to ~1 built from what it knows (can it see you, how far, how hurt, is it under fire, is an
attack token free...). The best feasible option wins, with a bonus for the current one so it
doesn't dither. Scores are kept on the enemy so the AI X-Ray can show them.
"""

import math

from game import config as C
from game.ai.fsm import State, StateMachine
from game.ai.senses import Senses
from game.geometry import (Point, add, angle_to, center, distance, from_angle, normalize, tile_of,
                           turn_toward)

HYSTERESIS = 0.12
THINK_EVERY = 0.35
REACTION = 0.2                    # entering combat: turn toward the threat for a beat, then decide


class Enemy:
    kind = "enemy"
    name = "ENEMY"
    base_hp = 3.0
    speed = 3.0
    radius = 0.35
    worth = 100
    view_range = C.VIEW_RANGE

    def __init__(self, room, pos: Point, patrol: list[Point], uid: int):
        self.room = room
        self.pos = pos
        self.uid = uid
        self.vel: Point = (0.0, 0.0)
        self.knock: Point = (0.0, 0.0)
        self.facing = math.pi + room.rng.uniform(-0.6, 0.6)
        self.max_hp = self.base_hp * room.tuning["hp"]
        self.hp = self.max_hp
        self.senses = Senses()
        self.alert = False
        self.dead = False
        self.path: list[Point] = []
        self.patrol = patrol or [pos]
        self.patrol_i = 0
        self.flash = 0.0
        self.icon: str | None = None
        self.icon_age = 0.0
        self.scores: dict[str, float] = {}
        self.action = ""
        self.windup = 0.0                 # 0..1 telegraph progress (drawn by the renderer)
        self.locked = False               # the telegraph has flashed white: direction fixed
        self.aim = 0.0                    # attack direction being telegraphed
        self.timer = 0.0
        self.think = 0.0
        self.cooldown = room.rng.uniform(0.3, 1.0)
        self.hit_time = -math.inf
        self.near_miss_time = -math.inf
        self.noise: Point | None = None
        self.stun = 0.0
        self.exposed = False              # takes double damage (a dazed charger)
        self.crouch = False
        self.spot: Point | None = None    # where it's heading on purpose (drawn in X-Ray)
        self.age = 0.0
        self.fsm = StateMachine(self, PATROL)

    # --- facts ---------------------------------------------------------------------------
    @property
    def health(self) -> float:
        return max(0.0, self.hp / self.max_hp)

    @property
    def state(self) -> str:
        return self.fsm.name

    @property
    def now(self) -> float:
        return self.room.time

    @property
    def player(self):
        return self.room.player

    def under_fire(self) -> float:
        """1 just after being shot at, fading to 0 over 1.5 s."""
        since = self.now - max(self.hit_time, self.near_miss_time)
        return max(0.0, 1 - since / 1.5)

    def say(self, icon: str | None):
        if icon != self.icon or self.icon_age > 1.2:
            self.icon, self.icon_age = icon, 0.0

    # --- the frame -------------------------------------------------------------------------
    def update(self, dt: float):
        self.age += dt
        self.flash = max(0.0, self.flash - dt)
        self.icon_age += dt
        if self.icon and self.icon_age > 1.4:
            self.icon = None
        self.cooldown = max(0.0, self.cooldown - dt)
        if abs(self.knock[0]) + abs(self.knock[1]) > 0.01:
            self.pos = self.room.grid.move(self.pos, (self.knock[0] * dt, self.knock[1] * dt), self.radius)
            decay = math.exp(-10 * dt)
            self.knock = (self.knock[0] * decay, self.knock[1] * decay)
        self.perceive(dt)
        self.fsm.update(dt)

    def perceive(self, dt: float):
        event = self.senses.update(self, dt)
        if event == "spotted":
            self.become_alert(self.player.pos, shout=True)
        elif self.alert and self.senses.sees and self.fsm.current is SEARCH:
            self.say("!")
            self.fsm.change(self.combat_state())

    # --- reactions -----------------------------------------------------------------------
    def combat_state(self) -> State:
        raise NotImplementedError

    def become_alert(self, where: Point, shout: bool):
        first = not self.alert
        self.alert = True
        if self.senses.last_known is None or not self.senses.sees:
            self.senses.heard(where, self.now)
        self.say("!")
        if shout:
            self.room.shout(self, where)
        if first or self.fsm.current in (PATROL, INVESTIGATE, SEARCH):
            self.fsm.change(self.combat_state())

    def hear_shot(self, where: Point):
        if self.alert:
            if not self.senses.sees:
                self.senses.heard(where, self.now)
            return
        self.noise = where
        self.say("?")
        if self.fsm.current in (PATROL, INVESTIGATE):
            self.fsm.change(INVESTIGATE)

    def take_hit(self, damage: float, direction: Point, source: Point) -> float:
        if self.dead:
            return 0.0
        if self.exposed:
            damage *= 2
        self.hp -= damage
        self.flash = 0.09
        self.hit_time = self.now
        self.knock = add(self.knock, direction, 2.2)
        if not self.alert:
            self.become_alert(source, shout=True)
        elif not self.senses.sees:
            self.senses.heard(source, self.now)
        if self.hp <= 0:
            self.room.kill(self)
        return damage

    def stunned(self, seconds: float):
        self.stun = seconds
        self.room.coordinator.release(self)
        self.fsm.change(STUNNED)

    # --- deciding ------------------------------------------------------------------------
    def options(self) -> dict[str, float]:
        return {}

    def feasible(self, action: str) -> bool:
        """Last-moment check (e.g. is there actually a cover spot?). May prepare the action."""
        return True

    def decide(self):
        """Score every option, keep the best feasible one (with a bonus for the current)."""
        self.think = THINK_EVERY
        if self.senses.age(self.now) > C.MEMORY_TIME and not self.senses.sees:
            self.fsm.change(SEARCH)
            return
        scores = self.options()
        if self.action in scores and scores[self.action] > 0:
            scores[self.action] += HYSTERESIS
        self.scores = scores
        for action in sorted(scores, key=scores.get, reverse=True):
            if scores[action] <= 0:
                break
            if action == self.action and self.fsm.current in self.states_for(action):
                return
            if self.feasible(action):
                self.action = action
                self.fsm.change(self.states_for(action)[0])
                return

    def states_for(self, action: str) -> tuple[State, ...]:
        raise NotImplementedError

    def rethink(self, dt: float):
        self.think -= dt
        if self.think <= 0:
            self.decide()

    # --- moving --------------------------------------------------------------------------
    def go_to(self, target: Point, extra_cost=None) -> bool:
        grid = self.room.grid
        start = grid.nearest_walkable(tile_of(self.pos))
        tiles = grid.route(start, tile_of(target), extra_cost)
        if tiles is None:
            self.path = []
            return False
        points = [center(t) for t in tiles[1:]]
        if points and grid.free(target, self.radius):
            points[-1] = target
        self.path = points or [target]
        return True

    def follow(self, dt: float, speed: float, face: bool = True) -> bool:
        """Walk the path; True once arrived. Skips ahead whenever the next corner is visible."""
        grid = self.room.grid
        for _ in range(2):
            if len(self.path) >= 2 and grid.clear_line(self.pos, self.path[1], self.radius * 0.95):
                self.path.pop(0)
            else:
                break
        while self.path and distance(self.pos, self.path[0]) < 0.2:
            self.path.pop(0)
        if not self.path:
            self.brake(dt)
            return True
        direction, _ = normalize((self.path[0][0] - self.pos[0], self.path[0][1] - self.pos[1]))
        self.steer(direction, dt, speed)
        if face:
            self.face(math.atan2(direction[1], direction[0]), dt)
        return False

    def steer(self, direction: Point, dt: float, speed: float):
        target = (direction[0] * speed, direction[1] * speed)
        k = min(1.0, 14 * dt)
        self.vel = (self.vel[0] + (target[0] - self.vel[0]) * k, self.vel[1] + (target[1] - self.vel[1]) * k)
        self.pos = self.room.grid.move(self.pos, (self.vel[0] * dt, self.vel[1] * dt), self.radius)

    def brake(self, dt: float):
        self.steer((0.0, 0.0), dt, 0.0)

    def face(self, angle: float, dt: float, rate: float = C.TURN_RATE):
        self.facing = turn_toward(self.facing, angle, rate * dt)

    def face_player(self, dt: float, rate: float = C.TURN_RATE):
        target = self.player.pos if self.senses.sees else self.senses.last_known
        if target is not None:
            self.face(angle_to(self.pos, target), dt, rate)

    def target(self) -> Point:
        """Where it thinks the player is."""
        return self.player.pos if self.senses.sees else (self.senses.last_known or self.player.pos)


# --- calm states ------------------------------------------------------------------------------
class Patrol(State):
    name = "PATROL"

    def enter(self, e):
        e.timer = e.room.rng.uniform(0.2, 1.0)          # a pause before setting off
        e.path = []
        e.spot = None

    def update(self, e, dt):
        if e.senses.suspicion > 0.15:                   # the double take: stop and stare
            e.brake(dt)
            e.face(angle_to(e.pos, e.player.pos), dt, 5.0)
            if e.senses.suspicion > 0.3:
                e.say("?")
            return
        if e.timer > 0:
            e.timer -= dt
            e.brake(dt)
            e.facing += math.sin(e.age * 1.7) * dt * 0.9       # look around
            if e.timer <= 0:
                e.patrol_i = (e.patrol_i + 1) % len(e.patrol)
                e.go_to(e.patrol[e.patrol_i])
            return
        if e.follow(dt, e.speed * 0.4):
            e.timer = e.room.rng.uniform(0.8, 1.8)


class Investigate(State):
    name = "INVESTIGATE"

    def enter(self, e):
        e.timer = 0.0
        e.go_to(e.noise or e.pos)
        e.spot = e.noise

    def update(self, e, dt):
        if e.senses.suspicion > 0.15:
            e.brake(dt)
            e.face(angle_to(e.pos, e.player.pos), dt, 6.0)
            return
        if e.follow(dt, e.speed * 0.7):
            e.timer += dt
            e.facing += dt * 2.2                                   # turn on the spot, looking
            if e.timer > 1.8:
                e.fsm.change(PATROL)


class Search(State):
    """Lost the player: go where he was last known, look around, try a couple of nearby spots."""
    name = "SEARCH"

    def enter(self, e):
        e.room.coordinator.forget(e)
        e.timer = 0.0
        e.windup = 0.0
        e.crouch = False
        e.searched = 0
        e.say("?")
        e.go_to(e.senses.last_known or e.pos)
        e.spot = e.senses.last_known

    def update(self, e, dt):
        e.timer += dt
        if e.follow(dt, e.speed * 0.75):
            e.facing += dt * 2.6
            if e.timer > 1.4 + 2.2 * e.searched:
                e.searched += 1
                if e.searched > 2 or e.timer > 9:
                    e.alert = False                                # gives up
                    e.senses.suspicion = 0.0
                    e.fsm.change(PATROL)
                    return
                around = e.senses.last_known or e.pos
                tiles = e.room.tactics.candidates(tile_of(around), 4)
                if tiles:
                    t = e.room.rng.choice(tiles)
                    e.go_to(center(t))
                    e.spot = center(t)


class Stunned(State):
    name = "STUNNED"

    def enter(self, e):
        e.timer = 0.0
        e.windup = 0.0
        e.path = []

    def update(self, e, dt):
        e.timer += dt
        e.brake(dt)
        if e.timer >= e.stun:
            e.exposed = False
            e.stun = 0.0
            e.fsm.change(e.combat_state())


PATROL, INVESTIGATE, SEARCH, STUNNED = Patrol(), Investigate(), Search(), Stunned()
CALM = (PATROL, INVESTIGATE)


def muzzle(e, angle: float) -> Point:
    return add(e.pos, from_angle(angle, e.radius + 0.1))
