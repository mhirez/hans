"""The Commission's field command: a shared blackboard that turns single enemies into a team.

Every frame it updates a guess at Hans's GOAL; every half second (a quarter with Pfungst in
charge) it hands out ROLES. Enemies read their role when choosing where to run.

  Goal recognition  For each carrot / pick-up: is Hans heading toward it? (the angle between his
                    velocity and the direction to it, weighted by distance). Smoothed over time
                    into a belief; the strongest one is "what he's after" once it passes 45%.
  Escape route      Of 16 points 4 tiles around Hans, the reachable one furthest from every enemy:
                    where a sensible horse would run next.
  Reading Hans      Tired (stamina almost gone) or hurt (one heart left) -> press the attack.

  Roles             CHASER   the nearest scientist: straight at him
                    BLOCKER  gets to the carrot he's after first and stands over it
                    FLANKER  circles to the far side of Hans from the chaser (the pincer)
                    CUTOFF   stands in his escape route
"""

import math

from game.config import STAMINA
from game.level import Point, distance, tile_of, center

GOAL_KINDS = ("carrot", "sugar", "horseshoe")


class Tactics:
    def __init__(self):
        self.belief: dict[int, float] = {}          # item uid -> how strongly Hans seems to be going for it
        self.goal = None                             # the item he's after (or None)
        self.goal_conf = 0.0
        self.escape: Point | None = None
        self.roles: dict[int, str] = {}
        self.timer = 0.0
        self.tired = False
        self.hurt = False
        self.commander = None                        # Pfungst, when he's on the field

    @property
    def pressing(self) -> bool:
        return self.tired or self.hurt

    # --- every frame ---------------------------------------------------------------------
    def update(self, match, dt: float):
        self._recognise_goal(match, dt)
        self._read_hans(match)
        self.commander = next((e for e in match.enemies if e.kind == "pfungst" and e.state != "KO"), None)
        self.timer -= dt
        if self.timer <= 0:
            self.timer = 0.25 if self.commander else 0.5
            self._assign(match)

    def _recognise_goal(self, match, dt: float):
        h = match.hans
        vx, vy = match.hans_velocity
        speed = math.hypot(vx, vy)
        items = [i for i in match.items if i.kind in GOAL_KINDS]
        live = {i.uid for i in items}
        self.belief = {k: v for k, v in self.belief.items() if k in live}
        for item in items:
            d = distance(h.pos, item.pos)
            if speed > 0.5 and d > 0.3:
                cos = (vx * (item.pos[0] - h.pos[0]) + vy * (item.pos[1] - h.pos[1])) / (speed * d)
                likelihood = math.exp(4 * (cos - 1)) / (1 + d / 8)
            else:
                likelihood = 0.15 / (1 + d / 8)
            old = self.belief.get(item.uid, 0.0)
            self.belief[item.uid] = old + (likelihood - old) * min(1.0, dt * 3)
        total = sum(self.belief.values())
        if not items or total <= 0:
            self.goal, self.goal_conf = None, 0.0
            return
        best = max(items, key=lambda i: self.belief[i.uid])
        self.goal, self.goal_conf = best, self.belief[best.uid] / total

    def _read_hans(self, match):
        h = match.hans
        was_tired, was_hurt = self.tired, self.hurt
        self.tired = h.stamina < 0.2 * STAMINA
        self.hurt = h.hearts == 1
        for now, before, cue in ((self.tired, was_tired, "tired_hans"), (self.hurt, was_hurt, "weak")):
            if now and not before:
                speaker = self._nearest_aware(match)
                if speaker is not None:
                    speaker.events.append(cue)

    @staticmethod
    def _nearest_aware(match):
        aware = [e for e in match.enemies if e.aware and e.state != "KO" and e.kind != "dog"]
        return min(aware, key=lambda e: distance(e.pos, match.hans.pos)) if aware else None

    # --- twice a second ------------------------------------------------------------------
    def _assign(self, match):
        h = match.hans
        attackers = sorted((e for e in match.enemies if e.kind in ("scientist", "pfungst") and e.aware and
                            not e.guard and e.state in ("CHASE", "SWING", "READ")),
                           key=lambda e: distance(e.pos, h.pos))
        roles: dict[int, str] = {}
        rest = list(attackers)
        if rest:
            roles[rest.pop(0).uid] = "chaser"
        goal = self.goal if (self.goal is not None and self.goal_conf > 0.45 and
                             distance(self.goal.pos, h.pos) > 2.5) else None
        if rest and goal is not None:
            blocker = min(rest, key=lambda e: distance(e.pos, goal.pos))
            if distance(blocker.pos, goal.pos) < distance(h.pos, goal.pos) + 2:   # only if he can get there
                roles[blocker.uid] = "blocker"
                rest.remove(blocker)
        if rest:
            roles[rest.pop(0).uid] = "flanker"
        if rest:
            self.escape = self._escape_point(match)
            for e in rest:
                roles[e.uid] = "cutoff" if self.escape else "flanker"
        for e in match.enemies:
            new = roles.get(e.uid)
            if new != self.roles.get(e.uid) and new in ("blocker", "cutoff", "flanker"):
                e.events.append(new)
            e.role = new
        self.roles = roles

    def _escape_point(self, match) -> Point | None:
        h, level = match.hans, match.level
        enemies = [e for e in match.enemies if e.state != "KO"]
        best, best_score = None, -math.inf
        for k in range(16):
            a = k * math.pi / 8
            p = (h.pos[0] + math.cos(a) * 4, h.pos[1] + math.sin(a) * 4)
            t = tile_of(p)
            if not level.walkable(*t) or not level.line_of_sight(h.pos, p):
                continue
            score = min((distance(p, e.pos) for e in enemies), default=10)
            if score > best_score:
                best, best_score = center(t), score
        return best

    def target_for(self, enemy, match) -> tuple[Point | None, str | None]:
        """Where an enemy with a role should run (None: just chase Hans)."""
        h = match.hans
        role = getattr(enemy, "role", None)
        if role == "blocker" and self.goal is not None and distance(enemy.pos, h.pos) > 2.2:
            gx, gy = self.goal.pos
            a = math.atan2(h.pos[1] - gy, h.pos[0] - gx)          # stand on Hans's side of the carrot
            spot = (gx + math.cos(a) * 0.9, gy + math.sin(a) * 0.9)
            return (spot if match.level.walkable(*tile_of(spot)) else self.goal.pos), role
        if role == "cutoff" and self.escape is not None and distance(enemy.pos, h.pos) > 2.5:
            return self.escape, role
        return None, role
