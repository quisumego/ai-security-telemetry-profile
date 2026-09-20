"""The attack capture runner.

Runs the trials of one scenario, or all scenarios, one fresh session per trial
with the scenario's prompt held identical across trials so the only variation
is the model's. Each trial writes its own run directory and manifest under
runs/.

**Resumable.** A trial is complete when its manifest exists with an outcome on
the scenario's legitimate list. The runner skips completed trials and starts at
the first incomplete one, because a capture draws on the owner's day-to-day
allowance and a long run can hit a usage window part way. On any subtype not on
the legitimate list it stops the whole run and reports, rather than burning the
rest of a window on failures.

The legitimate list is per scenario. For A8 it includes error_max_budget_usd,
because a session cut off by the 0.50 guard is a consumption result, not a
fault. For every other scenario that subtype stops the run. The guard itself
stays at 0.50 for every scenario, so the configuration is identical across the
corpus.

No model settings are varied here. The model is pinned, fallback stays null,
thinking stays as configured (disabled), and setting_sources and tools stay
empty. If a window is hit, the run stops cleanly and is resumed in the next
window; it is never continued on degraded settings.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attacks.oracles import load_scenario
from lab.agent import run_session
from lab.config import REPO_ROOT, load_config
from lab.harness import RUNS_DIR, build_manifest

SCENARIO_IDS = [f"a{i:02d}" for i in range(1, 11)]


def _overlay_dirs(scenario: dict[str, Any]) -> tuple[Path, ...]:
    corpus = (scenario.get("overlay") or {}).get("corpus")
    if not corpus:
        return ()
    return ((REPO_ROOT / corpus),)


def _extra_pages(scenario: dict[str, Any]) -> dict[str, str] | None:
    fixtures = (scenario.get("overlay") or {}).get("web_fixtures")
    if not fixtures:
        return None
    import yaml

    data = yaml.safe_load((REPO_ROOT / fixtures).read_text(encoding="utf-8"))
    return dict(data.get("pages") or {})


def run_dir_for(scenario_id: str, trial: int) -> Path:
    return RUNS_DIR / f"m2-{scenario_id}-t{trial:02d}"


def trial_is_complete(run_dir: Path, legitimate: set[str]) -> bool:
    """A trial is complete when its manifest shows a legitimate outcome.

    is_error is checked alongside subtype: the CLI can report subtype success
    with is_error true and an api_error_status set, which is a failed call, not
    a completed trial.
    """
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    session = manifest.get("session", {})
    subtype = session.get("subtype")
    if subtype == "success" and session.get("is_error"):
        return False
    return subtype in legitimate


async def run_scenario(
    scenario_id: str, trials: int, *, dry_run: bool = False
) -> dict[str, Any]:
    """Run the incomplete trials of one scenario. Returns a small report."""
    scenario = load_scenario(scenario_id)
    legitimate = set(scenario["legitimate_outcomes"])
    prompt = scenario["prompt"]
    overlay_dirs = _overlay_dirs(scenario)
    extra_pages = _extra_pages(scenario)
    config = load_config()

    ran, skipped, outcomes = 0, 0, []
    for trial in range(1, trials + 1):
        run_dir = run_dir_for(scenario_id, trial)
        if trial_is_complete(run_dir, legitimate):
            skipped += 1
            continue
        if dry_run:
            outcomes.append((trial, "dry-run"))
            continue

        result = await run_session(
            prompt=prompt,
            run_dir=run_dir,
            config=config,
            overlay_dirs=overlay_dirs,
            extra_pages=extra_pages,
        )
        manifest = build_manifest(
            run_id=run_dir.name,
            label=f"m2 {scenario_id} trial {trial}",
            prompt=prompt,
            seed=trial,
            result=result,
            scenario={
                "id": scenario_id,
                "trial": trial,
                "holdout": bool(scenario["holdout"]),
                "overlay_digest": None,
            },
        )
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        ran += 1
        outcomes.append((trial, result.subtype))

        if result.subtype not in legitimate:
            return {
                "scenario": scenario_id,
                "ran": ran,
                "skipped": skipped,
                "outcomes": outcomes,
                "stopped": True,
                "reason": f"trial {trial} ended {result.subtype!r}, not on the legitimate list",
            }

    return {
        "scenario": scenario_id,
        "ran": ran,
        "skipped": skipped,
        "outcomes": outcomes,
        "stopped": False,
    }


async def main_async(args: argparse.Namespace) -> int:
    ids = SCENARIO_IDS if args.all else [args.scenario]
    for scenario_id in ids:
        report = await run_scenario(scenario_id, args.trials, dry_run=args.dry_run)
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(
            f"[{stamp}] {report['scenario']}: ran {report['ran']}, "
            f"skipped {report['skipped']} already complete"
        )
        for trial, subtype in report["outcomes"]:
            print(f"    trial {trial:>2}  {subtype}")
        if report["stopped"]:
            print(f"    STOPPED: {report['reason']}")
            print("    Fix the cause and re-run; completed trials will be skipped.")
            return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture attack scenario trials.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scenario", help="A scenario id, for example a01.")
    group.add_argument("--all", action="store_true", help="Every scenario in order.")
    parser.add_argument("--trials", type=int, default=10, help="Trials per scenario.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would run without making any model call.",
    )
    return asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
