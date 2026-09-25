import random

from game.ai.temperament import TEMPERAMENTS
from game.case import make_case, train_hans, REGIMES, CaseResult, budget_for
from game.investigation import Investigation
from game.save import Casebook
from game.world import World


def test_case_one_is_the_historical_hans():
    case = make_case(1, random.Random(0))
    assert case.truth == "owner" and case.temperament.key == "steady"
    assert case.truth_margin > 0 and case.budget == 10


def test_regimes_shape_what_hans_learns():
    assert train_hans(REGIMES["lessons"], 7).dominant()[0] == "owner"
    assert train_hans(REGIMES["stable"], 7).dominant()[0] == "scent"
    assert train_hans(REGIMES["fair"], 7, TEMPERAMENTS["thorough"]).dominant()[0] == "crowd"


def test_later_cases_are_generated_and_harder():
    case = make_case(5, random.Random(5))
    assert case.title.startswith("Case 5") and case.truth in ("owner", "scent", "crowd")
    assert budget_for(1) == 10 and budget_for(5) == 8 and budget_for(40) == 6


def test_arrival_beliefs_are_kept_separate_from_the_live_hans():
    case = make_case(1, random.Random(0))
    inv = Investigation(case, World(), random.Random(0))
    inv.hans.beliefs.cues["owner"].beta += 50
    assert case.arrival.trust("owner") > inv.hans.beliefs.trust("owner")


def test_scoring():
    r = CaseResult("owner", "owner", 1, 1, trials_left=3, xray_used=False)
    assert r.score == 95 and r.rank == "Pfungst would be proud."
    assert CaseResult("owner", "owner", 1, 1, 3, False, hints_used=2).score == 85
    assert CaseResult("scent", "owner", 0, 1, 0, False).score == 0


def test_investigation_stage_flow_and_the_commission_rule():
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
    assert inv.setup.carrot is not None and not inv.can_run()
    inv.prediction = inv.setup.carrot
    assert not inv.can_run()                 # predicting success proves nothing
    inv.prediction = (inv.setup.carrot + 1) % 3
    assert inv.run()
    while inv.running:
        inv.update(1 / 30)
    assert inv.stage == "done" and inv.result is not None
    assert len(inv.trust_history) == 3


def test_casebook_round_trip(tmp_path):
    case = make_case(1, random.Random(0))
    inv = Investigation(case, World(), random.Random(0))
    inv.result = CaseResult("owner", "owner", 1, 1, 5, False)
    book = Casebook(tmp_path / "book.json")
    book.record(inv)
    again = Casebook(tmp_path / "book.json")
    assert again.next_case == 2 and again.total_score == book.total_score > 0
