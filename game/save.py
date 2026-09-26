"""Best run between sessions, saved as JSON."""

from pathlib import Path
import json

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "saves" / "lockdown.json"


class Best:
    def __init__(self, path: Path | None = DEFAULT_PATH):
        self.path = path
        self.score = 0
        self.floor = 0
        self.room = 0
        self.won = False
        if path is not None and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self.score = int(data.get("score", 0))
                self.floor, self.room = int(data.get("floor", 0)), int(data.get("room", 0))
                self.won = bool(data.get("won", False))
            except (ValueError, OSError, TypeError):
                pass

    def label(self) -> str:
        return "ESCAPED" if self.won else f"floor {self.floor}, room {self.room}"

    def record(self, score: int, floor: int, room: int, won: bool) -> bool:
        """Returns True for a new best."""
        if score <= self.score:
            return False
        self.score, self.floor, self.room, self.won = score, floor, room, won
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps({"score": score, "floor": floor, "room": room, "won": won}),
                                     encoding="utf-8")
            except OSError:
                pass
        return True
