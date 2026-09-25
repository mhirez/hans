"""What the scientists can see and hear.

Sight   A scientist sees by lantern light: a cone VIEW_RANGE long and 2 x VIEW_HALF_ANGLE wide,
        blocked by anything tall (walls, hay, carts, screens). No light, no sight: Hans is
        invisible in the dark, even right beside him.
Hearing Hans's hooves make Noise events (trotting, gravel, an empty door banging). A noise is
        heard by anyone within its radius; walls don't stop sound, but it only tells you *where*.
"""

from dataclasses import dataclass
import math

from game.config import CONE_RAYS
from game.level import Level, Point, distance, angle_to, angle_diff


@dataclass(frozen=True)
class Noise:
    pos: Point
    radius: float
    kind: str = "hoof"          # "hoof" or "door"


def sees(level: Level, eye: Point, facing: float, target: Point, view_range: float, half_angle: float) -> float | None:
    """Distance to the target if it is inside the lit cone with a clear line of sight, else None."""
    d = distance(eye, target)
    if d > view_range:
        return None
    if d > 0.3 and abs(angle_diff(facing, angle_to(eye, target))) > half_angle:
        return None
    return d if level.line_of_sight(eye, target) else None


def hears(listener: Point, noise: Noise) -> bool:
    return distance(listener, noise.pos) <= noise.radius


def cone(level: Level, eye: Point, facing: float, view_range: float, half_angle: float,
         rays: int = CONE_RAYS) -> list[Point]:
    """The lit area as a polygon: the eye plus where each ray of lantern light stops."""
    points = [eye]
    for i in range(rays + 1):
        a = facing - half_angle + 2 * half_angle * i / rays
        d = level.ray(eye, a, view_range)
        points.append((eye[0] + math.cos(a) * d, eye[1] + math.sin(a) * d))
    return points
