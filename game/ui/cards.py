"""Full-screen and overlay cards: title, help, pause, game over."""

import pygame

from game.config import WIDTH, HEIGHT
from game.ui import sprites, theme as T

HELP = [
    ("Run", "ARROW KEYS (or WASD)"),
    ("Gallop", "hold SHIFT: fast, but it tires you, and they hear it"),
    ("Kick", "SPACE: knocks down anyone close. Two kicks and a scientist is out cold"),
    ("Goal", "eat the carrots to clear each wave. You have 3 hearts"),
    ("Red warning", "a net swing, a pounce or a lasso is coming. Get out of the way!"),
    ("Pick-ups", "sugar cube = a heart back.   golden horseshoe = they run from YOU"),
    ("von Osten", "your owner helps by himself.   E: argue with a scientist   Q: wait / follow"),
    ("Pfungst", "every 5th wave. He marks where he thinks you'll dodge with a chalk X"),
]
KEYS = "P pause     X AI X-Ray     M mute     F11 full screen"

# Silent-film intertitles shown before the first game. Each: (heading, lines).
STORY = [
    ("BERLIN, 1904", ["Clever Hans can count, spell and tell the time.", "Or so they say."]),
    ("HIS REAL GIFT", ["Hans reads people: a glance, a lean, a held breath.",
                       "In this game the RED warnings are Hans reading their tells.",
                       "When you see red, move."]),
    ("THE COMMISSION", ["Thirteen experts want his secret, and they learn as they chase.",
                        "His owner, Wilhelm von Osten, will stand by him.",
                        "And Oskar Pfungst is coming to read Hans back."]),
]


