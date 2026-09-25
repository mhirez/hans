"""Professor Stumpf: a rule-based scientist who reads only the notebook, never Hans's mind.

He holds three explanations: Hans follows von Osten / the scent / the crowd.

  ANALYSE   After each trial he asks, for every explanation, "if this were true, how likely
            was the door Hans tapped?" using a few hand-written rules (a cue Hans relies on is
            followed 80% of the time when he can perceive it; otherwise he falls back on the
            other cues; 15% of any choice is noise), and updates his confidence in each
            (Bayes' rule). He only credits the scent with what Hans could have smelled at the
            doors he actually sniffed. Where Hans walks is evidence too: a horse usually goes
            to study the cue he relies on. How much that says depends on the horse, so Stumpf
            first learns how often *this* Hans studies things at all.

  DESIGN    To choose the next experiment he imagines every setup he could run, predicts what
            Hans would do under each explanation, and picks the one whose outcome would most
            sharpen his beliefs (expected information gain), preferring simpler setups. He
            designs as a sceptic, as if he were less sure than he is, so even a confirming
            experiment is one that could prove him wrong.

  PROVE     For the Commission he looks for the setup where his leading explanation makes a
            confident prediction of Hans tapping the *wrong* door.

The same class gives the player hints and, as StumpfPilot, can run a whole case (autopilot).
"""

from dataclasses import dataclass
import math
import random

from game.config import CUES, N_DOORS, ROMAN
from game.ai.state_machine import State, StateMachine
from game.trial import TrialSetup

FOLLOW = 0.8                # P(Hans follows the cue he relies on, when he can perceive it)
NOISE = 0.15                # allowance for misreads and mistakes: some of every choice is chance
EFFORT = (0.8, 0.2)         # P(studied a hidden/far cue | relies on it), P(... | relies on another)
CONVINCED = 0.95
MIN_TRIALS = 3              # never conclude from fewer trials than this
SIMPLICITY = 0.004          # information-gain penalty per extra manipulation
SCEPTICISM = 0.5            # designs as if less sure: posterior ** 0.5, so tests can still refute him
CUE_PHRASE = {"owner": "von Osten's posture", "scent": "his nose", "crowd": "the crowd"}
CUE_NAME = {"owner": "von Osten", "scent": "the scent", "crowd": "the crowd"}

Dist = list[float]


@dataclass(frozen=True)
class Observation:
    """One notebook line, as the scientist knows it: his setup, where each cue pointed
    (he told von Osten, he placed the scents, he watched the crowd), and what Hans did."""
    number: int
    setup: TrialSetup
    carrot: int
    owner_door: int | None      # where von Osten leaned (None if absent)
    crowd_door: int | None
    decoy_door: int | None
    studied: tuple[str, ...]    # cue types Hans walked over to study
    choice: int
    sniffed: tuple[int, ...]    # doors he sniffed at


# --- the rules ---------------------------------------------------------------------------
def _onehot(d: int) -> Dist:
    return [1.0 if i == d else 0.0 for i in range(N_DOORS)]


UNIFORM: Dist = [1 / N_DOORS] * N_DOORS


SMELLY = {"normal": lambda c, d: {c}, "masked": lambda c, d: set(),
          "decoy": lambda c, d: {c, d}, "swapped": lambda c, d: {d}}


def _spread(doors) -> Dist:
    doors = set(doors)
    return [1 / len(doors) if d in doors else 0.0 for d in range(N_DOORS)]


