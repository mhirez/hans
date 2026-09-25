"""Numbers for the report, printed as Markdown tables.

    python -m tools.evaluate regimes          what each training regime x temperament produces
    python -m tools.evaluate stumpf 200       Professor Stumpf's autopilot on N generated cases
    python -m tools.evaluate logs             your own play: Hans's accuracy by condition (logs/*.jsonl)
"""

from collections import Counter, defaultdict
from pathlib import Path
import json
import random
import statistics
import sys

from game.ai.temperament import TEMPERAMENTS
from game.case import REGIMES, train_hans, make_case
from game.investigation import Investigation
from game.world import World

ROOT = Path(__file__).resolve().parent.parent


def regimes(seeds: int = 8):
    print("| regime | temperament | Hans ends up relying on | median lead |")
    print("|---|---|---|---|")
    for rk, regime in REGIMES.items():
        for tk, temperament in TEMPERAMENTS.items():
            counts, leads = Counter(), []
            for seed in range(seeds):
                cue, lead = train_hans(regime, seed, temperament).dominant()
                counts[cue] += 1
                leads.append(lead)
            mix = ", ".join(f"{c} {n}/{seeds}" for c, n in counts.most_common())
            print(f"| {rk} | {tk} | {mix} | {statistics.median(leads):.2f} |")


def stumpf(n: int = 100):
    by_regime = defaultdict(lambda: [0, 0, 0, []])
    for i in range(1, n + 1):
        case = make_case(1 if i <= max(1, n // 20) else i, random.Random(i * 13))
        inv = Investigation(case, World(), random.Random(i))
        inv.start_autopilot(pause=0.02)
        while inv.stage != "done":
            inv.update(1 / 30)
        row = by_regime[case.regime.key]
        row[0] += 1
        row[1] += inv.result.verdict_correct
        row[2] += inv.result.prediction_correct
        row[3].append(inv.trials_used)
    print("| regime | cases | verdict right | Commission prediction right | mean trials |")
    print("|---|---|---|---|---|")
    total = [0, 0, 0, []]
    for key, (cases, verdicts, predictions, trials) in sorted(by_regime.items()):
        print(f"| {key} | {cases} | {verdicts / cases:.0%} | {predictions / cases:.0%} | {statistics.mean(trials):.1f} |")
        total = [total[0] + cases, total[1] + verdicts, total[2] + predictions, total[3] + trials]
    print(f"| **all** | {total[0]} | {total[1] / total[0]:.0%} | {total[2] / total[0]:.0%} | "
          f"{statistics.mean(total[3]):.1f} |")


def logs(directory: Path = ROOT / "logs"):
    rows = []
    for path in sorted(directory.glob("*.jsonl")):
        rows += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        print(f"No logs in {directory}. Play a few trials first.")
        return
    print(f"{len(rows)} trials from {directory}\n")
    for field in ("owner", "scent", "crowd", "blinkers", "screen"):
        groups = defaultdict(list)
        for r in rows:
            groups[str(r["conditions"][field])].append(r["success"])
        print(f"| {field} | trials | Hans right |\n|---|---|---|")
        for value, results in sorted(groups.items()):
            print(f"| {value} | {len(results)} | {sum(results) / len(results):.0%} |")
        print()


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "stumpf"
    if command == "regimes":
        regimes()
    elif command == "stumpf":
        stumpf(int(sys.argv[2]) if len(sys.argv) > 2 else 100)
    elif command == "logs":
        logs()
    else:
        print(__doc__)
