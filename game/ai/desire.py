"""Desirability: how much an enemy wants each thing right now (the "motivations" lecture topic).

Every enemy that knows where Hans is scores its options between 0 and ~1.5 and does the best:

    attack  = aggression x health            (nobody attacks a golden horse)
    flee    = 1.3 if Hans is golden, else  cowardice x wounds x how close Hans is
    heal    = wounds x how close the nearest coffee he has *seen* is x 2  (not dogs)
    cover   = how hard Hans is galloping at him                           (stable boys only)

The scores are shown live in the AI X-Ray, so you can watch a wounded scientist's "heal" overtake
"attack" the moment he spots a coffee cup.
"""

from game.level import distance


def desires(enemy, world) -> dict[str, float]:
    hans = world.hans
    health = enemy.hp / enemy.max_hp
    wounds = 1 - health
    d = distance(enemy.pos, hans.pos)
    scores = {"attack": 0.0 if hans.powered else enemy.aggression * (0.4 + 0.6 * health)}
    scores["flee"] = 1.3 if hans.powered else enemy.cowardice * wounds * max(0.0, 1 - d / 6)
    if enemy.can_heal:
        cup = enemy.known_coffee(world)
        near = max(0.0, 1 - distance(enemy.pos, cup.pos) / 16) if cup else 0.0
        scores["heal"] = wounds * (0.4 + 0.6 * near) * 2.0 if cup else 0.0
    if enemy.can_hide:
        vx, vy = world.hans_velocity
        ex, ey = enemy.pos[0] - hans.pos[0], enemy.pos[1] - hans.pos[1]
        charging = hans.galloping and d < 6 and vx * ex + vy * ey > 0     # galloping AT him
        scores["cover"] = (1.1 - 0.5 * health) if charging else 0.0
    return scores


def best(scores: dict[str, float], current: str | None = None, stickiness: float = 0.12) -> str:
    """The top option, but keep doing the current one unless another beats it clearly (no dithering)."""
    top = max(scores, key=scores.get)
    if current in scores and scores[top] - scores[current] < stickiness:
        return current
    return top