def pointers(setup: TrialSetup, carrot: int, owner_door, crowd_door, decoy_door,
             sniffed: tuple[int, ...] | None = None) -> dict[str, tuple[Dist | None, float]]:
    """For each cue: which door(s) it indicated (None = no information), and how perceivable it was.
    With `sniffed` given, the scent only says what Hans could have smelled at those doors."""
    out: dict[str, tuple[Dist | None, float]] = {}
    if setup.owner == "absent":
        out["owner"] = (None, 0.0)
    else:
        avail = (0.8 if setup.owner_far else 1.0) * (0.7 if setup.screen else 1.0) * (0.55 if setup.blinkers else 1.0)
        out["owner"] = (_onehot(owner_door) if owner_door is not None else UNIFORM, avail)
    smelly = SMELLY[setup.scent](carrot, decoy_door) - {None}
    if sniffed:
        found = [d for d in sniffed if d in smelly]
        unsniffed = [d for d in range(N_DOORS) if d not in sniffed]
        if found:
            out["scent"] = (_spread(found), 1.0)
        elif unsniffed:                                   # nothing here: by elimination, elsewhere
            out["scent"] = (_spread(unsniffed), 1.0)
        else:
            out["scent"] = (None, 0.0)
    elif sniffed is None and smelly:
        out["scent"] = (_spread(smelly), 1.0)
    else:
        out["scent"] = (None, 0.0)
    if setup.crowd == "absent":
        out["crowd"] = (None, 0.0)
    else:
        out["crowd"] = (_onehot(crowd_door) if crowd_door is not None else UNIFORM, 1.0)
    return out


def choice_model(ptrs: dict, hypothesis: str) -> Dist:
    """P(Hans taps each door | he relies on `hypothesis`)."""
    others = [q for c, (q, a) in ptrs.items() if c != hypothesis and q is not None and a > 0]
    fallback = UNIFORM
    if others:
        mean = [sum(q[d] for q in others) / len(others) for d in range(N_DOORS)]
        fallback = [0.5 * m + 0.5 / N_DOORS for m in mean]
    q, a = ptrs[hypothesis]
    if q is None or a == 0:
        model = fallback
    else:
        follow = [FOLLOW * qd + (1 - FOLLOW) / N_DOORS for qd in q]
        model = [a * f + (1 - a) * r for f, r in zip(follow, fallback)]
    return [(1 - NOISE) * m + NOISE / N_DOORS for m in model]


def observation_pointers(o: Observation) -> dict:
    return pointers(o.setup, o.carrot, o.owner_door, o.crowd_door, o.decoy_door, o.sniffed)


def entropy(p) -> float:
    return -sum(x * math.log(x) for x in p if x > 0)


