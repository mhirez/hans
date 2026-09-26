"""Barks: short lines enemies say out loud when their state changes (the "F.E.A.R. trick").

Nothing here makes an enemy smarter. It makes the smartness VISIBLE: a scientist who shouts
"Where did he go?" as he switches to SEARCH reads as thinking, where a silent one reads as random.
Every line is triggered by a real state change or decision, so what they say is always true.

Each enemy waits BARK_COOLDOWN between lines, and at most MAX_BUBBLES are on screen at once, so the
courtyard never turns into a wall of text.
"""

from dataclasses import dataclass

BARK_COOLDOWN = 3.0
MAX_BUBBLES = 3
BUBBLE_TIME = 1.9
URGENT = {"spotted", "flee", "kicked", "wary", "cover", "guard", "morale"}

LINES = {
    "scientist": {
        "spotted": ["There he is!", "The horse! Over there!", "Gentlemen, the horse!"],
        "hear": ["What was that?", "Hooves?", "Did you hear that?"],
        "lost": ["Where did he go?", "He was just here...", "Clever horse..."],
        "gave_up": ["Must be the wind.", "Nothing here.", "Hmph."],
        "windup": ["Hold still!", "Got you now!", "Steady..."],
        "kicked": ["Oof!", "Ach, my knee!", "Ow!"],
        "heal": ["I need a coffee...", "Coffee break!", "Just one sip..."],
        "flee": ["Run!", "It's glowing!", "Not the golden hooves!"],
        "morale": ["He's too strong!", "Fall back!", "Retreat!"],
        "flank": ["I'll go round!", "Round the other side!", "Trap him!"],
        "intercept": ["Cut him off!", "Head him off!"],
        "wary": ["Not this time!", "Ha! Missed me!"],
        "guard": ["I'll watch the carrots.", "Nobody touches these."],
        "sweep": ["Check behind the hay!", "He's hiding somewhere..."],
    },
    "stableboy": {
        "spotted": ["Oi! Horse!", "Found him!"],
        "hear": ["Eh?", "Who's there?"],
        "lost": ["Where'd he go?"],
        "gave_up": ["Lost him."],
        "throw": ["Yee-haw!", "Catch!", "Rope's coming!"],
        "kicked": ["Ow!", "Hey!"],
        "heal": ["Coffee time!"],
        "flee": ["Leg it!", "Not me!"],
        "morale": ["I'm off!"],
        "cover": ["Behind the hay!", "Hide!"],
        "wary": ["Missed!", "Too slow!"],
        "guard": ["I'll mind the carrots."],
        "sweep": ["Check the hay!"],
    },
    "dog": {
        "spotted": ["Woof!", "WOOF!", "Woof woof!"],
        "sniff": ["sniff sniff", "*sniff*"],
        "growl": ["Grrr!", "Rrrr!"],
        "kicked": ["Yelp!"],
        "flee": ["Whimper!", "Yip!"],
        "morale": ["Whimper..."],
        "lost": ["Hmm?"],
    },
}


@dataclass(eq=False)
class Bubble:
    enemy: object
    text: str
    age: float = 0.0


class Barks:
    def __init__(self, rng):
        self.rng = rng
        self.bubbles: list[Bubble] = []
        self.cooldown: dict[int, float] = {}
        self.used: dict[tuple, int] = {}

    def say(self, enemy, trigger: str) -> bool:
        lines = LINES.get(enemy.kind, {}).get(trigger)
        if not lines:
            return False
        if self.cooldown.get(enemy.uid, 0.0) > 0 and trigger not in URGENT:
            return False
        if len(self.bubbles) >= MAX_BUBBLES and trigger not in URGENT:
            return False
        key = (enemy.kind, trigger)
        n = self.used.get(key, self.rng.randrange(len(lines)))
        self.used[key] = n + 1                    # cycle through the lines: less repetition
        self.bubbles = [b for b in self.bubbles if b.enemy is not enemy]
        self.bubbles.append(Bubble(enemy, lines[n % len(lines)]))
        self.bubbles = self.bubbles[-MAX_BUBBLES:]
        self.cooldown[enemy.uid] = BARK_COOLDOWN
        return True

    def update(self, dt: float):
        for uid in self.cooldown:
            self.cooldown[uid] -= dt
        for b in self.bubbles:
            b.age += dt
        self.bubbles = [b for b in self.bubbles if b.age < BUBBLE_TIME and not getattr(b.enemy, "gone", False)]
