"""The scientist's desk: experiment setup, the notebook, and the AI X-Ray."""

from dataclasses import dataclass
from typing import Callable

import pygame

from game.config import (PANEL_X, PANEL_W, HEIGHT, CUES, CUE_LABELS, ROMAN, PATIENCE)
from game.ui import theme as T

DOOR_CHOICES = [(None, "Any"), (0, "I"), (1, "II"), (2, "III")]


@dataclass
class Field:
    key: str            # keyboard key that cycles it
    label: str
    options: list       # [(value, text)]
    get: Callable
    set: Callable
    enabled: Callable = lambda inv: True


def setup_fields() -> list[Field]:
    s = lambda inv: inv.setup   # noqa: E731
    return [
        Field("1", "Carrot behind", [(None, "Random"), (0, "Door I"), (1, "Door II"), (2, "Door III")],
              lambda inv: s(inv).carrot, lambda inv, v: setattr(s(inv), "carrot", v)),
        Field("2", "Von Osten", [("knows", "Knows"), ("guessing", "Doesn't know"), ("misled", "Misled"),
                                 ("absent", "Absent")],
              lambda inv: s(inv).owner, lambda inv, v: setattr(s(inv), "owner", v)),
        Field("3", "Misled toward", DOOR_CHOICES,
              lambda inv: s(inv).misled_to, lambda inv, v: setattr(s(inv), "misled_to", v),
              lambda inv: inv.setup.owner == "misled"),
        Field("4", "He stands", [(False, "Near Hans"), (True, "Far away")],
              lambda inv: s(inv).owner_far, lambda inv, v: setattr(s(inv), "owner_far", v),
              lambda inv: inv.setup.owner != "absent"),
        Field("5", "Screen", [(False, "Off"), (True, "Up")],
              lambda inv: s(inv).screen, lambda inv, v: setattr(s(inv), "screen", v)),
        Field("6", "Blinkers", [(False, "Off"), (True, "On")],
              lambda inv: s(inv).blinkers, lambda inv, v: setattr(s(inv), "blinkers", v)),
        Field("7", "Scent", [("normal", "Normal"), ("masked", "Masked"), ("decoy", "Decoy")],
              lambda inv: s(inv).scent, lambda inv, v: setattr(s(inv), "scent", v)),
        Field("8", "Decoy at", DOOR_CHOICES,
              lambda inv: s(inv).decoy_at, lambda inv, v: setattr(s(inv), "decoy_at", v),
              lambda inv: inv.setup.scent == "decoy"),
        Field("9", "Crowd", [("absent", "Absent"), ("saw", "Saw it hidden"), ("guessing", "Didn't see")],
              lambda inv: s(inv).crowd, lambda inv, v: setattr(s(inv), "crowd", v)),
        Field("0", "Your prediction", [(None, "-"), (0, "Door I"), (1, "Door II"), (2, "Door III")],
              lambda inv: inv.prediction, lambda inv, v: setattr(inv, "prediction", v),
              lambda inv: inv.stage == "proof"),
    ]


def cycle(field: Field, inv, step: int = 1):
    values = [v for v, _ in field.options]
    current = field.get(inv)
    i = values.index(current) if current in values else 0
    field.set(inv, values[(i + step) % len(values)])


