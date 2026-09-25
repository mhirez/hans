"""One game: Hans, the courtyard, the waves of enemies, the items, the score.

Pure logic (no pygame): the scene passes in the controls each frame and draws the result.
"""

from dataclasses import dataclass
import math
import random

from game.config import (KICK_RADIUS, KICK_NOISE, CARROTS_ON_FIELD, ITEM_RADIUS, SUGAR_EVERY, HORSESHOE_EVERY,
                         COFFEE_EVERY, COFFEE_HEAL, CARROT_POINTS, KO_POINTS, WAVE_BONUS, LASSO_SPEED, LASSO_RANGE,
                         LASSO_SPREAD, DOG_RING, ENEMY_RADIUS, CRUNCH_NOISE)
from game.ai.dog import Dog
from game.ai.enemy import Enemy
from game.ai.perception import Noise
from game.ai.scientist import Scientist
from game.ai.stableboy import StableBoy
from game.arena import make_level
from game.entities.hans import Hans
from game.level import Point, center, distance, angle_to, tile_of
from game.waves import plan

KINDS = {"scientist": Scientist, "stableboy": StableBoy, "dog": Dog}
SPOT_SHOUT = {"dog": 12.0}               # a bark carries further than a shout
SHOUT_RADIUS = 7.0


@dataclass(eq=False)
class Item:
    kind: str                            # carrot, sugar, horseshoe, coffee
    pos: Point
    uid: int
    age: float = 0.0


@dataclass(eq=False)
class Lasso:
    thrower: StableBoy
    pos: Point
    vel: tuple[float, float]
    travelled: float = 0.0


@dataclass
class Popup:
    text: str
    pos: Point
    age: float = 0.0


