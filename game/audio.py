"""Sound effects synthesised at start-up, so the game ships no audio files.

Hoof clops and taps are noise bursts through a low-pass filter; the correct-answer chime is
a pair of decaying bell partials; the crowd is slowly modulated band-limited noise. If the
mixer can't start (no audio device, CI), everything silently becomes a no-op.
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
        self._crowd_channel = None
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

    def _murmur(self, seconds, rng) -> list[float]:
        n = int(self.rate * seconds)
        voices = [(rng.uniform(0.6, 1.6), rng.uniform(0, 6.3)) for _ in range(5)]
        out, lp1, lp2 = [], 0.0, 0.0
        a1, a2 = 2 * math.pi * 900 / self.rate, 2 * math.pi * 250 / self.rate
        for i in range(n):
            t = i / self.rate
            x = rng.random() * 2 - 1
            lp1 += a1 * (x - lp1)
            lp2 += a2 * (lp1 - lp2)
            band = lp1 - lp2
            mod = sum(0.5 + 0.5 * math.sin(2 * math.pi * r * t + p) for r, p in voices) / len(voices)
            fade = min(1.0, t / 0.2, (seconds - t) / 0.2)       # seamless-ish loop
            out.append(band * mod * fade)
        return out

    def _build(self):
        rng = random.Random(1904)
        self.sounds = {
            "clop": [self._sound(self._burst(0.07, 120 + 25 * k, 0.014, 0.75, 1400, rng), 0.35) for k in range(3)],
            "tap": [self._sound(self._burst(0.12, 170, 0.028, 0.6, 2200, rng), 0.8)],
            "sniff": [self._sound(self._burst(0.1, 0, 0.05, 1.0, 3000, rng) + [0.0] * int(self.rate * 0.06)
                                  + self._burst(0.1, 0, 0.05, 1.0, 3000, rng), 0.35)],
            "study": [self._sound(self._burst(0.22, 95, 0.09, 0.8, 600, rng), 0.3)],
            "open": [self._sound(self._burst(0.45, 150, 0.25, 0.35, 900, rng, wobble=0.25), 0.4)],
            "correct": [self._sound(self._bell(0.9, [(880, 1.0, 0.35), (1320, 0.6, 0.25), (1760, 0.25, 0.15)]), 0.45)],
            "wrong": [self._sound(self._burst(0.5, 98, 0.16, 0.3, 500, rng), 0.55)],
            "click": [self._sound(self._burst(0.02, 900, 0.004, 0.4, 5000, rng), 0.25)],
            "page": [self._sound(self._burst(0.16, 0, 0.06, 1.0, 5000, rng), 0.2)],
            "murmur": [self._sound(self._murmur(2.4, rng), 0.18)],
        }

    # --- playback --------------------------------------------------------------------
    def play(self, name: str):
        if not self.ok or self.muted or name not in self.sounds:
            return
        variants = self.sounds[name]
        self._step = (self._step + 1) % len(variants)
        variants[self._step].play()

    def crowd(self, present: bool):
        if not self.ok:
            return
        playing = self._crowd_channel is not None and self._crowd_channel.get_busy()
        if present and not self.muted and not playing:
            self._crowd_channel = self.sounds["murmur"][0].play(loops=-1, fade_ms=400)
        elif (not present or self.muted) and playing:
            self._crowd_channel.fadeout(400)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.crowd(False)
