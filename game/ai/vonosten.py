"""Wilhelm von Osten: Hans's owner and your AI companion (the lecturer's "Companion AI" idea).

He believed in Hans to the end. He follows you, acts by himself, and takes two commands.

    FOLLOW    keeps a couple of tiles behind Hans (A*), watching his back
    PROTECT   a scientist is winding up his net at Hans and von Osten is close enough: he runs in and
              grabs the net ("Unhand my horse!"). Then he's out of breath for a while.
              A dog growling to pounce gets a stern "Down, boy!" from a few tiles away instead.
    POINT     a sugar cube or golden horseshoe that Hans isn't heading for: he walks toward it and
              NODS at it. That involuntary nod is the real history: it's how Hans "knew" the answers.
    DISTRACT  (press E) marches up to the nearest scientist and lectures him; the scientist is stuck
              arguing for a few seconds
    STAY      (press Q) waits where he is; Q again and he follows

Choosing between FOLLOW, PROTECT and POINT is a small utility system, re-scored 4 times a second:

    protect = 1.5  if an attack on Hans (net or pounce) is winding up within his reach and he isn't winded
    point   = worth of the item (sugar is worth more when Hans is hurt), if Hans isn't going for it
    follow  = 0.3

He also shouts "Behind you, Hans!" when an attack winds up behind Hans. Nobody can catch him.
"""

import math

from game.config import HEARTS, REPLAN_TIME
from game.ai.state_machine import State, StateMachine
from game.entities.walker import Walker
from game.level import Point, distance

WALK = 3.9
SPRINT = 5.4
WINDED = 8.0
HOARSE = 5.0                 # after shouting a dog down
SHOUT = 3.0                  # a dog hears "Down, boy!" from this far
WARN_EVERY = 4.0
DISTRACT_COOLDOWN = 12.0
DECIDE_EVERY = 0.25
ATTACKS = ("SWING", "READ", "POUNCE", "THROW")


def winding_up(e) -> bool:
    """A net or a pounce about to come down on Hans (the moment von Osten can still stop it)."""
    if e.state in ("SWING", "READ"):
        return not getattr(e, "swung", True)
    return e.state == "POUNCE" and getattr(e, "leap", 0) is None


class Follow(State):
    name = "FOLLOW"

    def enter(self, v):
        v.replan = 0.0

    def update(self, v, dt):
        hans = v.world.hans
        spot = (hans.pos[0] - hans.facing * 1.8, hans.pos[1] + 0.4)
        if distance(v.pos, hans.pos) > 2.8:
            v.replan -= dt
            if v.replan <= 0:
                v.go_to(spot)
                v.replan = REPLAN_TIME * 2
            v.walk(dt, WALK)
        else:
            v.path = []
            v.face(hans.pos, dt)
        v.every(dt)


class Stay(State):
    name = "STAY"

    def update(self, v, dt):
        v.face(v.world.hans.pos, dt)
        v.every(dt)


class Protect(State):
    name = "PROTECT"

    def enter(self, v):
        v.events.append("protect")
        v.replan = 0.0

    def update(self, v, dt):
        foe = v.foe
        if foe is None or not winding_up(foe):
            v.back()
            return
        if foe.kind == "dog" and distance(v.pos, foe.pos) < SHOUT:
            foe.grappled()                               # "Down, boy!": the dog flinches
            v.events.append("shoo")
            v.winded = HOARSE
            v.back()
            return
        if distance(v.pos, foe.pos) < 1.0:
            foe.grappled()
            v.winded = WINDED
            v.back()
            return
        v.steer(foe.pos, dt, SPRINT)


class Point_(State):
    name = "POINT"

    def enter(self, v):
        v.timer = 0.0
        v.nod_time = 0.0
        v.events.append("point")
        v.pointed.add(v.item.uid)
        v.go_to(v.item.pos)

    def update(self, v, dt):
        item = v.item
        v.timer += dt                                   # walking there (gives up after 10 s)
        if v.nodding:
            v.nod_time += dt                            # then nods for 4 s
        if (item not in v.world.items or v.timer > 10 or v.nod_time > 4.0
                or distance(v.world.hans.pos, item.pos) < 1.2):
            v.back()
            return
        if distance(v.pos, item.pos) > 2.2:
            v.walk(dt, WALK)
        else:
            v.path = []
            v.face(item.pos, dt)
        v.nodding = distance(v.pos, item.pos) < 3.5


class Distract(State):
    name = "DISTRACT"

    def enter(self, v):
        v.timer = 0.0
        v.replan = 0.0
        v.arguing = False

    def update(self, v, dt):
        foe = v.foe
        v.timer += dt
        if foe is None or foe.state == "KO" or v.timer > 8:
            v.back()
            return
        if not v.arguing:
            v.replan -= dt
            if v.replan <= 0:
                v.go_to(foe.pos)
                v.replan = REPLAN_TIME
            v.walk(dt, SPRINT)
            if distance(v.pos, foe.pos) < 1.3:
                v.arguing = True
                v.timer = 0.0
                v.events.append("distract")
                foe.distract(v)
        else:
            v.face(foe.pos, dt)
            if v.timer > 3.5:
                v.back()


