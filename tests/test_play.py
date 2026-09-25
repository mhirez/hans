import random

from game.ai.ghost import Ghost, danger_map
from game.config import HINT_TIME
from game.levels import LEVELS
from game.play import Play
from game.save import Progress


def play_with(ghost, night, seed=0, limit=150):
    play = Play(night, LEVELS[night], random.Random(seed))
    while play.state == "playing" and play.time < limit:
        move, trot, tap = ghost.act(play)
        play.update(1 / 30, move, trot)
        if tap:
            play.tap()
    return play


def test_tutorial_can_be_won_and_the_tips_advance():
    play = play_with(Ghost(), 0)
    assert play.state == "won" and play.hint_known and play.stars == 3
    assert play.tip is None


def test_von_osten_nods_only_while_hans_stays_close():
    play = Play(0, LEVELS[0], random.Random(1))
    play.hans.pos = (play.owner.pos[0] + 1.0, play.owner.pos[1])
    for _ in range(int((HINT_TIME + 0.2) * 30)):
        play.update(1 / 30, (0, 0), False)
    assert play.hint_known and "hint" in play.drain_events()


def test_wrong_door_is_loud():
    play = Play(1, LEVELS[1], random.Random(2))
    wrong = next(d for d in play.level.doors if d is not play.carrot)
    play.hans.pos = wrong.front
    assert not play.tap()
    assert wrong.index in play.opened
    assert any(s.state == "INVESTIGATE" for s in play.scientists)


def test_cannot_tap_while_chased():
    play = Play(1, LEVELS[1], random.Random(3))
    play.hans.pos = play.carrot.front
    play.scientists[0].fsm.change(__import__("game.ai.scientist", fromlist=["CHASE"]).CHASE)
    assert not play.tap() and play.state == "playing"


def test_careful_ghost_wins_the_first_nights():
    for night in (1, 2):
        assert play_with(Ghost(), night, seed=night).state == "won"


def test_danger_map_is_a_probability_grid():
    heat = danger_map(LEVELS[1], seconds=10)
    flat = [v for row in heat for v in row]
    assert 0 <= min(flat) and max(flat) <= 1 and max(flat) > 0


def test_assist_calms_the_scientists():
    easy = Play(1, LEVELS[1], random.Random(0), assist=2)
    assert easy.scientists[0].slow < 1 and easy.scientists[0].calm < 1


def test_progress_round_trip(tmp_path):
    p = Progress(tmp_path / "p.json")
    p.record(0, 3, len(LEVELS) - 1)
    p.record(0, 1, len(LEVELS) - 1)
    again = Progress(tmp_path / "p.json")
    assert again.unlocked == 1 and again.stars == {0: 3}
