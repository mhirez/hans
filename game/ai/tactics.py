"""Squad tactics shared by every enemy in a room.

COORDINATOR  Attack tokens: an enemy must hold one to start an attack, and only 2 (3 on the
             last floor) exist, with at least 0.35 s between attacks starting. Everyone else
             repositions, strafes or flanks. This keeps fights readable (you can always tell
             who's about to shoot) and makes the squad look like it's taking turns on purpose.
             It also hands out ONE flanker slot at a time.
TACTICAL MAP Scores tiles around an enemy for a purpose:
               cover spot   hidden from the player, hugging a block, 4-9 tiles away, close by,
                            and ideally one step from a tile that can see him (to peek out)
               firing spot  can see the player, at the right range, near cover, not crowded
               flank spot   can see the player from 70-130 degrees round from where he's
                            already being attacked
               escape spot  as far from the player as possible, preferably hidden
             Tiles another enemy has claimed score badly, so the squad spreads out.
             Every evaluation is kept so the AI X-Ray can draw it as a heat map.
DANGER COST  An A* cost: +4 for every tile the player can see. Flankers path through cover.
"""

import math

from game import config as C
from game.geometry import Point, Tile, angle_diff, angle_to, band, center, distance, tile_of


class Coordinator:
    def __init__(self, slots: int = C.ATTACK_SLOTS, gap: float = C.ATTACK_GAP):
        self.slots = slots
        self.gap = gap
        self.holders: set[int] = set()
        self.last_start = -math.inf
        self.flanker: int | None = None

    def can_attack(self, e, now: float) -> bool:
        return e.uid in self.holders or (len(self.holders) < self.slots and now - self.last_start >= self.gap)

    def acquire(self, e, now: float) -> bool:
        if e.uid in self.holders:
            return True
        if not self.can_attack(e, now):
            return False
        self.holders.add(e.uid)
        self.last_start = now
        return True

    def release(self, e):
        self.holders.discard(e.uid)

    def flank_free(self, e) -> bool:
        return self.flanker is None or self.flanker == e.uid

    def take_flank(self, e):
        self.flanker = e.uid

    def drop_flank(self, e):
        if self.flanker == e.uid:
            self.flanker = None

    def forget(self, e):
        self.release(e)
        self.drop_flank(e)


class TacticalMap:
    def __init__(self, room):
        self.room = room
        self.grid = room.grid
        self.claims: dict[int, Tile] = {}
        self.debug: dict[int, tuple[str, dict[Tile, float], Tile | None]] = {}

    # --- basics --------------------------------------------------------------------------
    def exposed(self, t: Tile, threat: Point) -> bool:
        return self.grid.sees_tile(tile_of(threat), t)

    def claim(self, e, t: Tile | None):
        if t is None:
            self.claims.pop(e.uid, None)
        else:
            self.claims[e.uid] = t

    def crowded(self, e, t: Tile) -> bool:
        return any(uid != e.uid and abs(c[0] - t[0]) <= 1 and abs(c[1] - t[1]) <= 1
                   for uid, c in self.claims.items())

    def candidates(self, around: Tile, radius: int) -> list[Tile]:
        g = self.grid
        out = []
        for r in range(max(1, around[1] - radius), min(g.rows - 1, around[1] + radius + 1)):
            for c in range(max(1, around[0] - radius), min(g.cols - 1, around[0] + radius + 1)):
                if g.at(c, r) == ".":
                    out.append((c, r))
        return out

    def _best(self, e, purpose: str, scores: dict[Tile, float]) -> Tile | None:
        best = max(scores, key=scores.get) if scores else None
        if best is not None and scores[best] <= 0:
            best = None
        self.debug[e.uid] = (purpose, scores, best)
        return best

    # --- spots ---------------------------------------------------------------------------
    def cover_spot(self, e, threat: Point) -> Tile | None:
        scores = {}
        for t in self.candidates(tile_of(e.pos), 6):
            if self.exposed(t, threat) or not self.grid.near_cover(t):
                continue
            d = distance(center(t), threat)
            if d < 2.5:
                continue
            s = 1.0 + 0.6 * band(d, 4, 9) - 0.12 * distance(center(t), e.pos)
            c, r = t
            if any(self.grid.at(c + dc, r + dr) == "." and self.exposed((c + dc, r + dr), threat)
                   for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                s += 0.4                                        # can peek out from here
            if self.crowded(e, t):
                s -= 2.0
            scores[t] = s
        return self._best(e, "cover", scores)

    def firing_spot(self, e, target: Point, lo: float, hi: float, radius: int = 7,
                    prefer_far: bool = False, avoid: Tile | None = None) -> Tile | None:
        scores = {}
        others = [o.pos for o in self.room.enemies if o is not e and not o.dead]
        for t in self.candidates(tile_of(e.pos), radius):
            if not self.exposed(t, target):
                continue
            p = center(t)
            d = distance(p, target)
            s = 1.5 * band(d, lo, hi, 2.0)
            if s <= 0:
                continue
            s -= 0.08 * distance(p, e.pos)
            s += 0.3 if self.grid.near_cover(t) else 0.0
            s -= 0.5 * sum(1 for o in others if distance(o, p) < 1.5)
            if prefer_far:
                s += 0.04 * d
            if avoid is not None and distance(p, center(avoid)) < 3:
                s -= 1.0
            if self.crowded(e, t):
                s -= 2.0
            scores[t] = s
        return self._best(e, "fire", scores)

    def flank_spot(self, e, target: Point, pinned_from: float) -> Tile | None:
        """A spot that sees the player from a different side than the attack already on him."""
        scores = {}
        for t in self.candidates(tile_of(target), 7):
            p = center(t)
            d = distance(p, target)
            if not 3.0 <= d <= 7.5 or not self.exposed(t, target):
                continue
            turn = abs(angle_diff(pinned_from, angle_to(target, p)))
            s = 1.2 * band(math.degrees(turn), 70, 130, 40) - 0.05 * distance(p, e.pos)
            if self.crowded(e, t):
                s -= 2.0
            scores[t] = s
        return self._best(e, "flank", scores)

    def escape_spot(self, e, threat: Point, radius: int = 8) -> Tile | None:
        scores = {}
        for t in self.candidates(tile_of(e.pos), radius):
            p = center(t)
            s = distance(p, threat) * 0.3 - 0.06 * distance(p, e.pos)
            if not self.exposed(t, threat):
                s += 1.0
            if distance(p, threat) < distance(e.pos, threat) - 0.5:
                continue                                        # never run past him
            if self.crowded(e, t):
                s -= 2.0
            scores[t] = s + 5.0
        return self._best(e, "escape", scores)

    def danger_cost(self, threat: Point):
        """A* extra cost: tiles in the player's line of fire are expensive."""
        return lambda c, r: 4.0 if self.exposed((c, r), threat) else 0.0
