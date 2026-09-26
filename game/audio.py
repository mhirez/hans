"""Sound effects and a background pulse, all synthesised at start-up (no audio files).

Zaps are pitch sweeps with a square-ish edge; hits and explosions are filtered noise; beeps and
chimes are decaying sines. If the mixer can't start (no audio device, CI) everything becomes a
silent no-op.
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
        self.music: pygame.mixer.Sound | None = None
        self._next: dict[str, int] = {}
        self._cooldown: dict[str, int] = {}
        if not enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            pygame.mixer.set_num_channels(24)
            self.rate, _, self.channels = pygame.mixer.get_init()
            self._build()
            self.ok = True
        except (pygame.error, TypeError, ValueError):
            self.ok = False

    # --- synthesis -------------------------------------------------------------------------
    def _sound(self, samples: list[float], volume: float) -> pygame.mixer.Sound:
        peak = max(1e-6, max(abs(s) for s in samples))
        k = 32000 * volume / peak
        data = array("h", (int(s * k) for s in samples))
        if self.channels == 2:
            stereo = array("h")
            for v in data:
                stereo.append(v)
                stereo.append(v)
            data = stereo
        return pygame.mixer.Sound(buffer=data.tobytes())

    def _zap(self, seconds, f0, f1, square=0.5, noise=0.0, rng=None, curve=2.0):
        n = int(self.rate * seconds)
        out, phase = [], 0.0
        for i in range(n):
            t = i / n
            f = f1 + (f0 - f1) * (1 - t) ** curve
            phase += 2 * math.pi * f / self.rate
            s = math.sin(phase)
            tone = (1 - square) * s + square * (1 if s >= 0 else -1) * 0.6
            env = (1 - t) ** 1.5 * min(1.0, i / (self.rate * 0.002) + 0.02)
            out.append(env * (tone + (noise * (rng.random() * 2 - 1) if noise else 0.0)))
        return out

    def _noise(self, seconds, cutoff0, cutoff1, rng, decay=1.5, thump=0.0):
        n = int(self.rate * seconds)
        out, lp, phase = [], 0.0, 0.0
        for i in range(n):
            t = i / n
            cutoff = cutoff0 + (cutoff1 - cutoff0) * t
            lp += min(1.0, 2 * math.pi * cutoff / self.rate) * ((rng.random() * 2 - 1) - lp)
            phase += 2 * math.pi * (70 - 30 * t) / self.rate
            env = (1 - t) ** decay * min(1.0, i / (self.rate * 0.002) + 0.02)
            out.append(env * (lp * 2.5 + thump * math.sin(phase)))
        return out

    def _bell(self, seconds, partials):
        n = int(self.rate * seconds)
        return [sum(a * math.exp(-i / self.rate / d) * math.sin(2 * math.pi * f * i / self.rate) for f, a, d in partials)
                for i in range(n)]

    def _silence(self, seconds):
        return [0.0] * int(self.rate * seconds)

    def _build(self):
        rng = random.Random(7)
        z = self._zap
        arp = []
        for f in (523, 659, 784, 1047):
            arp += self._bell(0.1, [(f, 1.0, 0.08), (f * 2, 0.25, 0.05)])
        arp += self._bell(0.5, [(1047, 1.0, 0.25), (1568, 0.4, 0.2)])
        win = []
        for f in (392, 523, 659, 784, 1047, 1319):
            win += self._bell(0.13, [(f, 1.0, 0.1), (f * 1.5, 0.3, 0.08)])
        win += self._bell(1.0, [(1047, 1.0, 0.5), (1319, 0.6, 0.4), (1568, 0.5, 0.4)])
        siren = []
        for _ in range(2):
            siren += z(0.28, 520, 880, square=0.3, curve=1.0) + z(0.28, 880, 520, square=0.3, curve=1.0)
        self.sounds = {
            "shoot": [self._sound(z(0.07, 1500 + 80 * k, 420, square=0.45, noise=0.15, rng=rng), 0.22) for k in range(3)],
            "eshoot": [self._sound(z(0.09, 800 + 40 * k, 220, square=0.6, noise=0.1, rng=rng), 0.2) for k in range(3)],
            "snipe": [self._sound(z(0.18, 2200, 300, square=0.3, noise=0.5, rng=rng), 0.5)],
            "hit": [self._sound(self._noise(0.04, 6000, 3000, rng), 0.3) for _ in range(3)],
            "kill": [self._sound(self._noise(0.35, 1400, 200, rng, 1.2, thump=0.8), 0.55) for _ in range(2)],
            "boom": [self._sound(self._noise(1.1, 1000, 80, rng, 1.0, thump=1.2), 0.8)],
            "hurt": [self._sound(z(0.3, 300, 70, square=0.8, noise=0.4, rng=rng, curve=1.0), 0.6)],
            "dash": [self._sound(self._noise(0.16, 700, 4500, rng, 0.8), 0.3)],
            "alert": [self._sound(z(0.06, 880, 880, 0.5) + self._silence(0.03) + z(0.07, 1320, 1320, 0.5), 0.25)],
            "alarm": [self._sound(siren, 0.22)],
            "laser": [self._sound(z(0.85, 300, 1300, square=0.2, curve=0.6), 0.12)],
            "growl": [self._sound(z(0.5, 90, 150, square=0.9, noise=0.3, rng=rng, curve=0.5), 0.3)],
            "slam": [self._sound(self._noise(0.3, 900, 150, rng, 1.3, thump=1.0), 0.65)],
            "warp": [self._sound(z(0.3, 200, 1700, square=0.2, curve=0.5), 0.22)],
            "pickup": [self._sound(self._bell(0.25, [(1320, 1.0, 0.1), (1980, 0.5, 0.07)]), 0.3)],
            "clear": [self._sound(arp, 0.35)],
            "select": [self._sound(z(0.035, 1500, 1500, 0.5), 0.2)],
            "upgrade": [self._sound(self._bell(0.8, [(523, 1, 0.4), (659, 0.8, 0.4), (784, 0.7, 0.4)]), 0.35)],
            "start": [self._sound(z(0.45, 200, 1200, square=0.3, curve=0.7), 0.25)],
            "win": [self._sound(win, 0.4)],
            "lose": [self._sound(z(1.2, 400, 60, square=0.7, noise=0.2, rng=rng, curve=0.8), 0.5)],
            "sync_in": [self._sound(z(0.35, 900, 140, square=0.2, curve=0.6), 0.25)],
            "sync_out": [self._sound(z(0.25, 140, 700, square=0.2, curve=0.6), 0.2)],
            "hack": [self._sound(self._glitch(rng), 0.4)],
            "denied": [self._sound(z(0.08, 220, 220, 0.9) + self._silence(0.04) + z(0.1, 180, 180, 0.9), 0.25)],
            "charge": [self._sound(self._bell(0.4, [(1760, 1.0, 0.15), (2640, 0.5, 0.1)]), 0.3)],
        }
        self.music = self._sound(self._pulse(rng), 0.28)

    def _glitch(self, rng) -> list[float]:
        """The rewrite: a stuttering, rising digital chirp."""
        out = []
        for k in range(8):
            f = 300 + 180 * k + rng.uniform(-60, 60)
            out += self._zap(0.035, f, f * 1.6, square=0.8)
            out += self._silence(0.01 if k % 3 else 0.02)
        return out + self._zap(0.25, 900, 1800, square=0.4, curve=0.5)

    def _pulse(self, rng) -> list[float]:
        """An 8 s loop: a low bass pulse on every beat and a quiet tick off the beat (120 bpm)."""
        beat = int(self.rate * 0.5)
        notes = [55.0, 55.0, 65.4, 49.0] * 4
        out = []
        for b, f in enumerate(notes):
            lp = 0.0
            for i in range(beat):
                t = i / self.rate
                bass = math.sin(2 * math.pi * f * t) * math.exp(-t * 5) * 0.9
                bass += math.sin(2 * math.pi * f * 2 * t) * math.exp(-t * 9) * 0.25
                tick = 0.0
                if i > beat // 2:
                    tt = (i - beat // 2) / self.rate
                    lp += 0.6 * ((rng.random() * 2 - 1) - lp)
                    tick = (rng.random() * 2 - 1 - lp) * math.exp(-tt * 60) * 0.18
                out.append(bass + tick)
        return out

    # --- playback --------------------------------------------------------------------------
    def play(self, name: str):
        if not self.ok or self.muted or name not in self.sounds:
            return
        variants = self.sounds[name]
        i = self._next.get(name, 0)
        self._next[name] = (i + 1) % len(variants)
        variants[i].play()

    def start_music(self):
        if self.ok and self.music is not None and not self.muted:
            self.music.play(loops=-1)

    def stop_music(self):
        if self.ok and self.music is not None:
            self.music.stop()

    def toggle_mute(self):
        self.muted = not self.muted
        if self.ok:
            if self.muted:
                pygame.mixer.stop()
            elif self.music is not None:
                self.music.play(loops=-1)
