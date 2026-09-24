"""Full-screen and overlay cards: the title, silent-film intertitles, the verdict and the case report."""

import pygame

from game.config import WIDTH, HEIGHT, CUES, CUE_LABELS, ROMAN
from game.ui import sprites, theme as T

VERDICT_HINTS = {"owner": "he reads his questioner's body",
                 "scent": "he smells where the carrot is",
                 "crowd": "he listens to the audience"}


class Cards:
    def __init__(self, theme: T.Theme):
        self.theme = theme
        self.verdict_rects = {cue: pygame.Rect(WIDTH // 2 - 280, 250 + i * 70, 560, 56) for i, cue in enumerate(CUES)}
        self.blink = 0.0

    def _film_card(self, surface):
        surface.fill(T.FILM)
        self.theme.ornate_border(surface, pygame.Rect(40, 36, WIDTH - 80, HEIGHT - 72), T.FILM_TEXT, 12)

    def _prompt(self, surface, text, y):
        self.blink += 1
        if (self.blink // 35) % 2 == 0:
            self.theme.text(surface, text, self.theme.serif(20, italic=True), T.FILM_TEXT, (WIDTH // 2, y), "center")

    # --- title -----------------------------------------------------------------------
    def title(self, surface):
        th = self.theme
        self._film_card(surface)
        horse = pygame.Surface((64, 56), pygame.SRCALPHA)
        sprites.hans(horse, (32, 52), facing=1, head="up", tap_up=True)
        horse.fill((*T.FILM_TEXT, 0), special_flags=pygame.BLEND_RGB_MAX)
        surface.blit(pygame.transform.scale(horse, (192, 168)), (WIDTH // 2 - 96, 88))
        th.spaced(surface, "HANS", th.display(110, bold=True), T.FILM_TEXT, (WIDTH // 2, 270), 18, "midtop")
        th.text(surface, "a game about learning the wrong clues", th.serif(26, italic=True), T.FILM_TEXT,
                (WIDTH // 2, 410), "center")
        th.rule(surface, WIDTH // 2 - 160, WIDTH // 2 + 160, 440, T.FILM_TEXT)
        th.text(surface, "Berlin, 1904", th.display(24), T.FILM_TEXT, (WIDTH // 2, 470), "center")
        self._prompt(surface, "Press Enter to begin", 560)
        th.text(surface, "X  AI X-Ray      F  fast-forward      Esc  quit", th.type(14), T.INK_FAINT,
                (WIDTH // 2, 640), "center")
        th.film_overlay(surface)

    # --- intertitle ------------------------------------------------------------------
    def intertitle(self, surface, heading, lines):
        th = self.theme
        self._film_card(surface)
        th.spaced(surface, heading.upper(), th.display(22, bold=True), T.FILM_TEXT, (WIDTH // 2, 120), 4, "midtop")
        th.rule(surface, WIDTH // 2 - 200, WIDTH // 2 + 200, 160, T.FILM_TEXT)
        y = 220
        for line in lines:
            for wrapped in th.wrap(line, th.serif(30, italic=True), WIDTH - 300):
                th.text(surface, wrapped, th.serif(30, italic=True), T.FILM_TEXT, (WIDTH // 2, y), "center")
                y += 46
            y += 14
        self._prompt(surface, "Press Enter", HEIGHT - 110)
        th.film_overlay(surface)

    # --- overlays --------------------------------------------------------------------
    def _overlay_card(self, surface, rect):
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((20, 14, 8, 170))
        surface.blit(dim, (0, 0))
        pygame.draw.rect(surface, T.PAPER, rect)
        self.theme.ornate_border(surface, rect, T.INK, 10)

    def verdict(self, surface, mouse, trials_left):
        th = self.theme
        card = pygame.Rect(WIDTH // 2 - 330, 120, 660, 470)
        self._overlay_card(surface, card)
        th.spaced(surface, "YOUR VERDICT", th.display(28, bold=True), T.INK, (WIDTH // 2, 150), 4, "midtop")
        th.text(surface, "What does Hans really rely on?", th.serif(22, italic=True), T.INK_SOFT,
                (WIDTH // 2, 210), "center")
        for i, cue in enumerate(CUES):
            r = self.verdict_rects[cue]
            hover = r.collidepoint(mouse)
            pygame.draw.rect(surface, T.PAPER_DARK if hover else T.PAPER, r, border_radius=4)
            pygame.draw.rect(surface, T.INK, r, 2 if hover else 1, border_radius=4)
            key = pygame.Rect(r.x + 12, r.y + 14, 28, 28)
            pygame.draw.rect(surface, T.INK, key, border_radius=4)
            th.text(surface, str(i + 1), th.type(16, bold=True), T.PAPER, key.center, "center")
            th.text(surface, CUE_LABELS[cue], th.serif(22, bold=True), T.INK, (r.x + 56, r.y + 6))
            th.text(surface, VERDICT_HINTS[cue], th.serif(15, italic=True), T.INK_SOFT, (r.x + 56, r.y + 32))
        note = (f"Esc  keep investigating ({trials_left} trial{'s' if trials_left != 1 else ''} left)"
                if trials_left > 0 else "Your trials are spent. The Commission wants an answer.")
        th.text(surface, note, th.serif(16, italic=True), T.INK_SOFT, (WIDTH // 2, 540), "center")

    def proof_intro(self, surface, verdict):
        th = self.theme
        card = pygame.Rect(WIDTH // 2 - 330, 150, 660, 400)
        self._overlay_card(surface, card)
        th.spaced(surface, "THE COMMISSION ASSEMBLES", th.display(26, bold=True), T.INK, (WIDTH // 2, 185), 3, "midtop")
        th.text(surface, f"Your verdict: {CUE_LABELS[verdict]}", th.serif(20, bold=True), T.RED,
                (WIDTH // 2, 250), "center")
        body = ("Thirteen experts are watching. Design one test, then predict which door Hans will tap. "
                "Get the door right and your verdict stands. Choose conditions where your explanation, "
                "and only your explanation, tells you the answer.")
        y = 290
        for line in th.wrap(body, th.serif(19, italic=True), 560):
            th.text(surface, line, th.serif(19, italic=True), T.INK, (WIDTH // 2, y), "center")
            y += 30
        th.text(surface, "Press Enter", th.serif(18, italic=True), T.INK_SOFT, (WIDTH // 2, 510), "center")

    # --- case report -----------------------------------------------------------------
    def result(self, surface, inv, beliefs_now):
        th = self.theme
        r = inv.result
        surface.fill(T.PAPER)
        th.ornate_border(surface, pygame.Rect(30, 26, WIDTH - 60, HEIGHT - 52), T.INK, 10)
        th.spaced(surface, "CASE CLOSED", th.display(34, bold=True), T.INK, (WIDTH // 2, 60), 5, "midtop")
        th.text(surface, inv.case.title, th.serif(20, italic=True), T.INK_SOFT, (WIDTH // 2, 112), "center")

        x, y = 90, 170
        ok = lambda good: ("RIGHT", T.GREEN) if good else ("WRONG", T.RED)   # noqa: E731
        word, colour = ok(r.verdict_correct)
        th.text(surface, "Your verdict", th.serif(16, italic=True), T.INK_SOFT, (x, y))
        th.text(surface, f"{CUE_LABELS[r.verdict]}   {word}", th.serif(24, bold=True), colour, (x, y + 20))
        if not r.verdict_correct:
            th.text(surface, f"Hans relied on: {CUE_LABELS[r.truth]}", th.serif(18), T.INK, (x, y + 54))
        y += 100
        word, colour = ok(r.prediction_correct)
        th.text(surface, "The Commission's test", th.serif(16, italic=True), T.INK_SOFT, (x, y))
        th.text(surface, f"You predicted door {ROMAN[r.predicted]}, Hans tapped {ROMAN[r.actual]}   {word}",
                th.serif(22, bold=True), colour, (x, y + 20))
        y += 90
        th.text(surface, r.rank, th.display(34), T.INK, (x, y))
        th.text(surface, f"Score {r.score}   (verdict 50, prediction 30, 5 per unused trial)",
                th.serif(16, italic=True), T.INK_SOFT, (x, y + 50))
        if r.xray_used:
            th.text(surface, "Unofficial: the AI X-Ray was used during this case.", th.serif(16, italic=True),
                    T.RED, (x, y + 76))

        x2, y2 = 700, 170
        th.text(surface, "What your experiments did to Hans", th.serif(16, italic=True), T.INK_SOFT, (x2, y2))
        y2 += 32
        for cue in CUES:
            before, after = inv.case.arrival.trust(cue), beliefs_now.trust(cue)
            th.text(surface, CUE_LABELS[cue], th.serif(18, bold=True), T.INK, (x2, y2))
            th.bar(surface, pygame.Rect(x2, y2 + 26, 300, 10), before, T.INK_FAINT)
            th.bar(surface, pygame.Rect(x2, y2 + 40, 300, 10), after, T.BLUE)
            th.text(surface, f"arrival {before:.2f}", th.type(12), T.INK_SOFT, (x2 + 310, y2 + 23))
            th.text(surface, f"now {after:.2f}", th.type(12), T.BLUE, (x2 + 310, y2 + 38))
            y2 += 66
        y2 += 8
        th.text(surface, "How this Hans was trained", th.serif(16, italic=True), T.INK_SOFT, (x2, y2))
        y2 += 24
        for line in th.wrap(inv.case.regime.trainer, th.serif(18), 460):
            th.text(surface, line, th.serif(18), T.INK, (x2, y2))
            y2 += 26
        th.text(surface, "Enter  next case        Esc  quit", th.type(14), T.INK_SOFT, (WIDTH // 2, HEIGHT - 70), "center")
        th.film_overlay(surface)
