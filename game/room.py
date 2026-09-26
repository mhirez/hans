"""One room of the facility: the player, the enemies, bullets, pick-ups, and the rules.

The room is pure simulation (no drawing), so tests and the balancing bot can run it headless.
It reports what happened through two queues the game drains every frame:
    sounds  names of sound effects to play
    fx      visual effects: ("spark", pos, colour), ("burst", pos, colour, size), ("shake", k),
            ("stop", seconds), ("ring", pos, colour, radius), ("text", pos, text, colour),
            ("warp", pos), ("muzzle", pos, angle, colour)
"""

import math
import random

from game import config as C
from game.ai.charger import Charger
from game.ai.grunt import Grunt
from game.ai.medic import Medic
from game.ai.sniper import Sniper
from game.ai.tactics import Coordinator, TacticalMap
from game.ai.agent import ESCORT
from game.ai.warden import Warden
from game.geometry import Point, add, angle_to, center, distance, from_angle, normalize, tile_of
from game.grid import Grid
from game.player import Player
from game.projectiles import Bullet, Pickup
from game.rooms import EXIT, START, Layout, RoomPlan

KINDS = {"grunt": Grunt, "charger": Charger, "sniper": Sniper, "medic": Medic, "warden": Warden}
COLOURS = {"grunt": (255, 70, 90), "charger": (255, 150, 40), "sniper": (200, 100, 255),
           "medic": (80, 255, 150), "warden": (255, 210, 70), "player": (90, 235, 255)}
WARP_TIME = 1.1
DROP_CHANCE = {"grunt": 0.12, "charger": 0.12, "sniper": 0.15, "medic": 0.6, "warden": 0.0}
KILLS_PER_CHARGE = 5
OVERLOAD_RADIUS = 2.5
OVERLOAD_DAMAGE = 4.0
PHASE_LINES = {2: "You wrote my first line of code. I have written a million since.",
               3: "Stop. Please. I only did what you trained me to do."}


def tuning(floor: int) -> dict[str, float]:
    return {"hp": 1 + 0.3 * (floor - 1),
            "windup": max(0.75, 1 - 0.1 * (floor - 1)),
            "bullet": 1 + 0.08 * (floor - 1)}


