import pygame

from game.app import Game


def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))


def test_title_to_playing_with_xray_and_pause():
    game = Game(seed=1, xray=True, save_path=None, sound=False)
    seen = set()

    def on_frame(g, n):
        seen.add(g.scenes.name)
        if n in (2, 5):
            key(pygame.K_RETURN)
        if n == 8:
            g.scripted_move = (1, 0)
        if n == 40:
            key(pygame.K_ESCAPE)
        if n == 45:
            key(pygame.K_RETURN)

    game.run(max_frames=90, fixed_dt=1 / 60, on_frame=on_frame)
    assert {"TITLE", "INTRO", "PLAY"} <= seen
    assert game.play.hans.walked > 0.5 and not game.paused


def test_ai_demo_from_the_title_finishes_the_tutorial():
    game = Game(seed=2, save_path=None, sound=False)
    seen = set()

    def on_frame(g, n):
        seen.add(g.scenes.name)
        if n == 2:
            key(pygame.K_d)
        if n == 5:
            key(pygame.K_RETURN)
        if g.scenes.name in ("WON", "CAUGHT"):
            g.running = False

    game.run(max_frames=3000, fixed_dt=1 / 30, on_frame=on_frame)
    assert "WON" in seen


def test_sound_synthesis_never_breaks_the_game():
    from game.audio import Audio
    pygame.init()
    audio = Audio(True)
    for name in ("step", "trot", "hmm", "alert", "hint", "won", "caught"):
        audio.play(name)
    audio.toggle_mute()
    assert audio.muted
