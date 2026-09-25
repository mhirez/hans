"""What the scientist sets up (TrialSetup) and the ground truth it resolves to (Trial).

Hans never sees a Trial. Perception reads its `signals` (what each source is actually
giving off) and turns them into noisy observations.
"""

from dataclasses import dataclass, field, asdict
import random

from game.config import (N_DOORS, ROMAN, OWNER_SURE, OWNER_GUESS, CROWD_SAW, CROWD_GUESS,
                         SCENT_PRESENT, SCENT_ABSENT)

OWNER_MODES = ("knows", "guessing", "misled", "absent")
SCENT_MODES = ("normal", "masked", "decoy", "swapped")
CROWD_MODES = ("absent", "saw", "guessing")


@dataclass
class TrialSetup:
    """The scientist's choices. `None` for a door means 'let chance decide'."""
    carrot: int | None = None
    owner: str = "knows"
    misled_to: int | None = None
    owner_far: bool = False
    screen: bool = False
    blinkers: bool = False
    scent: str = "normal"
    decoy_at: int | None = None
    crowd: str = "absent"

    def copy(self) -> "TrialSetup":
        return TrialSetup(**asdict(self))

    def summary(self, misled_to: int | None = None, decoy_at: int | None = None) -> str:
        """Short notebook line, e.g. 'VO misled>I far · screen · blinkers · decoy III · crowd saw'.
        Pass the resolved doors to show where 'Any' actually landed."""
        misled_to = self.misled_to if misled_to is None else misled_to
        decoy_at = self.decoy_at if decoy_at is None else decoy_at
        vo = {"knows": "VO knows", "guessing": "VO guessing", "misled": "VO misled", "absent": "no VO"}[self.owner]
        if self.owner == "misled" and misled_to is not None:
            vo += f">{ROMAN[misled_to]}"
        if self.owner != "absent" and self.owner_far:
            vo += " far"
        parts = [vo]
        if self.screen:
            parts.append("screen")
        if self.blinkers:
            parts.append("blinkers")
        if self.scent == "masked":
            parts.append("scent masked")
        elif self.scent in ("decoy", "swapped"):
            word = "decoy" if self.scent == "decoy" else "only decoy"
            parts.append(word + (f" {ROMAN[decoy_at]}" if decoy_at is not None else ""))
        if self.crowd != "absent":
            parts.append(f"crowd {self.crowd}")
        return " · ".join(parts)


@dataclass(frozen=True)
class Signal:
    door: int
    polarity: int      # +1 "the carrot is here", -1 "not here"
    strength: float


@dataclass
class Trial:
    number: int
    setup: TrialSetup
    carrot: int
    owner_door: int | None      # the door von Osten believes in (and so leans toward)
    crowd_door: int | None
    decoy_door: int | None
    signals: dict[str, Signal] = field(default_factory=dict)

    @property
    def blinkers(self) -> bool:
        return self.setup.blinkers

    def conditions(self) -> dict:
        return {**asdict(self.setup), "carrot": self.carrot, "owner_door": self.owner_door,
                "crowd_door": self.crowd_door, "decoy_door": self.decoy_door}


def _other_door(rng: random.Random, not_this: int, preferred: int | None) -> int:
    if preferred is not None and preferred != not_this:
        return preferred
    return rng.choice([d for d in range(N_DOORS) if d != not_this])


def resolve(setup: TrialSetup, rng: random.Random, number: int = 0) -> Trial:
    carrot = setup.carrot if setup.carrot is not None else rng.randrange(N_DOORS)

    owner_door = None
    if setup.owner == "knows":
        owner_door = carrot
    elif setup.owner == "misled":
        owner_door = _other_door(rng, carrot, setup.misled_to)
    elif setup.owner == "guessing":
        owner_door = rng.randrange(N_DOORS)

    decoy = _other_door(rng, carrot, setup.decoy_at) if setup.scent in ("decoy", "swapped") else None

    crowd_door = None
    if setup.crowd == "saw":
        crowd_door = carrot
    elif setup.crowd == "guessing":   # the crowd watches von Osten too
        crowd_door = owner_door if owner_door is not None else rng.randrange(N_DOORS)

    signals: dict[str, Signal] = {}
    if owner_door is not None:
        signals["owner"] = Signal(owner_door, +1, OWNER_GUESS if setup.owner == "guessing" else OWNER_SURE)
    if crowd_door is not None:
        signals["crowd"] = Signal(crowd_door, +1, CROWD_SAW if setup.crowd == "saw" else CROWD_GUESS)
    smelly = {"normal": {carrot}, "masked": set(), "decoy": {carrot, decoy}, "swapped": {decoy}}[setup.scent]
    for d in range(N_DOORS):
        smells = d in smelly
        signals[f"scent_{d}"] = Signal(d, +1, SCENT_PRESENT) if smells else Signal(d, -1, SCENT_ABSENT)

    return Trial(number, setup, carrot, owner_door, crowd_door, decoy, signals)
