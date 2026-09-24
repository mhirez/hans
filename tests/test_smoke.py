import pygame

from game.app import Game


def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))


def test_game_runs_title_to_a_finished_trial_with_xray():
    game = Game(seed=1, xray=True, log_dir=None)
    seen = set()

    def on_frame(g, n):
        seen.add(g.scenes.name)
        if n in (2, 4):
            key(pygame.K_RETURN)
        if n == 6:
            key(pygame.K_RETURN)      # run the first trial
            key(pygame.K_f)

    game.run(max_frames=900, fixed_dt=1 / 60, on_frame=on_frame)
    assert {"TITLE", "INTRO", "LAB"} <= seen
    assert len(game.inv.entries) >= 1
