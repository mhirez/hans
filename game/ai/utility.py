"""Hans's two decisions, both utility-based.

1. Which door?   score(door) = SUM over readings of  polarity * strength * clarity * weight(cue)
                  ("no scent here" readings count at NEGATIVE_EVIDENCE_SCALE)
2. Look closer?  utility(source) = value of a clearer look + curiosity - cost of walking there

Hans never picks what to study at random: he goes where his own trust says the information is.
That is why watching *where he looks* tells the scientist what he relies on.
"""

from dataclasses import dataclass
import random

from game.config import (N_DOORS, NEGATIVE_EVIDENCE_SCALE, CONFIDENT_MARGIN, CURIOSITY,
                         TRAVEL_COST, STUDY_TIME, FOCUSED_CLARITY, BLINKERS_FOCUSED)
from game.ai.beliefs import BeliefModel


@dataclass(frozen=True)
class Decision:
    scores: tuple[float, ...]
    choice: int
    mode: str          # CONFIDENT, UNSURE or GUESS
    margin: float


@dataclass(frozen=True)
class AttentionOption:
    source_id: str
    cue: str
    label: str
    gain: float
    curiosity: float
    travel_time: float
    utility: float


def score_doors(readings, beliefs: BeliefModel, n_doors: int = N_DOORS) -> list[float]:
    scores = [0.0] * n_doors
    for r in readings:
        e = r.strength * r.clarity * beliefs.weight(r.cue)
        scores[r.door] += e if r.polarity > 0 else -e * NEGATIVE_EVIDENCE_SCALE
    return scores


def margin(scores: list[float]) -> float:
    ordered = sorted(scores, reverse=True)
    return ordered[0] - ordered[1]


def decide(scores: list[float], rng: random.Random) -> Decision:
    if max(abs(s) for s in scores) < 1e-6:
        return Decision(tuple(scores), rng.randrange(len(scores)), "GUESS", 0.0)
    best = max(scores)
    tied = [i for i, s in enumerate(scores) if best - s < 1e-9]
    m = margin(scores)
    return Decision(tuple(scores), rng.choice(tied), "CONFIDENT" if m >= CONFIDENT_MARGIN else "UNSURE", m)


def rank_attention(sources, readings: dict, beliefs: BeliefModel, travel_times: dict,
                   patience_left: float, studied: set, blinkers: bool) -> list[AttentionOption]:
    """Score every source Hans could walk over and study. Best first; unreachable ones dropped."""
    options = []
    for s in sources:
        t = travel_times.get(s.id)
        if s.id in studied or t is None or t + STUDY_TIME > patience_left:
            continue
        expected = BLINKERS_FOCUSED if (blinkers and s.cue == "owner") else FOCUSED_CLARITY[s.cue]
        current = readings[s.id].clarity if s.id in readings else 0.0
        gain = beliefs.weight(s.cue) * max(0.0, expected - current)
        curiosity = CURIOSITY * beliefs.uncertainty(s.cue)
        options.append(AttentionOption(s.id, s.cue, s.label, gain, curiosity, t,
                                       gain + curiosity - TRAVEL_COST * t))
    return sorted(options, key=lambda o: o.utility, reverse=True)
