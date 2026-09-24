"""One case in progress: the scientist's setup, the notebook and the stage of the case.

Stages:  investigate -> verdict -> proof_intro -> proof -> done
Pure logic (no pygame), so the whole flow can be tested headlessly.
"""

from dataclasses import dataclass, asdict
import random

from game.ai.perception import Senses
from game.case import Case, CaseResult, configure_world
from game.entities.hans import Hans
from game.log import ExperimentLog
from game.trial import TrialSetup, Trial, resolve
from game.world import World


@dataclass(frozen=True)
class NotebookEntry:
    number: int
    summary: str
    carrot: int
    looked_at: tuple[str, ...]
    choice: int
    success: bool


class Investigation:
    def __init__(self, case: Case, world: World, rng: random.Random, log: ExperimentLog | None = None):
        self.case = case
        self.world = world
        self.rng = rng
        self.log = log
        self.hans = Hans(world, rng, case.fresh_beliefs())
        self.setup = TrialSetup()
        self.entries: list[NotebookEntry] = []
        self.stage = "investigate"
        self.verdict: str | None = None
        self.prediction: int | None = None
        self.trial: Trial | None = None
        self.running = False
        self.trials_used = 0
        self.xray_used = False
        self.result: CaseResult | None = None
        self._trust_before = None
        self.preview()

    @property
    def trials_left(self) -> int:
        return self.case.budget - self.trials_used

    def preview(self):
        """Show the scientist's current setup in the courtyard (and clear the last result)."""
        if not self.running:
            self.trial = None
            self.hans.outcome = None
            s = self.setup
            self.world.configure(owner_present=s.owner != "absent", owner_far=s.owner_far,
                                 screen=s.screen, crowd_present=s.crowd != "absent")

    def can_run(self) -> bool:
        if self.running:
            return False
        if self.stage == "investigate":
            return self.trials_left > 0
        return self.stage == "proof" and self.prediction is not None

    def run(self) -> bool:
        if not self.can_run():
            return False
        self.trial = resolve(self.setup.copy(), self.rng, self.trials_used + 1)
        configure_world(self.world, self.trial)
        self._trust_before = self.hans.beliefs.snapshot()
        self.hans.begin_trial(Senses(self.world, self.trial, self.rng))
        self.running = True
        return True

    def update(self, dt: float):
        if not self.running:
            return
        self.hans.update(dt)
        if self.hans.done:
            self.running = False
            self._finish()

    def open_verdict(self) -> bool:
        if self.stage == "investigate" and not self.running and self.trials_used > 0:
            self.stage = "verdict"
            return True
        return False

    def cancel_verdict(self):
        if self.stage == "verdict" and self.trials_left > 0:
            self.stage = "investigate"

    def give_verdict(self, cue: str):
        if self.stage == "verdict":
            self.verdict = cue
            self.stage = "proof_intro"

    def begin_proof(self):
        if self.stage == "proof_intro":
            self.stage = "proof"

    def _finish(self):
        o = self.hans.outcome
        if self.stage == "investigate":
            self.trials_used += 1
            self.entries.append(NotebookEntry(self.trials_used, self.trial.setup.summary(), o.carrot,
                                              tuple(self.hans.mind.looked_at), o.choice, o.success))
        elif self.stage == "proof":
            self.result = CaseResult(self.verdict, self.case.truth, self.prediction, o.choice,
                                     self.trials_left, self.xray_used)
            self.stage = "done"
        if self.log is not None:
            self.log.record(
                case=self.case.number, case_seed=self.case.seed, regime=self.case.regime.key,
                truth=self.case.truth, stage="proof" if self.result else "investigate",
                trial=self.trial.number, conditions=self.trial.conditions(),
                readings=[asdict(r) for r in self.hans.mind.readings.values()],
                looked_at=list(self.hans.mind.looked_at), scores=list(o.decision.scores),
                choice=o.choice, mode=o.decision.mode, success=o.success,
                trust_before=self._trust_before, trust_after=self.hans.beliefs.snapshot(),
                verdict=self.verdict, prediction=self.prediction)
