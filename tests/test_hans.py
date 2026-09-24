import random

from game.ai.beliefs import BeliefModel, CueBelief
from game.ai.perception import Senses
from game.case import configure_world
from game.entities.hans import Hans
from game.trial import TrialSetup, resolve
from game.world import World


def run_trial(hans, world, setup, rng, limit=60.0):
    trial = resolve(setup, rng)
    configure_world(world, trial)
    hans.begin_trial(Senses(world, trial, rng))
    t = 0.0
    while not hans.done and t < limit:
        hans.update(1 / 60)
        t += 1 / 60
    return trial, t


def owner_follower():
    b = BeliefModel()
    b.cues["owner"] = CueBelief(20, 2)
    return b


def test_full_cycle_through_every_state():
    rng = random.Random(1)
    world = World()
    hans = Hans(world, rng)
    _, t = run_trial(hans, world, TrialSetup(), rng)
    assert hans.done and hans.state == "WAITING"
    history = list(hans.fsm.history)
    for state in ("OBSERVING", "DECIDING", "ANSWERING", "LEARNING"):
        assert state in history
    assert t < 40


def test_owner_follower_is_fooled_by_a_misled_owner():
    rng = random.Random(2)
    world = World()
    fooled = 0
    for _ in range(8):
        hans = Hans(world, rng, owner_follower())
        trial, _ = run_trial(hans, world, TrialSetup(owner="misled", scent="masked"), rng)
        fooled += hans.outcome.choice == trial.owner_door
    assert fooled >= 6


def test_blinkered_owner_follower_walks_over_to_look():
    rng = random.Random(3)
    world = World()
    hans = Hans(world, rng, owner_follower())
    run_trial(hans, world, TrialSetup(blinkers=True), rng)
    assert "von Osten" in hans.mind.looked_at


def test_every_trial_teaches_hans():
    rng = random.Random(4)
    world = World()
    hans = Hans(world, rng, owner_follower())
    before = hans.beliefs.trust("owner")
    for _ in range(4):
        run_trial(hans, world, TrialSetup(owner="misled"), rng)
    assert hans.beliefs.trust("owner") < before
