"""The six nights. Each teaches one new idea; the map legend is in level.py.

Scientist routes are strings of waypoint digits: "12" walks 1 -> 2 -> 1 ..., "5" is a sentry
standing at 5, and a sentry's facing is given after it: > v < ^ (right, down, left, up) or
e q z c (up-right, up-left, down-left, down-right), e.g. "5v" or "5q". A trailing "o" makes a
patroller keep his lantern on von Osten as he walks: "3456o".
Tips are the on-screen tutorial: shown one at a time until their condition is met.
"""

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Tip:
    text: str                           # may contain {door}, the carrot door's number
    target: str | None                  # what the arrow points at: hans, owner, door, scientist
    done: Callable = lambda play: False


@dataclass(frozen=True)
class LevelSpec:
    name: str
    intro: tuple[str, ...]
    map: tuple[str, ...]
    scientists: tuple[str, ...] = ()
    tips: tuple[Tip, ...] = field(default_factory=tuple)


def _moved(play) -> bool:
    return play.hans.walked > 1.5


def _hint(play) -> bool:
    return play.hint_known


def _won(play) -> bool:
    return play.state == "won"


LEVELS = [
    LevelSpec(
        "Learning the Trick",
        ("Berlin, 1904.", "Everyone thinks Clever Hans can think.",
         "His secret: his owner, von Osten, can't help nodding toward the right answer."),
        ("#####D#####D#####D#####",
         "#.....................#",
         "#.....................#",
         "#.....................#",
         "#.....................#",
         "#...O.................#",
         "#.....................#",
         "#.....................#",
         "#..............H......#",
         "#.....................#",
         "#######################"),
        tips=(
            Tip("Use the ARROW KEYS (or WASD) to walk.", "hans", _moved),
            Tip("This is von Osten. He knows which door hides the carrot. Walk into his circle.", "owner",
                lambda p: p.owner.progress > 0.05 or p.hint_known),
            Tip("Stay in his circle and watch his head...", "owner", _hint),
            Tip("He nodded at door {door}! Walk up to door {door}.", "door", lambda p: p.near_carrot() or _won(p)),
            Tip("Press SPACE to tap the door with your hoof.", "door", _won),
        ),
    ),
    LevelSpec(
        "The Night Watch",
        ("The Commission has sent a scientist", "to watch Hans through the night.",
         "Stay out of his lantern light."),
        ("#######D######D######D#######",
         "#...........................#",
         "#.....1...............2.....#",
         "#...........................#",
         "#...........................#",
         "#.....hh.............hh.....#",
         "#.....hh.............hh.....#",
         "#...........................#",
         "#..O........................#",
         "#...........................#",
         "#.................H.........#",
         "#...........................#",
         "#############################"),
        scientists=("12",),
        tips=(
            Tip("A scientist! He sees only what his lantern lights. Keep to the dark.", "scientist",
                lambda p: p.time > 5 or p.hans.walked > 4),
            Tip("If he spots you he shows ?  Get out of the light before it turns to !", "scientist",
                lambda p: p.time > 11 or p.hint_known),
            Tip("First, get von Osten's nod.", "owner", _hint),
            Tip("Wait until his back is turned, then sneak to door {door} and press SPACE.", "door",
                lambda p: _won(p) or p.chased_now),
            Tip("He's chasing you! Trot away with SHIFT and hide in the dark. You can't tap while chased.", "hans",
                lambda p: _won(p) or not p.chased_now),
            Tip("Now sneak to door {door} and press SPACE.", "door", _won),
        ),
    ),
    LevelSpec(
        "Behind the Hay",
        ("Two scientists now.", "One stands guard over von Osten himself,",
         "sweeping his lantern. Light can't pass through hay."),
        ("#######D#######D#######D#######",
         "#.............................#",
         "#..1.......................2..#",
         "#.............................#",
         "#.............................#",
         "#......hh.............hh......#",
         "#......hh.............hh......#",
         "#.............................#",
         "#.............................#",
         "#...O.........................#",
         "#.............................#",
         "#.....hh......................#",
         "#.............................#",
         "#.......5...............H.....#",
         "#.............................#",
         "###############################"),
        scientists=("5q", "12"),
        tips=(
            Tip("A guard is watching von Osten! Lantern light stops at hay bales.", "scientist",
                lambda p: p.time > 7),
            Tip("Stand on the far side of von Osten, where the hay hides you from the lantern.", "owner",
                lambda p: p.time > 16 or p.hint_known),
        ),
    ),
    LevelSpec(
        "Gravel and Hooves",
        ("Someone has spread gravel across the yard.", "Scientists can't see in the dark,",
         "but they can hear."),
        ("#######D######D######D#######",
         "#...........................#",
         "#.....1...............2.....#",
         "#...........................#",
         "#.......hh....3.....hh....O.#",
         "#.......hh..........hh......#",
         "#gggggggggggg...gggggggggggg#",
         "#gggggggggggg...gggggggggggg#",
         "#...........................#",
         "#.....hh.............hh.....#",
         "#.............4.............#",
         "#...........................#",
         "#...H.......................#",
         "#############################"),
        scientists=("34", "12"),
        tips=(
            Tip("Hold SHIFT to trot: fast, but scientists HEAR it. Rings show how far a sound carries.", None,
                lambda p: p.time > 7),
            Tip("The quiet path through the gravel is guarded. Gravel crunches even at a walk: "
                "cross it slowly, far from the scientists.", None, lambda p: p.time > 16 or p.hint_known),
        ),
    ),
    LevelSpec(
        "The Wandering Master",
        ("Von Osten is restless tonight.", "He walks about the yard,",
         "and only nods when he stands still."),
        ("#######D######D######D#######",
         "#...........................#",
         "#..O.....................x..#",
         "#...........................#",
         "#.....hh....1.....2..hh.....#",
         "#.....hh.............hh.....#",
         "#...........................#",
         "#....3..ccc.......ccc..4....#",
         "#...........................#",
         "#.............y.............#",
         "#...........................#",
         "#.....hh.............hh.....#",
         "#.............H.............#",
         "#############################"),
        scientists=("12", "34"),
        tips=(
            Tip("Von Osten walks between spots. Catch him when he stops.", "owner", lambda p: p.time > 8),
        ),
    ),
    LevelSpec(
        "The Commission",
        ("September 1904. The Commission itself.", "One of them circles von Osten all night.",
         "Four doors. Prove that Clever Hans is clever."),
        ("######D#####D#####D#####D######",
         "#.............................#",
         "#.1.........................2.#",
         "#..............8..............#",
         "#...ss...................ss...#",
         "#.........3.........4.........#",
         "#ggggg..................ggggg.#",
         "#...........hh.hh.............#",
         "#..............O..............#",
         "#.............................#",
         "#ggggg...hh.........hh..ggggg.#",
         "#.........6.........5.........#",
         "#.............................#",
         "#.....ccc.............ccc...7.#",
         "#..............H..............#",
         "###############################"),
        scientists=("12", "3456o", "7q", "8v"),
    ),
]
