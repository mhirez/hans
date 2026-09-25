"""Best score between sessions, saved as JSON."""

from pathlib import Path
import json

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "saves" / "best.json"


class Best:
    def __init__(self, path: Path | None = DEFAULT_PATH):
        self.path = path
        self.score = 0
        self.wave = 0
        if path is not None and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.score, self.wave = int(data.get("score", 0)), int(data.get("wave", 0))
            except (ValueError, OSError):
                pass

    def record(self, score: int, wave: int) -> bool:
        """Returns True for a new best."""
        if score <= self.score:
            return False
        self.score, self.wave = score, wave
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps({"score": score, "wave": wave}), encoding="utf-8")
            except OSError:
                pass
        return True
