"""One case in progress: the scientist's setup, the notebook and the stage of the case.

Stages:  investigate -> verdict -> proof_intro -> proof -> done
Pure logic (no pygame), so the whole flow can be tested headlessly.
"""

from dataclasses import dataclass, asdict
import random

from game.ai.perception import Senses
from game.ai.scientist import Observation, Stumpf, Plan, StumpfPilot
from game.case import Case, CaseResult, configure_world
from game.entities.hans import Hans
from game.log import ExperimentLog
from game.trial import TrialSetup, Trial, resolve
from game.world import World


@dataclass(frozen=True)
class NotebookEntry(Observation):
    looked_at: tuple[str, ...]
    success: bool
    mode: str

    @property
    def summary(self) -> str:
        return self.setup.summary(self.owner_door if self.setup.owner in ("misled", "guessing") else None,
                                  self.decoy_door)


class Investigation:
    def __init__(self, case: Case, world: World, rng: random.Random, log: ExperimentLog | None = None):
        self.case = case
        self.world = world
        self.rng = rng
        self.log = log
        self.hans = Hans(world, rng, case.fresh_beliefs(), case.temperament)
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
        self.stumpf = Stumpf()
        self.hints_used = 0
        self.advice: list[str] = []
        self.advice_plan: Plan | None = None
        self._advice_key = None
        self.pilot: StumpfPilot | None = None
        self.trust_history = [case.arrival.snapshot()]
        self._trust_before = None
        self.preview()

    @property
    def trials_left(self) -> int:
        return self.case.budget - self.trials_used

    @property
    def autopilot(self) -> bool:
        return self.pilot is not None

    def preview(self):
        """Show the scientist's current setup in the courtyard (and clear the last result)."""
        if not self.running:
            self.trial = None
            self.hans.outcome = None
            s = self.setup
            self.world.configure(owner_present=s.owner != "absent", owner_far=s.owner_far,
                                 screen=s.screen, crowd_present=s.crowd != "absent")

    # --- the Commission's rule ---------------------------------------------------------
    def proof_problem(self) -> str | None:
        """Why the Commission test can't run yet (None = it can)."""
        if self.setup.carrot is None:
            return "Hide the carrot behind a chosen door (box 1)."
        if self.prediction is None:
            return "Predict the door Hans will tap (box 0)."
        if self.prediction == self.setup.carrot:
            return "Predict his mistake: a door other than the carrot's."
        return None

    def can_run(self) -> bool:
        if self.running:
            return False
        if self.stage == "investigate":
            return self.trials_left > 0
        return self.stage == "proof" and self.proof_problem() is None

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
        if self.pilot is not None:
            self.pilot.update(dt)
        if not self.running:
            return
        self.hans.update(dt)
        if self.hans.done:
            self.running = False
            self._finish()

    # --- stages ------------------------------------------------------------------------
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
            if self.setup.carrot is None:
                self.setup.carrot = 0
                self.preview()

    # --- Professor Stumpf --------------------------------------------------------------
    def ask_stumpf(self) -> bool:
        """Advice costs points once per notebook state; asking again shows the same advice."""
        if self.running or self.stage not in ("investigate", "proof"):
            return False
        key = (self.stage, self.trials_used)
        if key != self._advice_key:
            self._advice_key = key
            if not self.autopilot:
                self.hints_used += 1
            self.advice, self.advice_plan = self.stumpf.advise(self.rng, proof=self.stage == "proof")
        return True

    @property
    def advice_current(self) -> bool:
        return self._advice_key == (self.stage, self.trials_used)

    def apply_advice(self) -> bool:
        if not self.advice_current or self.advice_plan is None or self.running:
            return False
        self.setup = self.advice_plan.setup.copy()
        if self.stage == "proof":
            self.prediction = self.advice_plan.predicted
        self.preview()
        return True

    def start_autopilot(self, pause: float = 1.0):
        if self.pilot is None and self.stage != "done":
            self.pilot = StumpfPilot(self, self.rng, pause)

    def stop_autopilot(self):
        self.pilot = None

    # --- bookkeeping ---------------------------------------------------------------------
    def _finish(self):
        o, t = self.hans.outcome, self.trial
        sniffed = tuple(int(sid.split("_")[1]) for sid in self.hans.mind.studied if sid.startswith("scent_"))
        entry = NotebookEntry(self.trials_used + 1, t.setup, t.carrot, t.owner_door, t.crowd_door, t.decoy_door,
                              tuple(self.hans.mind.studied_cues), o.choice, sniffed,
                              tuple(self.hans.mind.looked_at), o.success, o.decision.mode)
        if self.stage == "investigate":
            self.trials_used += 1
            self.entries.append(entry)
            self.stumpf.observe(entry)
        elif self.stage == "proof":
            self.result = CaseResult(self.verdict, self.case.truth, self.prediction, o.choice, self.trials_left,
                                     self.xray_used, self.hints_used, self.autopilot)
            self.stage = "done"
        self.trust_history.append(self.hans.beliefs.snapshot())
        if self.log is not None:
            self.log.record(
                case=self.case.number, case_seed=self.case.seed, regime=self.case.regime.key,
                temperament=self.case.temperament.key, truth=self.case.truth,
                stage="proof" if self.result else "investigate", autopilot=self.autopilot,
                trial=t.number, conditions=t.conditions(),
                readings=[asdict(r) for r in self.hans.mind.readings.values()],
                looked_at=list(self.hans.mind.looked_at), belief=list(o.decision.belief),
                choice=o.choice, mode=o.decision.mode, success=o.success,
                trust_before=self._trust_before, trust_after=self.hans.beliefs.snapshot(),
                stumpf=self.stumpf.posterior, verdict=self.verdict, prediction=self.prediction)
