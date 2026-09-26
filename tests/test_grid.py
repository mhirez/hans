
from game.grid import Grid

ROWS = ["##########",
        "#........#",
        "#...X....#",
        "#...X....#",
        "#........#",
        "##########"]


def test_line_of_sight_is_blocked_by_cover_only():
    g = Grid(ROWS)
    assert not g.line_of_sight((2.5, 2.5), (6.5, 2.5))           # straight through the block
    assert g.line_of_sight((2.5, 1.5), (6.5, 1.5))               # above it
    assert g.line_of_sight((2.5, 4.5), (6.5, 4.5))               # below it


def test_raycast_stops_at_the_first_solid_tile():
    g = Grid(ROWS)
    assert abs(g.raycast((1.5, 2.5), 0.0, 20) - 2.5) < 1e-6      # the block starts at x = 4
    assert abs(g.raycast((1.5, 1.5), 0.0, 20) - 7.5) < 1e-6      # the east wall at x = 9


def test_moving_into_a_wall_slides_along_it():
    g = Grid(ROWS)
    p = g.move((7.5, 1.5), (3.0, 0.5), 0.3)
    assert g.free(p, 0.3)
    assert abs(p[0] - (9.0 - 0.3)) < 1e-6 and abs(p[1] - 2.0) < 1e-6    # stopped at the wall, slid down


def test_route_goes_around_cover():
    g = Grid(ROWS)
    path = g.route((2, 2), (6, 2))
    assert path[0] == (2, 2) and path[-1] == (6, 2)
    assert all(g.walkable(*t) for t in path)


def test_danger_cost_steers_a_route_out_of_sight():
    """Flanking: with every tile the threat can see made expensive, the path hides behind cover."""
    g = Grid(["############",
              "#..........#",
              "#..........#",
              "#...XXXX...#",
              "#..........#",
              "############"])
    threat = (5.5, 1.5)
    exposed = lambda c, r: 4.0 if g.line_of_sight(threat, (c + 0.5, r + 0.5)) else 0.0
    plain = g.route((1, 2), (10, 2))
    sneaky = g.route((1, 2), (10, 2), exposed)
    seen = lambda path: sum(1 for c, r in path if exposed(c, r))
    assert all(r == 2 for c, r in plain)                         # the short way: in plain view
    assert seen(sneaky) < seen(plain)
    assert any(r == 4 and 4 <= c <= 7 for c, r in sneaky)        # ducks behind the block
