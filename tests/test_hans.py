from game.config import STAMINA, HEARTS
from game.entities.hans import Hans
from game.level import Level

YARD = ["##########",
        "#........#",
        "#........#",
        "##########"]


def test_runs_and_is_stopped_by_walls():
    level = Level(YARD)
    h = Hans((2.5, 1.5))
    for _ in range(120):
        h.update(1 / 30, (1, 0), False, level)
    assert 8.0 < h.pos[0] < 9.0


def test_gallop_is_faster_tiring_and_loud():
    level = Level(YARD)
    walker, galloper = Hans((1.5, 1.5)), Hans((1.5, 2.5))
    noises = []
    for _ in range(15):
        walker.update(1 / 30, (1, 0), False, level)
        noises += galloper.update(1 / 30, (1, 0), True, level)
    assert galloper.pos[0] > walker.pos[0] and galloper.stamina < STAMINA and noises


def test_hurt_then_briefly_invulnerable():
    h = Hans((1.5, 1.5))
    assert h.hurt() and not h.hurt()
    assert h.hearts == HEARTS - 1


def test_golden_horseshoe_protects():
    h = Hans((1.5, 1.5))
    h.power_up()
    assert not h.hurt() and h.hearts == HEARTS
    h.tangle()
    assert not h.tangled
