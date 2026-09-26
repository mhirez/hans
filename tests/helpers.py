"""Build small, controlled rooms for AI tests."""

import random

from game.config import COLS, ROWS
from game.player import Player
from game.room import Room
from game.rooms import Layout, RoomPlan, _blank


def arena(blocks=(), floor: int = 1, seed: int = 1) -> Room:
    """An empty 32x18 room plus cover blocks given as (col, row, width, height)."""
    g = _blank()
    for c0, r0, w, h in blocks:
        for c in range(c0, c0 + w):
            for r in range(r0, r0 + h):
                g[r][c] = "X"
    layout = Layout(["".join(row) for row in g], "test")
    room = Room(RoomPlan(floor, 1, "normal", [[]]), layout, Player(pos=(2.0, 9.0)), random.Random(seed))
    room.state = "fight"
    return room


def place(room, kind, pos, facing=None, alert=False):
    e = room._spawn(kind, pos)
    e.patrol = [pos]
    if facing is not None:
        e.facing = facing
    if alert:
        e.become_alert(room.player.pos, shout=False)
    return e


def step(room, seconds, dt=1 / 60, move=(0, 0), aim=None, firing=False, dash=False):
    for _ in range(int(round(seconds / dt))):
        p = room.player
        room.update(dt, move, aim or (p.pos[0] + 1, p.pos[1]), firing, dash)
        room.sounds.clear()
        room.fx.clear()


__all__ = ["arena", "place", "step", "COLS", "ROWS"]
