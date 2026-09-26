"""The player model: what the Commission knows about how YOU move. Pfungst reads it to predict you.

It is the Clever Hans effect turned around. Hans answered questions by reading people's tiny,
involuntary movements; Pfungst finally understood him by watching Hans just as closely. Here the
scientists record every time Hans escapes an attack, and which way he went:

    left / right   sidestepped across the attacker's line
    back           backed straight away from him
    in             stepped IN toward him (usually to kick)

The counts start at 1 each (so nothing is certain at first), and Pfungst aims his net where Hans
has most often gone. Be unpredictable and his read is wrong.

It also keeps a SECOND-ORDER model: when Pfungst marks his guess with a chalk X, does Hans dodge
AWAY from it (he's reading Pfungst) or not? If he usually does, Pfungst starts to bluff.
"""

from dataclasses import dataclass, field
import math

from game.level import Point, angle_to, angle_diff, distance

SIDES = ("left", "right", "back", "in")
OPPOSITE = {"left": "right", "right": "left"}


@dataclass
class PlayerModel:
    dodges: dict[str, float] = field(default_factory=lambda: {s: 1.0 for s in SIDES})
    kick_range: float = 1.2                  # how close enemies usually are when Hans kicks
    kicks_seen: int = 0
    x_replies: dict[str, float] = field(default_factory=lambda: {"away": 1.0, "other": 1.0})
    pending: dict[int, tuple[Point, Point]] = field(default_factory=dict)   # attacker uid -> (attacker, hans)

    # --- watching ------------------------------------------------------------------------
    def attack_started(self, attacker, hans_pos: Point):
        self.pending[attacker.uid] = (attacker.pos, hans_pos)

    def attack_released(self, attacker, hans_pos: Point) -> str | None:
        """Where did Hans go between the wind-up and the release? Returns the side, if he moved."""
        start = self.pending.pop(attacker.uid, None)
        if start is None:
            return None
        where, before = start
        if distance(before, hans_pos) < 0.35:
            return None                                       # he didn't move: nothing to learn
        side = self.classify(where, before, hans_pos)
        self.dodges[side] += 1
        return side

    def saw_kick(self, nearest: float | None):
        if nearest is not None and nearest < 3:
            self.kicks_seen += 1
            self.kick_range += (nearest - self.kick_range) / min(self.kicks_seen + 1, 10)

    @staticmethod
    def classify(attacker: Point, before: Point, after: Point) -> str:
        line = angle_to(attacker, before)                     # attacker -> Hans
        move = angle_to(before, after)
        rel = angle_diff(line, move)                          # 0 = straight away, pi = straight at him
        if abs(rel) < math.radians(45):
            return "back"
        if abs(rel) > math.radians(135):
            return "in"
        return "left" if rel < 0 else "right"

    def saw_reply_to_x(self, x_side: str, dodged: str | None):
        """After a chalk X on `x_side`: did Hans dodge to the opposite side?"""
        if x_side in OPPOSITE:
            self.x_replies["away" if dodged == OPPOSITE[x_side] else "other"] += 1

    def reads_the_x(self) -> float:
        """How likely Hans is to dodge away from Pfungst's chalk X."""
        return self.x_replies["away"] / (self.x_replies["away"] + self.x_replies["other"])

    # --- predicting ----------------------------------------------------------------------
    def probabilities(self) -> dict[str, float]:
        total = sum(self.dodges.values())
        return {s: n / total for s, n in self.dodges.items()}

    def predict(self) -> tuple[str, float]:
        p = self.probabilities()
        side = max(p, key=p.get)
        return side, p[side]

    def landing_spot(self, attacker: Point, hans: Point, side: str, reach: float = 1.3) -> Point:
        """Where Hans will be if he dodges `side` again."""
        line = angle_to(attacker, hans)
        turn = {"back": 0.0, "left": -math.pi / 2, "right": math.pi / 2, "in": math.pi}[side]
        a = line + turn
        step = 0.6 if side == "in" else reach
        return hans[0] + math.cos(a) * step, hans[1] + math.sin(a) * step