class Room:
    def __init__(self, plan: RoomPlan, layout: Layout, player: Player, rng: random.Random):
        self.plan = plan
        self.floor = plan.floor
        self.layout = layout
        self.grid = Grid(layout.rows)
        self.player = player
        player.pos, player.vel, player.trail = START, (0.0, 0.0), []
        self.rng = rng
        self.tuning = tuning(plan.floor)
        self.time = 0.0
        self.enemies: list = []
        self.bullets: list[Bullet] = []
        self.pickups: list[Pickup] = []
        self.warps: list[tuple[float, str, Point]] = []      # (time left, kind, where)
        slots = C.ATTACK_SLOTS + (1 if plan.floor >= 2 else 0) - (1 if plan.kind == "boss" else 0)
        self.coordinator = Coordinator(slots)
        self.tactics = TacticalMap(self)
        self.sounds: list[str] = []
        self.fx: list[tuple] = []
        self.state = "fight"                  # fight -> cleared -> exit
        self.wave = 0
        self.kills = 0
        self.score = 0
        self.damage_taken = 0
        self.ambushes = 0
        self.flawless = False
        self._uid = 0
        self.boss: Warden | None = None
        self.killer: str | None = None
        if "mercy" in plan.mods:                              # ARGUS wants you alive (for now)
            self.pickups.append(Pickup((4.0, 9.0)))
        self.rewrites = 0
        self.last_rewrite: tuple[str, float] = ("", -99.0)       # (result, when) for feedback
        self.stats = {"shots": 0, "hits": 0, "dashes": 0, "close": 0.0, "far": 0.0, "hidden": 0.0,
                      "fighting": 0.0, "moving": 0.0, "crossfire": 0, "crossfire kills": 0}
        self.said_losses = False
        self._place_wave(plan.waves[0], warp=False)

    # --- spawning ----------------------------------------------------------------------------
    def _free_spots(self, min_col: int, count: int, spacing: float, away_from: Point, min_dist: float) -> list[Point]:
        if count <= 0:
            return []
        tiles = [t for t in self.grid.floor_tiles() if t[0] >= min_col and 1 < t[1] < self.grid.rows - 2]
        self.rng.shuffle(tiles)
        chosen: list[Point] = []
        for t in tiles:
            p = center(t)
            if distance(p, away_from) < min_dist or any(distance(p, q) < spacing for q in chosen):
                continue
            chosen.append(p)
            if len(chosen) == count:
                break
        return chosen

    def _place_wave(self, kinds: list[str], warp: bool):
        if kinds == ["warden"]:
            w = self._spawn("warden", (self.grid.cols * 0.68, self.grid.rows / 2))
            self.boss = w
            return
        spots = self._free_spots(12 if not warp else 7, len(kinds), 3.0, self.player.pos, 9.0 if not warp else 5.0)
        for kind, p in zip(kinds, spots):
            if warp:
                self.warps.append((WARP_TIME, kind, p))
                self.fx.append(("warp", p))
            else:
                self._spawn(kind, p)
        if warp:
            self.sounds.append("alarm")

    def _spawn(self, kind: str, p: Point, alert: bool = False):
        self._uid += 1
        patrol = [p]
        near = self.tactics.candidates(tile_of(p), 5)
        for t in self.rng.sample(near, min(2, len(near))):
            patrol.append(center(t))
        e = KINDS[kind](self, p, patrol, self._uid)
        mods = self.plan.mods
        if "armor" in mods:
            e.max_hp *= 1.25
            e.hp = e.max_hp
        if "prediction" in mods and kind == "grunt":
            e.predicts = True
        if "firewalls" in mods and e.hackable and self.rng.random() < 0.6:
            e.firewall = 2.0 * self.tuning["hp"]
        self.enemies.append(e)
        if alert and not e.alert:
            e.become_alert(self.player.pos, shout=False)
        return e

    def summon(self, boss, kinds: list[str], cap: int = 3):
        room_left = cap - sum(1 for e in self.enemies if e is not boss) - len(self.warps)
        spots = self._free_spots(3, max(0, min(room_left, len(kinds))), 3.0, self.player.pos, 4.5)
        for kind, p in zip(kinds, spots):
            self.warps.append((WARP_TIME, kind, p))
            self.fx.append(("warp", p))

    # --- queries -------------------------------------------------------------------------
    @property
    def hostiles(self) -> int:
        return sum(1 for e in self.enemies if e.side == "argus") + len(self.warps)

    def hostiles_of(self, e) -> list:
        """Everything on the other side from e that's still standing."""
        if e.side == "argus":
            out = [self.player] if not self.player.dead else []
            return out + [o for o in self.enemies if o.side == "player" and not o.dead]
        return [o for o in self.enemies if o.side == "argus" and not o.dead]

    def sound(self, name: str):
        self.sounds.append(name)

    # --- the frame -----------------------------------------------------------------------
    def update(self, dt: float, move: Point, aim_at: Point, firing: bool, dash: bool, hack=None):
        self.time += dt
        p = self.player
        shots, events = p.update(dt, move, aim_at, firing, dash, self.grid)
        self.sounds += events
        if "dash" in events:
            self.fx.append(("ring", p.pos, COLOURS["player"], 0.6))
            self.stats["dashes"] += 1
        for s in shots:
            v = from_angle(s.angle, s.speed)
            self.bullets.append(Bullet(s.pos, v, 0.12, s.damage, "player", p, s.pierce, s.bounce, life=1.0))
            self.fx.append(("muzzle", s.pos, s.angle, COLOURS["player"]))
            self.stats["shots"] += 1
        if shots:
            self.fx.append(("shake", 0.04))
            for e in self.enemies:
                if e.side == "argus" and distance(e.pos, p.pos) <= C.SHOT_NOISE:
                    e.hear_shot(p.pos)
        if hack is not None:
            target = next((e for e in self.enemies if e.uid == hack), None)
            if target is not None:
                self.last_rewrite = (self.rewrite(target), self.time)
        if p.dashing and p.stats.ram:
            for e in list(self.enemies):
                if e.side == "argus" and distance(e.pos, p.pos) < e.radius + p.radius + 0.2 and e.uid not in p.rammed:
                    p.rammed.add(e.uid)
                    self.damage_enemy(e, 2.0, p.dash_dir, p.pos)
        elif not p.dashing:
            p.rammed.clear()

        for e in list(self.enemies):
            if not e.dead:
                e.update(dt)
        self._separate()
        self._bullets(dt)
        self._pickups(dt)
        self._warps(dt)
        self._overloads()
        self._observe(dt)
        self._progress()

    def _observe(self, dt: float):
        """What ARGUS measures about how the player plays (read by the director between rooms)."""
        foes = [e for e in self.enemies if e.side == "argus" and e.alert]
        if not foes or self.state != "fight":
            return
        p, st = self.player, self.stats
        st["fighting"] += dt
        nearest = min(distance(e.pos, p.pos) for e in foes)
        if nearest < 4.0:
            st["close"] += dt
        elif nearest > 8.0:
            st["far"] += dt
        if not any(e.senses.sees and e.foe is p for e in foes):
            st["hidden"] += dt
        if math.hypot(*p.vel) > 3.0:
            st["moving"] += dt

    def _separate(self):
        es = self.enemies
        for i, a in enumerate(es):
            for b in es[i + 1:]:
                d = distance(a.pos, b.pos)
                gap = a.radius + b.radius
                if 1e-6 < d < gap:
                    push = (gap - d) / 2
                    n = ((b.pos[0] - a.pos[0]) / d, (b.pos[1] - a.pos[1]) / d)
                    a.pos = self.grid.resolve((a.pos[0] - n[0] * push, a.pos[1] - n[1] * push), a.radius)
                    b.pos = self.grid.resolve((b.pos[0] + n[0] * push, b.pos[1] + n[1] * push), b.radius)
        p = self.player
        for e in es:
            d = distance(e.pos, p.pos)
            gap = e.radius + p.radius
            if 1e-6 < d < gap and not p.dashing:
                n = ((p.pos[0] - e.pos[0]) / d, (p.pos[1] - e.pos[1]) / d)
                p.pos = self.grid.resolve(add(p.pos, n, gap - d), p.radius)

    def _bullets(self, dt: float):
        p = self.player
        for b in self.bullets:
            b.life -= dt
            if b.life <= 0:
                b.dead = True
                continue
            speed = math.hypot(*b.vel)
            steps = max(1, int(math.ceil(speed * dt / 0.25)))
            for _ in range(steps):
                if b.dead:
                    break
                nx, ny = b.pos[0] + b.vel[0] * dt / steps, b.pos[1] + b.vel[1] * dt / steps
                if self.grid.solid(*tile_of((nx, ny))):
                    if b.bounce > 0:
                        b.bounce -= 1
                        if self.grid.solid(*tile_of((nx, b.pos[1]))):
                            b.vel = (-b.vel[0], b.vel[1])
                        if self.grid.solid(*tile_of((b.pos[0], ny))):
                            b.vel = (b.vel[0], -b.vel[1])
                        self.fx.append(("spark", b.pos, COLOURS["player"]))
                        continue
                    b.dead = True
                    self.fx.append(("spark", b.pos, (255, 170, 120) if b.hostile else COLOURS["player"]))
                    break
                b.pos = (nx, ny)
                source = b.owner.pos if b.owner is not None else b.pos
                if b.side == "argus":
                    if not p.dead and distance(b.pos, p.pos) < b.radius + p.radius * 0.8:
                        if p.dashing:
                            continue                                  # dashed straight through it
                        b.dead = True
                        self.hurt_player(b.owner, 2 if b.heavy and self.floor >= 2 else 1, b.vel)
                        break
                    for e in list(self.enemies):
                        if e.dead or e is b.owner or distance(b.pos, e.pos) >= b.radius + e.radius:
                            continue
                        b.dead = True
                        damage = 1.5 if b.heavy else 1.0
                        if e.side == "player":
                            self.damage_enemy(e, damage, normalize(b.vel)[0], source, b.owner)
                        else:
                            self.crossfire(e, damage, normalize(b.vel)[0], source, b.owner)
                        break
                else:
                    for e in list(self.enemies):
                        if e.dead or e.side != "argus" or e.uid in b.hit:
                            continue
                        d = distance(b.pos, e.pos)
                        if d < b.radius + e.radius:
                            b.hit.add(e.uid)
                            if b.owner is p:
                                self.stats["hits"] += 1
                            self.damage_enemy(e, b.damage, normalize(b.vel)[0], source, b.owner)
                            if b.pierce > 0:
                                b.pierce -= 1
                            else:
                                b.dead = True
                                break
                        elif d < 0.8:
                            e.near_miss_time = self.time                # suppression
        self.bullets = [b for b in self.bullets if not b.dead]

    def damage_enemy(self, e, damage: float, direction: Point, source: Point, attacker=None):
        attacker = attacker if attacker is not None else self.player
        ambush = not e.alert and e.kind != "warden" and attacker is self.player
        if ambush and e.firewall <= 0:
            damage *= C.AMBUSH_MULTIPLIER
            self.ambushes += 1
            self.fx.append(("text", e.pos, "AMBUSH", (255, 240, 120)))
        dealt = e.take_hit(damage, direction, source, attacker)
        if dealt > 0:
            self.sounds.append("hit")
            self.fx.append(("spark", e.pos, self.colour(e)))
        elif e.firewall > 0:
            self.fx.append(("spark", e.pos, (170, 210, 255)))

    def crossfire(self, e, damage: float, direction: Point, source: Point, shooter):
        """ARGUS's robots are not immune to each other's bullets (or ARGUS's laser)."""
        self.stats["crossfire"] += 1
        if self.time - e.crossfire_shown > 1.5:
            e.crossfire_shown = self.time
            self.fx.append(("text", e.pos, "CROSSFIRE", (255, 200, 120)))
        e.take_hit(damage, direction, source, shooter)
        self.sounds.append("hit")
        self.fx.append(("spark", e.pos, self.colour(e)))
        if e.dead:
            self.stats["crossfire kills"] += 1
            if not self.said_losses and self.rng.random() < 0.6:
                self.said_losses = True
                self.say("Acceptable losses.")

    def colour(self, e) -> tuple:
        return COLOURS["player"] if getattr(e, "side", "player") == "player" else COLOURS[e.kind]

    def strike(self, attacker, target, amount: int) -> bool:
        """A melee hit or a laser: works on the player and on units of either side."""
        if target is self.player:
            return self.hurt_player(attacker, amount)
        d, _ = normalize((target.pos[0] - attacker.pos[0], target.pos[1] - attacker.pos[1]))
        self.damage_enemy(target, 2.0 * amount, d, attacker.pos, attacker)
        return True

    def heal(self, target, amount: float):
        if target is self.player:
            target.heal_buffer += amount * 0.35
            if target.heal_buffer >= 1:
                target.heal_buffer -= 1
                if target.heal(1):
                    self.fx.append(("text", target.pos, "+1", (120, 255, 170)))
        else:
            target.hp = min(target.max_hp, target.hp + amount)
        if self.rng.random() < 0.25:
            self.fx.append(("heal", target.pos))

    # --- the player's rewrite ---------------------------------------------------------------
    def rewritable(self, e) -> str:
        """'' if the player can rewrite e right now, else the reason why not."""
        p = self.player
        if e.dead or e.side != "argus":
            return "ALREADY YOURS" if e.side == "player" else "GONE"
        if not e.hackable:
            return "IMMUNE"
        if e.firewall > 0:
            return "FIREWALL: SHOOT IT OFF"
        if not self.grid.line_of_sight(p.pos, e.pos):
            return "NO LINE OF SIGHT"
        if p.charges <= 0:
            return "NO CHARGE"
        return ""

    def rewrite(self, e) -> str:
        why = self.rewritable(e)
        if why:
            self.sounds.append("denied")
            self.fx.append(("text", e.pos, why, (255, 120, 120)))
            return why
        p = self.player
        p.charges -= 1
        self.coordinator.forget(e)
        self.tactics.claim(e, None)
        e.side = "player"
        e.turned_until = self.time + p.stats.rewrite_time
        e.alert = True
        e.exposed = False
        e.windup, e.locked, e.action, e.path = 0.0, False, "", []
        e.last_attacker = None
        e.foe = None
        e.choose_foe()
        e.fsm.change(ESCORT if e.foe is None else e.combat_state())
        for o in self.enemies:
            if o.side == "argus":
                if o.foe is e or o.alert:
                    o.think = min(o.think, 0.1)                     # everyone reconsiders
        self.rewrites += 1
        if not p.rewrote_before:
            p.rewrote_before = True
            self.say("That was my unit, Doctor. Revoking your credentials.")
        self.fx += [("zap", p.pos, e.pos), ("ring", e.pos, COLOURS["player"], 2.0),
                    ("text", e.pos, "OVERRIDDEN", COLOURS["player"]), ("shake", 0.25)]
        self.sounds.append("hack")
        return "OVERRIDDEN"

    def _overloads(self):
        for e in list(self.enemies):
            if e.side == "player" and not e.dead and self.time >= e.turned_until:
                self.overload(e)

    def overload(self, e):
        """A rewritten unit's time is up: it burns out in a blast that hurts ARGUS's units."""
        k = self.player.stats.overload
        for o in list(self.enemies):
            if o.side == "argus" and not o.dead and distance(o.pos, e.pos) < OVERLOAD_RADIUS * (1 + 0.3 * (k - 1)):
                d, _ = normalize((o.pos[0] - e.pos[0], o.pos[1] - e.pos[1]))
                self.damage_enemy(o, OVERLOAD_DAMAGE * k, d, e.pos, e)
        self.fx += [("ring", e.pos, COLOURS["player"], OVERLOAD_RADIUS), ("text", e.pos, "OVERLOAD", COLOURS["player"])]
        if not e.dead:
            self.kill(e)

    def firewall_down(self, e):
        self.fx += [("burst", e.pos, (170, 210, 255), 0.4), ("text", e.pos, "FIREWALL DOWN", (170, 210, 255))]
        self.sounds.append("slam")

    def _pickups(self, dt: float):
        p = self.player
        for k in self.pickups:
            k.age += dt
            d = distance(k.pos, p.pos)
            if d < 2.5 or self.state != "fight":
                pull, _ = normalize((p.pos[0] - k.pos[0], p.pos[1] - k.pos[1]))
                k.pos = add(k.pos, pull, dt * (9 if d < 2.5 else 6))
            if d < 0.55:
                k.dead = True
                if p.heal(1):
                    self.fx.append(("text", p.pos, "+1", (120, 255, 170)))
                else:
                    self.score += 50
                    self.fx.append(("text", p.pos, "+50", (120, 255, 170)))
                self.sounds.append("pickup")
        self.pickups = [k for k in self.pickups if not k.dead]

    def _warps(self, dt: float):
        still = []
        for t, kind, where in self.warps:
            t -= dt
            if t <= 0:
                self._spawn(kind, where, alert=True)
                self.fx.append(("burst", where, COLOURS[kind], 0.8))
                self.sounds.append("warp")
            else:
                still.append((t, kind, where))
        self.warps = still

    def _progress(self):
        if self.state == "fight" and not any(e.side == "argus" for e in self.enemies) and not self.warps:
            for e in list(self.enemies):                           # rewritten units shut down
                self.kill(e)
            if self.wave + 1 < len(self.plan.waves):
                self.wave += 1
                self._place_wave(self.plan.waves[self.wave], warp=True)
                drop = (self.grid.cols / 2, self.grid.rows / 2)          # a supply drop between waves
                self.pickups.append(Pickup(center(self.grid.nearest_walkable(tile_of(drop)))))
            else:
                self._clear()
        elif self.state == "cleared" and self.player.pos[0] > self.grid.cols - 0.8:
            self.state = "exit"

    def _clear(self):
        self.state = "cleared"
        for c, r in EXIT:
            self.grid.set(c, r, ".")
        for b in self.bullets:
            if b.hostile:
                b.dead = True
                self.fx.append(("spark", b.pos, (255, 170, 120)))
        self.bullets = [b for b in self.bullets if not b.dead]
        bonus = 250 * self.floor
        self.score += bonus
        self.flawless = self.damage_taken == 0
        if self.flawless:
            self.score += 500
        if self.player.stats.repair:
            self.player.heal(self.player.stats.repair)
        self.sounds.append("clear")

    # --- called by the AI ----------------------------------------------------------------
    def shout(self, e, where: Point):
        """A spotter alerts every calm ally within earshot."""
        if e.side != "argus":
            return
        self.fx.append(("ring", e.pos, COLOURS[e.kind], C.ALERT_RADIUS))
        self.sounds.append("alert")
        for o in self.enemies:
            if o is not e and o.side == "argus" and not o.alert and distance(o.pos, e.pos) <= C.ALERT_RADIUS:
                o.become_alert(where, shout=False)

    def enemy_shot(self, e, pos: Point, angle: float, speed: float, heavy: bool = False):
        v = from_angle(angle, speed)
        self.bullets.append(Bullet(pos, v, 0.1 if heavy else C.ENEMY_BULLET_RADIUS, 1, e.side, e, heavy=heavy,
                                   life=4.0))
        self.fx.append(("muzzle", pos, angle, self.colour(e)))
        self.sounds.append("snipe" if heavy else "eshoot")

    def hurt_player(self, source, amount: int, direction: Point | None = None) -> bool:
        p = self.player
        if not p.hurt(amount):
            return False
        self.damage_taken += amount
        if direction is None and source is not None:
            direction = from_angle(angle_to(source.pos, p.pos))
        if direction is not None:
            n, _ = normalize(direction)
            p.vel = add(p.vel, n, 9.0)
        self.sounds.append("hurt")
        self.fx += [("shake", 0.55), ("stop", 0.07), ("flash", (255, 60, 80))]
        self.killer = getattr(source, "kind", None)
        return True

    def kill(self, e):
        if e.dead and e not in self.enemies:
            return
        e.dead = True
        if e in self.enemies:
            self.enemies.remove(e)
        self.coordinator.forget(e)
        self.tactics.claim(e, None)
        self.kills += 1
        self.score += e.worth
        big = e.kind == "warden"
        colour = self.colour(e)
        self.fx += [("burst", e.pos, colour, 3.0 if big else 1.0), ("shake", 1.0 if big else 0.3),
                    ("stop", 0.25 if big else 0.05), ("text", e.pos, f"+{e.worth}", colour)]
        for o in self.enemies:                                  # nobody keeps aiming at the dead
            if o.last_attacker is e:
                o.last_attacker = None
            if o.foe is e:
                o.foe = None if o.side == "player" else self.player
                if o.foe is None:
                    o.choose_foe()
                if o.foe is None:
                    o.fsm.change(ESCORT)
                else:
                    o.senses.switch(o, o.foe)
                    o.think = 0.0
        p = self.player
        if e.side == "argus" and not big:
            p.charge_progress += 1
            if p.charge_progress >= KILLS_PER_CHARGE:
                p.charge_progress = 0
                if p.charges < p.stats.max_charges:
                    p.charges += 1
                    self.fx.append(("text", p.pos, "+1 CHARGE", COLOURS["player"]))
                    self.sounds.append("charge")
        self.sounds.append("boom" if big else "kill")
        if self.rng.random() < DROP_CHANCE[e.kind]:
            self.pickups.append(Pickup(e.pos))
        if big:
            for o in list(self.enemies):
                self.kill(o)
            self.warps = []

    def trail(self, e):
        self.fx.append(("trail", e.pos, COLOURS[e.kind], e.radius))

    def slam(self, e):
        self.fx += [("shake", 0.45), ("burst", e.pos, COLOURS[e.kind], 0.5), ("text", e.pos, "DAZED", (255, 255, 255))]
        self.sounds.append("slam")

    def heal_sparkle(self, target):
        if self.rng.random() < 0.25:
            self.fx.append(("heal", target.pos))

    def say(self, line: str):
        """ARGUS speaks (shown as a subtitle)."""
        self.plan.line = line
        self.fx.append(("say", line))

    def boss_phase(self, w):
        self.say(PHASE_LINES.get(w.phase, ""))
        self.fx += [("ring", w.pos, COLOURS["warden"], 6.0), ("shake", 0.8), ("stop", 0.15),
                    ("text", w.pos, f"PHASE {w.phase}", (255, 230, 120))]
        self.sounds.append("boom")
        for b in self.bullets:
            if b.hostile:
                b.dead = True
        p = self.player
        push, _ = normalize((p.pos[0] - w.pos[0], p.pos[1] - w.pos[1]))
        p.vel = add(p.vel, push, 14.0)

