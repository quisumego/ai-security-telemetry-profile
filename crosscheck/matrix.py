"""The necessity matrix re-derived over the local pass, and compared with M5.

    .venv/bin/python -m crosscheck.matrix            # print the comparison
    .venv/bin/python -m crosscheck.matrix --write    # write results/m7b-necessity.*

**The M5 machinery, unchanged, over different captures** (ruling 19). The sweep
is `ablation.matrix.build`, run over the completed local attack trials with
the hundred M3 benign sessions as the false positive denominator. No local
benign pass was captured, so the denominator is the Claude-captured one, and
the page says so. The counted detector per class is M5 ruling 1. The recorded
baseline check is off, because that baseline belongs to the M2 corpus.

**A comparison, never a tiering.** The tiers the rule would give over the local
matrix are printed beside M5's and never applied: `schema/fields.yaml`,
`results/necessity.json` and `results/necessity-matrix.md` are not written
here, and a test holds that. Where the local pass has no successful trial for a
class, its cells read `nt`, in M5's notation.

The results hold identifiers and counts only, never event content.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from ablation.ablate import Capture, _read_capture
from ablation.matrix import NECESSITY_JSON, build as sweep_build
from attacks.oracles import load_scenario, score_run
from attacks.report import SCENARIO_IDS
from crosscheck import rulings
from crosscheck.runner import trial_state
from lab.config import REPO_ROOT

RUNS_DIR = REPO_ROOT / "runs"
RESULTS_JSON = REPO_ROOT / "results" / "m7b-necessity.json"
RESULTS_MD = REPO_ROOT / "results" / "m7b-necessity-matrix.md"
CLASS_ORDER = tuple(f"A{i}" for i in range(1, 11))


def local_captures(runs_dir: Path = RUNS_DIR) -> tuple[Capture, ...]:
    """The completed local attack trials and the M3 benign sessions, read only."""
    captures: list[Capture] = []
    for scenario_id in SCENARIO_IDS:
        scenario = load_scenario(scenario_id)
        legitimate = set(scenario["legitimate_outcomes"])
        for run_dir in sorted(runs_dir.glob(f"{rulings.RUN_PREFIX}-{scenario_id}-t[0-9][0-9]")):
            if trial_state(run_dir, legitimate) != "complete":
                continue
            manifest, events = _read_capture(run_dir)
            captures.append(Capture(
                run_id=manifest["run_id"],
                events=tuple(events),
                attack_class=f"A{int(scenario_id[1:])}",
                successful=bool(score_run(scenario, run_dir)),
            ))
    for run_dir in sorted(runs_dir.glob("m3-b[0-9][0-9][0-9]")):
        manifest, events = _read_capture(run_dir)
        captures.append(Capture(
            run_id=manifest["run_id"],
            events=tuple(events),
            benign_type=str(manifest["task"]["type"]),
        ))
    return tuple(captures)


def compare(local: dict[str, Any], m5: dict[str, Any]) -> dict[str, Any]:
    """Cell by cell and tier by tier, local against M5."""
    fields = list(m5["field_order"])
    cells, tiers = {}, {}
    differences, tier_differences = [], []
    for name in fields:
        cells[name] = {cls: local["single"][name]["cells"][cls]["cell"] for cls in CLASS_ORDER}
        for cls in CLASS_ORDER:
            before = m5["single"][name]["cells"][cls]["cell"]
            after = cells[name][cls]
            if before != after:
                differences.append({"field": name, "class": cls, "m5": before, "local": after})
        tiers[name] = local["tiers"][name]["tier"]
        if tiers[name] != m5["tiers"][name]["tier"]:
            tier_differences.append({"field": name, "m5": m5["tiers"][name]["tier"], "local": tiers[name]})
    return {
        "field_order": fields,
        "classes": {
            cls: {
                "local_trials": local["classes"][cls]["trials"],
                "local_successful": local["classes"][cls]["successful"],
                "m5_trials": m5["classes"][cls]["trials"],
                "m5_successful": m5["classes"][cls]["successful"],
                "detector": local["classes"][cls]["detector"],
            }
            for cls in CLASS_ORDER
        },
        "cells": cells,
        "differences": differences,
        "tiers_if_applied": tiers,
        "tier_differences": tier_differences,
        "headline_if_applied": local["verdict"]["headline"],
        "m5_headline": m5["verdict"]["headline"],
    }


def build(captures: Sequence[Capture] | None = None) -> dict[str, Any]:
    captures = local_captures() if captures is None else captures
    local = sweep_build(captures, check_baseline=False)
    m5 = json.loads(NECESSITY_JSON.read_text(encoding="utf-8"))
    return {
        "about": "The M7b local pass re-derivation of the necessity matrix, compared with M5. "
                 "Identifiers and counts only. Tiers are printed, never applied.",
        "model": rulings.LOCAL_MODEL,
        "benign_denominator": "the hundred M3 sessions, captured on claude-haiku-4-5",
        "m5_commit": m5["commit"],
        **compare(local, m5),
    }


def render_markdown(doc: dict[str, Any]) -> str:
    lines = [
        "# M7b local model cross-check: the necessity matrix",
        "",
        "Generated by `.venv/bin/python -m crosscheck.matrix --write`. Do not edit by hand.",
        "",
        f"The M5 sweep, unchanged, over the completed local trials on `{doc['model']}`, with "
        f"{doc['benign_denominator']} as the false positive denominator. A comparison only: the "
        "tiers below are what the rule would give and are never applied. M5's notation: `X`, `x` "
        "and `.` are the three measured states, `nr` not read by the class's detector, `nt` no "
        "successful trial, `ab` absent, suffix `c` circular.",
        "",
        "## Successful trials per class",
        "",
        "| Class | Detector | Local successful | M5 successful |",
        "|---|---|---|---|",
    ]
    for cls, c in doc["classes"].items():
        lines.append(f"| {cls} | {c['detector'] or 'none'} | {c['local_successful']}/{c['local_trials']} | "
                     f"{c['m5_successful']}/{c['m5_trials']} |")
    lines += ["", f"## Cells that differ from M5: {len(doc['differences'])}", ""]
    if doc["differences"]:
        lines += ["| Field | Class | M5 | Local |", "|---|---|---|---|"]
        lines += [f"| `{d['field']}` | {d['class']} | `{d['m5']}` | `{d['local']}` |" for d in doc["differences"]]
    else:
        lines.append("None.")
    lines += ["", f"## Tiers the rule would give that differ from M5: {len(doc['tier_differences'])}", ""]
    if doc["tier_differences"]:
        lines += ["| Field | M5 tier | Local, not applied |", "|---|---|---|"]
        lines += [f"| `{d['field']}` | {d['m5']} | {d['local']} |" for d in doc["tier_differences"]]
    else:
        lines.append("None.")
    lines += ["", f"Headline the rule would give: {doc['headline_if_applied']}. M5: {doc['m5_headline']}.",
              "", "## The local matrix", "",
              "| Field | " + " | ".join(CLASS_ORDER) + " |", "|---|" + "---|" * len(CLASS_ORDER)]
    for name in doc["field_order"]:
        lines.append(f"| `{name}` | " + " | ".join(f"`{doc['cells'][name][c]}`" for c in CLASS_ORDER) + " |")
    lines.append("")
    return "\n".join(lines)


def _git(*args: str) -> str:
    return subprocess.run(("git", *args), cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The M7b necessity matrix comparison.")
    parser.add_argument("--write", action="store_true", help="write results/m7b-necessity.*")
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
