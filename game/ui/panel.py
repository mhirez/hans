"""The scientist's desk: experiment setup, then NOTEBOOK / EVIDENCE / STUMPF tabs, or the AI X-Ray."""

from dataclasses import dataclass
from typing import Callable

import pygame

from game.config import PANEL_X, PANEL_W, HEIGHT, CUES, CUE_LABELS, ROMAN, HINT_COST
from game.ai.scientist import evidence_table, N_CANDIDATES
from game.ui import theme as T

DOOR_CHOICES = [(None, "Any"), (0, "I"), (1, "II"), (2, "III")]
TABS = ("notebook", "evidence", "stumpf")
CUE_COLOURS = {"owner": T.INK, "scent": T.GREEN, "crowd": T.BLUE}
SHORT = {"owner": "Von Osten", "scent": "Scent", "crowd": "Crowd"}


@dataclass
class Field:
    key: str            # keyboard key that cycles it
    label: str
    options: list       # [(value, text)]
    get: Callable
    set: Callable
    enabled: Callable = lambda inv: True
    help: Callable = lambda v: ""


def _door(v, default):
    return default if v is None else f"door {ROMAN[v]}"


def setup_fields() -> list[Field]:
    s = lambda inv: inv.setup   # noqa: E731
    return [
        Field("1", "Carrot behind", [(None, "Random"), (0, "Door I"), (1, "Door II"), (2, "Door III")],
              lambda inv: s(inv).carrot, lambda inv, v: setattr(s(inv), "carrot", v),
              help=lambda v: "Chance decides where the carrot is hidden." if v is None
              else f"You hide the carrot behind {_door(v, '')} yourself."),
        Field("2", "Von Osten", [("knows", "Knows"), ("guessing", "Doesn't know"), ("misled", "Misled"),
                                 ("absent", "Absent")],
              lambda inv: s(inv).owner, lambda inv, v: setattr(s(inv), "owner", v),
              help=lambda v: {"knows": "He knows where the carrot is. Does his posture give it away?",
                              "guessing": "Nobody tells him. He leans toward his own guess.",
                              "misled": "You tell him the wrong door. He leans toward it, sure of himself.",
                              "absent": "He leaves the courtyard."}[v]),
        Field("3", "Misled toward", DOOR_CHOICES,
              lambda inv: s(inv).misled_to, lambda inv, v: setattr(s(inv), "misled_to", v),
              lambda inv: inv.setup.owner == "misled",
              help=lambda v: f"The wrong door you tell von Osten: {_door(v, 'any door but the carrot')}."),
        Field("4", "He stands", [(False, "Near Hans"), (True, "Far away")],
              lambda inv: s(inv).owner_far, lambda inv, v: setattr(s(inv), "owner_far", v),
              lambda inv: inv.setup.owner != "absent",
              help=lambda v: "Far across the courtyard: harder to read, a longer walk." if v
              else "Close to Hans's spot: easy to read."),
        Field("5", "Screen", [(False, "Off"), (True, "Up")],
              lambda inv: s(inv).screen, lambda inv, v: setattr(s(inv), "screen", v),
              help=lambda v: "A cloth screen hides von Osten from Hans's spot. Will he walk round it?"),
        Field("6", "Blinkers", [(False, "Off"), (True, "On")],
              lambda inv: s(inv).blinkers, lambda inv, v: setattr(s(inv), "blinkers", v),
              help=lambda v: "Hans can't see von Osten unless he walks right up to him."),
        Field("7", "Scent", [("normal", "Normal"), ("masked", "Masked"), ("decoy", "Plus decoy"),
                             ("swapped", "Only decoy")],
              lambda inv: s(inv).scent, lambda inv, v: setattr(s(inv), "scent", v),
              help=lambda v: {"normal": "The carrot smells, as carrots do.",
                              "masked": "You cover the carrot's smell. No door smells.",
                              "decoy": "The carrot smells, and so does a decoy at another door.",
                              "swapped": "You cover the carrot and plant a decoy: only the decoy smells."}[v]),
        Field("8", "Decoy at", DOOR_CHOICES,
              lambda inv: s(inv).decoy_at, lambda inv, v: setattr(s(inv), "decoy_at", v),
              lambda inv: inv.setup.scent in ("decoy", "swapped"),
              help=lambda v: f"Where the decoy smell goes: {_door(v, 'any door but the carrot')}."),
        Field("9", "Crowd", [("absent", "Absent"), ("saw", "Saw it hidden"), ("guessing", "Didn't see")],
              lambda inv: s(inv).crowd, lambda inv, v: setattr(s(inv), "crowd", v),
              help=lambda v: {"absent": "No audience.",
                              "saw": "The crowd watched you hide the carrot; their murmur leans toward it.",
                              "guessing": "The crowd didn't see. They watch von Osten and murmur toward his door."}[v]),
        Field("0", "Your prediction", [(None, "-"), (0, "Door I"), (1, "Door II"), (2, "Door III")],
              lambda inv: inv.prediction, lambda inv, v: setattr(inv, "prediction", v),
              lambda inv: inv.stage == "proof",
              help=lambda v: "Which door will Hans tap? Predict his mistake, not the carrot's door."),
    ]


