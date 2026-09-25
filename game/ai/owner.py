"""Wilhelm von Osten, Hans's owner. He knows where the carrot is, and can't help showing it.

    state      does                                           leaves when                      goes to
    STANDING   stands at a stop, watching the yard           Hans is in his circle            NODDING
                                                             (wandering levels) time's up     WALKING
    NODDING    unconsciously nods toward the carrot door;     Hans leaves the circle           STANDING
               the hint fills while Hans stays close
    WALKING    strolls (A*) to his next stop; no nodding      arrives                          STANDING

Like the real von Osten, he isn't cheating. His cue is involuntary: it only works if Hans is
close enough to watch him (HINT_RADIUS, with a clear line of sight) and he is standing still.
"""

from game.config import HINT_RADIUS, HINT_TIME, HINT_DECAY, OWNER_SPEED, OWNER_STAND_TIME
from game.ai.state_machine import State, StateMachine
from game.entities.walker import Walker
from game.level import Level, Door, distance, angle_to


class Standing(State):
    name = "STANDING"

    def update(self, o, dt):
        o.fade(dt)
        if o.hans_close:
            o.fsm.change(NODDING)
        elif o.wanders and o.fsm.time_in_state >= OWNER_STAND_TIME:
            o.fsm.change(WALKING)


class Nodding(State):
    name = "NODDING"

    def update(self, o, dt):
        if not o.hans_close:
            o.fsm.change(STANDING)
            return
        o.turn_toward(angle_to(o.pos, o.carrot.front), dt)
        if not o.hint_given:
            o.progress = min(1.0, o.progress + dt / HINT_TIME)
            if o.progress >= 1.0:
                o.hint_given = True
                o.events.append("hint")


class Walking(State):
    name = "WALKING"

    def enter(self, o):
        o.stop_i = (o.stop_i + 1) % len(o.stops)
        o.go_to(o.stops[o.stop_i])

    def update(self, o, dt):
        o.fade(dt)
        if o.walk(dt, OWNER_SPEED):
            o.fsm.change(STANDING)


STANDING, NODDING, WALKING = Standing(), Nodding(), Walking()


class Owner(Walker):
    def __init__(self, level: Level, carrot: Door):
        super().__init__(level, level.owner_stops[0])
        self.stops = level.owner_stops
        self.stop_i = 0
        self.carrot = carrot
        self.progress = 0.0         # 0..1: how much of the nod Hans has seen
        self.hint_given = False
        self.hans_close = False
        self.events: list[str] = []
        self.fsm = StateMachine(self, STANDING)

    @property
    def wanders(self) -> bool:
        return len(self.stops) > 1

    @property
    def state(self) -> str:
        return self.fsm.name

    @property
    def nodding(self) -> bool:
        return self.state == "NODDING"

    def fade(self, dt: float):
        if not self.hint_given:
            self.progress = max(0.0, self.progress - HINT_DECAY * dt)

    def update(self, dt: float, hans):
        self.hans_close = (distance(self.pos, hans.pos) <= HINT_RADIUS
                           and self.level.line_of_sight(self.pos, hans.pos))
        self.fsm.update(dt)

    def drain_events(self) -> list[str]:
        events, self.events = self.events, []
        return events
