import pygame

from game.app import Game
from tools.autoplay import player


def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))


def test_title_to_play_with_xray_pause_and_bot():
    game = Game(seed=1, xray=True, save_path=None, sound=False)
    game.scripted = player
    seen = set()

    def on_frame(g, n):
        seen.add(g.scenes.name)
        if n == 2:
            key(pygame.K_RETURN)
        if n == 200:
            key(pygame.K_p)
        if n == 205:
            key(pygame.K_p)

    game.run(max_frames=900, fixed_dt=1 / 60, on_frame=on_frame)
    assert {"TITLE", "PLAY"} <= seen and not game.paused
    assert game.match.clock > 10


def test_sound_synthesis_never_breaks_the_game():
    from game.audio import Audio
    pygame.init()
    audio = Audio(True)
    for name in ("step", "trot", "kick", "bark", "whoosh", "fanfare", "caught"):
        audio.play(name)
    audio.toggle_mute()
    assert audio.muted
