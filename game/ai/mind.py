"""What Hans knows and how he reasons, with no position or timing.

The real-time agent (entities/hans.py, driven by the FSM) and the instant training
simulation (case.py) both call these same methods, so the Hans you investigate was shaped
by exactly the AI you watch.
"""

import random

from game.config import INVESTIGATE_THRESHOLD, MAX_INVESTIGATIONS, CONFIDENT_MARGIN
from game.ai.beliefs import BeliefModel
from game.ai.perception import CueObservation, Senses
from game.ai.utility import AttentionOption, Decision, score_doors, margin, decide, rank_attention


class HansMind:
    def __init__(self, beliefs: BeliefModel | None = None, rng: random.Random | None = None):
        self.beliefs = beliefs or BeliefModel()
        self.rng = rng or random.Random()
        self.readings: dict[str, CueObservation] = {}
        self.studied: set[str] = set()
        self.looked_at: list[str] = []          # what the scientist can see Hans doing
        self.options: list[AttentionOption] = []
        self.decision: Decision | None = None
        self.last_deltas: dict[str, float] = {}

    def start_trial(self):
        self.readings.clear()
        self.studied.clear()
        self.looked_at.clear()
        self.options = []
        self.decision = None
        self.last_deltas = {}

    # --- perception ------------------------------------------------------------------
    def perceive(self, senses: Senses, pos):
        """Passive sweep: keep a reading only if it is new or clearer than the one held."""
        for source in senses.sources():
            obs = senses.observe(source, pos, focused=False)
            if obs is None:
                continue
            held = self.readings.get(source.id)
            if held is None or (not held.focused and obs.clarity > held.clarity + 0.02):
                self.readings[source.id] = obs

    def study(self, senses: Senses, source, pos):
        """A focused look: always replaces what Hans thought before."""
        self.studied.add(source.id)
        self.looked_at.append(source.label)
        obs = senses.observe(source, pos, focused=True)
        if obs is not None:
            self.readings[source.id] = obs

    # --- reasoning -------------------------------------------------------------------
    def scores(self) -> list[float]:
        return score_doors(self.readings.values(), self.beliefs)

    def confident(self) -> bool:
        return margin(self.scores()) >= CONFIDENT_MARGIN

    def plan_attention(self, senses: Senses, travel_times: dict, patience_left: float) -> AttentionOption | None:
        self.options = rank_attention(senses.sources(), self.readings, self.beliefs, travel_times,
                                      patience_left, self.studied, senses.wearing_blinkers)
        if not self.options or len(self.studied) >= MAX_INVESTIGATIONS:
            return None
        best = self.options[0]
        return best if best.utility > INVESTIGATE_THRESHOLD else None

    def decide(self) -> Decision:
        self.decision = decide(self.scores(), self.rng)
        return self.decision

    def learn(self, correct_door: int) -> dict[str, float]:
        self.last_deltas = self.beliefs.learn(self.readings.values(), correct_door)
        return self.last_deltas
