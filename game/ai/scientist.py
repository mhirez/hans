"""A scientist of the Commission: a guard with a lantern, driven by a finite state machine.

    state        does                                   leaves when                       goes to
    PATROL       walks his route, pauses and looks      sees Hans                         SUSPICIOUS (CHASE if close)
                 (a one-point route = a sentry who      hears a noise / is alerted        INVESTIGATE
                  sweeps his lantern side to side;
                  a watcher keeps it on von Osten)
    SUSPICIOUS   stops, stares, "?" and a meter fills   meter full                        CHASE
                                                        lost sight for a moment           INVESTIGATE (where last seen)
                                                        meter empties                     RETURN
    INVESTIGATE  walks (A*) to a noise / last sighting,  sees Hans                        SUSPICIOUS
                 then looks around                      finished looking                  RETURN
    CHASE        "!", whistles for help, runs at Hans   lost him for LOSE_SIGHT_TIME      INVESTIGATE (where last seen)
                 (A*, replanned every REPLAN_TIME)      reaches him                       (the game ends the attempt)
    RETURN       walks (A*) back to his route           arrives                           PATROL
                                                        sees Hans / hears a noise         SUSPICIOUS / INVESTIGATE

Perception runs every frame in every state (perception.py). Suspicion only ever rises
while he can actually see Hans, faster when Hans is close or trotting.
"""

import math

from game.config import (PATROL_SPEED, INVESTIGATE_SPEED, CHASE_SPEED, VIEW_RANGE, VIEW_HALF_ANGLE, CLOSE_RANGE,
                         SUSPICION_RATE, SUSPICION_DECAY, TROT_VISIBILITY, WAYPOINT_PAUSE, LOOK_AROUND_TIME,
                         SUSPICIOUS_GIVE_UP, LOSE_SIGHT_TIME, REPLAN_TIME, SENTRY_SWEEP)
from game.ai.perception import Noise, sees, hears
from game.ai.state_machine import State, StateMachine
from game.entities.walker import Walker
from game.level import Level, Point, distance, angle_to, angle_diff


class Patrol(State):
    name = "PATROL"

    def enter(self, s):
        s.pause = 0.0
        if not s.sentry:
            s.go_to(s.route[s.route_i])

    def update(self, s, dt):
        if s.spotted():
            return
        if s.sentry:
            s.turn_toward(s.home_angle + math.sin(s.fsm.time_in_state * 0.7) * SENTRY_SWEEP, dt)
        elif s.pause > 0:
            s.pause -= dt
            s.turn_toward(s.look_base + math.sin((WAYPOINT_PAUSE - s.pause) * 2.5) * 0.6, dt)
            if s.pause <= 0:
                s.go_to(s.route[s.route_i])
        elif s.walk(dt, s.speed(PATROL_SPEED)):
            s.pause = WAYPOINT_PAUSE
            s.look_base = s.angle
            s.route_i = (s.route_i + 1) % len(s.route)
        if s.watch is not None and not s.sentry:
            s.face(s.watch, dt * 3)          # keeps his lantern on von Osten as he walks

    def on_event(self, s, event) -> bool:
        return s.investigate_event(event)


class Suspicious(State):
    name = "SUSPICIOUS"

    def enter(self, s):
        s.path = []
        s.events.append("hmm")

    def update(self, s, dt):
        if s.last_seen is not None:
            s.face(s.last_seen, dt)
        if s.suspicion >= 1:
            s.fsm.change(CHASE)
        elif not s.sees_hans:
            if s.suspicion <= 0:
                s.fsm.change(RETURN)
            elif s.unseen_time > SUSPICIOUS_GIVE_UP:
                s.target = s.last_seen
                s.fsm.change(INVESTIGATE)

    def on_event(self, s, event) -> bool:
        return s.investigate_event(event)


class Investigate(State):
    name = "INVESTIGATE"

    def enter(self, s):
        s.looking = False
        s.look_time = 0.0
        if not s.go_to(s.target):
            s.looking = True

    def update(self, s, dt):
        if s.spotted():
            return
        if not s.looking:
            if s.walk(dt, s.speed(INVESTIGATE_SPEED)):
                s.looking = True
                s.look_base = s.angle
            return
        s.look_time += dt
        s.turn_toward(s.look_base + math.sin(s.look_time * 2.4) * 1.7, dt)
        if s.look_time >= LOOK_AROUND_TIME:
            s.fsm.change(RETURN)

    def on_event(self, s, event) -> bool:
        return s.investigate_event(event)