class Panel:
    X0 = PANEL_X + 14
    COL_W = 246
    ROW_H = 38
    GRID_Y = 44

    def __init__(self, theme: T.Theme):
        self.theme = theme
        self.fields = setup_fields()
        self.cell_rects = []
        for i in range(len(self.fields)):
            col, row = i % 2, i // 2
            self.cell_rects.append(pygame.Rect(self.X0 + col * (self.COL_W + 12), self.GRID_Y + row * self.ROW_H,
                                               self.COL_W, self.ROW_H - 6))
        y = self.GRID_Y + 5 * self.ROW_H + 4
        self.run_rect = pygame.Rect(self.X0, y, 330, 34)
        self.verdict_rect = pygame.Rect(self.X0 + 342, y, PANEL_W - 28 - 342, 34)
        self.lower_y = y + 50

    # --- input -----------------------------------------------------------------------
    def field_at(self, pos) -> Field | None:
        for f, r in zip(self.fields, self.cell_rects):
            if r.collidepoint(pos):
                return f
        return None

    def field_for_key(self, key: str) -> Field | None:
        return next((f for f in self.fields if f.key == key), None)

    # --- drawing ---------------------------------------------------------------------
    def draw(self, surface, inv, hans, xray: bool, mouse=(0, 0)):
        th = self.theme
        panel = pygame.Rect(PANEL_X, 0, PANEL_W, HEIGHT)
        pygame.draw.rect(surface, T.PAPER, panel)
        pygame.draw.line(surface, T.INK, panel.topleft, panel.bottomleft, 3)
        pygame.draw.line(surface, T.PAPER_EDGE, (PANEL_X + 4, 0), (PANEL_X + 4, HEIGHT), 1)

        title = "THE COMMISSION'S TEST" if inv.stage == "proof" else "EXPERIMENT SETUP"
        th.spaced(surface, title, th.display(17, bold=True), T.INK, (self.X0, 14))
        if inv.stage == "proof":
            th.text(surface, "predict the door, then run", th.serif(14, italic=True), T.RED,
                    (PANEL_X + PANEL_W - 14, 17), "topright")
        locked = inv.running or inv.stage in ("verdict", "proof_intro", "done")
        for f, r in zip(self.fields, self.cell_rects):
            self._draw_field(surface, f, r, inv, locked, r.collidepoint(mouse))

        can_run = inv.can_run()
        run_label = "RUN THE TEST  [Enter]" if inv.stage == "proof" else "RUN TRIAL  [Enter]"
        if inv.running:
            run_label = "Hans is working..."
        self._button(surface, self.run_rect, run_label, can_run, self.run_rect.collidepoint(mouse))
        can_verdict = inv.stage == "investigate" and not inv.running and inv.trials_used > 0
        self._button(surface, self.verdict_rect, "VERDICT  [V]", can_verdict,
                     self.verdict_rect.collidepoint(mouse), accent=T.RED)
        th.rule(surface, self.X0, PANEL_X + PANEL_W - 14, self.lower_y - 12)

        if xray:
            self._draw_xray(surface, inv, hans)
        else:
            self._draw_notebook(surface, inv)
        th.film_overlay(surface, panel)

    def _draw_field(self, surface, f: Field, r: pygame.Rect, inv, locked: bool, hover: bool):
        th = self.theme
        enabled = f.enabled(inv)
        value = dict(f.options).get(f.get(inv), "?")
        if f.key == "0" and not enabled:
            return
        back = T.PAPER_DARK if (hover and enabled and not locked) else T.PAPER
        pygame.draw.rect(surface, back, r)
        pygame.draw.rect(surface, T.INK_SOFT if enabled else T.INK_FAINT, r, 1)
        key_box = pygame.Rect(r.x + 5, r.y + 7, 18, 18)
        pygame.draw.rect(surface, T.INK if enabled else T.INK_FAINT, key_box, border_radius=3)
        th.text(surface, f.key, th.type(12, bold=True), T.PAPER, key_box.center, "center")
        colour = T.INK if enabled else T.INK_FAINT
        th.text(surface, f.label, th.serif(13, italic=True), T.INK_SOFT if enabled else T.INK_FAINT, (r.x + 30, r.y + 1))
        th.text(surface, value if enabled else "-", th.serif(16, bold=True), colour, (r.x + 30, r.y + 15))
        if f.key == "0" and inv.prediction is None:
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

    # --- notebook --------------------------------------------------------------------
    def _draw_notebook(self, surface, inv):
        th = self.theme
        y = self.lower_y
        th.spaced(surface, "NOTEBOOK", th.display(15, bold=True), T.INK, (self.X0, y))
        done = len(inv.entries)
        correct = sum(e.success for e in inv.entries)
        summary = f"{done} trial{'s' if done != 1 else ''}, {correct} correct" if done else "no trials yet"
        th.text(surface, summary, th.serif(14, italic=True), T.INK_SOFT, (PANEL_X + PANEL_W - 14, y + 1), "topright")
        y += 26
        font, bold = th.type(12), th.type(12, bold=True)
        width = PANEL_W - 30
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
        for e in inv.entries[-10:]:
            mark, colour = ("RIGHT", T.GREEN) if e.success else ("WRONG", T.RED)
            th.text(surface, f"{e.number:>2}. {e.summary}", bold, T.INK, (self.X0, y), max_width=width)
            looked = ", ".join(e.looked_at) if e.looked_at else "nothing up close"
            line2 = f"    carrot {ROMAN[e.carrot]} · looked at {looked} · tapped {ROMAN[e.choice]}"
            th.text(surface, line2, font, T.INK_SOFT, (self.X0, y + 15), max_width=width - 50)
            th.text(surface, mark, bold, colour, (PANEL_X + PANEL_W - 14, y + 15), "topright")
            y += 38

    # --- X-Ray -----------------------------------------------------------------------
    def _draw_xray(self, surface, inv, hans):
        th = self.theme
        x0, x1 = self.X0, PANEL_X + PANEL_W - 14
        y = self.lower_y
        th.spaced(surface, "AI X-RAY", th.display(15, bold=True), T.RED, (x0, y))
        th.text(surface, "shows what Hans cannot know", th.serif(13, italic=True), T.RED, (x1, y + 1), "topright")
        y += 24
        f, fb = th.type(12), th.type(12, bold=True)

        chain = "  >  ".join(list(hans.fsm.history)[-4:])
        th.text(surface, f"FSM  {hans.state}  {hans.fsm.time_in_state:4.1f}s", fb, T.INK, (x0, y))
        th.text(surface, f"patience {max(0.0, hans.patience):4.1f}/{PATIENCE:.0f}s", f, T.INK_SOFT, (x1, y), "topright")
        th.text(surface, chain, f, T.INK_SOFT, (x0, y + 15), max_width=x1 - x0)
        y += 36

        th.text(surface, "TRUST  Beta(a, b) per cue   | = at arrival", fb, T.INK, (x0, y))
        y += 17
        for cue in CUES:
            b = hans.beliefs.cues[cue]
            th.text(surface, CUE_LABELS[cue], f, T.INK, (x0, y), max_width=150)
            bar = pygame.Rect(x0 + 152, y + 2, 170, 11)
            th.bar(surface, bar, b.mean, T.BLUE)
            arrival = inv.case.arrival.trust(cue)
            ax = bar.x + int(bar.width * arrival)
            pygame.draw.line(surface, T.RED, (ax, bar.y - 3), (ax, bar.bottom + 3), 2)
            th.text(surface, f"{b.mean:.2f}  a{b.alpha:4.1f} b{b.beta:4.1f}", f, T.INK_SOFT, (x1, y), "topright")
            y += 17
        y += 6

        th.text(surface, "READINGS  cue > door, strength x clarity", fb, T.INK, (x0, y))
        y += 17
        readings = list(hans.mind.readings.values())
        if not readings:
            th.text(surface, "(none yet)", f, T.INK_FAINT, (x0, y))
            y += 15
        for r in sorted(readings, key=lambda r: -abs(r.evidence))[:5]:
            src = hans.world.source(r.source_id)
            name = src.label if src else r.source_id
            sign = "+" if r.polarity > 0 else "-"
            note = ("focused" if r.focused else "passive") + ("  MISREAD" if r.misread else "")
            th.text(surface, f"{name:<10} > {ROMAN[r.door]:<3} {sign} {r.strength:.2f} x {r.clarity:.2f}",
                    f, T.INK, (x0, y))
            th.text(surface, note, f, T.RED if r.misread else T.INK_SOFT, (x1, y), "topright")
            y += 15
        y += 6

        th.text(surface, "ATTENTION  gain + curiosity - walk = utility", fb, T.INK, (x0, y))
        y += 17
        options = hans.mind.options[:3]
        if not options:
            th.text(surface, "(nothing weighed)" if hans.state in ("WAITING", "OBSERVING") else "(nothing worth the walk)",
                    f, T.INK_FAINT, (x0, y))
            y += 15
        for opt in options:
            th.text(surface, f"study {opt.label:<10} {opt.gain:.2f} + {opt.curiosity:.2f} - {opt.travel_time:3.1f}s",
                    f, T.INK, (x0, y))
            th.text(surface, f"= {opt.utility:+.2f}", fb, T.GREEN if opt.utility > 0.1 else T.INK_SOFT, (x1, y), "topright")
            y += 15
        y += 6

        d = hans.mind.decision
        scores = hans.mind.scores()
        th.text(surface, "DOOR SCORES  sum of evidence x weight(cue)", fb, T.INK, (x0, y))
        y += 17
        mid = x0 + 190
        for i, v in enumerate(scores):
            th.text(surface, f"door {ROMAN[i]}", f, T.INK, (x0, y))
            w = int(min(1.0, abs(v)) * 130)
            rect = pygame.Rect(mid if v >= 0 else mid - w, y + 2, w, 10)
            pygame.draw.rect(surface, T.GREEN if v >= 0 else T.RED, rect)
            pygame.draw.line(surface, T.INK, (mid, y), (mid, y + 13), 1)
            chosen = d is not None and d.choice == i
            th.text(surface, f"{v:+.2f}" + ("  < CHOSEN" if chosen else ""), fb if chosen else f,
                    T.INK, (x1, y), "topright")
            y += 15
        if d is not None:
            th.text(surface, f"decision {d.mode}  margin {d.margin:.2f}", f, T.INK_SOFT, (x0, y))
            y += 15
        y += 6

        t = inv.trial
        th.text(surface, "GROUND TRUTH", fb, T.RED, (x0, y))
        y += 17
        if t is not None:
            vo = ROMAN[t.owner_door] if t.owner_door is not None else "-"
            cr = ROMAN[t.crowd_door] if t.crowd_door is not None else "-"
            dc = ROMAN[t.decoy_door] if t.decoy_door is not None else "-"
            th.text(surface, f"carrot {ROMAN[t.carrot]} · von Osten believes {vo} · crowd {cr} · decoy {dc}",
                    f, T.INK, (x0, y), max_width=x1 - x0)
            y += 15
        th.text(surface, f"case answer: {CUE_LABELS[inv.case.truth]} (lead {inv.case.truth_margin:.2f})",
                f, T.RED, (x0, y))
