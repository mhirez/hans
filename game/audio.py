"""Sound effects synthesised at start-up, so the game ships no audio files.

Hoof-falls, kicks and barks are noise bursts through a low-pass filter; bells and the fanfare
are decaying sine partials; whooshes and crunches are sweeping bands of noise. If the mixer can't
start (no audio device, CI), everything silently becomes a no-op.
"""

from array import array
import math
import random

import pygame


class Audio:
    def __init__(self, enabled: bool = True):
        self.ok = False
        self.muted = False
        self.sounds: dict[str, list[pygame.mixer.Sound]] = {}
        self._step = 0
        if not enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.rate, _, self.channels = pygame.mixer.get_init()
            self._build()
            self.ok = True
        except (pygame.error, TypeError, ValueError):
            self.ok = False

    # --- synthesis -------------------------------------------------------------------
    def _sound(self, samples: list[float], volume: float) -> pygame.mixer.Sound:
        peak = max(1e-6, max(abs(s) for s in samples))
        scale = 32000 * volume / peak
        data = array("h", (int(max(-1.0, min(1.0, s / peak)) * scale) for s in samples))
        if self.channels == 2:
            stereo = array("h")
            for v in data:
                stereo.append(v)
                stereo.append(v)
            data = stereo
        return pygame.mixer.Sound(buffer=data.tobytes())

    def _burst(self, seconds, tone, decay, noise_mix, cutoff, rng, wobble=0.0) -> list[float]:
        n = int(self.rate * seconds)
        out, lp, phase = [], 0.0, 0.0
        a = min(1.0, 2 * math.pi * cutoff / self.rate)
        for i in range(n):
            t = i / self.rate
            f = tone * (1 + wobble * math.sin(2 * math.pi * 7 * t))
            phase += 2 * math.pi * f / self.rate
            lp += a * ((rng.random() * 2 - 1) - lp)
            env = math.exp(-t / decay) * min(1.0, i / (self.rate * 0.002) + 0.01)
            out.append(env * ((1 - noise_mix) * math.sin(phase) + noise_mix * lp * 3))
        return out

    def _bell(self, seconds, partials) -> list[float]:
        n = int(self.rate * seconds)
        return [sum(amp * math.exp(-i / self.rate / dec) * math.sin(2 * math.pi * f * i / self.rate)
                    for f, amp, dec in partials) for i in range(n)]

    def _sweep(self, seconds, f0, f1, vibrato=0.0) -> list[float]:
        n = int(self.rate * seconds)
        out, phase = [], 0.0
        for i in range(n):
            t = i / self.rate
            f = f0 + (f1 - f0) * t / seconds
            f *= 1 + vibrato * math.sin(2 * math.pi * 30 * t)
            phase += 2 * math.pi * f / self.rate
            env = min(1.0, t / 0.02, (seconds - t) / 0.05)
            out.append(env * math.sin(phase))
        return out

    def _noise_sweep(self, seconds, c0, c1, rng) -> list[float]:
        """Band of noise whose brightness slides from c0 to c1 Hz: whooshes and crunches."""
        n = int(self.rate * seconds)
        out, lp = [], 0.0
        for i in range(n):
            t = i / self.rate
            cutoff = c0 + (c1 - c0) * t / seconds
            lp += min(1.0, 2 * math.pi * cutoff / self.rate) * ((rng.random() * 2 - 1) - lp)
            out.append(lp * math.sin(math.pi * t / seconds))
        return out

    def _build(self):
        rng = random.Random(1904)
        bark = self._burst(0.09, 420, 0.05, 0.45, 2600, rng) + [0.0] * int(self.rate * 0.05) + \
            self._burst(0.1, 380, 0.05, 0.45, 2600, rng)
        fanfare = []
        for f in (523, 659, 784, 1047):
            fanfare += self._bell(0.16, [(f, 1.0, 0.12), (f * 2, 0.3, 0.08)])
        fanfare += self._bell(0.6, [(1047, 1.0, 0.35), (1568, 0.4, 0.25)])
        self.sounds = {
            "step": [self._sound(self._burst(0.06, 120 + 25 * k, 0.012, 0.75, 1400, rng), 0.16) for k in range(3)],
            "trot": [self._sound(self._burst(0.08, 140 + 20 * k, 0.018, 0.7, 1800, rng), 0.4) for k in range(3)],
            "kick": [self._sound(self._burst(0.16, 90, 0.05, 0.6, 1200, rng), 0.9)],
            "ko": [self._sound(self._sweep(0.4, 220, 80), 0.5)],
            "hurt": [self._sound(self._burst(0.35, 110, 0.12, 0.35, 600, rng), 0.7)],
            "whoosh": [self._sound(self._noise_sweep(0.3, 400, 3000, rng), 0.45)],
            "bark": [self._sound(bark, 0.45)],
            "growl": [self._sound(self._burst(0.4, 80, 0.3, 0.7, 500, rng, wobble=0.3), 0.35)],
            "hmm": [self._sound(self._sweep(0.35, 260, 360), 0.28)],
            "crunch": [self._sound(self._noise_sweep(0.12, 3000, 1200, rng), 0.45)],
            "bell": [self._sound(self._bell(0.7, [(660, 1.0, 0.3), (990, 0.5, 0.2)]), 0.4)],
            "fanfare": [self._sound(fanfare, 0.45)],
            "caught": [self._sound(self._sweep(0.8, 300, 90), 0.5)],
            "creak": [self._sound(self._burst(0.45, 150, 0.25, 0.35, 900, rng, wobble=0.25), 0.3)],
            "slurp": [self._sound(self._noise_sweep(0.35, 600, 1600, rng), 0.3)],
            "click": [self._sound(self._burst(0.02, 900, 0.004, 0.4, 5000, rng), 0.25)],
        }

    # --- playback --------------------------------------------------------------------
    def play(self, name: str):
        if not self.ok or self.muted or name not in self.sounds:
            return
        variants = self.sounds[name]
        self._step = (self._step + 1) % len(variants)
        variants[self._step].play()

    def toggle_mute(self):
        self.muted = not self.muted
