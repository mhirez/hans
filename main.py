"""LOCKDOWN: break out of the facility, room by room.

    python main.py                 play
    python main.py --floor 3       start on a later floor (3 = the Warden's floor)
    python main.py --boss          straight to the Warden (floor 3, room 4)
    python main.py --xray          start with the AI view on (for demo recordings)
    python main.py --seed 42       the same rooms every time
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
    parser = argparse.ArgumentParser(description="LOCKDOWN: break out of the facility, room by room")
    parser.add_argument("--floor", type=int, default=1, help="floor to start on (1-3)")
    parser.add_argument("--boss", action="store_true", help="go straight to the Warden")
    parser.add_argument("--xray", action="store_true", help="start with the AI view on")
    parser.add_argument("--seed", type=int, default=None, help="random seed for a reproducible run")
    parser.add_argument("--no-sound", action="store_true", help="turn sound off")
    args = parser.parse_args()
    floor, room = (3, 4) if args.boss else (min(3, max(1, args.floor)), 1)
    Game(seed=args.seed, start_floor=floor, start_room=room, xray=args.xray,
         sound=not args.no_sound).run_loop()


if __name__ == "__main__":
    main()
