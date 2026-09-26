"""Does each piece of the AI matter? Switch one off at a time and measure.

The AVERAGE bot plays the first two floors (8 rooms) under each condition. Reported per room:
hits the enemies land on the player, and how long the room takes to clear. More hits = the
enemies are more dangerous.

    full          everything on
    random        decisions picked at random among the options that are possible, instead of by
                  utility score (is the scoring actually making them smarter?)
    no cover      grunts never take cover
    no flank      grunts never flank
    no tokens     no attack tokens: everyone attacks whenever it likes

    python -m tools.ablation           12 runs per condition
"""

import contextlib
import random
import statistics
import sys

from game.ai import agent, grunt, tactics
from game.bot import make_bot
from game.run import Run

AVERAGE = make_bot(reaction=0.8, dodge=1.5, wobble=1.0, dash_bullets=False)


def run_two_floors(seed: int) -> tuple[int, float, int]:
    run = Run(seed)
    hits, rooms, t = 0, 0, 0.0
    while run.state in ("room", "upgrade") and run.floor <= 2 and t < 600:
        if run.state == "upgrade":
            run.choose(0)
            continue
        room = run.room
        run.update(1 / 60, *AVERAGE(run))
        room.sounds.clear()
        room.fx.clear()
        t += 1 / 60
        if run.room is not room:
            hits += room.damage_taken
            rooms += 1
    if run.state == "dead":
        hits += run.room.damage_taken
    return hits, t, rooms


@contextlib.contextmanager
def patched(condition: str):
    saved = []

    def patch(obj, name, value):
        saved.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    if condition == "random":
        rng = random.Random(0)
        original = agent.Enemy.decide

        def random_decide(self):
            if self.kind == "warden":
                return original(self)
            self.think = agent.THINK_EVERY
            options = [a for a, s in self.options().items() if s > 0]
            rng.shuffle(options)
            for action in options:
                if self.feasible(action):
                    self.action = action
                    self.fsm.change(self.states_for(action)[0])
                    return
        patch(agent.Enemy, "decide", random_decide)
    elif condition in ("no cover", "no flank"):
        drop = "cover" if condition == "no cover" else "flank"
        original = grunt.Grunt.options

        def options(self):
            o = original(self)
            o[drop] = 0.0
            return o
        patch(grunt.Grunt, "options", options)
    elif condition == "no tokens":
        patch(tactics.Coordinator, "can_attack", lambda self, e, now: True)
    try:
        yield
    finally:
        for obj, name, value in reversed(saved):
            setattr(obj, name, value)


def report(runs: int):
    print("| condition | hits on the player per room | seconds per room | rooms cleared (of 8) |")
    print("|---|---|---|---|")
    for condition in ("full", "random", "no cover", "no flank", "no tokens"):
        with patched(condition):
            results = [run_two_floors(s) for s in range(runs)]
        rooms = sum(r[2] for r in results)
        hits = sum(r[0] for r in results) / max(1, rooms + sum(1 for r in results if r[2] < 8))
        secs = sum(r[1] for r in results) / max(1, rooms)
        print(f"| {condition} | {hits:.2f} | {secs:.1f} | {statistics.mean(r[2] for r in results):.1f} |")


if __name__ == "__main__":
    report(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
