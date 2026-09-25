import random

from game.ai.beliefs import BeliefModel, CueBelief
from game.ai.perception import CueObservation
from game.ai.utility import door_belief, decide, value_of_information, likelihood, effectiveness


def obs(cue, door, polarity=1, clarity=1.0, strength=0.9):
    return CueObservation(f"{cue}_{door}", cue, door, polarity, strength, clarity, True, False)


def trusting(**trust):
    b = BeliefModel()
    for cue, (a, bb) in trust.items():
        b.cues[cue] = CueBelief(a, bb)
    return b


def test_belief_is_a_probability_distribution():
    p = door_belief([obs("owner", 1), obs("scent", 2, -1)], trusting(owner=(20, 2)))
    assert abs(sum(p) - 1) < 1e-9 and max(p) == p[1]


def test_trusted_cue_wins_a_conflict():
    b = trusting(owner=(20, 2), scent=(3, 3))
    d = decide(door_belief([obs("owner", 0), obs("scent", 2)], b), random.Random(0), 0.7)
    assert d.choice == 0


def test_agreeing_cues_reinforce_each_other():
    b = trusting(owner=(10, 3), crowd=(10, 3))
    one = door_belief([obs("owner", 1)], b)[1]
    two = door_belief([obs("owner", 1), obs("crowd", 1)], b)[1]
    assert two > one


def test_no_scent_here_lowers_that_door():
    p = door_belief([obs("scent", 1, polarity=-1)], trusting(scent=(20, 2)))
    assert p[1] < p[0] == p[2]


def test_untrusted_cue_changes_nothing():
    p = door_belief([obs("crowd", 2)], trusting(crowd=(1, 2)))   # trust exactly at chance
    assert all(abs(x - 1 / 3) < 1e-9 for x in p)


def test_no_evidence_means_a_guess():
    assert decide([1 / 3] * 3, random.Random(0), 0.7).mode == "GUESS"


def test_confidence_threshold():
    assert decide([0.8, 0.1, 0.1], random.Random(0), 0.7).mode == "CONFIDENT"
    assert decide([0.6, 0.3, 0.1], random.Random(0), 0.7).mode == "UNSURE"


def test_sniffing_the_last_door_is_worthless_after_elimination():
    b = trusting(scent=(40, 1))
    e = effectiveness(b, "scent", 0.9, 0.85)
    fresh = [1 / 3] * 3
    after_two_empty = door_belief([obs("scent", 0, -1, 0.9, 0.85), obs("scent", 1, -1, 0.9, 0.85)], b)
    assert value_of_information(fresh, fresh, "scent", 2, e) > 0.15
    assert value_of_information(after_two_empty, after_two_empty, "scent", 2, e) < \
        value_of_information(fresh, fresh, "scent", 2, e) / 3


def test_voi_is_zero_for_a_cue_hans_does_not_trust():
    assert value_of_information([1 / 3] * 3, [1 / 3] * 3, "owner", None, 0.0) < 1e-9


def test_likelihoods_are_normalised_for_pointing_cues():
    lik = likelihood("owner", 1, 1, 0.6)
    assert abs(sum(lik) - 1) < 1e-9 and lik[1] > lik[0]
