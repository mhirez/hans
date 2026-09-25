"""Sound effects synthesised at start-up, so the game ships no audio files.

Hoof-falls and taps are noise bursts through a low-pass filter; the bells are decaying sine
partials; the scientist's "hmm?" and police-style whistle are pitch sweeps. If the mixer can't
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

    def _build(self):
        rng = random.Random(1904)
        whistle = self._sweep(0.18, 2100, 2300, 0.03) + [0.0] * int(self.rate * 0.06) + self._sweep(0.32, 2300, 2000, 0.03)
        self.sounds = {
            "step": [self._sound(self._burst(0.06, 120 + 25 * k, 0.012, 0.75, 1400, rng), 0.18) for k in range(3)],
            "trot": [self._sound(self._burst(0.08, 140 + 20 * k, 0.018, 0.7, 1800, rng), 0.5) for k in range(3)],
            "tap": [self._sound(self._burst(0.12, 170, 0.028, 0.6, 2200, rng), 0.8)],
            "hmm": [self._sound(self._sweep(0.35, 260, 360), 0.3)],
            "alert": [self._sound(whistle, 0.35)],
            "hint": [self._sound(self._bell(0.7, [(660, 1.0, 0.3), (990, 0.5, 0.2)]), 0.4)],
            "open": [self._sound(self._burst(0.45, 150, 0.25, 0.35, 900, rng, wobble=0.25), 0.4)],
            "won": [self._sound(self._bell(1.2, [(880, 1.0, 0.45), (1320, 0.6, 0.35), (1760, 0.3, 0.2)]), 0.5)],
            "wrong": [self._sound(self._burst(0.5, 98, 0.16, 0.3, 500, rng), 0.55)],
            "caught": [self._sound(self._sweep(0.6, 300, 110), 0.45)],
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
