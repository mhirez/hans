"""Automated playtesting: bots play many games; we measure how far they get.

    naive    runs straight at the nearest carrot and kicks whenever something is close
    player   plays like a sensible human: dodges net swings, lassos and pounces it can see
             coming (the wind-ups), steps in to kick during a wind-up, gallops away when crowded,
             and goes for sugar and golden horseshoes

    python -m tools.autoplay             20 games per bot
    python -m tools.autoplay 50          50 games per bot
"""

import math
import random
import statistics
import sys

from game.config import KICK_RADIUS, NET_REACH, HEARTS
from game.level import distance, angle_to
from game.match import Match


def naive(m: Match):
    h = m.hans
    goals = [i for i in m.items if i.kind != "coffee"]
    target = min(goals, key=lambda i: distance(i.pos, h.pos)).pos if goals else h.pos
    near = any(e.state != "KO" and distance(e.pos, h.pos) < KICK_RADIUS for e in m.enemies)
    return (target[0] - h.pos[0], target[1] - h.pos[1]), False, near


def player(m: Match):
    h = m.hans
    live = [e for e in m.enemies if e.state not in ("KO", "STUNNED")]
    wants = [i for i in m.items if i.kind == "carrot" or (i.kind == "sugar" and h.hearts < HEARTS) or i.kind == "horseshoe"]
    target = min(wants, key=lambda i: distance(i.pos, h.pos) * (0.5 if i.kind != "carrot" else 1)).pos if wants else h.pos
    move = [target[0] - h.pos[0], target[1] - h.pos[1]]
    length = math.hypot(*move) or 1
    move = [move[0] / length, move[1] / length]
    kick, gallop = False, False
    if h.powered:
        chase = [e for e in live if distance(e.pos, h.pos) < 6]
        if chase:
            e = min(chase, key=lambda e: distance(e.pos, h.pos))
            return (e.pos[0] - h.pos[0], e.pos[1] - h.pos[1]), True, False
        return tuple(move), False, False
    for e in live:
        d = distance(e.pos, h.pos)
        if e.state == "SWING" and not e.swung:
            if d <= KICK_RADIUS:
                kick = True                                      # punish the wind-up
            elif d <= NET_REACH + 0.6:
                a = angle_to(e.pos, h.pos)                       # back out of reach
                move = [move[0] * 0.2 + math.cos(a) * 2, move[1] * 0.2 + math.sin(a) * 2]
                gallop = True
        elif e.state == "POUNCE" and e.leap is None and d < 4:
            a = angle_to(e.pos, h.pos) + math.pi / 2             # sidestep the leap
            move = [math.cos(a) * 2 + move[0] * 0.3, math.sin(a) * 2 + move[1] * 0.3]
            if d <= KICK_RADIUS:
                kick = True
        elif e.state == "THROW" and d < 8:
            a = angle_to(e.pos, h.pos) + math.pi / 2             # sidestep the lasso
            move = [math.cos(a) * 1.5 + move[0] * 0.5, math.sin(a) * 1.5 + move[1] * 0.5]
        elif d <= KICK_RADIUS * 0.9 and e.state in ("CHASE", "SURROUND", "POSITION", "RETREAT"):
            kick = True
    crowd = sum(1 for e in live if distance(e.pos, h.pos) < 4 and e.aware)
    if crowd >= 2:
        gallop = True
    return tuple(move), gallop, kick


def play(bot, seed: int, limit: float = 360.0) -> tuple[int, int, float]:
    m = Match(random.Random(seed))
    t, dt = 0.0, 1 / 30
    while m.state != "over" and t < limit:
        move, gallop, kick = bot(m)
        m.update(dt, move, gallop, kick)
        m.drain_events()
        t += dt
    return m.wave.number, m.score, t


def report(games: int):
    print("| bot | waves reached (median) | best | died in wave 1 | avg score |")
    print("|---|---|---|---|---|")
    for name, bot in (("naive", naive), ("player", player)):
        runs = [play(bot, s) for s in range(games)]
        waves = [r[0] for r in runs]
        print(f"| {name} | {statistics.median(waves)} | {max(waves)} | {sum(w == 1 for w in waves)}/{games} | "
              f"{statistics.mean(r[1] for r in runs):.0f} |")


if __name__ == "__main__":
    report(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
