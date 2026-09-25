"""Full-screen and overlay cards: title, night intertitles, help, pause, well done, caught, finale."""

import math

import pygame

from game.config import WIDTH, HEIGHT
from game.ui import sprites, theme as T

HELP = [
    ("Walk", "ARROW KEYS (or WASD). Hold SHIFT to trot: fast, but loud."),
    ("The trick", "Stand in von Osten's circle until he nods at a door."),
    ("Tap", "Walk up to that door and press SPACE."),
    ("Scientists", "They see only what their lantern lights.  ?  means suspicious,  !  means chasing."),
    ("Hide", "Stay in the dark and behind hay. Trotting and gravel make noise they can hear."),
]
KEYS = "R restart     Esc pause     X AI X-Ray     M mute     F11 full screen"
CAUGHT_TIPS = [
    "Scientists only see inside their lantern light. Wait in the dark until they turn away.",
    "When you see !, trot away with SHIFT and hide behind hay.",
    "Trotting is loud. Walk when a scientist is close.",
    "A ? is a warning: get out of the light before it fills up.",
]


def star(surface, center, size, filled, empty=T.PAPER_DARK):
    x, y = center
    pts = []
    for i in range(10):
        r = size if i % 2 == 0 else size * 0.45
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
    pygame.draw.polygon(surface, (236, 190, 70) if filled else empty, pts)
    pygame.draw.polygon(surface, T.INK if empty == T.PAPER_DARK else T.INK_FAINT, pts, 2)


def stars(surface, center, count, size=16, total=3, empty=T.PAPER_DARK):
    x, y = center
    gap = size * 2.4
    for i in range(total):
        star(surface, (x + (i - (total - 1) / 2) * gap, y), size, i < count, empty)