class Chase(State):
    name = "CHASE"

    def enter(self, s):
        s.suspicion = 1.0
        s.replan = 0.0
        s.events.append("alert")

    def update(self, s, dt):
        target = s.hans_pos if s.sees_hans else s.last_seen
        s.replan -= dt
        if s.replan <= 0:
            s.go_to(target)
            s.replan = REPLAN_TIME
        s.walk(dt, s.speed(CHASE_SPEED))
        if s.sees_hans:
            s.face(s.hans_pos, dt)
        elif s.unseen_time > LOSE_SIGHT_TIME:
            s.suspicion = 0.6
            s.target = s.last_seen
            s.fsm.change(INVESTIGATE)


class Return(State):
    name = "RETURN"

    def enter(self, s):
        s.route_i = min(range(len(s.route)), key=lambda i: distance(s.pos, s.route[i]))
        s.go_to(s.route[s.route_i])

    def update(self, s, dt):
        if s.spotted():
            return
        if s.walk(dt, s.speed(PATROL_SPEED)):
            if s.sentry:
                s.turn_toward(s.home_angle, dt)
                if abs(angle_diff(s.angle, s.home_angle)) > 0.05:
                    return
            s.fsm.change(PATROL)

    def on_event(self, s, event) -> bool:
        return s.investigate_event(event)


PATROL, SUSPICIOUS, INVESTIGATE, CHASE, RETURN = Patrol(), Suspicious(), Investigate(), Chase(), Return()


class Scientist(Walker):
    def __init__(self, level: Level, route: list[Point], name: str, facing: float | None = None,
                 calm: float = 1.0, slow: float = 1.0, watch: Point | None = None):
        start_angle = facing if facing is not None else (
            angle_to(route[0], route[1]) if len(route) > 1 else math.pi / 2)
        super().__init__(level, route[0], start_angle)
        self.name = name
        self.watch = watch          # a point he keeps his lantern on while patrolling (von Osten)
        self.route = route
        self.route_i = 1 % len(route)
        self.home_angle = start_angle
        self.calm = calm            # difficulty assist: < 1 means slower to get suspicious
        self.slow = slow            # difficulty assist: < 1 means slower on his feet
        self.suspicion = 0.0
        self.sees_hans = False
        self.hans_pos: Point = (0.0, 0.0)
        self.last_seen: Point | None = None
        self.unseen_time = 0.0
        self.target: Point | None = None
        self.pause = 0.0
        self.look_base = start_angle
        self.looking = False
        self.look_time = 0.0
        self.replan = 0.0
        self.events: list[str] = []
        self.fsm = StateMachine(self, PATROL)

    @property
    def sentry(self) -> bool:
        return len(self.route) == 1

    @property
    def state(self) -> str:
        return self.fsm.name

    @property
    def icon(self) -> str | None:
        if self.state == "CHASE":
            return "!"
        if self.state in ("SUSPICIOUS", "INVESTIGATE"):
            return "?"
        return None

    def speed(self, base: float) -> float:
        return base * self.slow

    # --- senses ------------------------------------------------------------------------
    def perceive(self, hans, dt: float):
        self.hans_pos = hans.pos
        d = sees(self.level, self.pos, self.angle, hans.pos, VIEW_RANGE, VIEW_HALF_ANGLE)
        self.sees_hans = d is not None
        if self.sees_hans:
            self.last_seen = hans.pos
            self.unseen_time = 0.0
            if d < CLOSE_RANGE:
                self.suspicion = 1.0
            else:
                gain = SUSPICION_RATE * (0.35 + 0.65 * (1 - d / VIEW_RANGE)) * self.calm
                if hans.trotting:
                    gain *= TROT_VISIBILITY
                self.suspicion = min(1.0, self.suspicion + gain * dt)
        else:
            self.unseen_time += dt
            if self.state != "CHASE":
                self.suspicion = max(0.0, self.suspicion - SUSPICION_DECAY * dt)

    def hear(self, noise: Noise) -> bool:
        if self.state != "CHASE" and hears(self.pos, noise):
            return self.fsm.handle(("noise", noise.pos))
        return False

    def alert(self, pos: Point):
        """A colleague whistled: come and look."""
        if self.state != "CHASE":
            self.fsm.handle(("alert", pos))

    # --- helpers the states share ------------------------------------------------------
    def spotted(self) -> bool:
        """React to seeing Hans. Returns True if the state changed."""
        if not self.sees_hans:
            return False
        self.fsm.change(CHASE if self.suspicion >= 1 else SUSPICIOUS)
        return True

    def investigate_event(self, event) -> bool:
        kind, pos = event
        if kind in ("noise", "alert"):
            self.target = pos
            if kind == "noise":
                self.suspicion = max(self.suspicion, 0.2)
            self.fsm.change(INVESTIGATE)
            return True
        return False

    def update(self, dt: float, hans):
        self.perceive(hans, dt)
        self.fsm.update(dt)

    def drain_events(self) -> list[str]:
        events, self.events = self.events, []
        return events

