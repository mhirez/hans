from game.ai.pathfinding import astar


def open_grid(c, r):
    return 0 <= c < 10 and 0 <= r < 10


def test_straight_line_path():
    result = astar((0, 0), (5, 0), open_grid)
    assert result.path[0] == (0, 0) and result.path[-1] == (5, 0) and result.cost == 5


def test_routes_around_a_wall():
    wall = {(3, r) for r in range(0, 8)}
    result = astar((0, 0), (6, 0), lambda c, r: open_grid(c, r) and (c, r) not in wall)
    assert result.path is not None and not wall.intersection(result.path) and result.cost > 6


def test_unreachable_goal_returns_none():
    wall = {(3, r) for r in range(10)}
    assert astar((0, 0), (6, 0), lambda c, r: open_grid(c, r) and (c, r) not in wall).path is None


def test_no_corner_cutting():
    blocked = {(1, 0), (0, 1)}
    assert astar((0, 0), (1, 1), lambda c, r: open_grid(c, r) and (c, r) not in blocked).path is None
