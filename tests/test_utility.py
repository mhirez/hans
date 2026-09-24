import random

from game.ai.beliefs import BeliefModel, CueBelief
from game.ai.perception import CueObservation
from game.ai.utility import score_doors, decide


def obs(cue, door, polarity=1, clarity=1.0, strength=0.9):
    return CueObservation(f"{cue}_{door}", cue, door, polarity, strength, clarity, True, False)


def test_trusted_cue_wins_a_conflict():
    b = BeliefModel()
    b.cues["owner"] = CueBelief(20, 2)
    b.cues["scent"] = CueBelief(3, 3)
    scores = score_doors([obs("owner", 0), obs("scent", 2)], b)
    assert decide(scores, random.Random(0)).choice == 0


def test_no_scent_pushes_a_door_down():
    b = BeliefModel()
    scores = score_doors([obs("scent", 1, polarity=-1)], b)
    assert scores[1] < 0 and scores[0] == scores[2] == 0


def test_no_evidence_means_a_guess():
    d = decide([0.0, 0.0, 0.0], random.Random(0))
    assert d.mode == "GUESS"


def test_useless_cue_is_ignored():
    b = BeliefModel()
    b.cues["crowd"] = CueBelief(1, 2)   # exactly chance
    assert score_doors([obs("crowd", 2)], b) == [0.0, 0.0, 0.0]
