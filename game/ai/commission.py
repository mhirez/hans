"""The Commission: an AI that watches how YOU play and changes the enemies' tactics between waves.

During a wave it keeps simple counts of the player's habits. When the wave ends it compares them
with thresholds and adopts a counter-tactic for the strongest habit it hasn't countered yet.
Tactics are remembered for the rest of the game (the Commission never forgets), up to four.

    habit                                   counter-tactic   what the enemies do
    kicks a lot                             WARY             hop back out of reach when Hans kicks nearby
    gallops a lot                           INTERCEPT        chase where Hans WILL be, not where he is
    hides next to hay and carts             SWEEP            when they lose him, check behind the hay first
    grabs carrots right under their noses   GUARD            one of them stands guard over the carrots

The wave banner tells the player what was learned, so the adaptation is visible, not just felt.
"""

from dataclasses import dataclass, field

from game.level import distance

HABITS = {
    # habit: (tactic, threshold, what the banner says)
    "kicks": ("wary", 7.0, "You kick a lot. Now they jump back from your hooves."),
    "gallop": ("intercept", 0.3, "You gallop a lot. Now they cut you off."),
    "hides": ("sweep", 6.0, "You hide by the hay. Now they check behind it."),
    "greedy": ("guard", 3.0, "You snatch carrots under their noses. Now one guards them."),
}
MAX_TACTICS = 4


@dataclass
class Habits:
    kicks: float = 0.0          # kicks per minute
    moving: float = 0.0         # seconds moving
    galloping: float = 0.0      # seconds galloping
    hides: float = 0.0          # seconds per minute lurking beside tall cover with enemies about
    greedy: float = 0.0         # carrots eaten with an enemy within 3 tiles
    minutes: float = 0.0

    def score(self, habit: str) -> float:
        per_minute = max(self.minutes, 0.25)
        return {"kicks": self.kicks / per_minute,
                "gallop": self.galloping / max(self.moving, 1.0),
                "hides": self.hides / per_minute,
                "greedy": self.greedy}[habit]


@dataclass
class Commission:
    tactics: list[str] = field(default_factory=list)
    habits: Habits = field(default_factory=Habits)
    lessons: list[str] = field(default_factory=list)      # what it learned at the last wave's end

    def has(self, tactic: str) -> bool:
        return tactic in self.tactics

    # --- watching ------------------------------------------------------------------------
    def watch(self, match, dt: float):
        h, level = match.hans, match.level
        self.habits.minutes += dt / 60
        if h.moving:
            self.habits.moving += dt
            if h.galloping:
                self.habits.galloping += dt
        enemies_about = any(e.aware for e in match.enemies)
        if enemies_about and not h.moving:
            c, r = int(h.pos[0]), int(h.pos[1])
            if any(level.blocks_sight(c + dc, r + dr) and level.at(c + dc, r + dr) in "hcs"
                   for dc in (-1, 0, 1) for dr in (-1, 0, 1)):
                self.habits.hides += dt

    def saw_kick(self):
        self.habits.kicks += 1

    def saw_carrot(self, match, pos):
        if any(e.state != "KO" and distance(e.pos, pos) < 3 for e in match.enemies):
            self.habits.greedy += 1

    # --- learning ------------------------------------------------------------------------
    def learn(self) -> list[str]:
        """End of a wave: adopt a counter to the strongest un-countered habit. Returns banner lines."""
        self.lessons = []
        ranked = sorted(HABITS, key=lambda k: self.habits.score(k) / HABITS[k][1], reverse=True)
        for habit in ranked:
            tactic, threshold, line = HABITS[habit]
            if self.habits.score(habit) >= threshold and tactic not in self.tactics and \
                    len(self.tactics) < MAX_TACTICS:
                self.tactics.append(tactic)
                self.lessons.append(line)
                break
        self.habits = Habits()
        return self.lessons