class Match:
    def __init__(self, rng: random.Random, start_wave: int = 1):
        self.rng = rng
        self.score = 0
        self.knockouts = 0
        self.carrots_total = 0
        self.hans: Hans | None = None
        self.state = "playing"          # playing, cleared, over
        self.events: list[str] = []
        self.popups: list[Popup] = []
        self.toast = ""
        self.toast_time = 0.0
        self.hans_velocity = (0.0, 0.0)
        self._uid = 0
        self._seen_horseshoe = False
        self.start_wave(start_wave)

    # --- waves ---------------------------------------------------------------------------
    def start_wave(self, n: int):
        self.wave = plan(n, self.rng)
        self.level = make_level(n, self.rng)
        hearts = self.hans.hearts if self.hans else None
        self.hans = Hans(self.level.start)
        if hearts is not None:
            self.hans.hearts = hearts
        self.enemies: list[Enemy] = []
        self.items: list[Item] = []
        self.lassos: list[Lasso] = []
        self.queue = list(self.wave.enemies)
        self.clock = 0.0
        self.carrots = 0
        self.state = "playing"
        self.state_time = 0.0
        self.timers = {"sugar": SUGAR_EVERY * 0.6, "horseshoe": HORSESHOE_EVERY * (0.5 if n >= 4 else 1.0),
                       "coffee": COFFEE_EVERY * 0.5}
        for _ in range(CARROTS_ON_FIELD):
            self.spawn_item("carrot")

    @property
    def cups(self) -> list[Item]:
        return [i for i in self.items if i.kind == "coffee"]

    # --- the frame -----------------------------------------------------------------------
    def update(self, dt: float, move: tuple[float, float], gallop: bool, kick: bool):
        self.toast_time = max(0.0, self.toast_time - dt)
        for p in self.popups:
            p.age += dt
        self.popups = [p for p in self.popups if p.age < 1.0]
        self.state_time += dt
        if self.state == "cleared":
            if self.state_time > 2.5:
                self.start_wave(self.wave.number + 1)
            return
        if self.state == "over":
            return
        self.clock += dt

        before = self.hans.pos
        noises = self.hans.update(dt, move, gallop, self.level)
        self.hans_velocity = ((self.hans.pos[0] - before[0]) / dt, (self.hans.pos[1] - before[1]) / dt) if dt else (0, 0)
        if kick:
            self.kick()

        while self.queue and self.queue[0][0] <= self.clock:
            _, kind = self.queue.pop(0)
            self.spawn_enemy(kind)

        for e in self.enemies:
            e.update(dt, self)
            for ev in e.drain_events():
                self.events.append(f"{e.kind}:{ev}")
        self._separate()
        for noise in noises:
            for e in self.enemies:
                e.hear(noise)
        self._lassos(dt)
        self._golden_touch()
        self._pickups()
        self._top_up_carrots()
        self._spawn_timers(dt)
        for e in self.enemies:
            if e.gone:
                self.events.append("carried_off")
        self.enemies = [e for e in self.enemies if not e.gone]

        if not self.hans.alive:
            self.state, self.state_time = "over", 0.0
            self.events.append("game_over")
        elif self.carrots >= self.wave.carrots:
            bonus = WAVE_BONUS * self.wave.number
            self.score += bonus
            self.state, self.state_time = "cleared", 0.0
            self.events.append("wave_clear")
            self.say(f"Wave {self.wave.number} cleared!  +{bonus}")

    # --- Hans's actions ------------------------------------------------------------------
    def kick(self) -> int:
        """Buck! Everyone within reach is knocked flying. Returns how many were hit."""
        if not self.hans.can_kick():
            return 0
        self.hans.start_kick()
        self.events.append("kick")
        hits = 0
        for e in self.enemies:
            if e.state != "KO" and distance(e.pos, self.hans.pos) <= KICK_RADIUS:
                hits += 1
                if e.kicked(self.hans.pos):
                    self._knocked_out(e)
        noise = Noise(self.hans.pos, KICK_NOISE)
        for e in self.enemies:
            e.hear(noise)
        return hits

    def _knocked_out(self, e: Enemy):
        self.score += KO_POINTS
        self.knockouts += 1
        self.popups.append(Popup(f"+{KO_POINTS}", e.pos))
        self.events.append("ko")

    def _golden_touch(self):
        if not self.hans.powered:
            return
        for e in self.enemies:
            if e.state != "KO" and distance(e.pos, self.hans.pos) < 0.8:
                e.knock_out()
                self._knocked_out(e)

    # --- what the enemies call -----------------------------------------------------------
    def hit_hans(self, enemy: Enemy, how: str):
        if self.hans.hurt():
            self.events.append("hurt")
            a = angle_to(enemy.pos, self.hans.pos)
            self.hans.knock = (math.cos(a) * 6, math.sin(a) * 6)
            self.say({"net": "Netted! Get away!", "bite": "Bitten!"}.get(how, "Ouch!"))

    def throw_lasso(self, thrower: StableBoy, aim: Point):
        a = angle_to(thrower.pos, aim) + self.rng.uniform(-LASSO_SPREAD, LASSO_SPREAD)
        self.lassos.append(Lasso(thrower, thrower.pos, (math.cos(a) * LASSO_SPEED, math.sin(a) * LASSO_SPEED)))
        self.events.append("throw")

    def drink(self, cup: Item, enemy: Enemy):
        if cup in self.items:
            self.items.remove(cup)
            enemy.hp = min(enemy.max_hp, enemy.hp + COFFEE_HEAL)
            self.events.append("slurp")
            self.popups.append(Popup("+1", enemy.pos))

    def on_spotted(self, enemy: Enemy):
        """A shout (or a bark) alerts others nearby; dogs alert the whole pack."""
        self.events.append("bark" if enemy.kind == "dog" else "shout")
        radius = SPOT_SHOUT.get(enemy.kind, SHOUT_RADIUS)
        for other in self.enemies:
            if other is not enemy and not other.aware and other.state != "KO" and \
                    distance(other.pos, enemy.pos) <= radius and (enemy.kind != "dog" or other.kind == "dog"):
                other.last_seen, other.unseen = self.hans.pos, 0.0
                other.spot(shout=False)

    def pack_slot(self, dog: Dog) -> Point:
        """Share a ring around Hans between the hunting dogs, starting from where the pack is."""
        pack = sorted((d for d in self.enemies if isinstance(d, Dog) and d.aware and d.state in
                       ("SURROUND", "POUNCE", "RETREAT")), key=lambda d: d.uid)
        if dog not in pack:
            pack.append(dog)
        hx, hy = self.hans.pos
        mx = sum(d.pos[0] for d in pack) / len(pack)
        my = sum(d.pos[1] for d in pack) / len(pack)
        base = math.atan2(my - hy, mx - hx)
        i = pack.index(dog)
        spread = 2 * math.pi / len(pack) if len(pack) > 1 else 0
        a = base + (i - (len(pack) - 1) / 2) * spread
        spot = (hx + math.cos(a) * DOG_RING, hy + math.sin(a) * DOG_RING)
        tile = self.level.nearest_walkable(tile_of(spot))
        return spot if self.level.walkable(*tile_of(spot)) else center(tile)

    # --- spawning ------------------------------------------------------------------------
    def next_uid(self) -> int:
        self._uid += 1
        return self._uid

    def spawn_enemy(self, kind: str):
        gate = self.rng.choice(sorted(self.level.waypoints))
        e = KINDS[kind](self.level, self.level.waypoints[gate], self.next_uid(), self.rng, self.wave.speed)
        e.world = self
        e.target = self.hans.pos                 # they come in having heard where he is
        e.fsm.handle(("noise", self.hans.pos))
        self.enemies.append(e)
        self.events.append("door")

    def spawn_item(self, kind: str) -> Item | None:
        for _ in range(60):
            c = self.rng.randrange(1, self.level.cols - 1)
            r = self.rng.randrange(1, self.level.rows - 1)
            p = center((c, r))
            if not self.level.walkable(c, r) or distance(p, self.hans.pos) < 4:
                continue
            if any(distance(p, i.pos) < 3 for i in self.items):
                continue
            if self.level.route(tile_of(self.hans.pos), (c, r)).path is None:
                continue
            item = Item(kind, p, self.next_uid())
            self.items.append(item)
            return item
        return None

    def _spawn_timers(self, dt: float):
        for kind, every in (("sugar", SUGAR_EVERY), ("horseshoe", HORSESHOE_EVERY), ("coffee", COFFEE_EVERY)):
            self.timers[kind] -= dt
            if self.timers[kind] <= 0:
                self.timers[kind] = every * self.rng.uniform(0.8, 1.2)
                if not any(i.kind == kind for i in self.items) and (kind != "sugar" or self.hans.hearts < 3):
                    item = self.spawn_item(kind)
                    if item and kind == "horseshoe" and not self._seen_horseshoe:
                        self._seen_horseshoe = True
                        self.say("A golden horseshoe! Grab it and THEY run from YOU.")

    def _pickups(self):
        for item in list(self.items):
            if item.kind == "coffee" or distance(item.pos, self.hans.pos) > ITEM_RADIUS + 0.3:
                continue
            self.items.remove(item)
            if item.kind == "carrot":
                self.carrots += 1
                self.carrots_total += 1
                self.score += CARROT_POINTS
                self.popups.append(Popup(f"+{CARROT_POINTS}", item.pos))
                self.events.append("crunch")
                crunch = Noise(item.pos, CRUNCH_NOISE)
                for e in self.enemies:
                    e.hear(crunch)
            elif item.kind == "sugar":
                self.hans.heal()
                self.events.append("heal")
                self.popups.append(Popup("+heart", item.pos))
            elif item.kind == "horseshoe":
                self.hans.power_up()
                self.events.append("power")
                self.say("GOLDEN HANS! Now they run from you!")

    def _top_up_carrots(self):
        """Keep enough carrots on the field to finish the wave (retries if a spawn ever fails)."""
        on_field = sum(1 for i in self.items if i.kind == "carrot")
        want = min(CARROTS_ON_FIELD, self.wave.carrots - self.carrots)
        if on_field < want:
            self.spawn_item("carrot")

    def _lassos(self, dt: float):
        for lasso in list(self.lassos):
            step = (lasso.vel[0] * dt, lasso.vel[1] * dt)
            lasso.pos = (lasso.pos[0] + step[0], lasso.pos[1] + step[1])
            lasso.travelled += math.hypot(*step)
            if distance(lasso.pos, self.hans.pos) < 0.55:
                self.lassos.remove(lasso)
                if not self.hans.powered:
                    self.hans.tangle()
                    self.events.append("tangled")
                    self.say("Lassoed! You're slowed down.")
            elif lasso.travelled > LASSO_RANGE or self.level.blocks_sight(*tile_of(lasso.pos)):
                self.lassos.remove(lasso)

    def _separate(self):
        """Keep enemies from standing inside each other."""
        live = [e for e in self.enemies if e.state != "KO"]
        for i, a in enumerate(live):
            for b in live[i + 1:]:
                d = distance(a.pos, b.pos)
                if 0 < d < ENEMY_RADIUS * 2:
                    push = (ENEMY_RADIUS * 2 - d) / 2
                    ang = angle_to(b.pos, a.pos)
                    a.slide(math.cos(ang) * push, math.sin(ang) * push)
                    b.slide(-math.cos(ang) * push, -math.sin(ang) * push)

    def say(self, text: str):
        self.toast, self.toast_time = text, 2.6

    def drain_events(self) -> list[str]:
        events, self.events = self.events, []
        return events
