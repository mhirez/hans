"""Hans: catch me if you can.

    python main.py                 play
    python main.py --wave 4        start on a later wave
    python main.py --xray          start with the AI X-Ray on (for demo recordings)
    python main.py --no-sound      silence
"""

import argparse
import importlib.util
import os
import sys
from pathlib import Path


def use_project_venv():
    """Started with a Python that has no pygame? Re-run with the project's .venv if there is one."""
    if importlib.util.find_spec("pygame") is not None:
        return
    venv = Path(__file__).resolve().parent / ".venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if python.exists() and Path(sys.prefix).resolve() != venv.resolve():
        os.execv(str(python), [str(python), *sys.argv])
    sys.exit("pygame-ce is not installed. Run:  pip install -r requirements.txt")


use_project_venv()

from game.app import Game  # noqa: E402


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