FOLLOW, STAY, PROTECT, POINT, DISTRACT = Follow(), Stay(), Protect(), Point_(), Distract()


class VonOsten(Walker):
    kind = "vonosten"
    uid = 0
    gone = False

    def __init__(self, level, pos: Point):
        super().__init__(level, pos)
        self.world = None
        self.staying = False
        self.winded = 0.0
        self.distract_cooldown = 0.0
        self.foe = None
        self.item = None
        self.pointed: set[int] = set()
        self.nodding = False
        self.arguing = False
        self.replan = 0.0
        self.timer = 0.0
        self.nod_time = 0.0
        self.decide_timer = 0.0
        self.warned: set[int] = set()
        self.warn_cooldown = 0.0
        self.scores: dict[str, float] = {}
        self.foe_candidate = None
        self.item_candidate = None
        self.events: list[str] = []
        self.fsm = StateMachine(self, FOLLOW)

    @property
    def state(self) -> str:
        return self.fsm.name

    # --- commands ------------------------------------------------------------------------
    def toggle_stay(self):
        self.staying = not self.staying
        self.events.append("stay" if self.staying else "follow")
        self.fsm.change(STAY if self.staying else FOLLOW)

    def order_distract(self) -> bool:
        if self.distract_cooldown > 0:
            return False
        foes = [e for e in self.world.enemies if e.kind != "dog" and e.state not in ("KO", "DISTRACTED")
                and distance(e.pos, self.pos) < 14]
        if not foes:
            self.events.append("nobody")
            return False
        self.foe = min(foes, key=lambda e: distance(e.pos, self.pos))
        self.distract_cooldown = DISTRACT_COOLDOWN
        self.fsm.change(DISTRACT)
        return True

    # --- thinking ------------------------------------------------------------------------
    def utilities(self) -> dict[str, float]:
        world, hans = self.world, self.world.hans
        scores = {"follow": 0.3}
        threats = [e for e in world.enemies if winding_up(e) and distance(e.pos, hans.pos) < 4.0
                   and distance(e.pos, self.pos) < (SHOUT + 1.0 if e.kind == "dog" else 3.2)]
        scores["protect"] = 1.5 if threats and self.winded <= 0 else 0.0
        self.foe_candidate = min(threats, key=lambda e: distance(e.pos, self.pos)) if threats else None
        best_item, best_value = None, 0.0
        goal = getattr(world.tactics, "goal", None)
        for item in world.items:
            if item.kind not in ("sugar", "horseshoe") or item.uid in self.pointed or item is goal:
                continue
            if distance(hans.pos, item.pos) < 3:
                continue
            value = 0.8 if item.kind == "horseshoe" else (1.0 if hans.hearts < HEARTS else 0.2)
            if value > best_value:
                best_item, best_value = item, value
        scores["point"] = best_value * 0.9
        self.item_candidate = best_item
        return scores

    def every(self, dt: float):
        self.decide_timer += dt
        if self.decide_timer < DECIDE_EVERY:
            return
        self.decide_timer = 0.0
        self.scores = self.utilities()
        best = max(self.scores, key=self.scores.get)
        if best == "protect":
            self.foe = self.foe_candidate
            self.fsm.change(PROTECT)
        elif best == "point" and not self.staying:
            self.item = self.item_candidate
            self.fsm.change(POINT)

    def back(self):
        self.nodding = False
        self.arguing = False
        self.fsm.change(STAY if self.staying else FOLLOW)

    def watch_hans_back(self):
        """Shout a warning when an attack winds up behind Hans."""
        hans = self.world.hans
        for e in self.world.enemies:
            if e.state in ATTACKS and e.uid not in self.warned:
                self.warned.add(e.uid)
                behind = (e.pos[0] - hans.pos[0]) * hans.facing < 0
                if behind and distance(e.pos, hans.pos) < 4 and self.warn_cooldown <= 0:
                    self.events.append("warn")
                    self.warn_cooldown = WARN_EVERY
            elif e.state not in ATTACKS:
                self.warned.discard(e.uid)

    def update(self, dt: float, world):
        self.world = world
        self.moved = False
        self.winded = max(0.0, self.winded - dt)
        self.distract_cooldown = max(0.0, self.distract_cooldown - dt)
        self.warn_cooldown = max(0.0, self.warn_cooldown - dt)
        if self.state not in ("POINT",):
            self.nodding = False
        self.watch_hans_back()
        self.fsm.update(dt)

    def drain_events(self) -> list[str]:
        events, self.events = self.events, []
        return events

    def point_line(self):
        """The nod: from his head to the item he's nodding at."""
        return (self.pos, self.item.pos) if self.nodding and self.item is not None else None

    def lean(self, t: float) -> float:
        if self.nodding and self.item is not None:
            side = 1 if self.item.pos[0] > self.pos[0] else -1
            return side * (0.5 + 0.5 * math.sin(t * 9))
        if self.arguing:
            return math.sin(t * 12) * 0.6
        if self.state == "PROTECT":
            return 1 if self.foe and self.foe.pos[0] > self.pos[0] else -1
        return 0.0
