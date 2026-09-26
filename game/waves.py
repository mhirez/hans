"""The waves. The first five are hand-made to introduce one enemy at a time; after that each wave is
generated from a growing budget, so the game never ends and never repeats exactly.
"""

import random
from dataclasses import dataclass

COST = {"scientist": 1.0, "stableboy": 1.5, "dog": 0.8}

SCRIPTED = {
    1: ["scientist", "scientist"],
    2: ["scientist", "scientist", "scientist"],
    3: ["scientist", "scientist", "stableboy"],
    4: ["scientist", "stableboy", "dog", "dog", "dog"],
    5: ["scientist", "scientist", "stableboy", "dog", "dog"],        # + Oskar Pfungst (match.py)
}

INTROS = {
    1: ("Everyone wants to catch the clever horse!", "Eat the carrots. Kick the scientists. Don't get netted."),
    2: ("More scientists.", "Watch for the red arc: that's a net swing coming."),
    3: ("A stable boy with a lasso!", "He throws from far away. A lasso slows you down."),
    4: ("Guard dogs!", "They hunt as a pack and surround you. Keep moving!"),
    5: ("Oskar Pfungst arrives!", "He studies how you dodge, and swings where you'll go. Surprise him."),
}


@dataclass(frozen=True)
class Wave:
    number: int
    enemies: tuple[tuple[float, str], ...]    # (spawn time, kind)
    carrots: int                              # carrots to eat to clear the wave
    speed: float                              # enemy speed multiplier
    intro: tuple[str, str]


def plan(n: int, rng: random.Random) -> Wave:
    if n in SCRIPTED:
        kinds = list(SCRIPTED[n])
    else:
        budget = 4.0 + 0.9 * n
        kinds = ["scientist", "stableboy", "dog"]
        budget -= sum(COST[k] for k in kinds)
        while budget > 0.8:
            kind = rng.choice(list(COST))
            kinds.append(kind)
            budget -= COST[kind]
    rng.shuffle(kinds)
    times, t = [], 1.5
    for i, kind in enumerate(kinds):
        times.append((t, kind))
        t += 8.0 if n == 1 else 1.0 if i < 2 else rng.uniform(3.0, 5.5)   # wave 1: one at a time
    intro = INTROS.get(n, ("Pfungst is back.", "He remembers every dodge you've made.") if n % 5 == 0 else
                       (f"Wave {n}.", f"{len(kinds)} of them. They're getting quicker."))
    return Wave(n, tuple(times), min(24, 5 + 2 * n), min(1.35, 0.82 + 0.06 * (n - 1)), intro)
