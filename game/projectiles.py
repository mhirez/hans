"""Bullets and pick-ups."""

from dataclasses import dataclass, field
import math

from game.geometry import Point


@dataclass(eq=False)
class Bullet:
    pos: Point
    vel: Point
    radius: float
    damage: float
    side: str                        # "argus" (hurts the player's side) or "player" (hurts ARGUS's)
    owner: object = None
    pierce: int = 0
    bounce: int = 0
    life: float = 3.0
    heavy: bool = False              # sniper round: drawn as a streak
    hit: set = field(default_factory=set)
    dead: bool = False

    @property
    def hostile(self) -> bool:
        return self.side == "argus"

    @property
    def angle(self) -> float:
        return math.atan2(self.vel[1], self.vel[0])


@dataclass(eq=False)
class Pickup:
    pos: Point
    kind: str = "repair"             # a heart back
    age: float = 0.0
    vel: Point = (0.0, 0.0)
    dead: bool = False
