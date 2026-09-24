from game.ai.beliefs import BeliefModel, CueBelief
from game.ai.perception import CueObservation


def obs(cue, door, polarity=1, clarity=1.0):
    return CueObservation(f"{cue}_src", cue, door, polarity, 0.9, clarity, True, False)


def test_prior_is_half_and_uncertain():
    b = BeliefModel()
    assert b.trust("owner") == 0.5
    assert b.uncertainty("owner") > 0.28


def test_weight_is_zero_at_chance():
    b = BeliefModel()
    b.cues["owner"] = CueBelief(1, 2)          # trust 1/3 = chance with three doors
    assert abs(b.weight("owner")) < 1e-9


def test_correct_claims_raise_trust_and_wrong_ones_lower_it():
    b = BeliefModel()
    b.learn([obs("owner", 1), obs("crowd", 2)], correct_door=1)
    assert b.trust("owner") > 0.5
    assert b.trust("crowd") < 0.5


def test_negative_claims_are_not_learned_from():
    b = BeliefModel()
    b.learn([obs("scent", 0, polarity=-1)], correct_door=2)
    assert abs(b.trust("scent") - 0.5) < 1e-9


def test_clarity_scales_the_update():
    clear, fuzzy = BeliefModel(), BeliefModel()
    clear.learn([obs("owner", 0, clarity=1.0)], 0)
    fuzzy.learn([obs("owner", 0, clarity=0.2)], 0)
    assert clear.trust("owner") > fuzzy.trust("owner") > 0.5


def test_decay_pulls_back_toward_the_prior():
    b = CueBelief(21, 1)
    b.decay(0.5)
    assert b.alpha == 11 and b.beta == 1


def test_copy_is_independent():
    b = BeliefModel()
    c = b.copy()
    c.learn([obs("owner", 0)], 0)
    assert b.trust("owner") == 0.5
