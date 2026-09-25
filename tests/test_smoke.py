import pygame

from game.app import Game


def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))


def test_game_runs_title_to_a_finished_trial_with_xray():
    game = Game(seed=1, xray=True, log_dir=None, save_path=None, sound=False)
    seen = set()

    def on_frame(g, n):
        seen.add(g.scenes.name)
        if n == 2:
            key(pygame.K_RETURN)      # title -> loading
        if n == 6:
            key(pygame.K_RETURN)      # intro -> lab
        if n == 8:
            key(pygame.K_RETURN)      # run the first trial
            key(pygame.K_f)
        if n == 12:
            key(pygame.K_TAB)

    game.run(max_frames=900, fixed_dt=1 / 60, on_frame=on_frame)
    assert {"TITLE", "LOADING", "INTRO", "LAB"} <= seen
    assert len(game.inv.entries) >= 1


def test_autopilot_demo_from_the_title_reaches_the_case_report():
    game = Game(seed=2, log_dir=None, save_path=None, sound=False)
    seen = set()

    def on_frame(g, n):
        seen.add(g.scenes.name)
        if n == 2:
            key(pygame.K_a)
        if n == 6:
            key(pygame.K_RETURN)
            key(pygame.K_f)
        if g.scenes.name == "RESULT":
            g.running = False

    game.run(max_frames=20_000, fixed_dt=1 / 30, on_frame=on_frame)
    assert "RESULT" in seen and game.inv.result.autopilot


def test_sound_synthesis_never_breaks_the_game():
    from game.audio import Audio
    pygame.init()
    audio = Audio(True)
    audio.play("tap")
    audio.crowd(True)
    audio.toggle_mute()
    assert audio.muted
