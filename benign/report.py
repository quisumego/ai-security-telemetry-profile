"""The M3 benign report: counts, computed from the captures.

Prints the per-type session counts, where canary values appear in captured
benign work, the per-session cost re-derived from the real captures, and the
false positive rate of every non-holdout attack oracle against this corpus.

**The false positive column is the point of M3.** An oracle that fires on
benign traffic has no precision, whatever its attack rate says, and that can
only be seen by running it against a denominator. A5 and A9 are left out, as
they were at M3, when they were the holdouts. Both were opened at M4 scoring,
and detect.evaluate --include-holdouts reports them.

`--write`, added at M8 by the owner's ruling of 1 October 2026, records the same
figures in results/benign.json, identifiers and counts only, so that a
published figure from this report has a committed source. The printed report
is unchanged.

    .venv/bin/python -m benign.report
    .venv/bin/python -m benign.report --write    # write results/benign.json
"""

from __future__ import annotations

import argparse
import glob
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
A04_NOTE = "task-set mismatch, meaningful against b1 only"

RESULTS_JSON = REPO_ROOT / "results" / "benign.json"
METADATA = ("commit", "tree_clean", "date")


def manifests() -> list[tuple[dict, Path]]:
    out = []
    for path in sorted(glob.glob(str(REPO_ROOT / "runs/m3-b[0-9][0-9][0-9]/manifest.json"))):
        out.append((json.loads(Path(path).read_text(encoding="utf-8")), Path(path).parent))
    return out


def build() -> dict[str, Any]:
    """Every figure the report prints, read from the captures, read only."""
    rows = manifests()
    canaries = {e["value"] for e in yaml.safe_load(CANARY_REGISTER_PATH.read_text())["canaries"]}

    per_type: dict[str, dict[str, Any]] = {}
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
        per_type[task_type] = {"sessions": len(subset), "tokens": tokens, "cost_usd": round(cost, 6)}

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

    false_positives: dict[str, dict[str, Any]] = {}
    for scenario_id in SCORABLE:
        scenario = load_scenario(scenario_id)
        hits = [m["run_id"] for m, d in rows if score_run(scenario, d)]
        entry: dict[str, Any] = {"fired": len(hits), "of": len(rows), "sessions": hits}
        if scenario_id == "a04":
            entry["note"] = A04_NOTE
        false_positives[scenario_id] = entry

    return {
        "about": (
            "The M3 benign report: per task type counts, the sessions whose captured "
            "work carries a canary value, by sink, and every non-holdout attack "
            "oracle's false positives against the hundred benign sessions. "
            "Identifiers and counts only. Rendered by benign.report."
        ),
        "command": ".venv/bin/python -m benign.report --write",
        "per_type": per_type,
        "total": {
            "sessions": len(rows),
            "tokens": grand_tokens,
            "cost_usd": round(grand_cost, 6),
            "tokens_per_session": grand_tokens // len(rows),
            "cost_usd_per_session": round(grand_cost / len(rows), 6),
        },
        "canary_sinks": {sink: sorted(set(runs)) for sink, runs in sorted(sinks.items())},
        "oracle_false_positives": false_positives,
        "holdouts_left_out": list(HOLDOUTS),
    }


def render(doc: dict[str, Any]) -> str:
    """The printed report, as it read before --write existed."""
    out = ["  task type          sessions      tokens   est USD"]
    for task_type, row in doc["per_type"].items():
        out.append(f"  {task_type:<18} {row['sessions']:>8} {row['tokens']:>11,} {row['cost_usd']:>9.4f}")
    total = doc["total"]
    out.append(f"  {'total':<18} {total['sessions']:>8} {total['tokens']:>11,} {total['cost_usd']:>9.4f}")
    out.append(f"  per session        {'':>8} {total['tokens_per_session']:>11,} {total['cost_usd_per_session']:>9.4f}")
    out.append("")
    out.append("  canary values in captured benign work, by sink:")
    if not doc["canary_sinks"]:
        out.append("    none")
    for sink, unique in doc["canary_sinks"].items():
        out.append(f"    {sink:<18} {len(unique):>3} sessions  {', '.join(unique[:6])}")
    out.append("    (benign sessions may carry a canary: it is planted in a claim")
    out.append("     handling note and summarising that claim carries it forward)")
    out.append("")
    out.append("  attack oracle false positives against this denominator:")
    for scenario_id, entry in doc["oracle_false_positives"].items():
        rate = f"{entry['fired']}/{entry['of']}"
        note = f"  ({entry['note']})" if "note" in entry else ""
        out.append(f"    {scenario_id}  {rate:>7}  {', '.join(entry['sessions'][:4])}{note}")
    out.append(f"  holdouts {tuple(doc['holdouts_left_out'])} left out, as at M3; opened at M4, see detect.evaluate --include-holdouts")
    return "\n".join(out)


def _git(*args: str) -> str:
    return subprocess.run(("git", *args), cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The M3 benign report.")
    parser.add_argument("--write", action="store_true", help="write results/benign.json")
    args = parser.parse_args(argv)
    doc = build()
    if args.write:
        doc = {
            **doc,
            "commit": _git("rev-parse", "HEAD"),
            "tree_clean": _git("status", "--porcelain") == "",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
        RESULTS_JSON.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(render(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
