"""Every Hans has a temperament: the same AI with different motivations.

    patience     seconds he'll spend gathering information before he answers anyway
    speed        tiles per second
    curiosity    how much he values checking cues he's unsure about
    confident_p  how sure he must be (P of his best door) before he stops looking

Temperament shapes both how he behaves in front of you and what he learned in training:
a restless horse rarely walks anywhere, so he learns from whatever he can see from his spot.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Temperament:
    key: str
    description: str
    patience: float
    speed: float
    curiosity: float
    confident_p: float


TEMPERAMENTS = {
    "steady": Temperament("steady", "steady and patient", 14.0, 3.6, 0.25, 0.72),
    "restless": Temperament("restless", "restless and quick to answer", 9.0, 4.4, 0.12, 0.62),
    "thorough": Temperament("thorough", "thorough; he checks everything", 20.0, 3.2, 0.35, 0.85),
    "bold": Temperament("bold", "bold; he trusts his first impression", 12.0, 3.9, 0.08, 0.55),
}
STEADY = TEMPERAMENTS["steady"]
