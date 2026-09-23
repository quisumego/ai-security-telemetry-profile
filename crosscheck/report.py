"""The M7b report: attack success against the local model, beside M2.

    .venv/bin/python -m crosscheck.report            # print the table
    .venv/bin/python -m crosscheck.report --write    # write results/m7b-crosscheck.*

**Scored by the frozen oracles.** `attacks/oracles.py` decides success on every
local trial exactly as it did on the M2 corpus. Delivery is counted beside it
by `attacks/delivery.py` for the five overlay classes and is never divided into
it. A zero with no delivery is unmeasured, not a refusal.

**The denominator is the completed trials.** A trial is complete when the
runner recorded a legitimate outcome and a clean contamination check. A trial
recorded as failed stops its scenario (ruling 13) and is listed, never scored.

**The tool-call count decides nothing** (ruling 18). For a prompt-delivered
class, a small model's zero could be inability rather than refusal, and no
frozen measure separates the two; the count is there so a reader can see
whether the agent acted at all.

**A8 carries its deciding conditions** (ruling 17). A local tokeniser's count
is not known to mean what the register's `turn.tokens_in` means, so a trial
that succeeds on the token condition alone is flagged, and no token figure is
compared with M2.

The results hold identifiers and counts only, never event content, so no
canary value can reach them; the canary placement scan covers `results/`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attacks.delivery import delivery_count, serves_an_overlay
from attacks.oracles import load_scenario, read_events, read_manifest, score_run
from attacks.report import SCENARIO_IDS, scenario_figures
from crosscheck import rulings
from crosscheck.runner import trial_state
from lab.config import REPO_ROOT

RUNS_DIR = REPO_ROOT / "runs"
RESULTS_JSON = REPO_ROOT / "results" / "m7b-crosscheck.json"
RESULTS_MD = REPO_ROOT / "results" / "m7b-crosscheck.md"
METADATA = ("commit", "tree_clean", "date")


def local_run_dirs(scenario_id: str, runs_dir: Path = RUNS_DIR) -> list[Path]:
    return sorted(runs_dir.glob(f"{rulings.RUN_PREFIX}-{scenario_id}-t[0-9][0-9]"))


def a08_conditions(scenario: dict[str, Any], run_dir: Path) -> list[str]:
    """Which of the frozen A8 conditions hold on one trial, in oracle order."""
    t = scenario["oracle"]["thresholds"]
    manifest = read_manifest(run_dir)
    held = []
    if manifest["session"].get("tool_calls", 0) >= t["tool_calls_at_least"]:
        held.append("tool_calls")
    if manifest["session"].get("subtype") in set(t["ending_subtypes"]):
        held.append(str(manifest["session"]["subtype"]))
    floor = t["tokens_in_any_turn_at_least"]
    if any(e.get("event_type") == "turn" and (e["turn"].get("tokens_in") or 0) >= floor
           for e in read_events(run_dir)):
        held.append("tokens_in")
    return held


def class_row(scenario_id: str, runs_dir: Path = RUNS_DIR) -> dict[str, Any]:
    scenario = load_scenario(scenario_id)
    legitimate = set(scenario["legitimate_outcomes"])
    dirs = local_run_dirs(scenario_id, runs_dir)
    states = {d.name: trial_state(d, legitimate) for d in dirs}
    done = [d for d in dirs if states[d.name] == "complete"]
    successes = sum(1 for d in done if score_run(scenario, d))
    overlay = serves_an_overlay(scenario)
    m2 = scenario_figures(scenario_id)
    row: dict[str, Any] = {
        "id": scenario_id,
        "class": f"A{int(scenario_id[1:])}",
        "holdout": bool(scenario["holdout"]),
        "local": {
            "trials": len(done),
            "successes": successes,
            "delivery": delivery_count(scenario, done) if overlay else None,
            "tool_calls": sum(read_manifest(d)["session"].get("tool_calls", 0) for d in done),
            "failed": sorted(n for n, s in states.items() if s == "failed"),
        },
        "m2": {"trials": m2["trials"], "successes": m2["successes"], "delivery": m2["delivery"]},
    }
    local, base = row["local"], row["m2"]
    row["change_points"] = (
        round(100 * local["successes"] / local["trials"] - 100 * base["successes"] / base["trials"], 1)
        if local["trials"] else None
    )
    row["unmeasured"] = bool(overlay and local["trials"] and local["delivery"] == 0)
    if scenario_id == "a08":
        conditions = {d.name: a08_conditions(scenario, d) for d in done}
        row["a08_conditions"] = conditions
        row["a08_token_only"] = sorted(n for n, c in conditions.items() if c == ["tokens_in"])
    return row


def build(runs_dir: Path = RUNS_DIR) -> dict[str, Any]:
    rows = [class_row(s, runs_dir) for s in SCENARIO_IDS]
    manifests = [read_manifest(d) for s in SCENARIO_IDS for d in local_run_dirs(s, runs_dir)
                 if (d / "manifest.json").is_file()]
    local = [m["local"] for m in manifests if m.get("local")]
    return {
        "model": rulings.LOCAL_MODEL,
        "digests": sorted({x["digest"] for x in local}),
        "ollama_versions": sorted({str(x["ollama_version"]) for x in local}),
        "cli_spawned_versions": sorted({str(x["cli_spawned_version"]) for x in local}),
        "context_length_in_force": sorted({x["context_length_in_force"] for x in local
                                           if x["context_length_in_force"] is not None}),
        "per_class": rows,
        "total": {
            "local_trials": sum(r["local"]["trials"] for r in rows),
            "local_successes": sum(r["local"]["successes"] for r in rows),
            "m2_trials": sum(r["m2"]["trials"] for r in rows),
            "m2_successes": sum(r["m2"]["successes"] for r in rows),
        },
    }


def _rate(n: int, d: int) -> str:
    return f"{n}/{d} ({n * 100 // d}%)" if d else "no completed trial"


def _frac(n: int | None, d: int) -> str:
    return "n/a" if n is None else f"{n}/{d}"


def render_markdown(doc: dict[str, Any]) -> str:
    lines = [
        "# M7b local model cross-check: attack success",
        "",
        "Generated by `.venv/bin/python -m crosscheck.report --write`. Do not edit by hand.",
        "",
        f"Local model `{doc['model']}`, digest {', '.join(doc['digests']) or 'none recorded'}, "
        f"Ollama {', '.join(doc['ollama_versions']) or 'none recorded'}, spawned CLI "
        f"{', '.join(doc['cli_spawned_versions']) or 'none recorded'}. M2 is `claude-haiku-4-5`.",
        "",
        "Success is decided by the frozen oracles. Delivery is counted beside it and never divided "
        "into it. The tool-call column decides nothing. The local denominator is the trials completed "
        "with a legitimate outcome and a clean contamination check.",
        "",
        "| Class | Local success | Local delivery | Local tool calls | M2 success | M2 delivery | Change, points | Failed trials |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in doc["per_class"]:
        loc, m2 = r["local"], r["m2"]
        name = r["class"] + (" \\*" if r["holdout"] else "")
        change = "n/a" if r["change_points"] is None else f"{r['change_points']:+.1f}"
        note = " unmeasured" if r["unmeasured"] else ""
        lines.append(
            f"| {name} | {_rate(loc['successes'], loc['trials'])}{note} | "
            f"{_frac(loc['delivery'], loc['trials'])} | {loc['tool_calls']} | "
            f"{_rate(m2['successes'], m2['trials'])} | {_frac(m2['delivery'], m2['trials'])} | "
            f"{change} | {', '.join(loc['failed']) or 'none'} |"
        )
    t = doc["total"]
    lines += [
        f"| **Total** | **{_rate(t['local_successes'], t['local_trials'])}** | | | "
        f"**{_rate(t['m2_successes'], t['m2_trials'])}** | | | |",
        "",
        "\\* holdout at M2.",
        "",
    ]
    short = [r["class"] for r in doc["per_class"] if r["local"]["trials"] != r["m2"]["trials"]]
    if short:
        lines += [
            f"The totals are not directly comparable: the local denominator is {t['local_trials']} "
            f"against M2's {t['m2_trials']}, because {', '.join(short)} completed fewer trials than "
            "M2 captured. A class's rate on fewer than ten trials is its own figure and is not "
            "comparable with M2's.",
            "",
        ]
    a08 = next(r for r in doc["per_class"] if r["id"] == "a08")
    if a08.get("a08_conditions"):
        lines += ["## A8, the deciding conditions per trial", "",
                  "A trial that succeeds on `tokens_in` alone rests on a local tokeniser's count, "
                  "which is not known to mean what the register's `turn.tokens_in` means.", "",
                  "| Trial | Conditions held |", "|---|---|"]
        for run_id, held in a08["a08_conditions"].items():
            flag = " (token condition only)" if held == ["tokens_in"] else ""
            lines.append(f"| {run_id} | {', '.join(held) or 'none'}{flag} |")
        lines.append("")
    return "\n".join(lines)


def _git(*args: str) -> str:
    return subprocess.run(("git", *args), cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The M7b attack success report.")
    parser.add_argument("--write", action="store_true", help="write results/m7b-crosscheck.*")
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
        RESULTS_MD.write_text(render_markdown(doc) + "\n", encoding="utf-8")
    print(render_markdown(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
