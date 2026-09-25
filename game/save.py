"""Progress between sessions: which nights are unlocked and the best stars on each. Saved as JSON."""

from pathlib import Path
import json

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "saves" / "progress.json"


class Progress:
    def __init__(self, path: Path | None = DEFAULT_PATH):
        self.path = path
        self.unlocked = 0                  # highest night you may play
        self.stars: dict[int, int] = {}    # night -> best stars
        if path is not None and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.unlocked = int(data.get("unlocked", 0))
                self.stars = {int(k): int(v) for k, v in data.get("stars", {}).items()}
            except (ValueError, OSError):
                pass

    def record(self, night: int, stars: int, last_night: int):
        self.stars[night] = max(stars, self.stars.get(night, 0))
        self.unlocked = min(last_night, max(self.unlocked, night + 1))
        self.save()

    def save(self):
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"unlocked": self.unlocked, "stars": self.stars}, indent=2),
                                 encoding="utf-8")
        except OSError:
            pass
