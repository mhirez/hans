"""Automated playtesting: bots (game/bot.py) play whole runs so the game can be balanced with
numbers. Two profiles: a SKILLED bot (reacts 0.3 s into a telegraph, dashes through bullets) and
an AVERAGE one (reacts late, aims loosely, never dashes through bullets). Both take the first
upgrade offered.

    python -m tools.autoplay           20 runs
    python -m tools.autoplay 50        50 runs
"""

import collections
import statistics
import sys

from game.bot import bot, make_bot

AVERAGE = make_bot(reaction=0.8, dodge=1.5, wobble=1.0, dash_bullets=False)
from game.run import Run


def play(seed: int, limit: float = 900.0, player=bot) -> dict:
    run = Run(seed)
    t = 0.0
    while run.state in ("room", "upgrade") and t < limit:
        if run.state == "upgrade":
            run.choose(0)
            continue
        run.update(1 / 60, *player(run))
        run.room.sounds.clear()
        run.room.fx.clear()
        t += 1 / 60
    return {"state": run.state, "floor": run.floor, "room": run.index + 1, "cleared": run.rooms_cleared,
            "score": run.total_score, "time": run.time, "killer": run.killer}


def report(runs: int):
    for label, player in (("skilled bot", bot), ("average bot", AVERAGE)):
        print(f"--- {label}")
        _report(runs, player)


def _report(runs: int, player):
    results = [play(s, player=player) for s in range(runs)]
    cleared = [r["cleared"] for r in results]
    print(f"runs {runs}: rooms cleared median {statistics.median(cleared)}, best {max(cleared)}, "
          f"escaped {sum(r['state'] == 'won' for r in results)}/{runs}")
    where = collections.Counter(f"F{r['floor']}R{r['room']}" for r in results if r["state"] == "dead")
    print("died in:", ", ".join(f"{k} x{v}" for k, v in sorted(where.items())))
    print("killed by:", dict(collections.Counter(r["killer"] for r in results if r["state"] == "dead")))
    print(f"mean run time {statistics.mean(r['time'] for r in results):.0f} s, "
          f"mean score {statistics.mean(r['score'] for r in results):.0f}")


if __name__ == "__main__":
    report(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
