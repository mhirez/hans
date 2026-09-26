"""MENDER (medic): unarmed, keeps the squad alive. Kill it first, if you can reach it.

Combat states:
    ENGAGE    thinking
    HEAL      goes to the most-hurt ally it knows about and, within 3.5 tiles with a clear line,
              heals it with a green beam (1.2 health per second)
    SHELTER   you can see it: it tucks in behind the ally nearest to it (on the far side from you)
    FLEE      you're within 4 tiles: it runs for the spot furthest from you
    TAG ALONG nothing to do: it stays near the squad, away from you

Utility:  flee     you're within 4 tiles:               1.0
          heal     the most-hurt ally:                   0.35 + 0.65 x (1 - its health)
          shelter  you can see it and it has allies:     0.45
          tag      always:                               0.25
"""

from game.ai.agent import REACTION, Enemy
from game.ai.fsm import State
from game.geometry import add, angle_to, center, distance, normalize

HEAL_RANGE = 3.5
HEAL_RATE = 1.2


class Medic(Enemy):
    kind = "medic"
    name = "MENDER"
    base_hp = 5.0
    speed = 3.6
    radius = 0.32
    worth = 150

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.patient = None
        self.beam = None                  # who it's healing right now (drawn as a beam)
        self.spot_tile = None

    def combat_state(self):
        return ENGAGE

    def states_for(self, action):
        return {"heal": (HEAL,), "shelter": (SHELTER,), "flee": (FLEE,), "tag": (TAG,)}[action]

    def allies(self):
        return [e for e in self.room.enemies if e is not self and not e.dead]

    def options(self):
        d = distance(self.pos, self.player.pos)
        allies = self.allies()
        hurt = [e for e in allies if e.health < 0.95]
        self.patient = min(hurt, key=lambda e: (e.health, distance(e.pos, self.pos))) if hurt else None
        exposed = self.room.grid.line_of_sight(self.pos, self.player.pos)
        return {"flee": 1.0 if d < 4.0 else 0.0,
                "heal": 0.35 + 0.65 * (1 - self.patient.health) if self.patient else 0.0,
                "shelter": 0.45 if exposed and allies else 0.0,
                "tag": 0.25}

    def feasible(self, action):
        if action == "flee":
            self.spot_tile = self.room.tactics.escape_spot(self, self.player.pos)
            return self.spot_tile is not None
        return True

    def shelter_point(self):
        allies = self.allies()
        if not allies:
            return self.pos
        ally = min(allies, key=lambda e: distance(e.pos, self.pos))
        away, _ = normalize((ally.pos[0] - self.player.pos[0], ally.pos[1] - self.player.pos[1]))
        return add(ally.pos, away, 1.4)

    def squad_point(self):
        allies = self.allies()
        if not allies:
            return self.pos
        cx = sum(e.pos[0] for e in allies) / len(allies)
        cy = sum(e.pos[1] for e in allies) / len(allies)
        away, _ = normalize((cx - self.player.pos[0], cy - self.player.pos[1]))
        return add((cx, cy), away, 2.0)


class Engage(State):
    name = "ENGAGE"

    def enter(self, m):
        m.think = REACTION
        m.beam = None

    def update(self, m, dt):
        m.brake(dt)
        m.face_player(dt)
        m.rethink(dt)


class Heal(State):
    name = "HEAL"

    def enter(self, m):
        m.timer = 0.0
        m.beam = None

    def exit(self, m):
        m.beam = None

    def update(self, m, dt):
        p = m.patient
        if p is None or p.dead or p.hp >= p.max_hp:
            m.action = ""
            m.think = 0.0
            m.rethink(dt)
            return
        close = distance(m.pos, p.pos) <= HEAL_RANGE and m.room.grid.line_of_sight(m.pos, p.pos)
        if close:
            m.path = []
            m.brake(dt)
            m.face(angle_to(m.pos, p.pos), dt)
            m.beam = p
            p.hp = min(p.max_hp, p.hp + HEAL_RATE * dt)
            m.room.heal_sparkle(p)
        else:
            m.beam = None
            m.timer -= dt
            if m.timer <= 0:
                m.timer = 0.3
                m.go_to(p.pos)
            m.follow(dt, m.speed)
        m.spot = p.pos
        m.rethink(dt)


class Shelter(State):
    name = "SHELTER"

    def enter(self, m):
        m.timer = 0.0

    def update(self, m, dt):
        m.timer -= dt
        if m.timer <= 0:
            m.timer = 0.3
            m.spot = m.shelter_point()
            m.go_to(m.spot)
        m.follow(dt, m.speed, face=False)
        m.face_player(dt)
        m.rethink(dt)


class Flee(State):
    name = "FLEE"

    def enter(self, m):
        m.timer = 0.0
        m.room.tactics.claim(m, m.spot_tile)
        m.spot = center(m.spot_tile)
        m.go_to(m.spot)

    def exit(self, m):
        m.room.tactics.claim(m, None)

    def update(self, m, dt):
        m.timer += dt
        if m.follow(dt, m.speed * 1.2) or m.timer > 3:
            m.action = ""
            m.think = 0.0
        m.rethink(dt)


class Tag(State):
    name = "TAG ALONG"

    def enter(self, m):
        m.timer = 0.0

    def update(self, m, dt):
        m.timer -= dt
        if m.timer <= 0:
            m.timer = 0.5
            m.spot = m.squad_point()
            m.go_to(m.spot)
        m.follow(dt, m.speed * 0.8, face=False)
        m.face_player(dt)
        m.rethink(dt)


ENGAGE, HEAL, SHELTER, FLEE, TAG = Engage(), Heal(), Shelter(), Flee(), Tag()
