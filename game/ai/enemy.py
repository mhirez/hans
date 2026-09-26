"""What every enemy shares: senses, memory, being kicked, and the states that aren't about attacking.

Shared states (each enemy type adds its own attack states on top):

    WANDER       strolls between random spots             notices Hans -> decides (desire.py)
                                                           hears a noise -> INVESTIGATE
                                                           (dogs) finds fresh hoofprints -> TRACK
    GUARD        (the Commission's GUARD tactic) stands    notices Hans -> decides
                 watch beside a carrot
    DISTRACTED   von Osten is arguing with him             after a while -> decides
    (in these three calm states a glimpse of Hans makes him stop and turn to look: a "double take",
     shown as "?", until he's sure (-> decides) or the glimpse fades)
    INVESTIGATE  walks (A*) to a noise, looks around       notices Hans -> decides;  done -> WANDER
    SEARCH       lost Hans: goes to where he last saw      finds him -> decides;  gives up -> WANDER
                 him and looks around (with the SWEEP
                 tactic: then checks behind nearby hay)
    STUNNED      knocked flying by a kick, seeing stars    recovers -> decides (knows where Hans is)
    FLEE         runs to the spot furthest from Hans       the reason passes -> decides
    HEAL         walks (A*) to a coffee cup he has SEEN    drinks (+1 health) -> decides
    KO           out cold; carried off                     (removed)

"Decides" means: score attack / flee / heal / cover with desire.py and switch to the winner.
While attacking, every enemy re-decides twice a second, so a scientist you've kicked once
can break off his chase to go and drink a coffee he noticed.

State changes also post events ("lost", "heal", "flank"...) that barks.py turns into speech
bubbles, so the player can see each decision being made.
"""

import math
import random

from game.config import (VIEW_RANGE, VIEW_HALF_ANGLE, NOTICE_TIME, MEMORY_TIME, STUN_TIME, SEARCH_TIME,
                         KICK_KNOCKBACK)
from game.ai.desire import desires, best
from game.ai.perception import Noise, sees, hears
from game.ai.state_machine import State, StateMachine
from game.entities.walker import Walker
from game.level import Level, Point, center, distance, angle_to

DECIDE_EVERY = 0.5


# --- shared states ---------------------------------------------------------------------
class Wander(State):
    name = "WANDER"

    def enter(self, e):
        e.pause = 0.0
        e.pick_wander_spot()

    def update(self, e, dt):
        if e.aware:
            e.act()
            return
        if e.double_take(dt):
            return
        if e.guard:
            e.fsm.change(GUARD)
            return
        if e.follow_trail():
            return
        if e.pause > 0:
            e.pause -= dt
            e.turn_toward(e.look_base + math.sin(e.pause * 3) * 0.8, dt)
            if e.pause <= 0:
                e.pick_wander_spot()
        elif e.walk(dt, e.wander_speed * e.scale):
            e.pause = e.rng.uniform(0.4, 1.4)
            e.look_base = e.angle

    def on_event(self, e, event) -> bool:
        return e.investigate(event)


class Investigate(State):
    name = "INVESTIGATE"

    def enter(self, e):
        e.events.append("hear")
        e.looking = 0.0 if not e.go_to(e.target) else -1.0

    def update(self, e, dt):
        if e.aware:
            e.act()
            return
        if e.double_take(dt):
            return
        if e.looking < 0:
            if e.walk(dt, e.run_speed * e.scale * 0.8):
                e.looking, e.look_base = 0.0, e.angle
            return
        e.looking += dt
        e.turn_toward(e.look_base + math.sin(e.looking * 2.5) * 1.8, dt)
        if e.looking > SEARCH_TIME:
            e.give_up()

    def on_event(self, e, event) -> bool:
        return e.investigate(event)


class Search(State):
    name = "SEARCH"

    def enter(self, e):
        e.aware = False
        e.target = e.last_seen or e.pos
        e.events.append("lost")
        e.sweep = e.hiding_spots(e.target) if e.tactic("sweep") else []
        e.looking = 0.0 if not e.go_to(e.target) else -1.0

    def update(self, e, dt):
        if e.aware:
            e.act()
            return
        if e.double_take(dt):
            return
        if e.looking < 0:
            if e.walk(dt, e.run_speed * e.scale):
                e.looking, e.look_base = 0.0, e.angle
            return
        e.looking += dt
        e.turn_toward(e.look_base + math.sin(e.looking * 2.5) * 1.8, dt)
        if e.sweep and e.looking > 1.0:            # SWEEP: next hiding place behind the hay
            if e.looking < 1.1:
                e.events.append("sweep")
            e.looking = 0.0 if not e.go_to(e.sweep.pop(0)) else -1.0
        elif e.looking > SEARCH_TIME:
            e.give_up()

    def on_event(self, e, event) -> bool:
        return e.investigate(event)


