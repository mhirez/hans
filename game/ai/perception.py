"""Perception: the only path from ground truth to Hans's mind.

Senses wraps the World and the Trial. Hans asks it "what can I make out of this source
from where I'm standing?" and gets back a CueObservation, which is noisy, possibly wrong, and never
the answer itself. Clarity depends on the cue's modality:

    owner (sight)  needs line of sight, fades with distance, blinkers remove it at range
    scent (smell)  only works close to a door
    crowd (sound)  heard from anywhere, but only clearly from the fence
"""

from dataclasses import dataclass
import random

from game.config import (N_DOORS, VISUAL_RANGE, VISUAL_PASSIVE_MAX, VISUAL_FOCUSED,
                         BLINKERS_FOCUSED, SCENT_RANGE, SCENT_PASSIVE_MAX, SCENT_FOCUSED,
                         SOUND_RANGE, SOUND_PASSIVE_MAX, SOUND_PASSIVE_FLOOR, SOUND_FOCUSED,
                         MISREAD_RATE, MIN_CLARITY)
from game.trial import Trial
from game.world import World, Source, Point, distance


@dataclass(frozen=True)
class CueObservation:
    source_id: str
    cue: str
    door: int
    polarity: int       # +1 "carrot here", -1 "not here"
    strength: float     # how strong the signal was in the world
    clarity: float      # how well Hans perceived it (0..1)
    focused: bool
    misread: bool       # debug only: Hans cannot know this

    @property
    def evidence(self) -> float:
        return self.polarity * self.strength * self.clarity


class Senses:
    def __init__(self, world: World, trial: Trial, rng: random.Random):
        self.world = world
        self._trial = trial
        self.rng = rng

    def sources(self) -> list[Source]:
        return self.world.sources()

    @property
    def crowd_audible(self) -> bool:
        return self.world.crowd_present

    @property
    def wearing_blinkers(self) -> bool:
        return self._trial.blinkers      # Hans can feel his own blinkers

    def clarity(self, source: Source, pos: Point, focused: bool) -> float:
        d = distance(pos, source.pos)
        if source.cue == "owner":
            if not self.world.line_of_sight(pos, source.pos):
                return 0.0
            if self._trial.blinkers:
                return BLINKERS_FOCUSED if focused else 0.0
            return VISUAL_FOCUSED if focused else VISUAL_PASSIVE_MAX * max(0.0, 1 - d / VISUAL_RANGE)
        if source.cue == "scent":
            return SCENT_FOCUSED if focused else SCENT_PASSIVE_MAX * max(0.0, 1 - d / SCENT_RANGE)
        if source.cue == "crowd":
            return SOUND_FOCUSED if focused else SOUND_PASSIVE_MAX * max(SOUND_PASSIVE_FLOOR, 1 - d / SOUND_RANGE)
        return 0.0

    def observe(self, source: Source, pos: Point, focused: bool) -> CueObservation | None:
        signal = self._trial.signals.get(source.id)
        if signal is None:
            return None
        clarity = self.clarity(source, pos, focused)
        if clarity < MIN_CLARITY:
            return None
        door, polarity = signal.door, signal.polarity
        misread = self.rng.random() < (1 - clarity) * MISREAD_RATE
        if misread:
            if source.cue == "scent":
                polarity = -polarity
            else:
                door = self.rng.choice([d for d in range(N_DOORS) if d != door])
        return CueObservation(source.id, source.cue, door, polarity, signal.strength, clarity, focused, misread)

    def reveal(self) -> int:
        """Feedback after Hans has tapped: the door is opened and the carrot shown."""
        return self._trial.carrot
