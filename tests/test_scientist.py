import random

from game.ai.scientist import (Stumpf, Observation, choice_model, pointers, candidate_setups, canonical_pointers,
                               evidence_table, N_CANDIDATES)
from game.case import make_case
from game.investigation import Investigation
from game.trial import TrialSetup
from game.world import World


def conflict(number, choice, studied=("owner",), sniffed=()):
    """Carrot I, von Osten misled to II, only a decoy smell at III, crowd saw the carrot (I)."""
    setup = TrialSetup(carrot=0, owner="misled", misled_to=1, scent="swapped", decoy_at=2, crowd="saw")
    return Observation(number, setup, 0, 1, 0, 2, studied, choice, sniffed)


def test_three_way_conflict_separates_every_explanation():
    ptrs = canonical_pointers(TrialSetup(carrot=0, owner="misled", misled_to=1, scent="swapped", decoy_at=2, crowd="saw"))
    favourite = {c: max(range(3), key=lambda d: choice_model(ptrs, c)[d]) for c in ("owner", "scent", "crowd")}
    assert favourite == {"owner": 1, "scent": 2, "crowd": 0}


def test_stumpf_identifies_an_owner_follower():
    s = Stumpf()
    for i in range(3):
        s.observe(conflict(i + 1, choice=1))
    assert s.leader()[0] == "owner" and s.convinced()


def test_stumpf_identifies_a_scent_follower_who_eliminates():
    s = Stumpf()
    for i in range(3):   # sniffed I (nothing), then II (nothing): taps III, the decoy
        s.observe(conflict(i + 1, choice=2, studied=("scent",), sniffed=(0, 1)))
    assert s.leader()[0] == "scent" and s.convinced()


def test_stumpf_only_credits_scent_with_what_was_sniffed():
    ptrs = pointers(TrialSetup(carrot=0, scent="swapped", decoy_at=2), 0, None, None, 2, sniffed=(1,))
    assert ptrs["scent"][0] == [0.5, 0.0, 0.5]       # door II was empty: I or III by elimination


def test_first_experiment_is_the_crucial_one():
    plan = Stumpf().design_test(random.Random(0))
    assert len({d for d in plan.predictions.values() if d is not None}) == 3


def test_proof_predicts_a_wrong_door():
    s = Stumpf()
    for i in range(3):
        s.observe(conflict(i + 1, choice=1))
    plan = s.design_proof(random.Random(1))
    assert plan.predicted != plan.setup.carrot and plan.p_correct > 0.6


def test_candidate_space():
    assert N_CANDIDATES == sum(1 for _ in candidate_setups()) == 84


def test_evidence_table_counts_followed_lies():
    table = evidence_table([conflict(1, choice=1), conflict(2, choice=0)])
    assert table["owner"]["misleading"] == [1, 2]
    assert table["crowd"]["truthful"] == [1, 2]


def test_autopilot_solves_case_one():
    case = make_case(1, random.Random(3))
    inv = Investigation(case, World(), random.Random(3))
    inv.start_autopilot(pause=0.05)
    for _ in range(100_000):
        if inv.stage == "done":
            break
        inv.update(1 / 30)
    assert inv.result is not None and inv.result.verdict == "owner" and inv.result.autopilot
    assert inv.result.predicted != inv.setup.carrot


def test_advice_costs_once_per_notebook_state():
    case = make_case(1, random.Random(0))
    inv = Investigation(case, World(), random.Random(0))
    inv.ask_stumpf()
    inv.ask_stumpf()
    assert inv.hints_used == 1 and inv.advice
    assert inv.apply_advice() and inv.setup.owner in ("knows", "misled", "guessing", "absent")