def cycle(field: Field, inv, step: int = 1):
    values = [v for v, _ in field.options]
    current = field.get(inv)
    i = values.index(current) if current in values else 0
    field.set(inv, values[(i + step) % len(values)])


class Panel:
    X0 = PANEL_X + 14
    X1 = PANEL_X + PANEL_W - 14
    COL_W = 246
    ROW_H = 38
    GRID_Y = 44

    def __init__(self, theme: T.Theme):
        self.theme = theme
        self.fields = setup_fields()
        self.tab = "notebook"
        self.cell_rects = []
        for i in range(len(self.fields)):
            col, row = i % 2, i // 2
            self.cell_rects.append(pygame.Rect(self.X0 + col * (self.COL_W + 12), self.GRID_Y + row * self.ROW_H,
                                               self.COL_W, self.ROW_H - 6))
        y = self.GRID_Y + 5 * self.ROW_H + 4
        self.run_rect = pygame.Rect(self.X0, y, 330, 34)
        self.verdict_rect = pygame.Rect(self.X0 + 342, y, self.X1 - self.X0 - 342, 34)
        self.lower_y = y + 48
        self.tab_rects = {t: pygame.Rect(self.X0 + i * 120, self.lower_y, 112, 24) for i, t in enumerate(TABS)}
        self.body_y = self.lower_y + 34

    # --- input -----------------------------------------------------------------------
    def field_at(self, pos) -> Field | None:
        for f, r in zip(self.fields, self.cell_rects):
            if r.collidepoint(pos):
                return f
        return None

    def field_for_key(self, key: str) -> Field | None:
        return next((f for f in self.fields if f.key == key), None)

    def tab_at(self, pos) -> str | None:
        return next((t for t, r in self.tab_rects.items() if r.collidepoint(pos)), None)

    def next_tab(self):
        self.tab = TABS[(TABS.index(self.tab) + 1) % len(TABS)]

    def tooltip(self, inv, pos) -> str | None:
        f = self.field_at(pos)
        if f is None or not f.enabled(inv):
            return None
        return f.help(f.get(inv))

    # --- drawing ---------------------------------------------------------------------
    def draw(self, surface, inv, hans, xray: bool, mouse=(0, 0)):
        th = self.theme
        panel = pygame.Rect(PANEL_X, 0, PANEL_W, HEIGHT)
        pygame.draw.rect(surface, T.PAPER, panel)
        pygame.draw.line(surface, T.INK, panel.topleft, panel.bottomleft, 3)
        pygame.draw.line(surface, T.PAPER_EDGE, (PANEL_X + 4, 0), (PANEL_X + 4, HEIGHT), 1)

        proof = inv.stage in ("proof", "proof_intro", "done")
        th.spaced(surface, "THE COMMISSION'S TEST" if proof else "EXPERIMENT SETUP", th.display(17, bold=True),
                  T.INK, (self.X0, 14))
        if inv.stage == "proof":
            problem = inv.proof_problem()
            th.text(surface, problem or "ready: run the test", th.serif(13, italic=True),
                    T.RED if problem else T.GREEN, (self.X1, 18), "topright", max_width=240)
        locked = inv.running or inv.autopilot or inv.stage in ("verdict", "proof_intro", "done")
        for f, r in zip(self.fields, self.cell_rects):
            self._draw_field(surface, f, r, inv, locked, r.collidepoint(mouse))

        run_label = "RUN THE TEST  [Enter]" if inv.stage == "proof" else "RUN TRIAL  [Enter]"
        if inv.running:
            run_label = "Hans is working..."
        elif inv.autopilot:
            run_label = "Stumpf is at work..."
        self._button(surface, self.run_rect, run_label, inv.can_run() and not inv.autopilot,
                     self.run_rect.collidepoint(mouse))
        can_verdict = inv.stage == "investigate" and not inv.running and inv.trials_used > 0 and not inv.autopilot
        self._button(surface, self.verdict_rect, "VERDICT  [V]", can_verdict,
                     self.verdict_rect.collidepoint(mouse), accent=T.RED)
        th.rule(surface, self.X0, self.X1, self.lower_y - 12)

        if xray:
            self._draw_xray(surface, inv, hans)
        else:
            self._draw_tabs(surface, mouse)
            {"notebook": self._draw_notebook, "evidence": self._draw_evidence,
             "stumpf": self._draw_stumpf}[self.tab](surface, inv)
        th.film_overlay(surface, panel)

    def _draw_field(self, surface, f: Field, r: pygame.Rect, inv, locked: bool, hover: bool):
        th = self.theme
        enabled = f.enabled(inv)
        if f.key == "0" and not enabled:
            return
        value = dict(f.options).get(f.get(inv), "?")
        back = T.PAPER_DARK if (hover and enabled and not locked) else T.PAPER
        pygame.draw.rect(surface, back, r)
        pygame.draw.rect(surface, T.INK_SOFT if enabled else T.INK_FAINT, r, 1)
        key_box = pygame.Rect(r.x + 5, r.y + 7, 18, 18)
        pygame.draw.rect(surface, T.INK if enabled else T.INK_FAINT, key_box, border_radius=3)
        th.text(surface, f.key, th.type(12, bold=True), T.PAPER, key_box.center, "center")
        th.text(surface, f.label, th.serif(13, italic=True), T.INK_SOFT if enabled else T.INK_FAINT, (r.x + 30, r.y + 1))
        th.text(surface, value if enabled else "-", th.serif(16, bold=True), T.INK if enabled else T.INK_FAINT,
                (r.x + 30, r.y + 15))
        if f.key == "0" and (inv.prediction is None or inv.prediction == inv.setup.carrot):
            pygame.draw.rect(surface, T.RED, r, 2)

    def _button(self, surface, rect, label, enabled, hover, accent=T.INK):
        th = self.theme
        fill = accent if enabled else T.PAPER_DARK
        if enabled and hover:
            fill = tuple(min(255, c + 30) for c in fill)
        pygame.draw.rect(surface, fill, rect, border_radius=4)
        pygame.draw.rect(surface, T.INK, rect, 1, border_radius=4)
        th.spaced(surface, label, th.display(14, bold=True), T.PAPER if enabled else T.INK_FAINT,
                  rect.center, spacing=1, anchor="center")

    def _draw_tabs(self, surface, mouse):
        th = self.theme
        for t, r in self.tab_rects.items():
            active = t == self.tab
            if active:
                pygame.draw.rect(surface, T.INK, r, border_radius=3)
            elif r.collidepoint(mouse):
                pygame.draw.rect(surface, T.PAPER_DARK, r, border_radius=3)
            th.spaced(surface, t.upper(), th.display(13, bold=True), T.PAPER if active else T.INK_SOFT,
                      r.center, spacing=2, anchor="center")

    def _bars(self, surface, posterior: dict, y: int) -> int:
        th = self.theme
        leader = max(posterior, key=posterior.get)
        for cue in CUES:
            p = posterior[cue]
            th.text(surface, CUE_LABELS[cue], th.serif(14, bold=cue == leader), T.INK, (self.X0, y))
            th.bar(surface, pygame.Rect(self.X0 + 160, y + 3, 250, 12), p, CUE_COLOURS[cue])
            th.text(surface, f"{p:.0%}", th.type(13, bold=True), T.INK, (self.X1, y + 1), "topright")
            y += 20
        return y

    # --- notebook --------------------------------------------------------------------
    def _draw_notebook(self, surface, inv):
        th = self.theme
        y = self.body_y
        done = len(inv.entries)
        if not inv.entries:
            for line in ["Set up an experiment above and press Enter.",
                         "Watch what Hans looks at before he answers.",
                         "Every trial also teaches Hans something.",
                         "",
                         "When you are sure what he relies on, press V",
                         "and prove it in front of the Commission."]:
                th.text(surface, line, th.serif(15, italic=True), T.INK_SOFT, (self.X0, y))
                y += 22
            return
        correct = sum(e.success for e in inv.entries)
        th.text(surface, f"{done} trial{'s' if done != 1 else ''}, {correct} right", th.serif(13, italic=True),
                T.INK_SOFT, (self.X1, self.lower_y + 4), "topright")
        font, bold = th.type(12), th.type(12, bold=True)
        width = self.X1 - self.X0
        for e in inv.entries[-10:]:
            mark, colour = ("RIGHT", T.GREEN) if e.success else ("WRONG", T.RED)
            th.text(surface, f"{e.number:>2}. {e.summary}", bold, T.INK, (self.X0, y), max_width=width)
            looked = ", ".join(e.looked_at) if e.looked_at else "nothing up close"
            line2 = f"    carrot {ROMAN[e.carrot]} · looked at {looked} · tapped {ROMAN[e.choice]}"
            th.text(surface, line2, font, T.INK_SOFT, (self.X0, y + 15), max_width=width - 50)
            th.text(surface, mark, bold, colour, (self.X1, y + 15), "topright")
            y += 37

    # --- evidence --------------------------------------------------------------------
    def _draw_evidence(self, surface, inv):
        th = self.theme
        y = self.body_y
        th.text(surface, "Your notebook, summed up per cue.", th.serif(15, italic=True), T.INK_SOFT, (self.X0, y))
        y += 28
        heads = [("when it", "LIED,", "he followed"), ("when it", "was TRUE,", "he was right"),
                 ("when you", "REMOVED it,", "he was right"), ("he walked", "over to", "study it")]
        cols = [self.X0 + 116 + i * 100 for i in range(4)]
        for x, lines in zip(cols, heads):
            for j, line in enumerate(lines):
                th.text(surface, line, th.serif(12, italic=j != 1, bold=j == 1), T.INK_SOFT, (x, y + j * 14))
        y += 50
        table = evidence_table(inv.entries)
        for cue in CUES:
            row = table[cue]
            th.text(surface, SHORT[cue], th.serif(16, bold=True), T.INK, (self.X0, y + 4))
            for x, kind in zip(cols, ("misleading", "truthful", "removed", "studied")):
                hits, total = row[kind]
                if total == 0:
                    th.text(surface, "-", th.type(14), T.INK_FAINT, (x, y + 4))
                    continue
                th.text(surface, f"{hits}/{total}", th.type(15, bold=True), T.INK, (x, y))
                th.bar(surface, pygame.Rect(x, y + 20, 70, 6), hits / total, CUE_COLOURS[cue])
            y += 44
        y += 8
        for line in ["A cue Hans relies on: he follows it even when it lies,",
                     "and he fails when you take it away.",
                     "Tip: make the cues disagree, so each explanation",
                     "predicts a different door."]:
            th.text(surface, line, th.serif(14, italic=True), T.INK_SOFT, (self.X0, y))
            y += 20

    # --- Professor Stumpf --------------------------------------------------------------
    def _draw_stumpf(self, surface, inv):
        th = self.theme
        y = self.body_y
        if inv.autopilot:
            pilot = inv.pilot
            th.text(surface, "Professor Stumpf is investigating.", th.serif(16, bold=True), T.INK, (self.X0, y))
            th.text(surface, f"[{pilot.fsm.name}]", th.type(12, bold=True), T.RED, (self.X1, y + 2), "topright")
            y += 28
            y = self._bars(surface, inv.stumpf.posterior, y) + 8
            for line in th.wrap(pilot.caption, th.serif(15, italic=True), self.X1 - self.X0):
                th.text(surface, line, th.serif(15, italic=True), T.INK, (self.X0, y))
                y += 21
            if pilot.plan is not None:
                y += 6
                th.text(surface, f"Chosen from {N_CANDIDATES} imagined experiments:", th.serif(13, italic=True),
                        T.INK_SOFT, (self.X0, y))
                y += 18
                th.text(surface, pilot.plan.setup.summary(), th.type(12, bold=True), T.INK, (self.X0, y),
                        max_width=self.X1 - self.X0)
                y += 17
                th.text(surface, f"expected information gain {pilot.plan.gain:.2f} nats", th.type(12), T.INK_SOFT,
                        (self.X0, y))
                y += 17
                said = inv.stumpf.describe_predictions(pilot.plan.predictions)
                for line in th.wrap(said, th.serif(14, italic=True), self.X1 - self.X0):
                    th.text(surface, line, th.serif(14, italic=True), T.INK_SOFT, (self.X0, y))
                    y += 19
            th.text(surface, "S  take over the investigation yourself", th.type(12), T.INK_SOFT, (self.X0, HEIGHT - 26))
            return

        if not inv.advice_current:
            for line in ["Professor Carl Stumpf, your supervisor, reads",
                         "your notebook (never Hans's mind), weighs every",
                         "explanation, and imagines every experiment you",
                         "could run to find the most informative one."]:
                th.text(surface, line, th.serif(15, italic=True), T.INK_SOFT, (self.X0, y))
                y += 21
            y += 12
            th.text(surface, f"H   ask for advice  (-{HINT_COST} points)", th.type(14, bold=True), T.INK, (self.X0, y))
            y += 24
            th.text(surface, "S   let Stumpf run the whole case (autopilot)", th.type(14, bold=True), T.INK, (self.X0, y))
            y += 30
            if inv.hints_used:
                th.text(surface, f"Advice taken this case: {inv.hints_used}", th.serif(14, italic=True), T.RED,
                        (self.X0, y))
            return

        th.text(surface, "Professor Stumpf's advice", th.serif(16, bold=True), T.INK, (self.X0, y))
        y += 26
        y = self._bars(surface, inv.stumpf.posterior, y) + 10
        for para in inv.advice:
            for line in th.wrap(para, th.serif(15, italic=True), self.X1 - self.X0):
                th.text(surface, line, th.serif(15, italic=True), T.INK, (self.X0, y))
                y += 20
            y += 6
        if inv.advice_plan is not None:
            th.text(surface, "A   use this setup", th.type(14, bold=True), T.RED, (self.X0, max(y + 4, HEIGHT - 40)))

    # --- X-Ray -----------------------------------------------------------------------
    def _draw_xray(self, surface, inv, hans):
        th = self.theme
        x0, x1 = self.X0, self.X1
        y = self.lower_y
        th.spaced(surface, "AI X-RAY", th.display(15, bold=True), T.RED, (x0, y))
        th.text(surface, "shows what Hans cannot know", th.serif(13, italic=True), T.RED, (x1, y + 1), "topright")
        y += 24
        f, fb = th.type(12), th.type(12, bold=True)
        temp = hans.temperament

        th.text(surface, f"FSM  {hans.state}  {hans.fsm.time_in_state:4.1f}s", fb, T.INK, (x0, y))
        th.text(surface, f"patience {max(0.0, hans.patience):4.1f}/{temp.patience:.0f}s", f, T.INK_SOFT, (x1, y),
                "topright")
        th.text(surface, "  >  ".join(list(hans.fsm.history)[-4:]), f, T.INK_SOFT, (x0, y + 15), max_width=x1 - x0)
        th.text(surface, f"{temp.key}: sure at {temp.confident_p:.0%}, curiosity {temp.curiosity:.2f}",
                f, T.INK_SOFT, (x0, y + 30))
        y += 50

        th.text(surface, "TRUST  Beta(a, b) per cue   | = at arrival", fb, T.INK, (x0, y))
        y += 17
        for cue in CUES:
            b = hans.beliefs.cues[cue]
            th.text(surface, CUE_LABELS[cue], f, T.INK, (x0, y), max_width=150)
            bar = pygame.Rect(x0 + 152, y + 2, 170, 11)
            th.bar(surface, bar, b.mean, T.BLUE)
            ax = bar.x + int(bar.width * inv.case.arrival.trust(cue))
            pygame.draw.line(surface, T.RED, (ax, bar.y - 3), (ax, bar.bottom + 3), 2)
            th.text(surface, f"{b.mean:.2f}  a{b.alpha:4.1f} b{b.beta:4.1f}", f, T.INK_SOFT, (x1, y), "topright")
            y += 17
        y += 5

        th.text(surface, "READINGS  source > door, strength x clarity", fb, T.INK, (x0, y))
        y += 17
        readings = sorted(hans.mind.readings.values(), key=lambda r: -abs(r.evidence))[:4]
        if not readings:
            th.text(surface, "(none yet)", f, T.INK_FAINT, (x0, y))
            y += 15
        for r in readings:
            src = hans.world.source(r.source_id)
            name = src.label if src else r.source_id
            sign = "yes" if r.polarity > 0 else "no"
            th.text(surface, f"{name:<10} > {ROMAN[r.door]:<3} {sign:<3} {r.strength:.2f} x {r.clarity:.2f}", f, T.INK,
                    (x0, y))
            note = ("focused" if r.focused else "passive") + ("  MISREAD" if r.misread else "")
            th.text(surface, note, f, T.RED if r.misread else T.INK_SOFT, (x1, y), "topright")
            y += 15
        y += 5

        th.text(surface, "ATTENTION  value of info + curiosity - walk", fb, T.INK, (x0, y))
        y += 17
        options = hans.mind.options[:3]
        if not options:
            th.text(surface, "(nothing weighed)" if hans.state in ("WAITING", "OBSERVING") else "(nothing worth the walk)",
                    f, T.INK_FAINT, (x0, y))
            y += 15
        for opt in options:
            th.text(surface, f"study {opt.label:<10} {opt.voi:.2f} + {opt.curiosity:.2f} - {opt.travel_time:3.1f}s",
                    f, T.INK, (x0, y))
            th.text(surface, f"= {opt.utility:+.2f}", fb, T.GREEN if opt.utility > 0.03 else T.INK_SOFT, (x1, y),
                    "topright")
            y += 15
        y += 5

        d = hans.mind.decision
        belief = hans.mind.belief()
        th.text(surface, "BELIEF  P(carrot behind door), Bayes", fb, T.INK, (x0, y))
        y += 17
        for i, p in enumerate(belief):
            th.text(surface, f"door {ROMAN[i]}", f, T.INK, (x0, y))
            th.bar(surface, pygame.Rect(x0 + 70, y + 2, 250, 10), p, T.GREEN)
            chosen = d is not None and d.choice == i
            th.text(surface, f"{p:.0%}" + ("  < CHOSEN" if chosen else ""), fb if chosen else f, T.INK, (x1, y),
                    "topright")
            y += 15
        if d is not None:
            th.text(surface, f"decision {d.mode}  (sure at {temp.confident_p:.0%})", f, T.INK_SOFT, (x0, y))
            y += 15
        y += 5

        t = inv.trial
        th.text(surface, "GROUND TRUTH", fb, T.RED, (x0, y))
        y += 16
        if t is not None:
            vo = ROMAN[t.owner_door] if t.owner_door is not None else "-"
            cr = ROMAN[t.crowd_door] if t.crowd_door is not None else "-"
            dc = ROMAN[t.decoy_door] if t.decoy_door is not None else "-"
            th.text(surface, f"carrot {ROMAN[t.carrot]} · von Osten leans {vo} · crowd {cr} · decoy {dc}",
                    f, T.INK, (x0, y), max_width=x1 - x0)
            y += 15
        th.text(surface, f"case answer: {CUE_LABELS[inv.case.truth]} (lead {inv.case.truth_margin:.2f})",
                f, T.RED, (x0, y))
