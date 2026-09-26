"""The guard dog: a pack hunter. One dog's bark brings the whole pack.

    SURROUND  each dog takes its own place on a ring around Hans (the pack shares the ring out
              evenly, starting from the side they're coming from), runs there       -> POUNCE
    POUNCE    crouches (your cue), then leaps in a straight line; a bite costs a heart -> RETREAT
    RETREAT   backs off for a moment                                                   -> SURROUND

So the pack closes in from several sides at once, and you have to keep moving or kick.
Dogs have a third sense: SMELL. Within DOG_SMELL tiles they find Hans even behind a hay bale.
Further away they TRACK him: Hans leaves hoofprints, and a dog that finds fresh ones follows
the trail from print to fresher print, nose down, until the scent is strong enough to spot him.
They never go for coffee.
"""

import math

from game.config import (DOG_HP, DOG_WANDER, DOG_RUN, DOG_POUNCE_WINDUP, DOG_POUNCE_SPEED,
                         DOG_POUNCE_DISTANCE, DOG_RETREAT_TIME, REPLAN_TIME, DOG_SMELL, PRINT_SNIFF, PRINT_FRESH)
from game.ai.enemy import Enemy, WANDER as WANDER_STATE
from game.ai.state_machine import State
from game.level import distance, angle_to


class Surround(State):
    name = "SURROUND"

    def enter(self, d):
        d.replan = 0.0

    def update(self, d, dt):
        if d.lost_him():
            return
        hans = d.world.hans
        slot = d.world.pack_slot(d)
        d.slot = slot
        if d.level.line_of_sight(d.pos, slot) and distance(d.pos, slot) < 5:
            d.path = []
            there = d.steer(slot, dt, d.run_speed * d.scale)
        else:
            d.replan -= dt
            if d.replan <= 0:
                d.go_to(slot)
                d.replan = REPLAN_TIME
            there = d.walk(dt, d.run_speed * d.scale) and distance(d.pos, slot) < 1.0
        d.cooldown -= dt
        if (there or distance(d.pos, slot) < 0.8) and d.cooldown <= 0 and d.sees_hans:
            d.fsm.change(POUNCE)
            return
        if distance(d.pos, hans.pos) < 3:
            d.face(hans.pos, dt)
        d.every(dt, lambda: d.decide() != "attack" and d.act())


class Pounce(State):
    name = "POUNCE"

    def enter(self, d):
        d.timer = 0.0
        d.leap = None
        d.path = []
        d.events.append("growl")

    def update(self, d, dt):
        hans = d.world.hans
        d.timer += dt
        if d.leap is None:
            d.face(hans.pos, dt)
            if d.timer >= d.windup(DOG_POUNCE_WINDUP):
                a = angle_to(d.pos, hans.pos)
                d.leap = (math.cos(a), math.sin(a))
                d.leaped = 0.0
                d.events.append("bark")
            return
        step = DOG_POUNCE_SPEED * dt
        before = d.pos
        d.slide(d.leap[0] * step, d.leap[1] * step)
        d.leaped += step
        d.moved = True
        if distance(d.pos, hans.pos) < 0.6:
            d.world.hit_hans(d, "bite")
            d.fsm.change(RETREAT)
        elif d.leaped >= DOG_POUNCE_DISTANCE or distance(before, d.pos) < step * 0.3:
            d.fsm.change(RETREAT)

    @staticmethod
    def progress(d) -> float:
        return min(1.0, d.timer / d.windup(DOG_POUNCE_WINDUP)) if d.leap is None else 0.0


class Retreat(State):
    name = "RETREAT"

    def enter(self, d):
        d.timer = 0.0
        d.cooldown = 1.0

    def update(self, d, dt):
        hans = d.world.hans
        d.timer += dt
        a = angle_to(hans.pos, d.pos)
        d.steer((d.pos[0] + math.cos(a), d.pos[1] + math.sin(a)), dt, d.run_speed * d.scale * 0.8)
        if d.timer >= DOG_RETREAT_TIME:
            d.act(force=True)


class Track(State):
    """Nose to the ground: follow the hoofprints toward fresher and fresher ones."""
    name = "TRACK"

    def enter(self, d):
        d.events.append("sniff")
        d.scent_age = 99.0

    def update(self, d, dt):
        if d.aware:
            d.act()
            return
        prints = [p for p in d.world.prints if distance(p.pos, d.pos) <= PRINT_SNIFF and p.age < d.scent_age]
        if prints:
            nxt = min(prints, key=lambda p: p.age)             # the freshest print in reach
            d.scent_age = nxt.age
            d.trail_to = nxt.pos
        if d.trail_to is None or d.steer(d.trail_to, dt, d.wander_speed * d.scale * 1.3):
            if not prints:
                d.trail_to = None
                d.fsm.change(WANDER_STATE)


SURROUND, POUNCE, RETREAT, TRACK = Surround(), Pounce(), Retreat(), Track()


class Dog(Enemy):
    kind = "dog"
    max_hp = DOG_HP
    aggression = 1.1
    cowardice = 0.3
    can_heal = False
    wander_speed = DOG_WANDER
    run_speed = DOG_RUN

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cooldown = 0.0
        self.slot = self.pos
        self.leap = None
        self.leaped = 0.0
        self.trail_to = None
        self.scent_age = 99.0

    def attack_state(self):
        return SURROUND

    def perceive(self, dt: float):
        super().perceive(dt)
        hans = self.world.hans
        if not self.aware and self.state != "KO" and distance(self.pos, hans.pos) <= DOG_SMELL:
            self.last_seen, self.unseen = hans.pos, 0.0
            self.spot()

    def follow_trail(self) -> bool:
        """While wandering: any fresh hoofprints nearby? Then start tracking."""
        if any(distance(p.pos, self.pos) <= PRINT_SNIFF and p.age < PRINT_FRESH for p in self.world.prints):
            self.fsm.change(TRACK)
            return True
        return False
