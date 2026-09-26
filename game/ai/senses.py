"""What an enemy knows about its foe: only what it has seen or heard (imperfect information).

(Its foe is normally the player, Seven. It can be a rewritten traitor.)

SIGHT    a cone (100 degrees while calm, 220 once alert) that needs a clear line of sight;
         anything within 1.6 tiles is felt regardless.
NOTICING while calm, seeing the player fills a SUSPICION meter (faster up close). Full = "!".
         Partly full = "?": the enemy stops and stares (a double take), so a quick player can
         still break line of sight before being spotted.
HEARING  gunshots carry 11 tiles. A calm enemy goes to investigate; an alert one learns
         where the player is from the sound.
MEMORY   the last known position, and when it was last confirmed. Out of touch for 5 s, an
         alert enemy stops fighting and SEARCHes.
"""

import math

from game import config as C
from game.geometry import Point, angle_diff, angle_to, distance


class Senses:
    def __init__(self):
        self.suspicion = 0.0
        self.sees = False
        self.last_known: Point | None = None
        self.seen_at = -math.inf
        self.heard_at = -math.inf

    def age(self, now: float) -> float:
        """Seconds since the player's position was last confirmed by sight or sound."""
        return now - max(self.seen_at, self.heard_at)

    def heard(self, pos: Point, now: float):
        self.last_known = pos
        self.heard_at = now

    def switch(self, e, foe):
        """A new foe: what do I know about it?"""
        if e.room.grid.line_of_sight(e.pos, foe.pos):
            self.last_known = foe.pos
            self.seen_at = e.room.time
        else:
            self.last_known = foe.pos
            self.heard_at = e.room.time - 2.0

    def update(self, e, dt: float) -> str | None:
        room = e.room
        p = e.foe or room.player
        d = distance(e.pos, p.pos)
        half = C.ALERT_HALF_ANGLE if e.alert else C.VIEW_HALF_ANGLE
        reach = e.view_range * (1.2 if e.alert else 1.0)
        in_view = d <= C.PROXIMITY or (d <= reach and abs(angle_diff(e.facing, angle_to(e.pos, p.pos))) <= half)
        self.sees = in_view and room.grid.line_of_sight(e.pos, p.pos)
        if self.sees:
            self.last_known = p.pos
            self.seen_at = room.time
        if e.alert:
            return None
        if self.sees:
            rate = (2.5 if d < 3 else 1.5 if d < 6 else 1.0) / C.NOTICE_TIME
            self.suspicion = min(1.0, self.suspicion + rate * dt)
            if self.suspicion >= 1.0:
                return "spotted"
        else:
            self.suspicion = max(0.0, self.suspicion - dt * 0.4)
        return None