class Cards:
    def __init__(self, theme: T.Theme):
        self.theme = theme
        self.blink = 0

    def _film_card(self, surface):
        surface.fill(T.FILM)
        self.theme.ornate_border(surface, pygame.Rect(40, 36, WIDTH - 80, HEIGHT - 72), T.FILM_TEXT, 12)

    def _prompt(self, surface, text, y):
        self.blink += 1
        if (self.blink // 35) % 2 == 0:
            self.theme.text(surface, text, self.theme.serif(22, italic=True), T.FILM_TEXT, (WIDTH // 2, y), "center")

    # --- title -----------------------------------------------------------------------
    def title(self, surface, levels, selected, progress):
        th = self.theme
        self._film_card(surface)
        horse = pygame.Surface((64, 56), pygame.SRCALPHA)
        sprites.hans(horse, (32, 52), facing=1, head="up", tap_up=(self.blink // 20) % 2 == 0)
        horse.fill((*T.FILM_TEXT, 0), special_flags=pygame.BLEND_RGB_MAX)
        surface.blit(pygame.transform.scale(horse, (160, 140)), (WIDTH // 2 - 80, 64))
        th.spaced(surface, "HANS", th.display(96, bold=True), T.FILM_TEXT, (WIDTH // 2, 206), 18, "midtop")
        th.text(surface, "a sneaky game about a clever horse", th.serif(25, italic=True), T.FILM_TEXT,
                (WIDTH // 2, 332), "center")
        th.rule(surface, WIDTH // 2 - 160, WIDTH // 2 + 160, 360, T.FILM_TEXT)

        spec = levels[selected]
        box = pygame.Rect(WIDTH // 2 - 300, 392, 600, 104)
        pygame.draw.rect(surface, (44, 34, 26), box, border_radius=8)
        pygame.draw.rect(surface, T.FILM_TEXT, box, 2, border_radius=8)
        th.text(surface, f"Night {selected}", th.serif(18, italic=True), T.INK_FAINT, (box.centerx, box.y + 12), "midtop")
        th.text(surface, spec.name, th.display(32, bold=True), T.FILM_TEXT, (box.centerx, box.y + 34), "midtop")
        stars(surface, (box.centerx, box.y + 84), progress.stars.get(selected, 0), 11, empty=(60, 50, 40))
        if selected > 0:
            th.text(surface, "<", th.display(40, bold=True), T.FILM_TEXT, (box.x + 30, box.centery), "center")
        if selected < progress.unlocked:
            th.text(surface, ">", th.display(40, bold=True), T.FILM_TEXT, (box.right - 30, box.centery), "center")
        self._prompt(surface, "Press Enter to play", 540)
        th.text(surface, "LEFT / RIGHT  choose a night     D  watch the AI play it     H  how to play     Esc  quit",
                th.type(15), T.FILM_TEXT, (WIDTH // 2, 598), "center")
        total = sum(progress.stars.values())
        th.text(surface, f"{total} of {3 * len(levels)} stars", th.serif(16, italic=True), T.INK_FAINT,
                (WIDTH // 2, 640), "center")
        th.film_overlay(surface)

    # --- intertitle ------------------------------------------------------------------
    def intertitle(self, surface, heading, lines, footer="Press Enter"):
        th = self.theme
        self._film_card(surface)
        th.spaced(surface, heading.upper(), th.display(24, bold=True), T.FILM_TEXT, (WIDTH // 2, 130), 4, "midtop")
        th.rule(surface, WIDTH // 2 - 200, WIDTH // 2 + 200, 174, T.FILM_TEXT)
        y = 250
        for line in lines:
            th.text(surface, line, th.serif(34, italic=True), T.FILM_TEXT, (WIDTH // 2, y), "center")
            y += 58
        self._prompt(surface, footer, HEIGHT - 110)
        th.film_overlay(surface)

    # --- overlays --------------------------------------------------------------------
    def _overlay_card(self, surface, rect):
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((20, 14, 8, 170))
        surface.blit(dim, (0, 0))
        pygame.draw.rect(surface, T.PAPER, rect)
        self.theme.ornate_border(surface, rect, T.INK, 10)

    def help(self, surface):
        th = self.theme
        card = pygame.Rect(150, 80, WIDTH - 300, HEIGHT - 160)
        self._overlay_card(surface, card)
        th.spaced(surface, "HOW TO PLAY", th.display(30, bold=True), T.INK, (WIDTH // 2, 112), 4, "midtop")
        y = 180
        for head, body in HELP:
            th.text(surface, head, th.serif(22, bold=True), T.RED, (card.x + 60, y))
            th.text(surface, body, th.serif(21), T.INK, (card.x + 200, y))
            y += 52
        th.text(surface, KEYS, th.type(15), T.INK_SOFT, (WIDTH // 2, y + 20), "center")
        th.text(surface, "any key to close", th.serif(17, italic=True), T.INK_SOFT, (WIDTH // 2, card.bottom - 36), "center")

    def pause(self, surface):
        th = self.theme
        card = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 120, 520, 240)
        self._overlay_card(surface, card)
        th.spaced(surface, "PAUSED", th.display(34, bold=True), T.INK, (WIDTH // 2, card.y + 40), 6, "midtop")
        for i, line in enumerate(["Enter   carry on", "R   start the night again", "Q   back to the title"]):
            th.text(surface, line, th.type(17, bold=i == 0), T.INK, (WIDTH // 2, card.y + 110 + i * 32), "midtop")

    def won(self, surface, play, last: bool):
        th = self.theme
        card = pygame.Rect(WIDTH // 2 - 330, 130, 660, 440)
        self._overlay_card(surface, card)
        th.spaced(surface, "WELL DONE!", th.display(40, bold=True), T.GREEN, (WIDTH // 2, card.y + 38), 5, "midtop")
        th.text(surface, f"Hans tapped door {play.carrot.name}. The carrot is his.", th.serif(22, italic=True), T.INK,
                (WIDTH // 2, card.y + 112), "center")
        stars(surface, (WIDTH // 2, card.y + 190), play.stars, 30)
        verdict = {3: "Never seen. A true ghost.", 2: "Seen, but never chased.", 1: "Chased, but you made it."}
        th.text(surface, verdict[play.stars], th.serif(20, bold=True), T.INK, (WIDTH // 2, card.y + 250), "center")
        mins, secs = int(play.time) // 60, int(play.time) % 60
        th.text(surface, f"time {mins}:{secs:02d}      times seen {play.seen_count}", th.type(16), T.INK_SOFT,
                (WIDTH // 2, card.y + 290), "center")
        nxt = "Enter   finish the story" if last else "Enter   next night"
        th.text(surface, f"{nxt}        R   play this night again", th.type(16, bold=True), T.INK,
                (WIDTH // 2, card.bottom - 60), "center")

    def caught(self, surface, play, tip_index: int):
        th = self.theme
        card = pygame.Rect(WIDTH // 2 - 330, 150, 660, 400)
        self._overlay_card(surface, card)
        th.spaced(surface, "CAUGHT!", th.display(44, bold=True), T.RED, (WIDTH // 2, card.y + 40), 6, "midtop")
        who = play.caught_by.name if play.caught_by else "A scientist"
        th.text(surface, f"{who} caught Hans sneaking about.", th.serif(23, italic=True), T.INK,
                (WIDTH // 2, card.y + 124), "center")
        th.text(surface, "Tip", th.serif(18, bold=True), T.RED, (WIDTH // 2, card.y + 180), "center")
        for i, line in enumerate(th.wrap(CAUGHT_TIPS[tip_index % len(CAUGHT_TIPS)], th.serif(20), 540)):
            th.text(surface, line, th.serif(20), T.INK, (WIDTH // 2, card.y + 212 + i * 28), "center")
        th.text(surface, "Enter   try again        Esc   title", th.type(16, bold=True), T.INK,
                (WIDTH // 2, card.bottom - 56), "center")

    def finale(self, surface, total_stars, max_stars):
        lines = ["The Commission is baffled.", "They find no trickery at all.", "Clever Hans is famous across Europe."]
        self.intertitle(surface, "The End", lines, "Press Enter")
        th = self.theme
        th.text(surface, "(Later that year, the psychologist Oskar Pfungst worked it out: Hans was reading von Osten all along.)",
                th.serif(18, italic=True), T.INK_FAINT, (WIDTH // 2, 470), "center")
        stars(surface, (WIDTH // 2, 530), 3 if total_stars == max_stars else 2 if total_stars > max_stars // 2 else 1, 18,
              empty=(60, 50, 40))
        th.text(surface, f"{total_stars} of {max_stars} stars", th.serif(18, italic=True), T.FILM_TEXT,
                (WIDTH // 2, 566), "center")