class Stunned(State):
    name = "STUNNED"

    def enter(self, e):
        e.stun = STUN_TIME
        e.path = []

    def update(self, e, dt):
        e.stun -= dt
        if e.stun <= 0:
            e.aware = True                 # after a kick you know exactly where the horse is
            e.last_seen = e.world.hans.pos
            e.unseen = 0.0
            e.act(force=True)


class Flee(State):
    name = "FLEE"

    def enter(self, e):
        e.timer = 0.0
        e.events.append("flee" if e.world.hans.powered or getattr(e.world, "morale", 1.0) > 0.75 else "morale")
        e.pick_escape()

    def update(self, e, dt):
        e.timer += dt
        if e.walk(dt, e.run_speed * e.scale) or e.timer > 0.8:
            e.timer = 0.0
            if e.decide() != "flee":
                e.act()
                return
            e.pick_escape()


class Heal(State):
    name = "HEAL"

    def enter(self, e):
        cup = e.known_coffee(e.world)
        e.cup = cup
        e.events.append("heal")
        if cup is None or not e.go_to(cup.pos):
            e.act(force=True)

    def update(self, e, dt):
        cup = e.cup
        if cup is None or cup not in e.world.items:
            e.act(force=True)
            return
        if e.walk(dt, e.run_speed * e.scale) or distance(e.pos, cup.pos) < 0.7:
            e.world.drink(cup, e)
            e.act(force=True)
            return
        e.every(dt, lambda: e.decide() != "heal" and e.act())


class Guard(State):
    """The GUARD tactic: stand beside a carrot, lantern-sweeping the approach, until Hans shows up."""
    name = "GUARD"

    def enter(self, e):
        e.events.append("guard")
        e.post = None

    def update(self, e, dt):
        if e.aware:
            e.act()
            return
        if e.double_take(dt):
            return
        carrots = [i for i in e.world.items if i.kind == "carrot"]
        if not carrots:
            return
        carrot = min(carrots, key=lambda c: distance(c.pos, e.pos))
        if e.post is None or distance(e.post, carrot.pos) > 2.0:
            e.post = e.guard_post(carrot.pos)
            e.go_to(e.post)
        if e.walk(dt, e.run_speed * e.scale * 0.8):
            e.turn_toward(angle_to(carrot.pos, e.pos) + math.sin(e.fsm.time_in_state * 0.9) * 1.3, dt)

    def on_event(self, e, event) -> bool:
        return e.investigate(event)


class Distracted(State):
    """Von Osten has buttonholed him about the scientific method. He can't get away."""
    name = "DISTRACTED"

    def enter(self, e):
        e.path = []
        e.timer = 0.0
        e.events.append("distracted")

    def update(self, e, dt):
        e.timer += dt
        if e.distracted_by is not None:
            e.face(e.distracted_by.pos, dt)
        if e.timer > 3.5:
            e.distracted_by = None
            e.act(force=True)


class KnockedOut(State):
    name = "KO"

    def enter(self, e):
        e.path = []
        e.timer = 0.0

    def update(self, e, dt):
        e.timer += dt
        if e.timer > 1.4:
            e.gone = True


WANDER, INVESTIGATE, SEARCH, STUNNED, FLEE, HEAL, GUARD, DISTRACTED, KO = (
    Wander(), Investigate(), Search(), Stunned(), Flee(), Heal(), Guard(), Distracted(), KnockedOut())


