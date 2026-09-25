"""Hans: catch me if you can.

    python main.py                 play
    python main.py --wave 4        start on a later wave
    python main.py --xray          start with the AI X-Ray on (for demo recordings)
    python main.py --no-sound      silence
"""

import argparse

from game.app import Game


def main():
    parser = argparse.ArgumentParser(description="Hans: catch me if you can")
    parser.add_argument("--wave", type=int, default=1, help="wave to start on")
    parser.add_argument("--xray", action="store_true", help="start with the AI X-Ray overlay on")
    parser.add_argument("--seed", type=int, default=None, help="random seed for a reproducible run")
    parser.add_argument("--no-sound", action="store_true", help="turn sound effects off")
    args = parser.parse_args()
    Game(seed=args.seed, xray=args.xray, start_wave=max(1, args.wave), sound=not args.no_sound).run()


if __name__ == "__main__":
    main()
