"""Level-design check: simulate the scientists patrolling (Hans hidden away) and print how
often each tile is lit by a lantern. Also verifies every level is reachable and well formed.

    python -m tools.danger_map          all levels
    python -m tools.danger_map 3        one level

Legend:  space = never lit   . <10%   : <25%   * <50%   # >=50%   (walls shown as |)
         H Hans  O von Osten  D door  S scientist start
"""

import sys

from game.ai.ghost import danger_map
from game.level import Level, tile_of
from game.levels import LEVELS


def check(index: int) -> list[str]:
    """Structural problems with a level: ragged rows, too few doors, unreachable places, bad routes."""
    spec = LEVELS[index]
    problems = []
    widths = {len(r) for r in spec.map}
    if len(widths) != 1:
        problems.append(f"rows have different widths: {sorted(widths)}")
    level = Level(list(spec.map))
    if len(level.doors) < 2:
        problems.append("fewer than 2 doors")
    start = tile_of(level.start)
    for p in level.owner_stops + [d.front for d in level.doors]:
        if level.route(start, tile_of(p)).path is None:
            problems.append(f"unreachable from the start: {tile_of(p)}")
    for route in spec.scientists:
        for d in route.rstrip("o").rstrip("<>^vqezc"):
            if d not in level.waypoints:
                problems.append(f"route {route}: no waypoint {d} on the map")
    return problems


def danger(index: int) -> list[list[float]]:
    return danger_map(LEVELS[index], seconds=60.0)


def show(index: int):
    spec = LEVELS[index]
    level = Level(list(spec.map))
    heat = danger(index)
    marks = {tile_of(level.start): "H"}
    marks.update({tile_of(p): "O" for p in level.owner_stops})
    marks.update({d.tile: "D" for d in level.doors})
    for route in spec.scientists:
        marks[tile_of(level.waypoints[route[0]])] = "S"
    print(f"\n=== Level {index}: {spec.name} ===")
    for r in range(level.rows):
        line = ""
        for c in range(level.cols):
            if (c, r) in marks:
                line += marks[(c, r)]
            elif not level.walkable(c, r):
                line += "|" if level.at(c, r) == "#" else level.at(c, r)
            else:
                v = heat[r][c]
                line += " " if v == 0 else "." if v < 0.1 else ":" if v < 0.25 else "*" if v < 0.5 else "#"
        print(line)
    start = tile_of(level.start)
    print(f"start lit {heat[start[1]][start[0]]:.0%}", end="")
    for i, p in enumerate(level.owner_stops):
        t = tile_of(p)
        print(f" | von Osten stop {i} lit {heat[t[1]][t[0]]:.0%}", end="")
    for d in level.doors:
        t = tile_of(d.front)
        print(f" | door {d.name} front lit {heat[t[1]][t[0]]:.0%}", end="")
    print()
    for p in check(index):
        print("PROBLEM:", p)


if __name__ == "__main__":
    for i in ([int(sys.argv[1])] if len(sys.argv) > 1 else range(len(LEVELS))):
        show(i)
