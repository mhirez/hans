"""Cases: each one is a Hans with a hidden training history, and the scientist has to
find out what he learned from it.

A Hans is *not* hand-authored. We pick a training regime (who trained him, and how) and a
temperament, then run TRAINING_TRIALS instant rehearsals through the same HansMind the
player watches. The case's answer is whichever cue he ended up trusting most: emergent,
not scripted.
"""

from dataclasses import dataclass
import random

from game.config import (TRAINING_TRIALS, TRUTH_MARGIN, INVESTIGATION_TRIALS, MIN_TRIALS, STUDY_TIME,
                         CROWD_PATIENCE_DRAIN, START_DELAY, MIN_OBSERVE_TIME, HINT_COST)
from game.ai.beliefs import BeliefModel
from game.ai.mind import HansMind
from game.ai.perception import Senses
from game.ai.temperament import Temperament, TEMPERAMENTS, STEADY
from game.entities.hans import travel_times
from game.trial import Trial, TrialSetup, resolve
from game.world import World, START, center


@dataclass(frozen=True)
class Regime:
    key: str
    trainer: str                 # revealed at the end of the case
    owner: dict[str, float]      # von Osten's mode -> probability
    owner_far: float
    scent: dict[str, float]
    crowd: dict[str, float]


REGIMES = {
    "lessons": Regime(
        "lessons", "Wilhelm von Osten's daily lessons. He always knew the answer and stood close by.",
        owner={"knows": 0.95, "guessing": 0.05}, owner_far=0.1,
        scent={"normal": 0.25, "masked": 0.75}, crowd={"absent": 0.8, "saw": 0.1, "guessing": 0.1}),
    "stable": Regime(
        "stable", "A stable boy who hid carrots in fresh straw and never stayed to watch.",
        owner={"absent": 0.6, "guessing": 0.4}, owner_far=0.5,
        scent={"normal": 1.0}, crowd={"absent": 0.9, "guessing": 0.1}),
    "fair": Regime(
        "fair", "A travelling fair: food stalls everywhere, and the crowd always saw the carrot hidden.",
        owner={"guessing": 0.6, "absent": 0.4}, owner_far=0.5,
        scent={"normal": 0.2, "masked": 0.4, "decoy": 0.4}, crowd={"saw": 0.9, "guessing": 0.1}),
    "mixed": Regime(
        "mixed", "A bit of everything: lessons, shows and games in the stable.",
        owner={"knows": 0.5, "guessing": 0.3, "absent": 0.2}, owner_far=0.3,
        scent={"normal": 0.45, "masked": 0.3, "decoy": 0.25}, crowd={"absent": 0.4, "saw": 0.3, "guessing": 0.3}),
}

PLACES = ["Hamburg", "Elberfeld", "Vienna", "Munich", "Leipzig", "Dresden", "Breslau", "Cologne",
          "Königsberg", "Prague", "Zurich", "Stuttgart"]

CASE_ONE_INTRO = [
    "Berlin, 1904.",
    "Wilhelm von Osten swears his horse can think.",
    "Crowds watch Hans find the hidden carrot, tapping the door's number with his hoof.",
    "You are Oskar Pfungst, a young psychologist. Find out what Hans really reads.",
]
LATER_INTRO = [
    "{place}, {year}.",
    "Another wonder-horse, named Hans after the famous one.",
    "His groom says he is {temperament}.",
    "Find out what this Hans really reads.",
]


def _pick(weights: dict[str, float], rng: random.Random) -> str:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def training_setup(regime: Regime, rng: random.Random) -> TrialSetup:
    return TrialSetup(owner=_pick(regime.owner, rng), owner_far=rng.random() < regime.owner_far,
                      scent=_pick(regime.scent, rng), crowd=_pick(regime.crowd, rng))


def configure_world(world: World, trial: Trial):
    s = trial.setup
    world.configure(owner_present=s.owner != "absent", owner_far=s.owner_far,
                    screen=s.screen, crowd_present=s.crowd != "absent")


