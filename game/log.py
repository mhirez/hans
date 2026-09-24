"""Experiment log: one JSON line per trial, for evaluating the AI in the report."""

from datetime import datetime
from pathlib import Path
import json


class ExperimentLog:
    def __init__(self, directory: str | Path = "logs", enabled: bool = True):
        self.enabled = enabled
        self.path = Path(directory) / f"session-{datetime.now():%Y%m%d-%H%M%S}.jsonl"
        if enabled:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, **entry):
        if self.enabled:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
