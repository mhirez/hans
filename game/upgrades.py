"""Upgrades: after each floor, pick one of three."""

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class Upgrade:
    key: str
    name: str
    text: str
    icon: str              # a glyph drawn on the card
    limit: int = 3

    def apply(self, player):
        s = player.stats
        if self.key == "rate":
            s.fire_rate *= 1.3
        elif self.key == "damage":
            s.damage += 0.5
        elif self.key == "split":
            s.shots += 1
        elif self.key == "pierce":
            s.pierce += 1
        elif self.key == "bounce":
            s.bounce += 1
        elif self.key == "plating":
            s.max_hp += 2
            player.hp = min(s.max_hp, player.hp + 2)
        elif self.key == "dash":
            s.dash_cooldown *= 0.65
        elif self.key == "ram":
            s.ram = True
        elif self.key == "repair":
            s.repair += 1
        elif self.key == "speed":
            s.speed *= 1.15
            s.bullet_speed *= 1.2
        elif self.key == "deep":
            s.rewrite_time += 4.0
        elif self.key == "overload":
            s.overload *= 1.6
        elif self.key == "spare":
            s.max_charges += 1
            player.charges = min(s.max_charges, player.charges + 1)


ALL = [
    Upgrade("rate", "OVERCLOCK", "Fire 30% faster", ">>>"),
    Upgrade("damage", "HEAVY ROUNDS", "+50% damage per shot", "[#]"),
    Upgrade("split", "SPLIT SHOT", "+1 bullet per shot", "<|>", limit=2),
    Upgrade("pierce", "PIERCING", "Bullets pass through an enemy", "->|", limit=2),
    Upgrade("bounce", "RICOCHET", "Bullets bounce off walls once", "/\\/", limit=2),
    Upgrade("plating", "PLATING", "+2 max health, and heal 2", "+H+"),
    Upgrade("dash", "AFTERBURNER", "Dash recharges 35% faster", "~>", limit=2),
    Upgrade("ram", "RAM DASH", "Dashing through enemies hurts them", "=>*", limit=1),
    Upgrade("repair", "NANO-REPAIR", "Heal 1 after every cleared room", "(+)", limit=2),
    Upgrade("speed", "THRUSTERS", "Move 15% faster, faster bullets", "^^", limit=2),
    Upgrade("deep", "DEEP REWRITE", "Rewritten units stay yours 4 s longer", "{7}", limit=2),
    Upgrade("overload", "OVERLOAD", "Rewritten units explode harder and wider", "(*)", limit=2),
    Upgrade("spare", "SPARE CHARGE", "Hold one more rewrite charge (+1 now)", "<>+", limit=1),
]


def offer(rng: random.Random, taken: list[str], player, n: int = 3) -> list[Upgrade]:
    pool = [u for u in ALL if taken.count(u.key) < u.limit]
    if player.hp <= player.stats.max_hp // 2:
        pool.sort(key=lambda u: u.key != "plating")          # hurt: always offer plating
        first, rest = pool[:1], pool[1:]
        return first + rng.sample(rest, min(n - 1, len(rest)))
    return rng.sample(pool, min(n, len(pool)))
