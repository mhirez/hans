"""The ghost: an AI that plays Hans. It powers the title screen's demo and the automated playtests.

It thinks like a sensible player:
  1. LEARN THE NIGHT   Watch the scientists patrol for 40 seconds (with Hans hidden away) and record
                       how often each tile is lit: an influence map, the "danger map".
  2. PLAN              Dijkstra over the grid where often-lit tiles cost 30x more and gravel 4x more,
                       so the route hugs the dark and avoids noisy ground.
  3. WAIT              If the next step would be lit, stand still in the dark and wait.
  4. TAKE COVER        If a scientist sees or chases Hans, run (trot) to the nearest tile that
                       scientist can't see: behind something tall, or well out of range.
  5. THE TRICK         Stand in von Osten's circle until he nods, then tap the door he nodded at.

A careless ghost skips 2-4 and just walks straight there: the playtests compare the two.
"""

import heapq
import math
import random

from game.ai.perception import sees
from game.config import VIEW_RANGE, VIEW_HALF_ANGLE
from game.level import Level, tile_of, center, distance

_HEAT_CACHE: dict[str, list[list[float]]] = {}


class _Nowhere:
    """A stand-in Hans far outside the map, so the scientists just patrol."""
    pos = (-50.0, -50.0)
    trotting = False


def danger_map(spec, seconds: float = 40.0, dt: float = 0.1) -> list[list[float]]:
    """Fraction of time each tile is lit by a lantern while the scientists patrol undisturbed."""
    if spec.name in _HEAT_CACHE:
        return _HEAT_CACHE[spec.name]
    from game.play import Play
    play = Play(0, spec, random.Random(0))
    level = play.level
    lit = [[0] * level.cols for _ in range(level.rows)]
    frames = int(seconds / dt)
    ghost = _Nowhere()
    for _ in range(frames):
        for s in play.scientists:
            s.update(dt, ghost)
            for r in range(max(0, int(s.pos[1] - VIEW_RANGE)), min(level.rows, int(s.pos[1] + VIEW_RANGE) + 1)):
                for c in range(max(0, int(s.pos[0] - VIEW_RANGE)), min(level.cols, int(s.pos[0] + VIEW_RANGE) + 1)):
                    if level.walkable(c, r) and sees(level, s.pos, s.angle, center((c, r)), VIEW_RANGE,
                                                     VIEW_HALF_ANGLE) is not None:
                        lit[r][c] += 1
    heat = [[v / frames for v in row] for row in lit]
    _HEAT_CACHE[spec.name] = heat
    return heat


def safe_route(level: Level, heat, start, goal) -> list:
    """Dijkstra where often-lit tiles cost much more: the route a player learns."""
    goal = level.nearest_walkable(goal)
    dist, prev, frontier = {start: 0.0}, {}, [(0.0, start)]
    while frontier:
        d, node = heapq.heappop(frontier)
        if node == goal:
            break
        if d > dist[node]:
            continue
        c, r = node
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                nxt = (c + dc, r + dr)
                if nxt == node or not level.walkable(*nxt):
                    continue
                if dc and dr and not (level.walkable(c + dc, r) and level.walkable(c, r + dr)):
                    continue
                step = math.hypot(dc, dr) * (1 + 30 * heat[nxt[1]][nxt[0]])
                if level.at(*nxt) == "g":
                    step *= 4                           # gravel is loud: only cross it where it's cheap
                if d + step < dist.get(nxt, math.inf):
                    dist[nxt], prev[nxt] = d + step, node
                    heapq.heappush(frontier, (d + step, nxt))
    path, node = [], goal
    while node in prev:
        path.append(node)
        node = prev[node]
    return path[::-1]


class Ghost:
    def __init__(self, careful: bool = True):
        self.careful = careful
        self.path: list = []
        self.goal = None
        self.mode = "PLAN"            # what it's doing, for the demo caption

    def steer(self, play, target):
        if self.goal != target or not self.path:
            if self.careful:
                tiles = safe_route(play.level, danger_map(play.spec), tile_of(play.hans.pos), tile_of(target))
            else:
                tiles = (play.level.route(tile_of(play.hans.pos), tile_of(target)).path or [])[1:]
            self.path = [center(t) for t in tiles] + [target]
            self.goal = target
        while len(self.path) > 1 and distance(play.hans.pos, self.path[0]) < 0.2:
            self.path.pop(0)
        tx, ty = self.path[0]
        return tx - play.hans.pos[0], ty - play.hans.pos[1]

    @staticmethod
    def watchers(play, point, margin: float = 0.0):
        return [s for s in play.scientists
                if sees(play.level, s.pos, s.angle, point, VIEW_RANGE + margin, VIEW_HALF_ANGLE + margin / 4)
                is not None]

    @staticmethod
    def cover(play, threat):
        """The nearest tile the threat can't see: behind something tall, or well out of range."""
        level, here = play.level, tile_of(play.hans.pos)
        best, best_cost = None, math.inf
        for r in range(here[1] - 7, here[1] + 8):
            for c in range(here[0] - 7, here[0] + 8):
                if not level.walkable(c, r):
                    continue
                p = center((c, r))
                if distance(p, threat.pos) < 2.5:
                    continue
                if distance(p, threat.pos) <= VIEW_RANGE + 1.5 and level.line_of_sight(threat.pos, p):
                    continue
                res = level.route(here, (c, r))
                if res.path is None:
                    continue
                cost = res.cost + 3 * max(0.0, 4 - distance(p, threat.pos))
                if cost < best_cost:
                    best, best_cost = (c, r), cost
        return best

    def act(self, play) -> tuple[tuple[float, float], bool, bool]:
        """One decision: (move direction, trot?, tap?)."""
        target = play.owner.pos if not play.hint_known else play.carrot.front
        if play.hint_known and play.near_carrot() and not play.chased_now:
            self.mode = "TAP"
            return (0, 0), False, True
        chasers = [s for s in play.scientists if s.state == "CHASE"]
        seen_by = self.watchers(play, play.hans.pos)
        if self.careful and (chasers or seen_by):
            threat = min(chasers or seen_by, key=lambda s: distance(s.pos, play.hans.pos))
            spot = self.cover(play, threat)
            self.goal = None                            # re-plan the real route once safe
            self.mode = "TAKE COVER"
            if spot is not None:
                res = play.level.route(tile_of(play.hans.pos), spot)
                if res.path and len(res.path) > 1:
                    nx, ny = center(res.path[1])
                    return (nx - play.hans.pos[0], ny - play.hans.pos[1]), True, False
            return (play.hans.pos[0] - threat.pos[0], play.hans.pos[1] - threat.pos[1]), bool(chasers), False
        if not play.hint_known and play.owner.hans_close:
            self.mode = "WATCH VON OSTEN"
            return (0, 0), False, False
        move = self.steer(play, target)
        if not self.careful:
            self.mode = "WALK"
            return move, False, False
        length = math.hypot(*move) or 1
        ahead = (play.hans.pos[0] + move[0] / length * 0.9, play.hans.pos[1] + move[1] / length * 0.9)
        if self.watchers(play, ahead, margin=0.8):
            self.path = []
            self.mode = "WAIT IN THE DARK"
            return (0, 0), False, False
        self.mode = "SNEAK TO VON OSTEN" if not play.hint_known else "SNEAK TO THE DOOR"
        return move, False, False