class Enemy(Walker):
    kind = "enemy"
    max_hp = 1
    aggression = 1.0
    cowardice = 0.5
    can_heal = True
    can_hide = False
    wander_speed = 1.6
    run_speed = 3.0

    def __init__(self, level: Level, pos: Point, uid: int, rng: random.Random, scale: float = 1.0):
        super().__init__(level, pos)
        self.uid = uid
        self.rng = rng
        self.scale = scale                 # waves make them a little quicker
        self.hp = self.max_hp
        self.aware = False
        self.notice = 0.0                  # 0..1: how sure he is that he's seen the horse
        self.sees_hans = False
        self.last_seen: Point | None = None
        self.unseen = 0.0
        self.knockback = (0.0, 0.0)
        self.stun = 0.0
        self.target: Point | None = None
        self.pause = 0.0
        self.look_base = self.angle
        self.looking = 0.0
        self.timer = 0.0
        self.decide_timer = 0.0
        self.plan = "attack"
        self.scores: dict[str, float] = {}
        self.known_cups: set[int] = set()
        self.cup = None
        self.guard = False                 # the Commission's GUARD tactic picked him
        self.post = None
        self.sweep: list[Point] = []
        self.chase_mode = None             # "flank" / "intercept" while chasing, for barks
        self.role: str | None = None       # given by the Commission's field command (tactics.py)
        self.distracted_by = None
        self.gone = False
        self.world = None
        self.events: list[str] = []
        self.fsm = StateMachine(self, WANDER)

    # --- identity ------------------------------------------------------------------------
    @property
    def state(self) -> str:
        return self.fsm.name

    def attack_state(self) -> State:
        raise NotImplementedError

    def cover_state(self) -> State | None:
        return None

    @property
    def icon(self) -> str | None:
        if self.state in ("INVESTIGATE", "SEARCH") or (self.notice > 0 and not self.aware):
            return "?"
        if self.state == "STUNNED":
            return "stars"
        if self.state == "TRACK":
            return "nose"
        if self.state == "DISTRACTED":
            return "talk"
        if self.state == "OFF-BALANCE":
            return "?!"
        if self.state == "FLEE":
            return "!!"
        if self.state == "HEAL":
            return "cup"
        if self.state not in ("WANDER", "KO") and self.aware:
            return "!"
        return None

    # --- senses --------------------------------------------------------------------------
    def perceive(self, dt: float):
        world = self.world
        hans = world.hans
        d = sees(self.level, self.pos, self.angle, hans.pos, VIEW_RANGE, VIEW_HALF_ANGLE)
        self.sees_hans = d is not None and self.state != "KO"
        if self.sees_hans:
            self.last_seen = hans.pos
            self.unseen = 0.0
            if not self.aware:
                self.notice += dt / (NOTICE_TIME * (0.3 + 0.7 * d / VIEW_RANGE))
                if self.notice >= 1 or hans.galloping and d < 3:
                    self.spot()
        else:
            self.unseen += dt
            self.notice = max(0.0, self.notice - dt)
        for cup in world.cups:
            if cup.uid not in self.known_cups and sees(self.level, self.pos, self.angle, cup.pos, VIEW_RANGE,
                                                       VIEW_HALF_ANGLE) is not None:
                self.known_cups.add(cup.uid)

    def double_take(self, dt: float) -> bool:
        """Caught a glimpse? Stop and stare at it until sure. Returns True while doing so."""
        if self.notice <= 0:
            return False
        self.face(self.last_seen or self.world.hans.pos, dt)
        return True

    def spot(self, shout: bool = True):
        if self.aware:
            return
        self.aware = True
        self.notice = 1.0
        self.events.append("spotted")
        if shout:
            self.world.on_spotted(self)

    def hear(self, noise: Noise):
        if self.state == "KO" or not hears(self.pos, noise):
            return
        if self.aware:
            self.last_seen, self.unseen = noise.pos, 0.0
        else:
            self.fsm.handle(("noise", noise.pos))

    def known_coffee(self, world):
        cups = [c for c in world.cups if c.uid in self.known_cups]
        return min(cups, key=lambda c: distance(self.pos, c.pos)) if cups else None

    # --- deciding ------------------------------------------------------------------------
    def decide(self) -> str:
        self.scores = desires(self, self.world)
        self.plan = best(self.scores, self.plan)
        return self.plan

    def act(self, force: bool = False):
        """Switch to the state that carries out the best plan."""
        plan = self.decide()
        state = {"attack": self.attack_state(), "flee": FLEE, "heal": HEAL, "cover": self.cover_state()}[plan]
        if state is None:
            state = self.attack_state()
        if force or state is not self.fsm.current:
            self.fsm.change(state)

    def windup(self, base: float) -> float:
        """Attack wind-ups shorten as the waves speed up: early waves give you longer to react."""
        return base / self.scale

    def every(self, dt: float, fn):
        """Run fn twice a second: attack states use it to re-decide."""
        self.decide_timer += dt
        if self.decide_timer >= DECIDE_EVERY:
            self.decide_timer = 0.0
            fn()

    def lost_him(self) -> bool:
        """While attacking: has he been out of sight too long? Then go and search."""
        if self.last_seen is None or (not self.sees_hans and self.unseen > MEMORY_TIME):
            self.fsm.change(SEARCH)
            return True
        return False

    def tactic(self, name: str) -> bool:
        commission = getattr(self.world, "commission", None)
        return commission is not None and commission.has(name)

    def give_up(self):
        self.events.append("gave_up")
        self.fsm.change(GUARD if self.guard else WANDER)

    def follow_trail(self) -> bool:
        """Dogs override this to track hoofprints."""
        return False

    def hiding_spots(self, around: Point) -> list[Point]:
        """SWEEP: open tiles tucked behind tall cover near where Hans vanished, nearest first."""
        spots = []
        c0, r0 = int(around[0]), int(around[1])
        for r in range(r0 - 4, r0 + 5):
            for c in range(c0 - 4, c0 + 5):
                if not self.level.walkable(c, r):
                    continue
                p = center((c, r))
                beside_cover = any(self.level.at(c + dc, r + dr) in "hc" for dc in (-1, 0, 1) for dr in (-1, 0, 1))
                if beside_cover and not self.level.line_of_sight(around, p):
                    spots.append(p)
        spots.sort(key=lambda p: distance(p, around))
        return spots[:3]

    def guard_post(self, carrot: Point) -> Point:
        for dc, dr in ((1, 1), (-1, 1), (1, -1), (-1, -1), (1, 0), (-1, 0)):
            c, r = int(carrot[0]) + dc, int(carrot[1]) + dr
            if self.level.walkable(c, r):
                return center((c, r))
        return carrot

    def investigate(self, event) -> bool:
        kind, pos = event
        if kind == "noise":
            self.target = pos
            self.fsm.change(INVESTIGATE)
            return True
        return False

    # --- movement helpers ----------------------------------------------------------------
    def pick_wander_spot(self):
        for _ in range(20):
            c = int(self.pos[0]) + self.rng.randint(-6, 6)
            r = int(self.pos[1]) + self.rng.randint(-5, 5)
            if self.level.walkable(c, r) and self.go_to(center((c, r))):
                return
        self.path = []

    def pick_escape(self):
        hans = self.world.hans.pos
        best_spot, best_score = None, -math.inf
        for _ in range(24):
            c = int(self.pos[0]) + self.rng.randint(-8, 8)
            r = int(self.pos[1]) + self.rng.randint(-6, 6)
            if not self.level.walkable(c, r):
                continue
            p = center((c, r))
            score = distance(p, hans) - 0.4 * distance(p, self.pos) - (3 if distance(p, hans) < distance(self.pos, hans) else 0)
            if score > best_score:
                best_spot, best_score = p, score
        if best_spot is not None:
            self.go_to(best_spot)

    # --- being kicked --------------------------------------------------------------------
    def kicked(self, from_point: Point) -> bool:
        """Returns True if this kick knocked him out."""
        if self.state == "KO":
            return False
        a = angle_to(from_point, self.pos)
        self.knockback = (math.cos(a) * KICK_KNOCKBACK / 0.3, math.sin(a) * KICK_KNOCKBACK / 0.3)
        self.hp -= 1
        self.events.append("hit" if self.hp > 0 else "ko")
        self.fsm.change(KO if self.hp <= 0 else STUNNED)
        return self.hp <= 0

    def distract(self, by):
        if self.state not in ("KO", "STUNNED"):
            self.distracted_by = by
            self.fsm.change(DISTRACTED)

    def grappled(self):
        """Von Osten grabbed his net mid-swing."""
        if self.state != "KO":
            self.events.append("grappled")
            self.fsm.change(STUNNED)
            self.stun = 1.2

    def knock_out(self):
        if self.state != "KO":
            self.hp = 0
            self.fsm.change(KO)

    # --- tick ----------------------------------------------------------------------------
    def update(self, dt: float, world):
        self.world = world
        self.moved = False
        kx, ky = self.knockback
        if kx or ky:
            self.slide(kx * dt, ky * dt)
            self.knockback = (kx * 0.82, ky * 0.82) if math.hypot(kx, ky) > 0.4 else (0.0, 0.0)
        self.perceive(dt)
        self.fsm.update(dt)

    def drain_events(self) -> list[str]:
        events, self.events = self.events, []
        return events
