"""The guard dog: a pack hunter. One dog's bark brings the whole pack.

    SURROUND  each dog takes its own place on a ring around Hans (the pack shares the ring out
              evenly, starting from the side they're coming from), runs there       -> POUNCE
    POUNCE    crouches (your cue), then leaps in a straight line; a bite costs a heart -> RETREAT
    RETREAT   backs off for a moment                                                   -> SURROUND

So the pack closes in from several sides at once, and you have to keep moving or kick.
Dogs have a third sense: SMELL. Within DOG_SMELL tiles they find Hans even behind a hay bale,
and a wandering dog usually heads off along his scent. They never go for coffee.
"""

import math

from game.config import (DOG_HP, DOG_WANDER, DOG_RUN, DOG_POUNCE_WINDUP, DOG_POUNCE_SPEED,
                         DOG_POUNCE_DISTANCE, DOG_RETREAT_TIME, REPLAN_TIME, DOG_SMELL, DOG_TRACKING)
from game.ai.enemy import Enemy
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


SURROUND, POUNCE, RETREAT = Surround(), Pounce(), Retreat()


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

    def attack_state(self):
        return SURROUND

    def perceive(self, dt: float):
        super().perceive(dt)
        hans = self.world.hans
        if not self.aware and self.state != "KO" and distance(self.pos, hans.pos) <= DOG_SMELL:
            self.last_seen, self.unseen = hans.pos, 0.0
            self.spot()

    def pick_wander_spot(self):
        """Nose to the ground: usually wander toward where the horse's scent comes from."""
        if self.world is not None and self.rng.random() < DOG_TRACKING:
            hx, hy = self.world.hans.pos
            for _ in range(10):
                c, r = int(hx) + self.rng.randint(-4, 4), int(hy) + self.rng.randint(-4, 4)
                if self.level.walkable(c, r) and self.go_to((c + 0.5, r + 0.5)):
                    return
        super().pick_wander_spot()
