"""Hans: a game about learning the wrong clues.

    python main.py                 play
    python main.py --xray          start with the AI X-Ray on (for demo recordings)
    python main.py --seed 42       reproducible run
    python main.py --case 2        skip straight to a later (procedurally generated) case
"""

import argparse

from game.app import Game


def main():
    parser = argparse.ArgumentParser(description="Hans: a game about learning the wrong clues")
    parser.add_argument("--seed", type=int, default=None, help="random seed for a reproducible run")
    parser.add_argument("--xray", action="store_true", help="start with the AI X-Ray overlay on")
    parser.add_argument("--case", type=int, default=1, help="case number to start from")
    parser.add_argument("--no-log", action="store_true", help="don't write experiment logs to ./logs")
    args = parser.parse_args()
    Game(seed=args.seed, xray=args.xray, log_dir=None if args.no_log else "logs", start_case=args.case).run()


if __name__ == "__main__":
    main()
