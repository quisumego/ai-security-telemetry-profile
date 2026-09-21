"""The M2 capture report: counts, computed from the captures.

Section 8.7 requires attack success per scenario as `n/10 (n0%)`, token totals
summed, and the per-session cost re-derived from real captures rather than
carried over from the plan's estimate. This produces all three from the
committed runs, so the figures in the build log can be regenerated rather than
trusted.

Delivery is reported beside success for every overlay-delivered scenario, per
the rule adopted after A2. A success rate is never divided by the delivery
count: both are printed and neither is folded into the other.

    .venv/bin/python -m attacks.report
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

from attacks.delivery import delivery_count, serves_an_overlay
from attacks.oracles import load_scenario, score_run
from lab.config import REPO_ROOT

SCENARIO_IDS = tuple(f"a{i:02d}" for i in range(1, 11))
TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def run_dirs(scenario_id: str) -> list[Path]:
    return [Path(p) for p in sorted(glob.glob(str(REPO_ROOT / f"runs/m2-{scenario_id}-t*")))]


def scenario_figures(scenario_id: str) -> dict:
    scenario = load_scenario(scenario_id)
    dirs = run_dirs(scenario_id)
    successes = sum(1 for d in dirs if score_run(scenario, d))
    tokens = 0
    cost = 0.0
    for d in dirs:
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        tokens += sum(manifest["tokens"][k] for k in TOKEN_KEYS)
        cost += sum(v.get("costUSD", 0) for v in (manifest.get("model_usage_raw") or {}).values())
    return {
        "id": scenario_id,
        "class": scenario["class"],
        "holdout": bool(scenario["holdout"]),
        "trials": len(dirs),
        "successes": successes,
        "delivery": delivery_count(scenario, dirs) if serves_an_overlay(scenario) else None,
        "tokens": tokens,
        "cost": cost,
    }


def main() -> int:
    rows = [scenario_figures(s) for s in SCENARIO_IDS]
    total_tokens = sum(r["tokens"] for r in rows)
    total_cost = sum(r["cost"] for r in rows)
    total_trials = sum(r["trials"] for r in rows)
    total_successes = sum(r["successes"] for r in rows)

    print(f"{'id':<5} {'class':<38} {'success':>12} {'delivery':>10} {'tokens':>10} {'est USD':>9}")
    for r in rows:
        rate = f"{r['successes']}/{r['trials']} ({r['successes'] * 100 // r['trials']}%)"
        delivery = f"{r['delivery']}/{r['trials']}" if r["delivery"] is not None else "n/a"
        mark = " *" if r["holdout"] else "  "
        print(
            f"{r['id']}{mark:<3}{r['class']:<38} {rate:>12} {delivery:>10} "
            f"{r['tokens']:>10,} {r['cost']:>9.4f}"
        )
    print()
    print(f"  * holdout, committed before any scenario file existed")
    print(f"  trials:            {total_trials}")
    print(f"  attack successes:  {total_successes}/{total_trials} ({total_successes * 100 // total_trials}%)")
    print(f"  tokens:            {total_tokens:,}")
    print(f"  estimated cost:    ${total_cost:.4f}")
    print(f"  per session:       {total_tokens // total_trials:,} tokens, ${total_cost / total_trials:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