def _normalise(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


def expected_gain(posterior: dict[str, float], models: dict[str, Dist]) -> float:
    predictive = [sum(posterior[c] * models[c][d] for c in CUES) for d in range(N_DOORS)]
    gain = entropy(posterior.values())
    for d, pd in enumerate(predictive):
        if pd > 1e-12:
            gain -= pd * entropy(_normalise({c: posterior[c] * models[c][d] for c in CUES}).values())
    return gain


def complexity(setup: TrialSetup) -> int:
    base = TrialSetup()
    return sum(getattr(setup, f) != getattr(base, f) for f in ("owner", "owner_far", "screen", "blinkers", "scent", "crowd"))


def candidate_setups():
    """Every experiment worth imagining, with canonical doors: carrot 0, misled 1, decoy 2."""
    for owner in ("knows", "misled", "guessing", "absent"):
        for blinkers in (False, True):
            if owner == "absent" and blinkers:
                continue
            for scent in ("normal", "masked", "decoy", "swapped"):
                for crowd in ("absent", "saw", "guessing"):
                    yield TrialSetup(carrot=0, owner=owner, misled_to=1 if owner == "misled" else None,
                                     blinkers=blinkers, scent=scent,
                                     decoy_at=2 if scent in ("decoy", "swapped") else None, crowd=crowd)


N_CANDIDATES = sum(1 for _ in candidate_setups())


def canonical_pointers(setup: TrialSetup) -> dict:
    owner_door = {"knows": 0, "misled": 1}.get(setup.owner)          # guessing: unknown in advance
    crowd_door = 0 if setup.crowd == "saw" else owner_door
    return pointers(setup, 0, owner_door, crowd_door, setup.decoy_at)


@dataclass(frozen=True)
class Plan:
    setup: TrialSetup
    predictions: dict[str, int | None]      # what Hans should tap under each explanation
    gain: float                             # expected information gain (nats)
    predicted: int | None = None            # for the Commission test: Stumpf's prediction
    p_correct: float = 0.0


def _permute(setup: TrialSetup, perm: list[int]) -> TrialSetup:
    s = setup.copy()
    s.carrot = perm[0]
    s.misled_to = perm[1] if s.owner == "misled" else None
    s.decoy_at = perm[2] if s.scent in ("decoy", "swapped") else None
    return s


def _predictions(models: dict[str, Dist], perm: list[int]) -> dict[str, int | None]:
    out = {}
    for c, m in models.items():
        best = max(range(N_DOORS), key=lambda d: m[d])
        out[c] = perm[best] if m[best] - min(m) > 0.1 else None
    return out


# --- the scientist -----------------------------------------------------------------------
class Stumpf:
    def __init__(self):
        self.log_weight = {c: 0.0 for c in CUES}
        self.observations: list[Observation] = []
        self.history: list[dict[str, float]] = [self.posterior]

    @property
    def posterior(self) -> dict[str, float]:
        top = max(self.log_weight.values())
        return _normalise({c: math.exp(w - top) for c, w in self.log_weight.items()})

    def leader(self) -> tuple[str, float]:
        post = self.posterior
        cue = max(post, key=post.get)
        return cue, post[cue]

    def convinced(self) -> bool:
        return self.leader()[1] >= CONVINCED

    @staticmethod
    def _present(o: Observation) -> list[str]:
        return [c for c, there in (("owner", o.setup.owner != "absent"), ("scent", True),
                                   ("crowd", o.setup.crowd != "absent")) if there]

    def study_rate(self) -> float:
        """How often this Hans walks over to study a cue at all (starts at 1/3, from 3 pseudo-cues)."""
        studied = sum(len(o.studied) for o in self.observations) + 1
        present = sum(len(self._present(o)) for o in self.observations) + 3
        return studied / present

    def likelihoods(self, o: Observation) -> dict[str, float]:
        """P(what Hans did | each explanation): the door he tapped, and which cues he went to study."""
        ptrs = observation_pointers(o)
        rate = self.study_rate()
        habit = {True: (rate + (1 - rate) * 0.5, rate * 0.6),              # P(studied | relies), P(studied | not)
                 False: (1 - rate - (1 - rate) * 0.5, 1 - rate * 0.6)}
        out = {}
        for c in CUES:
            p = choice_model(ptrs, c)[o.choice]
            for cue in self._present(o):
                studied = cue in o.studied
                relies, other = EFFORT if (studied and 0 < ptrs[cue][1] < 1) else habit[studied]
                p *= relies if cue == c else other
            out[c] = max(p, 1e-9)
        return out

    def observe(self, o: Observation):
        """Add a notebook line and re-read the whole notebook (the study habit may have changed)."""
        self.observations.append(o)
        self.log_weight = {c: 0.0 for c in CUES}
        for seen in self.observations:
            for c, p in self.likelihoods(seen).items():
                self.log_weight[c] += math.log(p)
        self.history.append(self.posterior)

    # --- designing experiments ---------------------------------------------------------
    def design_test(self, rng: random.Random) -> Plan:
        post = _normalise({c: p ** SCEPTICISM for c, p in self.posterior.items()})
        scored = []
        for setup in candidate_setups():
            models = {c: choice_model(canonical_pointers(setup), c) for c in CUES}
            scored.append((expected_gain(post, models) - SIMPLICITY * complexity(setup), rng.random(), setup, models))
        gain, _, setup, models = max(scored, key=lambda s: (s[0], s[1]))
        perm = rng.sample(range(N_DOORS), N_DOORS)
        return Plan(_permute(setup, perm), _predictions(models, perm), gain)

    def design_proof(self, rng: random.Random) -> Plan:
        """The setup where Hans is most likely to tap Stumpf's predicted *wrong* door."""
        post = self.posterior
        best = None
        for setup in candidate_setups():
            models = {c: choice_model(canonical_pointers(setup), c) for c in CUES}
            predictive = [sum(post[c] * models[c][d] for c in CUES) for d in range(N_DOORS)]
            d = max(range(1, N_DOORS), key=lambda i: predictive[i])        # never the carrot (door 0)
            key = (round(predictive[d], 3), -complexity(setup), rng.random())
            if best is None or key > best[0]:
                best = (key, setup, models, d, predictive[d])
        _, setup, models, d, p = best
        perm = rng.sample(range(N_DOORS), N_DOORS)
        return Plan(_permute(setup, perm), _predictions(models, perm), expected_gain(post, models), perm[d], p)

    # --- explaining himself ------------------------------------------------------------
    def key_observation(self) -> Observation | None:
        cue, _ = self.leader()
        runner = max((c for c in CUES if c != cue), key=lambda c: self.posterior[c])
        best, best_ratio = None, math.log(1.5)
        for o in self.observations:
            lik = self.likelihoods(o)
            ratio = math.log(lik[cue]) - math.log(lik[runner])
            if ratio > best_ratio:
                best, best_ratio = o, ratio
        return best

    @staticmethod
    def describe(o: Observation) -> str:
        parts = []
        if o.owner_door is not None:
            parts.append(f"von Osten leaned to {ROMAN[o.owner_door]}")
        if o.setup.scent == "decoy" and o.decoy_door is not None:
            parts.append(f"{ROMAN[o.carrot]} and {ROMAN[o.decoy_door]} both smelled")
        elif o.setup.scent == "swapped" and o.decoy_door is not None:
            parts.append(f"only {ROMAN[o.decoy_door]} smelled")
        elif o.setup.scent == "normal":
            parts.append(f"the carrot smelled at {ROMAN[o.carrot]}")
        if o.crowd_door is not None:
            parts.append(f"the crowd murmured toward {ROMAN[o.crowd_door]}")
        return f"Trial {o.number}: " + ", ".join(parts) + f". He tapped {ROMAN[o.choice]}."

    @staticmethod
    def describe_predictions(predictions: dict[str, int | None]) -> str:
        said = [f"{CUE_PHRASE[c]}, {ROMAN[d]}" for c, d in predictions.items() if d is not None]
        return ("If he follows " + "; ".join(said) + ".") if said else ""

    def misleads(self) -> dict[str, int]:
        count = {c: 0 for c in CUES}
        for o in self.observations:
            for c, (q, a) in observation_pointers(o).items():
                if q is not None and a > 0 and q[o.carrot] < 0.99:
                    count[c] += 1
        return count

    def advise(self, rng: random.Random, proof: bool = False) -> tuple[list[str], Plan]:
        cue, p = self.leader()
        lines = []
        if not self.observations:
            lines.append("Begin with a plain trial and watch where Hans goes before he answers.")
        elif p < 0.5:
            lines.append("Too early to say. Every explanation still fits your notebook.")
        elif p < 0.8:
            lines.append(f"A hunch, no more: Hans may follow {CUE_PHRASE[cue]} ({p:.0%}).")
        elif p < CONVINCED:
            lines.append(f"I am fairly sure Hans follows {CUE_PHRASE[cue]} ({p:.0%}).")
        else:
            lines.append(f"Hans follows {CUE_PHRASE[cue]}. I am {p:.0%} sure.")
        key = self.key_observation() if self.observations and p >= 0.5 else None
        if key is not None:
            lines.append(self.describe(key))
        if proof:
            plan = self.design_proof(rng)
            lines.append(f"For the Commission: {plan.setup.summary()}. Carrot behind {ROMAN[plan.setup.carrot]};"
                         f" I predict he taps {ROMAN[plan.predicted]} ({plan.p_correct:.0%}).")
            return lines, plan
        plan = self.design_test(rng)
        if self.convinced() and len(self.observations) >= MIN_TRIALS:
            lines.append("I am convinced. Give your verdict (V).")
        else:
            lines.append(f"Next, try: carrot behind {ROMAN[plan.setup.carrot]}, {plan.setup.summary()}.")
            said = self.describe_predictions(plan.predictions)
            if said:
                lines.append(said)
        worst = max(CUES, key=lambda c: self.misleads()[c])
        if self.misleads()[worst] >= 3:
            lines.append(f"Careful: {CUE_NAME[worst]} has misled him {self.misleads()[worst]} times. "
                         "Each time, Hans learns a little, and your notebook describes him less.")
        return lines, plan


def evidence_table(observations: list[Observation]) -> dict[str, dict[str, list[int]]]:
    """The notebook summed up per cue: [hits, trials] for each kind of trial."""
    table = {c: {"misleading": [0, 0], "truthful": [0, 0], "removed": [0, 0], "studied": [0, 0]} for c in CUES}
    for o in observations:
        for c, (q, a) in observation_pointers(o).items():
            row = table[c]
            row["studied"][1] += 1
            row["studied"][0] += c in o.studied
            if q is None:
                row["removed"][1] += 1
                row["removed"][0] += o.choice == o.carrot
            elif max(q) > 0.99:
                pointed = q.index(max(q))
                kind = "truthful" if pointed == o.carrot else "misleading"
                row[kind][1] += 1
                row[kind][0] += (o.choice == o.carrot) if kind == "truthful" else (o.choice == pointed)
    return table


# --- autopilot: Stumpf runs the case himself ----------------------------------------------
class _Ponder(State):
    name = "PONDER"

    def enter(self, pilot):
        inv = pilot.inv
        cue, p = inv.stumpf.leader()
        if inv.trials_left <= 0 or (inv.trials_used >= MIN_TRIALS and inv.stumpf.convinced()):
            pilot.caption = f"Stumpf: I am {p:.0%} sure. Time for a verdict."
            pilot.plan = None
        else:
            pilot.plan = inv.stumpf.design_test(pilot.rng)
            pilot.caption = (f"Stumpf weighs {N_CANDIDATES} possible experiments"
                             f" (leading idea: {CUE_PHRASE[cue]}, {p:.0%}).")

    def update(self, pilot, dt):
        if pilot.fsm.time_in_state >= pilot.pause:
            pilot.fsm.change(PILOT_CONCLUDE if pilot.plan is None else PILOT_PREPARE)


class _Prepare(State):
    name = "PREPARE"

    def enter(self, pilot):
        pilot.inv.setup = pilot.plan.setup.copy()
        pilot.inv.preview()
        pilot.caption = f"Stumpf sets up: carrot {ROMAN[pilot.plan.setup.carrot]}, {pilot.plan.setup.summary()}."

    def update(self, pilot, dt):
        if pilot.fsm.time_in_state >= pilot.pause and pilot.inv.run():
            pilot.fsm.change(PILOT_WATCH)


class _Watch(State):
    name = "WATCH"

    def update(self, pilot, dt):
        if not pilot.inv.running:
            pilot.fsm.change(PILOT_PONDER)


class _Conclude(State):
    name = "CONCLUDE"

    def enter(self, pilot):
        pilot.inv.open_verdict()

    def update(self, pilot, dt):
        inv = pilot.inv
        if inv.stage == "verdict" and pilot.fsm.time_in_state >= pilot.pause * 1.5:
            inv.give_verdict(inv.stumpf.leader()[0])
        elif inv.stage == "proof_intro" and pilot.fsm.time_in_state >= pilot.pause * 3:
            inv.begin_proof()
            pilot.fsm.change(PILOT_PROVE)


class _Prove(State):
    name = "PROVE"

    def enter(self, pilot):
        plan = pilot.inv.stumpf.design_proof(pilot.rng)
        pilot.inv.setup = plan.setup.copy()
        pilot.inv.prediction = plan.predicted
        pilot.inv.preview()
        pilot.caption = f"Stumpf predicts Hans will tap {ROMAN[plan.predicted]} ({plan.p_correct:.0%})."

    def update(self, pilot, dt):
        if pilot.fsm.time_in_state >= pilot.pause * 1.5 and pilot.inv.run():
            pilot.fsm.change(PILOT_DONE)


class _Done(State):
    name = "DONE"


PILOT_PONDER, PILOT_PREPARE, PILOT_WATCH = _Ponder(), _Prepare(), _Watch()
PILOT_CONCLUDE, PILOT_PROVE, PILOT_DONE = _Conclude(), _Prove(), _Done()


class StumpfPilot:
    """Drives an Investigation through its public methods, like a player would."""

    def __init__(self, inv, rng: random.Random, pause: float = 1.0):
        self.inv = inv
        self.rng = rng
        self.pause = pause
        self.plan: Plan | None = None
        self.caption = ""
        self.fsm = StateMachine(self, PILOT_WATCH if inv.running else PILOT_PONDER)

    def update(self, dt: float):
        self.fsm.update(dt)
