"""Small 2D helpers. Points are (x, y) tuples in tile units; angles are radians, y points down."""

import math

Point = tuple[float, float]
Tile = tuple[int, int]


def distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angle_to(a: Point, b: Point) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def angle_diff(a: float, b: float) -> float:
    """Signed smallest turn from a to b, in [-pi, pi]."""
    return (b - a + math.pi) % (2 * math.pi) - math.pi


def turn_toward(current: float, target: float, max_step: float) -> float:
    d = angle_diff(current, target)
    return target if abs(d) <= max_step else current + math.copysign(max_step, d)


def from_angle(a: float, length: float = 1.0) -> Point:
    return math.cos(a) * length, math.sin(a) * length


def add(a: Point, b: Point, k: float = 1.0) -> Point:
    return a[0] + b[0] * k, a[1] + b[1] * k


def normalize(v: Point) -> tuple[Point, float]:
    length = math.hypot(v[0], v[1])
    if length < 1e-9:
        return (0.0, 0.0), 0.0
    return (v[0] / length, v[1] / length), length


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def tile_of(p: Point) -> Tile:
    return int(math.floor(p[0])), int(math.floor(p[1]))


def center(t: Tile) -> Point:
    return t[0] + 0.5, t[1] + 0.5


def band(x: float, lo: float, hi: float, soft: float = 1.5) -> float:
    """1 inside [lo, hi], falling to 0 over `soft` tiles outside it (a utility response curve)."""
    if x < lo:
        return clamp(1 - (lo - x) / soft, 0.0, 1.0)
    if x > hi:
        return clamp(1 - (x - hi) / soft, 0.0, 1.0)
    return 1.0
