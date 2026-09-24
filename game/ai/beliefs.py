"""How much Hans trusts each cue type: a Beta(alpha, beta) success/failure count per cue.

    trust  = alpha / (alpha + beta)          starts at 0.5 (alpha = beta = 1)
    weight = how far trust is above chance    0 means "no better than guessing a door"

After every trial each positive claim Hans perceived ("the carrot is behind II") is checked
against the revealed door; alpha grows when it was right, beta when it was wrong, scaled by how
clearly Hans perceived it. Evidence decays a little every trial so Hans can re-learn when the
world changes, which is exactly what the scientist's experiments do to him.
"""

from dataclasses import dataclass
import math

from game.config import CUES, N_DOORS, PRIOR, DECAY


@dataclass
class CueBelief:
    alpha: float = PRIOR
    beta: float = PRIOR

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def std(self) -> float:
        a, b = self.alpha, self.beta
        return math.sqrt(a * b / ((a + b) ** 2 * (a + b + 1)))

    @property
    def evidence(self) -> float:
        return self.alpha + self.beta - 2 * PRIOR

    def decay(self, rate: float = DECAY):
        self.alpha = PRIOR + (self.alpha - PRIOR) * rate
        self.beta = PRIOR + (self.beta - PRIOR) * rate

    def update(self, correct: bool, weight: float = 1.0):
        if correct:
            self.alpha += weight
        else:
            self.beta += weight


class BeliefModel:
    def __init__(self, cues=CUES):
        self.cues: dict[str, CueBelief] = {c: CueBelief() for c in cues}

    def trust(self, cue: str) -> float:
        return self.cues[cue].mean

    def weight(self, cue: str) -> float:
        chance = 1 / N_DOORS
        return max(0.0, (self.trust(cue) - chance) / (1 - chance))

    def uncertainty(self, cue: str) -> float:
        return self.cues[cue].std

    def learn(self, observations, correct_door: int) -> dict[str, float]:
        """Decay all beliefs, then score every positive claim. Returns the change in trust per cue."""
        before = {c: self.trust(c) for c in self.cues}
        for belief in self.cues.values():
            belief.decay()
        for obs in observations:
            if obs.polarity > 0:
                self.cues[obs.cue].update(obs.door == correct_door, obs.clarity)
        return {c: self.trust(c) - before[c] for c in self.cues}

    def ranking(self) -> list[tuple[str, float]]:
        return sorted(((c, self.weight(c)) for c in self.cues), key=lambda cw: cw[1], reverse=True)

    def dominant(self) -> tuple[str, float]:
        """The cue Hans leans on most, and its lead over the runner-up."""
        (top, w1), (_, w2) = self.ranking()[:2]
        return top, w1 - w2

    def snapshot(self) -> dict[str, dict[str, float]]:
        return {c: {"alpha": round(b.alpha, 3), "beta": round(b.beta, 3), "trust": round(b.mean, 3)}
                for c, b in self.cues.items()}

    def copy(self) -> "BeliefModel":
        clone = BeliefModel(tuple(self.cues))
        for c, b in self.cues.items():
            clone.cues[c] = CueBelief(b.alpha, b.beta)
        return clone
