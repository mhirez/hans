"""Hans: a sneaky game about a clever horse.

    python main.py                 play (continues where you left off)
    python main.py --night 3       jump to a night
    python main.py --xray          start with the AI X-Ray on (for demo recordings)
    python main.py --no-sound      silence
"""

import argparse

from game.app import Game


def main():
    parser = argparse.ArgumentParser(description="Hans: a sneaky game about a clever horse")
    parser.add_argument("--night", type=int, default=None, help="night (level) to start on, 0-5")
    parser.add_argument("--xray", action="store_true", help="start with the AI X-Ray overlay on")
    parser.add_argument("--seed", type=int, default=None, help="random seed for a reproducible run")
    parser.add_argument("--no-sound", action="store_true", help="turn sound effects off")
    args = parser.parse_args()
    Game(seed=args.seed, xray=args.xray, night=args.night, sound=not args.no_sound).run()


if __name__ == "__main__":
    main()