def rehearse(mind: HansMind, world: World, trial: Trial, rng: random.Random) -> bool:
    """One trial at instant speed: same perception, attention, decision and learning calls as
    the real-time FSM, with walking replaced by its A* travel time."""
    configure_world(world, trial)
    senses = Senses(world, trial, rng)
    t = mind.temperament
    drain = CROWD_PATIENCE_DRAIN if world.crowd_present else 1.0
    pos, patience = START, t.patience - (START_DELAY + MIN_OBSERVE_TIME) * drain
    mind.start_trial()
    mind.perceive(senses, pos)
    while patience > 0 and not mind.confident():
        option = mind.plan_attention(senses, travel_times(world, pos, senses.sources(), t.speed), patience)
        if option is None:
            break
        source = world.source(option.source_id)
        patience -= (option.travel_time + STUDY_TIME) * drain
        pos = center(source.observe_tile)
        mind.perceive(senses, pos)
        mind.study(senses, source, pos)
    decision = mind.decide()
    mind.learn(senses.reveal())
    return decision.choice == trial.carrot


def train_hans(regime: Regime, seed: int, temperament: Temperament = STEADY,
               trials: int = TRAINING_TRIALS) -> BeliefModel:
    rng = random.Random(seed)
    world, mind = World(), HansMind(BeliefModel(), rng, temperament)
    for i in range(trials):
        rehearse(mind, world, resolve(training_setup(regime, rng), rng, i), rng)
    return mind.beliefs


def budget_for(number: int) -> int:
    """Later cases give the scientist fewer trials: 10, 10, 9, 9, 8, 8, 7, 7, 6..."""
    return max(MIN_TRIALS, INVESTIGATION_TRIALS - (number - 1) // 2)


@dataclass
class Case:
    number: int
    title: str
    intro: list[str]
    regime: Regime
    temperament: Temperament
    seed: int
    arrival: BeliefModel         # Hans's beliefs the day Pfungst arrives (kept untouched)
    truth: str
    truth_margin: float
    budget: int = INVESTIGATION_TRIALS

    def fresh_beliefs(self) -> BeliefModel:
        return self.arrival.copy()


def make_case(number: int, rng: random.Random) -> Case:
    if number == 1:
        regime, temperament, want = REGIMES["lessons"], STEADY, "owner"
        seeds = range(1904, 1904 + 200)
        title, intro = "Case 1: Berlin, 1904", CASE_ONE_INTRO
    else:
        regime, temperament, want = rng.choice(list(REGIMES.values())), rng.choice(list(TEMPERAMENTS.values())), None
        seeds = [rng.randrange(10**9) for _ in range(40)]
        place, year = rng.choice(PLACES), rng.randint(1905, 1913)
        title = f"Case {number}: {place}, {year}"
        intro = [line.format(place=place, year=year, temperament=temperament.description) for line in LATER_INTRO]

    best = None
    for seed in seeds:
        beliefs = train_hans(regime, seed, temperament)
        cue, lead = beliefs.dominant()
        if want is not None and cue != want:
            continue
        if best is None or lead > best[3]:
            best = (seed, beliefs, cue, lead)
        if lead >= TRUTH_MARGIN:
            break
    seed, beliefs, cue, lead = best
    return Case(number, title, intro, regime, temperament, seed, beliefs, cue, lead, budget_for(number))


@dataclass(frozen=True)
class CaseResult:
    verdict: str
    truth: str
    predicted: int
    actual: int
    trials_left: int
    xray_used: bool
    hints_used: int = 0
    autopilot: bool = False

    @property
    def verdict_correct(self) -> bool:
        return self.verdict == self.truth

    @property
    def prediction_correct(self) -> bool:
        return self.predicted == self.actual

    @property
    def score(self) -> int:
        raw = 50 * self.verdict_correct + 30 * self.prediction_correct + 5 * self.trials_left
        return max(0, raw - HINT_COST * self.hints_used)

    @property
    def rank(self) -> str:
        if self.verdict_correct and self.prediction_correct:
            return "Pfungst would be proud."
        if self.verdict_correct:
            return "Right idea, shaky proof."
        if self.prediction_correct:
            return "A lucky demonstration."
        return "Hans fooled you too."
