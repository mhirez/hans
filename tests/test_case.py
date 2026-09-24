import random

from game.case import make_case, train_hans, REGIMES, CaseResult
from game.investigation import Investigation
from game.world import World


def test_case_one_is_the_historical_hans():
    case = make_case(1, random.Random(0))
    assert case.truth == "owner"
    assert case.truth_margin > 0


def test_regimes_shape_what_hans_learns():
    assert train_hans(REGIMES["stable"], 7).dominant()[0] == "scent"
    assert train_hans(REGIMES["fair"], 7).dominant()[0] == "crowd"


def test_later_cases_are_generated():
    case = make_case(2, random.Random(5))
    assert case.title.startswith("Case 2")
    assert case.truth in ("owner", "scent", "crowd")


def test_arrival_beliefs_are_kept_separate_from_the_live_hans():
    case = make_case(1, random.Random(0))
    inv = Investigation(case, World(), random.Random(0))
    inv.hans.beliefs.cues["owner"].beta += 50
    assert case.arrival.trust("owner") > inv.hans.beliefs.trust("owner")


def test_scoring():
    r = CaseResult("owner", "owner", 1, 1, trials_left=3, xray_used=False)
    assert r.score == 95 and r.rank == "Pfungst would be proud."
    assert CaseResult("scent", "owner", 0, 1, 0, False).score == 0


def test_investigation_stage_flow():
    case = make_case(1, random.Random(0))
    inv = Investigation(case, World(), random.Random(0))
    assert not inv.open_verdict()            # need at least one trial first
    assert inv.run()
    while inv.running:
        inv.update(1 / 30)
    assert len(inv.entries) == 1 and inv.trials_left == case.budget - 1
    assert inv.open_verdict()
    inv.give_verdict("owner")
    inv.begin_proof()
    assert not inv.can_run()                 # a prediction is required
    inv.prediction = 0
    assert inv.run()
    while inv.running:
        inv.update(1 / 30)
    assert inv.stage == "done" and inv.result is not None
