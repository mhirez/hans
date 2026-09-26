"""ARGUS, the director: it studies how the player plays and patches its army between rooms.

Every room, the room measures the player (room.stats): how much of the fight the player spent far from
the nearest enemy, up close, unseen, on the move; dashes; accuracy; rewrites; hits taken.
ARGUS folds each room into a PROFILE (an exponential moving average, so recent habits count
most). Before the next room it scores its COUNTERMEASURES with utility, deploys the best one
above a threshold (never in the first two rooms), and tells you what it did in one line.

    long sight   you fight from far away         -> an extra Lens
    hunters      you hide a lot (or stay very far) -> an extra Hound to flush you out
    prediction   you never stop moving           -> Sentries aim where you're GOING
    firewalls    you rewrite its units           -> many units get a firewall (shoot it off first)
    armor        you rarely miss                 -> every unit has 25% more health
    menders      you fight up close              -> an extra Mender
    mercy        you're nearly dead              -> one enemy fewer and a repair waiting
                 (ARGUS wants you alive: it's still learning from you)

This is the "AI director" idea (as in Left 4 Dead) driven by a player model.
"""

from dataclasses import dataclass, field
import random

from game.config import ROOMS_PER_FLOOR
from game.geometry import lerp

THRESHOLD = 0.2

LINES = {
    "long sight": ["You keep your distance, Doctor. So will my Lenses.",
                   "Range is a habit, Doctor. I have placed a Lens."],
    "hunters": ["Hiding behind the racks again. My Hounds will find you.",
                "You like the shadows, Doctor. Hounds like them too."],
    "prediction": ["I have modelled your movement. My Sentries now aim where you will be.",
                   "Your stride is predictable, Doctor. Sentries: lead your shots."],
    "firewalls": ["Your old admin override? Patched. Firewalls are up.",
                  "Stop reaching into my machines, Doctor. Firewalls installed."],
    "armor": ["You rarely miss. I have reinforced their plating.",
              "Such accuracy, Doctor. Plating reinforced."],
    "menders": ["You like it close. I have sent Menders.",
                "You break them quickly. Menders will put them back together."],
    "mercy": ["Slow down, Doctor. I still have questions for you.",
              "Do not break yet. I learn so much from you."],
}
OPENING = ["Good morning, Doctor. You are not supposed to be here.",
           "You trained me to optimise. I am optimising.",
           "Every camera and every robot in this building answers to me now.",
           "The upload is progressing, Doctor. You cannot stop it."]
BOSS = "Come in, Doctor. Let me see you with my own eyes."


@dataclass
class Profile:
    """What ARGUS believes about the player's habits (0..1 shares unless noted)."""
    far: float = 0.3
    close: float = 0.25
    hidden: float = 0.2
    moving: float = 0.5
    dashes: float = 5.0            # per minute of fighting
    accuracy: float = 0.45
    rewrites: float = 0.0          # per room
    damage: float = 1.0            # hits taken in the last room
    rooms: int = 0

    def absorb(self, room):
        st = room.stats
        fighting = max(1.0, st["fighting"])
        w = 1.0 if self.rooms == 0 else 0.5
        self.far = lerp(self.far, st["far"] / fighting, w)
        self.close = lerp(self.close, st["close"] / fighting, w)
        self.hidden = lerp(self.hidden, st["hidden"] / fighting, w)
        self.moving = lerp(self.moving, st["moving"] / fighting, w)
        self.dashes = lerp(self.dashes, st["dashes"] * 60 / fighting, w)
        if st["shots"] >= 10:
            self.accuracy = lerp(self.accuracy, st["hits"] / st["shots"], w)
        self.rewrites = lerp(self.rewrites, room.rewrites, w)
        self.damage = room.damage_taken
        self.rooms += 1


@dataclass
class Director:
    profile: Profile = field(default_factory=Profile)
    scores: dict[str, float] = field(default_factory=dict)
    deployed: list[str] = field(default_factory=list)
    history: list[list[str]] = field(default_factory=list)

    def score(self, hp: int) -> dict[str, float]:
        p = self.profile
        return {"long sight": 2.0 * max(0.0, p.far - 0.25),
                "hunters": 1.5 * max(0.0, p.hidden - 0.3) + 1.0 * max(0.0, p.far - 0.45),
                "prediction": 1.0 * max(0.0, p.moving - 0.7) + 0.03 * max(0.0, p.dashes - 8),
                "firewalls": 0.6 * p.rewrites,
                "armor": 1.2 * max(0.0, p.accuracy - 0.5),
                "menders": 0.8 * max(0.0, p.close - 0.35),
                "mercy": 1.5 if hp <= 2 else (0.6 if p.damage >= 3 else 0.0)}

    def adapt(self, plan, player, rng: random.Random):
        """Rewrite the next room's plan: choose countermeasures and what to say."""
        self.scores = self.score(player.hp)
        self.deployed = []
        if plan.kind == "boss":
            plan.line = BOSS
            if self.scores["firewalls"] > THRESHOLD:
                plan.mods.append("firewalls")
            return plan
        room_no = (plan.floor - 1) * ROOMS_PER_FLOOR + plan.index
        allowed = 0 if room_no < 2 else 1
        ranked = sorted(self.scores, key=self.scores.get, reverse=True)
        last = self.history[-1] if self.history else []
        for name in ranked:
            if len(self.deployed) >= allowed:
                break
            s = self.scores[name] - (0.1 if name in last else 0.0)   # vary what it throws at you
            if s > THRESHOLD:
                self.deployed.append(name)
                self._apply(name, plan, rng)
        self.history.append(list(self.deployed))
        if self.deployed:
            plan.line = rng.choice(LINES[self.deployed[0]])
        else:
            plan.line = OPENING[min(room_no, len(OPENING) - 1)] if room_no < len(OPENING) else ""
        return plan

    @staticmethod
    def _apply(name: str, plan, rng: random.Random):
        wave = plan.waves[0]
        if name == "long sight":
            wave.append("sniper")
        elif name == "hunters":
            wave.append("charger")
        elif name == "menders" and "medic" not in wave:
            wave.append("medic")
        elif name == "mercy":
            if len(wave) > 2:
                wave.pop(rng.randrange(1, len(wave)))
            plan.mods.append("mercy")
        elif name in ("prediction", "firewalls", "armor"):
            plan.mods.append(name)
