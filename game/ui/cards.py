"""Full-screen and overlay cards: title, intertitles, help, verdict, the Commission, the case report."""

import pygame

from game.config import WIDTH, HEIGHT, CUES, CUE_LABELS, ROMAN, HINT_COST
from game.ui import sprites, theme as T

VERDICT_HINTS = {"owner": "he reads his questioner's body",
                 "scent": "he smells where the carrot is",
                 "crowd": "he listens to the audience"}
CUE_COLOURS = {"owner": T.INK, "scent": T.GREEN, "crowd": T.BLUE}

HELP_LINES = [
    ("The case", "Everyone thinks Hans can think. Something tells him where the carrot is: von Osten's "
                 "posture, the scent, or the crowd's murmur. Your job is to find out which."),
    ("Experiments", "Set the conditions on the right (keys 1-9 or click) and run a trial (Enter). Hans "
                    "decides for himself what to look at, then taps the door he believes in."),
    ("Evidence", "The notebook records what he studied and what he tapped. The EVIDENCE tab sums it up. "
                 "A cue he relies on is followed even when it lies, and missed when it's gone."),
    ("He learns", "Every trial also teaches Hans. Fool him with the same cue too often and he stops "
                  "trusting it, and your notebook describes a different horse."),
    ("Verdict", "Press V to name the cue. Then convince the Commission: hide the carrot behind a chosen "
                "door, and predict the wrong door Hans will tap."),
    ("Help", f"H asks Professor Stumpf for advice (-{HINT_COST} points). S lets him run the case. "
             "X shows Hans's mind (the AI X-Ray) but makes the result unofficial."),
]
KEYS = "Enter run   V verdict   Tab tabs   H advice   A apply   S autopilot   X x-ray   F fast   P pause   M mute   F11 full screen"


