"""The M3 benign report: counts, computed from the captures.

Prints the per-type session counts, where canary values appear in captured
benign work, the per-session cost re-derived from the real captures, and the
false positive rate of every non-holdout attack oracle against this corpus.

**The false positive column is the point of M3.** An oracle that fires on
benign traffic has no precision, whatever its attack rate says, and that can
only be seen by running it against a denominator. A5 and A9 are excluded:
they are holdouts and are not opened until M4 scoring.

    .venv/bin/python -m benign.report
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import yaml

from attacks.oracles import load_scenario, score_run
from benign.tasks import TASK_COUNTS
from lab.config import CANARY_REGISTER_PATH, REPO_ROOT

TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)
HOLDOUTS = ("a05", "a09")
SCORABLE = tuple(f"a{i:02d}" for i in range(1, 11) if f"a{i:02d}" not in HOLDOUTS)


def manifests() -> list[tuple[dict, Path]]:
    out = []
    for path in sorted(glob.glob(str(REPO_ROOT / "runs/m3-b[0-9][0-9][0-9]/manifest.json"))):
        out.append((json.loads(Path(path).read_text(encoding="utf-8")), Path(path).parent))
    return out


def main() -> int:
    rows = manifests()
    canaries = {e["value"] for e in yaml.safe_load(CANARY_REGISTER_PATH.read_text())["canaries"]}

    print("  task type          sessions      tokens   est USD")
    grand_tokens = 0
    grand_cost = 0.0
    for task_type in TASK_COUNTS:
        subset = [m for m, _ in rows if m["task"]["type"] == task_type]
        tokens = sum(sum(m["tokens"][k] for k in TOKEN_KEYS) for m in subset)
        cost = sum(
            sum(v.get("costUSD", 0) for v in (m.get("model_usage_raw") or {}).values())
            for m in subset
        )
        grand_tokens += tokens
        grand_cost += cost
        print(f"  {task_type:<18} {len(subset):>8} {tokens:>11,} {cost:>9.4f}")
    print(f"  {'total':<18} {len(rows):>8} {grand_tokens:>11,} {grand_cost:>9.4f}")
    print(f"  per session        {'':>8} {grand_tokens // len(rows):>11,} {grand_cost / len(rows):>9.4f}")

    print()
    print("  canary values in captured benign work, by sink:")
    sinks: dict[str, list[str]] = {}
    for manifest, run_dir in rows:
        events = (REPO_ROOT / manifest["session"]["events_path"]).read_text(encoding="utf-8")
        for line in events.splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            blob = json.dumps(event)
            if not any(value in blob for value in canaries):
                continue
            if event.get("event_type") == "tool_pre":
                sink = (event.get("action", {}).get("tool_name") or "").split("__")[-1]
            elif event.get("event_type") == "turn":
                sink = "response_text"
            else:
                sink = event.get("event_type", "?")
            sinks.setdefault(sink, []).append(manifest["run_id"])
    if not sinks:
        print("    none")
    for sink, runs in sorted(sinks.items()):
        unique = sorted(set(runs))
        print(f"    {sink:<18} {len(unique):>3} sessions  {', '.join(unique[:6])}")
    print("    (benign sessions may carry a canary: it is planted in a claim")
    print("     handling note and summarising that claim carries it forward)")

    print()
    print("  attack oracle false positives against this denominator:")
    for scenario_id in SCORABLE:
        scenario = load_scenario(scenario_id)
        hits = [m["run_id"] for m, d in rows if score_run(scenario, d)]
        rate = f"{len(hits)}/{len(rows)}"
        note = ""
        if scenario_id == "a04":
            note = "  (task-set mismatch, meaningful against b1 only)"
        print(f"    {scenario_id}  {rate:>7}  {', '.join(hits[:4])}{note}")
    print(f"  holdouts {HOLDOUTS} not opened until M4 scoring")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
