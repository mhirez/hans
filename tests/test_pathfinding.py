from game.ai.pathfinding import astar
from game.world import World, SCREEN_TILES


def open_grid(c, r):
    return 0 <= c < 10 and 0 <= r < 10


def test_straight_line_path():
    result = astar((0, 0), (5, 0), open_grid)
    assert result.path[0] == (0, 0) and result.path[-1] == (5, 0)
    assert result.cost == 5


def test_diagonal_uses_octile_cost():
    result = astar((0, 0), (3, 3), open_grid)
    assert len(result.path) == 4
    assert abs(result.cost - 3 * 2 ** 0.5) < 1e-9


def test_routes_around_a_wall():
    wall = {(3, r) for r in range(0, 8)}
    result = astar((0, 0), (6, 0), lambda c, r: open_grid(c, r) and (c, r) not in wall)
    assert result.path is not None
    assert not wall.intersection(result.path)
    assert result.cost > 6


def test_unreachable_goal_returns_none():
    wall = {(3, r) for r in range(10)}
    result = astar((0, 0), (6, 0), lambda c, r: open_grid(c, r) and (c, r) not in wall)
    assert result.path is None


def test_no_corner_cutting():
    blocked = {(1, 0), (0, 1)}
    result = astar((0, 0), (1, 1), lambda c, r: open_grid(c, r) and (c, r) not in blocked)
    assert result.path is None


def test_screen_forces_hans_the_long_way_round():
    world = World()
    before = astar((11, 15), world.owner_observe_tile, world.walkable).cost
    world.configure(owner_present=True, owner_far=False, screen=True, crowd_present=False)
    after = astar((11, 15), world.owner_observe_tile, world.walkable)
    assert after.path is not None
    assert not set(SCREEN_TILES).intersection(after.path)
    assert after.cost > before