class Cards:
    def __init__(self, theme: T.Theme):
        self.theme = theme
        self.verdict_rects = {cue: pygame.Rect(WIDTH // 2 - 280, 250 + i * 70, 560, 56) for i, cue in enumerate(CUES)}
        self.blink = 0

    def _film_card(self, surface):
        surface.fill(T.FILM)
        self.theme.ornate_border(surface, pygame.Rect(40, 36, WIDTH - 80, HEIGHT - 72), T.FILM_TEXT, 12)

    def _prompt(self, surface, text, y):
        self.blink += 1
        if (self.blink // 35) % 2 == 0:
            self.theme.text(surface, text, self.theme.serif(20, italic=True), T.FILM_TEXT, (WIDTH // 2, y), "center")

    # --- title -----------------------------------------------------------------------
    def title(self, surface, casebook):
        th = self.theme
        self._film_card(surface)
        horse = pygame.Surface((64, 56), pygame.SRCALPHA)
        sprites.hans(horse, (32, 52), facing=1, head="up", tap_up=(self.blink // 20) % 2 == 0)
        horse.fill((*T.FILM_TEXT, 0), special_flags=pygame.BLEND_RGB_MAX)
        surface.blit(pygame.transform.scale(horse, (176, 154)), (WIDTH // 2 - 88, 70))
        th.spaced(surface, "HANS", th.display(104, bold=True), T.FILM_TEXT, (WIDTH // 2, 232), 18, "midtop")
        th.text(surface, "a game about learning the wrong clues", th.serif(25, italic=True), T.FILM_TEXT,
                (WIDTH // 2, 366), "center")
        th.rule(surface, WIDTH // 2 - 160, WIDTH // 2 + 160, 394, T.FILM_TEXT)
        th.text(surface, "Berlin, 1904", th.display(22), T.FILM_TEXT, (WIDTH // 2, 420), "center")
        cont = casebook.next_case
        self._prompt(surface, "Press Enter to begin" if cont == 1 else f"Press Enter to continue with Case {cont}", 478)
        menu = ["A   watch Professor Stumpf investigate a case",
                "H   how to play"]
        if cont > 1:
            menu.insert(0, "N   start again from Case 1")
        y = 522
        for line in menu:
            th.text(surface, line, th.type(15), T.FILM_TEXT, (WIDTH // 2, y), "center")
            y += 24
        if casebook.cases:
            th.text(surface, f"Casebook: {len(casebook.cases)} case{'s' if len(casebook.cases) != 1 else ''} closed, "
                             f"{casebook.solved} solved, {casebook.total_score} points",
                    th.serif(16, italic=True), T.INK_FAINT, (WIDTH // 2, 640), "center")
        th.film_overlay(surface)

    def loading(self, surface, text):
        th = self.theme
        self._film_card(surface)
        th.text(surface, text, th.serif(30, italic=True), T.FILM_TEXT, (WIDTH // 2, HEIGHT // 2), "center")
        th.film_overlay(surface)

    # --- intertitle ------------------------------------------------------------------
    def intertitle(self, surface, heading, lines, footer="Press Enter"):
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
        card = pygame.Rect(90, 50, WIDTH - 180, HEIGHT - 100)
        self._overlay_card(surface, card)
        th.spaced(surface, "HOW TO PLAY", th.display(26, bold=True), T.INK, (WIDTH // 2, 76), 4, "midtop")
        y = 128
        for head, body in HELP_LINES:
            th.text(surface, head, th.serif(18, bold=True), T.RED, (card.x + 50, y))
            for line in th.wrap(body, th.serif(17), card.width - 250):
                th.text(surface, line, th.serif(17), T.INK, (card.x + 170, y))
                y += 23
            y += 12
        for line in th.wrap(KEYS, th.type(13), card.width - 100):
            th.text(surface, line, th.type(13), T.INK_SOFT, (WIDTH // 2, y + 6), "center")
            y += 19
        th.text(surface, "any key to close", th.serif(15, italic=True), T.INK_SOFT, (WIDTH // 2, card.bottom - 32), "center")

    def pause(self, surface):
        th = self.theme
        card = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 - 70, 400, 140)
        self._overlay_card(surface, card)
        th.spaced(surface, "PAUSED", th.display(30, bold=True), T.INK, card.center, 6, "center")
        th.text(surface, "P to continue", th.serif(16, italic=True), T.INK_SOFT, (card.centerx, card.bottom - 30), "center")

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
        card = pygame.Rect(WIDTH // 2 - 340, 140, 680, 420)
        self._overlay_card(surface, card)
        th.spaced(surface, "THE COMMISSION ASSEMBLES", th.display(26, bold=True), T.INK, (WIDTH // 2, 175), 3, "midtop")
        th.text(surface, f"Your verdict: {CUE_LABELS[verdict]}", th.serif(20, bold=True), T.RED,
                (WIDTH // 2, 240), "center")
        body = ("Thirteen experts are watching, and they have seen Hans succeed a hundred times. "
                "Success proves nothing. Show them his mistake: hide the carrot behind a door you choose, "
                "set up the courtyard so your explanation leads him astray, and predict the wrong door he will tap.")
        y = 280
        for line in th.wrap(body, th.serif(19, italic=True), 580):
            th.text(surface, line, th.serif(19, italic=True), T.INK, (WIDTH // 2, y), "center")
            y += 30
        th.text(surface, "Press Enter", th.serif(18, italic=True), T.INK_SOFT, (WIDTH // 2, 520), "center")

    # --- case report -----------------------------------------------------------------
    def result(self, surface, inv):
        th = self.theme
        r = inv.result
        surface.fill(T.PAPER)
        th.ornate_border(surface, pygame.Rect(30, 26, WIDTH - 60, HEIGHT - 52), T.INK, 10)
        th.spaced(surface, "CASE CLOSED", th.display(34, bold=True), T.INK, (WIDTH // 2, 54), 5, "midtop")
        subtitle = f"{inv.case.title}  ·  investigated by Professor Stumpf" if r.autopilot else inv.case.title
        th.text(surface, subtitle, th.serif(20, italic=True), T.INK_SOFT, (WIDTH // 2, 104), "center")

        x, y = 80, 150
        ok = lambda good: ("RIGHT", T.GREEN) if good else ("WRONG", T.RED)   # noqa: E731
        word, colour = ok(r.verdict_correct)
        th.text(surface, "Verdict", th.serif(16, italic=True), T.INK_SOFT, (x, y))
        th.text(surface, f"{CUE_LABELS[r.verdict]}   {word}", th.serif(24, bold=True), colour, (x, y + 20))
        if not r.verdict_correct:
            th.text(surface, f"Hans relied on: {CUE_LABELS[r.truth]}", th.serif(18), T.INK, (x, y + 52))
        y += 88
        word, colour = ok(r.prediction_correct)
        th.text(surface, "The Commission's test", th.serif(16, italic=True), T.INK_SOFT, (x, y))
        th.text(surface, f"Predicted door {ROMAN[r.predicted]}, Hans tapped {ROMAN[r.actual]}   {word}",
                th.serif(22, bold=True), colour, (x, y + 20))
        y += 76
        th.text(surface, r.rank, th.display(32), T.INK, (x, y))
        parts = [f"verdict {50 if r.verdict_correct else 0}", f"proof {30 if r.prediction_correct else 0}",
                 f"{r.trials_left} unused x 5"]
        if r.hints_used:
            parts.append(f"{r.hints_used} advice x -{HINT_COST}")
        th.text(surface, f"Score {r.score}   (" + ", ".join(parts) + ")", th.serif(16, italic=True), T.INK_SOFT,
                (x, y + 46))
        y += 84
        cue, p = inv.stumpf.leader()
        th.text(surface, "Professor Stumpf, reading your notebook:", th.serif(16, italic=True), T.INK_SOFT, (x, y))
        th.text(surface, f"{CUE_LABELS[cue]}, {p:.0%} sure after {inv.trials_used} trial"
                         f"{'s' if inv.trials_used != 1 else ''}", th.serif(19, bold=True), CUE_COLOURS[cue], (x, y + 20))
        y += 58
        th.text(surface, "How this Hans was trained", th.serif(16, italic=True), T.INK_SOFT, (x, y))
        y += 22
        for line in th.wrap(f"{inv.case.regime.trainer} Temperament: {inv.case.temperament.description}.",
                            th.serif(17), 520):
            th.text(surface, line, th.serif(17), T.INK, (x, y))
            y += 23
        if r.xray_used and not r.autopilot:
            th.text(surface, "Unofficial: the AI X-Ray was used during this case.", th.serif(15, italic=True),
                    T.RED, (x, y + 6))

        self._trust_chart(surface, inv, pygame.Rect(690, 170, 500, 300))
        th.text(surface, "Enter  next case        Esc  title", th.type(14), T.INK_SOFT, (WIDTH // 2, HEIGHT - 66), "center")
        th.film_overlay(surface)

    def _trust_chart(self, surface, inv, rect):
        """Hans's trust in each cue, trial by trial: the observer effect made visible."""
        th = self.theme
        th.text(surface, "What your experiments did to Hans", th.serif(16, italic=True), T.INK_SOFT,
                (rect.x, rect.y - 34))
        th.text(surface, "trust in each cue after every trial", th.serif(13, italic=True), T.INK_FAINT,
                (rect.x, rect.y - 15))
        pygame.draw.rect(surface, T.PAPER_DARK, rect)
        for v in (0.25, 0.5, 0.75):
            yy = rect.bottom - int(v * rect.height)
            pygame.draw.line(surface, T.PAPER_EDGE, (rect.x, yy), (rect.right, yy), 1)
            th.text(surface, f"{v:.2f}", th.type(11), T.INK_FAINT, (rect.x - 6, yy), "midright")
        chance = rect.bottom - int(rect.height / 3)
        pygame.draw.line(surface, T.RED, (rect.x, chance), (rect.right, chance), 1)
        th.text(surface, "chance", th.type(11), T.RED, (rect.right + 4, chance), "midleft")
        history = inv.trust_history
        n = len(history)
        step = rect.width / max(1, n - 1)
        for cue in CUES:
            pts = [(rect.x + i * step, rect.bottom - h[cue]["trust"] * rect.height) for i, h in enumerate(history)]
            if len(pts) > 1:
                pygame.draw.lines(surface, CUE_COLOURS[cue], False, pts, 3)
            for pt in pts:
                pygame.draw.circle(surface, CUE_COLOURS[cue], (int(pt[0]), int(pt[1])), 3)
        pygame.draw.rect(surface, T.INK_SOFT, rect, 1)
        th.text(surface, "arrival", th.type(11), T.INK_SOFT, (rect.x, rect.bottom + 6), "midtop")
        th.text(surface, "Commission", th.type(11), T.INK_SOFT, (rect.right, rect.bottom + 6), "midtop")
        ly = rect.bottom + 30
        for i, cue in enumerate(CUES):
            lx = rect.x + i * 170
            pygame.draw.line(surface, CUE_COLOURS[cue], (lx, ly + 8), (lx + 22, ly + 8), 3)
            th.text(surface, f"{CUE_LABELS[cue]}", th.serif(14), T.INK, (lx + 28, ly))
