import random

from game.ai.perception import Senses
from game.case import configure_world
from game.trial import TrialSetup, resolve
from game.world import World, START


def make(setup, seed=0):
    rng = random.Random(seed)
    trial = resolve(setup, rng)
    world = World()
    configure_world(world, trial)
    return world, trial, Senses(world, trial, rng)


def test_misled_owner_never_points_at_the_carrot():
    for seed in range(50):
        trial = resolve(TrialSetup(owner="misled"), random.Random(seed))
        assert trial.owner_door != trial.carrot


def test_decoy_never_sits_on_the_carrot():
    for seed in range(50):
        trial = resolve(TrialSetup(scent="decoy"), random.Random(seed))
        assert trial.decoy_door is not None and trial.decoy_door != trial.carrot
        assert trial.signals[f"scent_{trial.decoy_door}"].polarity == 1


def test_guessing_crowd_follows_von_osten():
    for seed in range(20):
        trial = resolve(TrialSetup(owner="misled", crowd="guessing"), random.Random(seed))
        assert trial.crowd_door == trial.owner_door


def test_masked_scent_says_nothing_anywhere():
    trial = resolve(TrialSetup(scent="masked"), random.Random(1))
    assert all(trial.signals[f"scent_{d}"].polarity == -1 for d in range(3))


def test_screen_blocks_the_passive_view_of_von_osten():
    world, _, senses = make(TrialSetup(screen=True))
    owner = world.source("owner")
    assert senses.clarity(owner, START, focused=False) == 0.0
    assert senses.clarity(owner, (world.owner_observe_tile[0] + 0.5, world.owner_observe_tile[1] + 0.5), True) > 0.9


def test_blinkers_hide_von_osten_unless_hans_walks_up():
    world, _, senses = make(TrialSetup(blinkers=True))
    owner = world.source("owner")
    assert senses.clarity(owner, START, focused=False) == 0.0
    assert 0 < senses.clarity(owner, START, focused=True) < 0.5


def test_far_owner_is_harder_to_read():
    near_world, _, near = make(TrialSetup())
    far_world, _, far = make(TrialSetup(owner_far=True))
    assert far.clarity(far_world.source("owner"), START, False) < near.clarity(near_world.source("owner"), START, False)


def test_scent_only_works_up_close():
    world, _, senses = make(TrialSetup())
    door = world.source("scent_1")
    assert senses.clarity(door, START, False) == 0.0
    assert senses.clarity(door, door.pos, False) > 0.7


def test_absent_crowd_is_not_a_source():
    world, _, _ = make(TrialSetup())
    assert world.source("crowd") is None
