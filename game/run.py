"""A run: floor after floor, room after room, until you escape or are terminated."""

import random

from game import config as C
from game import rooms, upgrades
from game.ai.director import Director
from game.player import Player
from game.room import Room


class Run:
    def __init__(self, seed: int | None = None, start_floor: int = 1, start_room: int = 1):
        self.rng = random.Random(seed)
        self.player = Player(pos=rooms.START)
        self.floor = start_floor
        self.index = max(0, min(C.ROOMS_PER_FLOOR, start_room) - 1)
        self.score = 0
        self.kills = 0
        self.time = 0.0
        self.rooms_cleared = 0
        self.taken: list[str] = []
        self.offers: list[upgrades.Upgrade] = []
        self.state = "room"                  # room -> upgrade -> room ... -> dead / won
        self.killer: str | None = None
        self.director = Director()
        self.room = self._make_room()
        self.room_number = 1                 # counts up for the transition effect

    def _make_room(self) -> Room:
        plan = self.director.adapt(rooms.plan(self.floor, self.index, self.rng), self.player, self.rng)
        style = "center" if plan.kind == "boss" else None
        return Room(plan, rooms.generate(self.rng, style), self.player, self.rng)

    @property
    def total_score(self) -> int:
        return self.score + self.room.score

    def update(self, dt: float, move, aim_at, firing: bool, dash: bool, hack=None):
        if self.state != "room":
            return
        self.time += dt
        room = self.room
        room.update(dt, move, aim_at, firing, dash, hack)
        if self.player.hp <= 0:
            self.state = "dead"
            self.killer = room.killer
            self._bank()
        elif room.state == "exit":
            self.director.profile.absorb(room)
            self._bank()
            self.rooms_cleared += 1
            self._next()

    def _bank(self):
        self.score += self.room.score
        self.kills += self.room.kills
        self.room.score = 0
        self.room.kills = 0

    def _next(self):
        last = self.index == C.ROOMS_PER_FLOOR - 1
        if last and self.floor >= C.FLOORS:
            self.state = "won"
        elif last:
            self.state = "upgrade"
            self.offers = upgrades.offer(self.rng, self.taken, self.player)
        else:
            self.index += 1
            self.room = self._make_room()
            self.room_number += 1

    def choose(self, i: int):
        if self.state != "upgrade" or not 0 <= i < len(self.offers):
            return
        up = self.offers[i]
        up.apply(self.player)
        self.taken.append(up.key)
        self.floor += 1
        self.index = 0
        self.room = self._make_room()
        self.room_number += 1
        self.state = "room"
