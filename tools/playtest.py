"""Automated playtesting: a careless and a careful ghost (game/ai/ghost.py) play every night.

    careless   walks straight to von Osten, then straight to the door
    careful    plans around the lantern light, waits in the dark, runs for cover

The careless ghost shows how hard a night is; the careful one shows it can be won.

    python -m tools.playtest            all nights, 24 runs each
    python -m tools.playtest 3 50       night 3, 50 runs
"""

import random
import sys

from game.ai.ghost import Ghost
from game.levels import LEVELS
from game.play import Play


def run(night: int, careful: bool, seed: int, limit: float = 150.0) -> tuple[str, float, int]:
    rng = random.Random(seed)
    play = Play(night, LEVELS[night], rng)
    ghost = Ghost(careful)
    delay = rng.uniform(0, 8)             # players start moving at different moments
    dt = 1 / 30
    while play.state == "playing" and play.time < limit:
        move, trot, tap = ghost.act(play) if play.time >= delay else ((0, 0), False, False)
        play.update(dt, move, trot)
        if tap:
            play.tap()
    return play.state, play.time, play.stars if play.state == "won" else 0


def report(nights, runs: int):
    print("| night | careless: won | careful: won | careful: avg stars | careful: avg time |")
    print("|---|---|---|---|---|")
    for night in nights:
        careless = [run(night, False, s) for s in range(runs)]
        careful = [run(night, True, s) for s in range(runs)]
        won_a = sum(r[0] == "won" for r in careless)
        won_b = [r for r in careful if r[0] == "won"]
        stars = sum(r[2] for r in won_b) / max(1, len(won_b))
        time = sum(r[1] for r in won_b) / max(1, len(won_b))
        print(f"| {night} {LEVELS[night].name} | {won_a}/{runs} | {len(won_b)}/{runs} | {stars:.1f} | {time:.0f}s |")


if __name__ == "__main__":
    nights = [int(sys.argv[1])] if len(sys.argv) > 1 else range(len(LEVELS))
    report(nights, int(sys.argv[2]) if len(sys.argv) > 2 else 24)
