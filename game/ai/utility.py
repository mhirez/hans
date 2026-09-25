"""Hans's two decisions.

1. Which door?   Hans keeps a belief P(carrot behind d). Every reading is evidence, weighed by
                 how much he trusts that cue, combined with Bayes' rule, and he taps the door
                 he believes in most.

2. Look closer?  For each source he asks: "if I walked over and studied it, how much more
                 likely would I be to pick the right door?" (expected value of information).
                 Add curiosity about cues he's unsure of, subtract the walk (A* travel time):

                     utility = VOI + curiosity x uncertainty(cue) - TRAVEL_COST x seconds

Because VOI depends on what he already believes, Hans behaves sensibly without special
cases: after two empty doors he doesn't bother sniffing the third, when two cues disagree
he goes to the one that can settle it, and a cue he doesn't trust is never worth the walk.
"""

from dataclasses import dataclass
import random

from game.config import N_DOORS, TRAVEL_COST, STUDY_TIME, FOCUSED_CLARITY, BLINKERS_FOCUSED, TYPICAL_STRENGTH
from game.ai.beliefs import BeliefModel


@dataclass(frozen=True)
class Decision:
    belief: tuple[float, ...]    # P(carrot behind each door)
    choice: int
    mode: str                    # CONFIDENT, UNSURE or GUESS
    margin: float                # P(best) - P(runner-up)


@dataclass(frozen=True)
class AttentionOption:
    source_id: str
    cue: str
    label: str
    voi: float
    curiosity: float
    travel_time: float
    utility: float


# --- the sensor model --------------------------------------------------------------------
def effectiveness(beliefs: BeliefModel, cue: str, clarity: float, strength: float) -> float:
    """0 = tells Hans nothing, 1 = perfectly reliable. Trust above chance x how well he perceived it."""
    return beliefs.weight(cue) * clarity * strength


def likelihood(cue: str, door: int, polarity: int, e: float, n: int = N_DOORS) -> list[float]:
    """P(this reading | carrot behind d), for every door d."""
    if cue == "scent":                          # a yes/no sniff at one door
        hit, false_alarm = 0.5 + 0.5 * e, 0.5 - 0.5 * e
        if polarity > 0:
            return [hit if d == door else false_alarm for d in range(n)]
        return [1 - hit if d == door else 1 - false_alarm for d in range(n)]
    right = 1 / n + (1 - 1 / n) * e             # a pointer at one door (posture, murmur)
    return [right if d == door else (1 - right) / (n - 1) for d in range(n)]


def normalise(p: list[float]) -> list[float]:
    total = sum(p)
    return [x / total for x in p] if total > 0 else [1 / len(p)] * len(p)


def door_belief(readings, beliefs: BeliefModel, n: int = N_DOORS) -> list[float]:
    p = [1 / n] * n
    for r in readings:
        e = effectiveness(beliefs, r.cue, r.clarity, r.strength)
        p = normalise([a * b for a, b in zip(p, likelihood(r.cue, r.door, r.polarity, e, n))])
    return p


# --- decision 1: which door --------------------------------------------------------------
def decide(belief: list[float], rng: random.Random, confident_p: float) -> Decision:
    ordered = sorted(belief, reverse=True)
    if ordered[0] - ordered[-1] < 1e-6:
        return Decision(tuple(belief), rng.randrange(len(belief)), "GUESS", 0.0)
    tied = [i for i, p in enumerate(belief) if ordered[0] - p < 1e-9]
    mode = "CONFIDENT" if ordered[0] >= confident_p else "UNSURE"
    return Decision(tuple(belief), rng.choice(tied), mode, ordered[0] - ordered[1])


# --- decision 2: where to look -----------------------------------------------------------
def value_of_information(before: list[float], now: list[float], cue: str, door: int | None, e: float) -> float:
    """Expected P(right door) after a focused reading, minus P(right door) now.
    `before` is the belief without this source's current (fuzzier) reading, which a closer look replaces."""
    n = len(before)
    if cue == "scent":
        outcomes = [likelihood(cue, door, +1, e, n), likelihood(cue, door, -1, e, n)]
    else:
        outcomes = [likelihood(cue, d, +1, e, n) for d in range(n)]
    expected = sum(max(p * l for p, l in zip(before, lik)) for lik in outcomes)
    return max(0.0, expected - max(now))


def rank_attention(sources, readings: dict, beliefs: BeliefModel, travel_times: dict, patience_left: float,
                   studied: set, blinkers: bool, curiosity: float) -> list[AttentionOption]:
    """Score every source Hans could walk over and study. Best first; unreachable or unaffordable ones dropped."""
    now = door_belief(readings.values(), beliefs)
    options = []
    for s in sources:
        t = travel_times.get(s.id)
        if s.id in studied or t is None or t + STUDY_TIME > patience_left:
            continue
        clarity = BLINKERS_FOCUSED if (blinkers and s.cue == "owner") else FOCUSED_CLARITY[s.cue]
        e = effectiveness(beliefs, s.cue, clarity, TYPICAL_STRENGTH)
        before = door_belief([r for sid, r in readings.items() if sid != s.id], beliefs)
        voi = value_of_information(before, now, s.cue, s.door, e)
        bonus = curiosity * beliefs.uncertainty(s.cue)
        options.append(AttentionOption(s.id, s.cue, s.label, voi, bonus, t, voi + bonus - TRAVEL_COST * t))
    return sorted(options, key=lambda o: o.utility, reverse=True)
