"""The casebook: which case you're on and how the ones you closed went. Saved as JSON."""

from datetime import date
from pathlib import Path
import json

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "saves" / "casebook.json"


class Casebook:
    def __init__(self, path: Path | None = DEFAULT_PATH):
        self.path = path
        self.next_case = 1
        self.cases: list[dict] = []
        if path is not None and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.next_case = int(data.get("next_case", 1))
                self.cases = list(data.get("cases", []))
            except (ValueError, OSError):
                pass

    @property
    def total_score(self) -> int:
        return sum(c["score"] for c in self.cases)

    @property
    def solved(self) -> int:
        return sum(1 for c in self.cases if c["verdict_correct"] and c["prediction_correct"])

    def record(self, inv):
        r = inv.result
        self.cases.append({
            "number": inv.case.number, "title": inv.case.title, "date": date.today().isoformat(),
            "verdict": r.verdict, "truth": r.truth, "verdict_correct": r.verdict_correct,
            "prediction_correct": r.prediction_correct, "score": r.score, "rank": r.rank,
            "hints": r.hints_used, "trials_used": inv.trials_used, "xray": r.xray_used,
        })
        self.next_case = inv.case.number + 1
        self.save()

    def restart(self):
        self.next_case = 1
        self.save()

    def save(self):
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"next_case": self.next_case, "cases": self.cases}, indent=2),
                                 encoding="utf-8")
        except OSError:
            pass
