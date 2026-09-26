"""Does Pfungst really read you? One-on-one duels between Pfungst and bot "players" with habits.

    habit    always sidesteps LEFT of the attacker (a real player's favourite dodge)
    reader   reads the chalk X and dodges the other way
    random   picks a side at random every time

Each is tested against Pfungst as he is, and with parts of his mind switched off:

    full       player model + bluffing
    no model   guesses a side at random instead of using the player model
    no bluff   never bluffs

    python -m tools.pfungst_lab          prints the hit-rate table (Pfungst's successful reads)
"""

import math
import random

from game.ai import pfungst as pf
from game.ai.playermodel import PlayerModel, SIDES
from game.level import angle_to, distance
from game.match import Match

DUEL_TIME = 90.0


def habit(m, p, rng):
    return "left"


def reader(m, p, rng):
    return "away"


def randomly(m, p, rng):
    return rng.choice(("left", "right", "back"))


def bot(policy, rng):
    plan = {}

    def act(m):
        h = m.hans
        foe = next((e for e in m.enemies if e.kind == "pfungst"), None)
        if foe is None:
            return (0, 0), False, False
        if foe.state == "READ" and not foe.swung:
            side = plan.setdefault(id(foe.aim_from), policy(m, foe, rng))
            if side == "away":
                a = angle_to(foe.pred_spot, foe.aim_from)
            else:
                line = angle_to(foe.pos, foe.aim_from)
                a = line + {"back": 0.0, "left": -math.pi / 2, "right": math.pi / 2}[side]
            return (math.cos(a), math.sin(a)), False, False
        plan.clear()
        if distance(foe.pos, h.pos) > 2.4:                     # wander toward him to start a read
            return (foe.pos[0] - h.pos[0], foe.pos[1] - h.pos[1]), False, False
        return (0, 0), False, False
    return act


def duel(policy, seed: int) -> tuple[int, int]:
    rng = random.Random(seed)
    m = Match(random.Random(seed), start_wave=5)
    m.queue = []
    m.enemies = []
    m.spawn_enemy("pfungst")
    m.vonosten.update = lambda dt, world: None               # just the two of them
    act = bot(policy, rng)
    hits = reads = 0
    t = 0.0
    while t < DUEL_TIME:
        m.hans.hearts = 3
        m.carrots = 0
        move, gallop, kick = act(m)
        m.update(1 / 30, move, gallop, kick)
        for ev in m.drain_events():
            if ev in ("pfungst:predicted", "pfungst:bluffed"):
                hits += 1
                reads += 1
            elif ev == "pfungst:surprised":
                reads += 1
        t += 1 / 30
    return hits, reads


def report(seeds: int = 8):
    policies = (("habit (always left)", habit), ("reader (away from X)", reader), ("random", randomly))
    real_predict = PlayerModel.predict
    guess = random.Random(0)
    minds = (("full", real_predict, True),
             ("no model", lambda self: (guess.choice(SIDES), 0.25), True),
             ("no bluff", real_predict, False))
    print("| player | " + " | ".join(name for name, _, _ in minds) + " |")
    print("|---|" + "---|" * len(minds))
    for label, policy in policies:
        cells = []
        for _, predict, bluffing in minds:
            PlayerModel.predict, pf.BLUFFING = predict, bluffing
            results = [duel(policy, s) for s in range(seeds)]
            hits, reads = sum(r[0] for r in results), sum(r[1] for r in results)
            cells.append(f"{hits / max(reads, 1):.0%} ({hits}/{reads})")
        print(f"| {label} | " + " | ".join(cells) + " |")
    PlayerModel.predict, pf.BLUFFING = real_predict, True


if __name__ == "__main__":
    report()
