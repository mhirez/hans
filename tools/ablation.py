"""Does each piece of the AI matter? Switch one off at a time and measure.

An AVERAGE bot plays the first two floors (8 rooms) under each condition, many times, in
parallel. Reported: hits the enemies land on the player per room (with a 95% confidence
interval), seconds per room, rooms cleared. More hits = more dangerous enemies.

1. ARGUS's side (the bot never rewrites, so only the enemy AI is being measured)
    full          everything on
    random        decisions picked at random among the options that are possible, instead of by
                  utility score (is the scoring actually making them smarter?)
    no cover      Sentries never take cover
    no flank      Sentries never flank
    no tokens     no attack tokens: everyone attacks whenever it likes
    no director   ARGUS never adapts the rooms to how you play
    no fire discipline   robots don't check whether a friend is in their line of fire
2. the player's side (the bot rewrites)
    rewrites          everything on
    no target choice  ARGUS's units always target the player and ignore rewritten traitors
3. Does the director recognise play styles? Which countermeasures it deploys against a bot that
   strafes a lot (average), one that always fights from 9-12 tiles (far), and one that
   rewrites (rewriter).

    python -m tools.ablation           40 runs per condition
    python -m tools.ablation 100       100 runs per condition
    python -m tools.ablation 100 full "no cover"      just those conditions
"""

import collections
import contextlib
import math
import multiprocessing
import random
import sys

from game.ai import agent, director, grunt, tactics
from game.bot import make_bot
from game.run import Run

AVERAGE = make_bot(reaction=0.8, dodge=1.5, wobble=1.0, dash_bullets=False)
NO_REWRITES = make_bot(reaction=0.8, dodge=1.5, wobble=1.0, dash_bullets=False, rewrites=False)
FAR = make_bot(reaction=0.8, dodge=1.5, wobble=1.0, dash_bullets=False, rewrites=False, band=(9.0, 12.0))
BOTS = {"average": NO_REWRITES, "far": FAR, "rewriter": AVERAGE}


def run_two_floors(seed: int, player) -> tuple[int, float, int, list[str], int]:
    """(hits taken, seconds played, rooms cleared, countermeasures deployed, robot-on-robot hits)
    over floors 1-2."""
    run = Run(seed)
    seen, t, deployed = [], 0.0, []
    while run.state in ("room", "upgrade") and run.floor <= 2 and t < 900:
        if run.state == "upgrade":
            run.choose(0)
            continue
        if not seen or seen[-1] is not run.room:
            seen.append(run.room)
            deployed += run.director.deployed
        room = run.room
        run.update(1 / 60, *player(run))
        room.sounds.clear()
        room.fx.clear()
        t += 1 / 60
    return (sum(r.damage_taken for r in seen), t, min(8, run.rooms_cleared), deployed,
            sum(r.stats["crossfire"] for r in seen))


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
            self.choose_foe()
            if self.foe is None and self.needs_foe:
                self.fsm.change(agent.ESCORT)
                return
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
    elif condition == "no fire discipline":
        patch(agent.Enemy, "clear_shot", lambda self, target, margin=0.25: True)
    elif condition == "no director":
        def adapt(self, plan, player, rng):
            self.scores, self.deployed = {}, []
            return plan
        patch(director.Director, "adapt", adapt)
    elif condition == "no target choice":
        original_choose = agent.Enemy.choose_foe

        def choose_foe(self):
            if self.side == "argus":
                self.foe = self.player
                return
            original_choose(self)
        patch(agent.Enemy, "choose_foe", choose_foe)
    try:
        yield
    finally:
        for obj, name, value in reversed(saved):
            setattr(obj, name, value)


def bot_for(condition: str):
    if condition in ("rewrites", "no target choice"):
        return BOTS["rewriter"]
    if condition.startswith("diag "):
        return BOTS[condition[5:]]
    return BOTS["average"]


def _one(job):
    condition, seed = job
    with patched(condition):
        return run_two_floors(seed, bot_for(condition))


def measure(condition: str, runs: int, pool) -> list:
    return pool.map(_one, [(condition, s) for s in range(runs)])


def table(runs: int, conditions, pool):
    print("| condition | hits on the player per room (95% CI) | robot-on-robot hits per room | seconds per room | "
          "rooms cleared (of 8) |")
    print("|---|---|---|---|---|")
    for condition in conditions:
        results = measure(condition, runs, pool)
        rates = [r[0] / (r[2] + (1 if r[2] < 8 else 0)) for r in results]        # the room you died in counts
        mean = sum(rates) / len(rates)
        sd = math.sqrt(sum((x - mean) ** 2 for x in rates) / max(1, len(rates) - 1))
        ci = 1.96 * sd / math.sqrt(len(rates))
        played = sum(r[2] + (1 if r[2] < 8 else 0) for r in results)
        print(f"| {condition} | {mean:.2f} ± {ci:.2f} | {sum(r[4] for r in results) / max(1, played):.2f} | "
              f"{sum(r[1] for r in results) / max(1, played):.1f} | {sum(r[2] for r in results) / len(results):.1f} |")


def director_table(runs: int, pool):
    print("| player | countermeasures ARGUS deployed (share of all its decisions) |")
    print("|---|---|")
    for name in ("average", "far", "rewriter"):
        counts = collections.Counter()
        for r in measure(f"diag {name}", runs, pool):
            counts.update(r[3])
        total = sum(counts.values()) or 1
        top = ", ".join(f"{k} {100 * v / total:.0f}%" for k, v in counts.most_common(4))
        print(f"| {name} | {top} |")


def report(runs: int):
    with multiprocessing.Pool() as pool:
        print("1. ARGUS'S SIDE (the bot never rewrites)")
        table(runs, ("full", "random", "no cover", "no flank", "no tokens", "no director", "no fire discipline"), pool)
        print()
        print("2. THE PLAYER'S SIDE (the bot rewrites)")
        table(runs, ("rewrites", "no target choice"), pool)
        print()
        print("3. WHAT THE DIRECTOR DEPLOYS AGAINST EACH PLAY STYLE")
        director_table(runs, pool)


if __name__ == "__main__":
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    if len(sys.argv) > 2:                                   # just these conditions
        with multiprocessing.Pool() as pool:
            table(runs, sys.argv[2:], pool)
    else:
        report(runs)