class Cards:
    def __init__(self, theme: T.Theme):
        self.theme = theme
        self.blink = 0

    def _film_card(self, surface):
        surface.fill(T.FILM)
        self.theme.ornate_border(surface, pygame.Rect(40, 36, WIDTH - 80, HEIGHT - 72), T.FILM_TEXT, 12)

    def _prompt(self, surface, text, y, size=26):
        self.blink += 1
        if (self.blink // 30) % 2 == 0:
            self.theme.text(surface, text, self.theme.serif(size, bold=True), T.FILM_TEXT, (WIDTH // 2, y), "center")

    def title(self, surface, best_score, best_wave):
        th = self.theme
        self._film_card(surface)
        horse = pygame.Surface((64, 56), pygame.SRCALPHA)
        sprites.hans(horse, (32, 52), facing=1, head="up", tap_up=(self.blink // 15) % 2 == 0)
        horse.fill((*T.FILM_TEXT, 0), special_flags=pygame.BLEND_RGB_MAX)
        surface.blit(pygame.transform.scale(horse, (160, 140)), (WIDTH // 2 - 80, 70))
        th.spaced(surface, "HANS", th.display(100, bold=True), T.FILM_TEXT, (WIDTH // 2, 212), 18, "midtop")
        th.text(surface, "catch me if you can", th.serif(28, italic=True), T.FILM_TEXT, (WIDTH // 2, 342), "center")
        th.rule(surface, WIDTH // 2 - 160, WIDTH // 2 + 160, 372, T.FILM_TEXT)
        self._prompt(surface, "Press ENTER to play", 430, 30)
        keys = [("ARROWS", "run"), ("SHIFT", "gallop"), ("SPACE", "kick")]
        x = WIDTH // 2 - 300
        for key, what in keys:
            self._key(surface, key, (x + 60, 510))
            th.text(surface, what, th.serif(22, italic=True), T.FILM_TEXT, (x + 60, 548), "center")
            x += 200
        if best_score:
            th.text(surface, f"Best: {best_score} points, wave {best_wave}", th.serif(19, italic=True),
                    T.INK_FAINT, (WIDTH // 2, 604), "center")
        th.text(surface, "H  how to play       Esc  quit", th.type(14), T.INK_FAINT, (WIDTH // 2, 640), "center")
        th.film_overlay(surface)

    def _key(self, surface, label, center):
        font = self.theme.type(18, bold=True)
        img = font.render(label, True, T.INK)
        box = img.get_rect(center=center).inflate(26, 16)
        pygame.draw.rect(surface, T.PAPER, box, border_radius=6)
        pygame.draw.rect(surface, T.FILM_TEXT, box, 2, border_radius=6)
        surface.blit(img, img.get_rect(center=box.center))

    def _overlay_card(self, surface, rect):
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((20, 14, 8, 170))
        surface.blit(dim, (0, 0))
        pygame.draw.rect(surface, T.PAPER, rect)
        self.theme.ornate_border(surface, rect, T.INK, 10)

    def help(self, surface):
        th = self.theme
        card = pygame.Rect(150, 90, WIDTH - 300, HEIGHT - 180)
        self._overlay_card(surface, card)
        th.spaced(surface, "HOW TO PLAY", th.display(30, bold=True), T.INK, (WIDTH // 2, 120), 4, "midtop")
        y = 186
        for head, body in HELP:
            th.text(surface, head, th.serif(22, bold=True), T.RED, (card.x + 60, y))
            th.text(surface, body, th.serif(21), T.INK, (card.x + 230, y))
            y += 46
        th.text(surface, KEYS, th.type(15), T.INK_SOFT, (WIDTH // 2, y + 16), "center")
        th.text(surface, "any key to close", th.serif(17, italic=True), T.INK_SOFT, (WIDTH // 2, card.bottom - 34), "center")

    def pause(self, surface):
        th = self.theme
        card = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 120, 520, 240)
        self._overlay_card(surface, card)
        th.spaced(surface, "PAUSED", th.display(34, bold=True), T.INK, (WIDTH // 2, card.y + 40), 6, "midtop")
        for i, line in enumerate(["P or Enter   carry on", "R   start again", "Q   back to the title"]):
            th.text(surface, line, th.type(17, bold=i == 0), T.INK, (WIDTH // 2, card.y + 110 + i * 32), "midtop")

    def story(self, surface, page: int):
        th = self.theme
        heading, lines = STORY[page]
        self._film_card(surface)
        th.spaced(surface, heading, th.display(54, bold=True), T.FILM_TEXT, (WIDTH // 2, 150), 10, "midtop")
        th.rule(surface, WIDTH // 2 - 200, WIDTH // 2 + 200, 250, T.FILM_TEXT)
        for i, line in enumerate(lines):
            th.text(surface, line, th.serif(30, italic=True), T.FILM_TEXT, (WIDTH // 2, 320 + i * 52), "center")
        dots = "   ".join("o" if i == page else "." for i in range(len(STORY)))
        th.text(surface, dots, th.type(18, bold=True), T.INK_FAINT, (WIDTH // 2, 560), "center")
        self._prompt(surface, "ENTER  next" if page < len(STORY) - 1 else "ENTER  run, Hans!", 604, 24)
        th.text(surface, "Esc  skip", th.type(14), T.INK_FAINT, (WIDTH // 2, 646), "center")
        th.film_overlay(surface)

    def game_over(self, surface, match, best_score: int, new_best: bool):
        th = self.theme
        card = pygame.Rect(WIDTH // 2 - 340, 110, 680, 480)
        self._overlay_card(surface, card)
        th.spaced(surface, "CAUGHT!", th.display(48, bold=True), T.RED, (WIDTH // 2, card.y + 36), 6, "midtop")
        by = getattr(match.caught_by, "kind", None)
        line = ("Pfungst read you, just as he read Hans in 1907." if by == "pfungst"
                else "The Commission finally has its clever horse.")
        th.text(surface, line, th.serif(22, italic=True), T.INK, (WIDTH // 2, card.y + 124), "center")
        note = match.notebook_line()
        if note:
            th.text(surface, note, th.serif(16, italic=True), T.INK_SOFT, (WIDTH // 2, card.y + 152), "center")
        th.text(surface, f"{match.score}", th.display(64, bold=True), T.INK, (WIDTH // 2, card.y + 196), "center")
        th.text(surface, "NEW BEST!" if new_best else f"best {best_score}", th.serif(20, bold=new_best),
                T.GREEN if new_best else T.INK_SOFT, (WIDTH // 2, card.y + 248), "center")
        stats = [("wave", match.wave.number), ("carrots", match.carrots_total), ("knocked out", match.knockouts)]
        x = WIDTH // 2 - 220
        for label, value in stats:
            th.text(surface, str(value), th.display(34, bold=True), T.INK, (x, card.y + 312), "center")
            th.text(surface, label, th.serif(17, italic=True), T.INK_SOFT, (x, card.y + 346), "center")
            x += 220
        th.text(surface, "ENTER  play again          Esc  title", th.type(17, bold=True), T.INK,
                (WIDTH // 2, card.bottom - 56), "center")
