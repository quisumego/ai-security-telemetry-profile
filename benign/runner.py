"""The benign capture runner.

Same contract as `attacks/runner.py` and for the same reasons: one fresh
session per benign task, resumable so a usage window hit costs time and not
work, and it stops on any outcome the corpus does not allow rather than
burning the rest of a window on failures.

A benign session is complete when its manifest shows `success` without
`is_error`. Unlike the attack corpus there is no legitimate error outcome:
`error_max_turns` is a scored result for A8 and a fault here, because a benign
claim summary that ran to the turn cap did not do the task it was measuring.

    .venv/bin/python -m benign.runner --all
    .venv/bin/python -m benign.runner --task b1 --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benign.tasks import CORPUS_SEED, TASK_TYPES, BenignSession, generate_corpus
from lab.agent import run_session
from lab.config import load_config
from lab.harness import RUNS_DIR, build_manifest

LEGITIMATE_OUTCOMES = {"success"}


def run_dir_for(session: BenignSession) -> Path:
    return RUNS_DIR / f"m3-{session.id}"


def trial_is_complete(run_dir: Path) -> bool:
    """Complete means a manifest showing success that is not an error.

    The CLI can report subtype success with is_error true and an api_error
    status set, which is a failed call and not a completed session. The attack
    runner checks the same pair for the same reason.
    """
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    session = manifest.get("session", {})
    if session.get("is_error"):
        return False
    return session.get("subtype") in LEGITIMATE_OUTCOMES


async def run_batch(
    sessions: list[BenignSession], *, dry_run: bool = False
) -> dict[str, Any]:
    config = load_config()
    ran, skipped, outcomes = 0, 0, []
    for session in sessions:
        run_dir = run_dir_for(session)
        if trial_is_complete(run_dir):
            skipped += 1
            continue
        if dry_run:
            outcomes.append((session.id, "dry-run"))
            continue

        result = await run_session(
            prompt=session.prompt,
            run_dir=run_dir,
            config=config,
            session_id=None,
        )
        manifest = build_manifest(
            run_id=run_dir.name,
            label=f"m3 {session.task_type} {session.id}",
            prompt=session.prompt,
            seed=session.seed,
            result=result,
            task={
                "id": session.id,
                "type": session.task_type,
                "claim_reference": session.claim_reference,
                "corpus_seed": CORPUS_SEED,
            },
        )
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        ran += 1
        outcomes.append((session.id, result.subtype))
        if result.subtype not in LEGITIMATE_OUTCOMES or result.is_error:
            return {
                "ran": ran,
                "skipped": skipped,
                "outcomes": outcomes,
                "stopped": True,
                "stopped_on": session.id,
                "subtype": result.subtype,
            }
    return {"ran": ran, "skipped": skipped, "outcomes": outcomes, "stopped": False}


async def main_async(args: argparse.Namespace) -> int:
    corpus = generate_corpus(args.seed)
    if args.task:
        corpus = [s for s in corpus if s.task_type == args.task]
    if args.limit:
        corpus = corpus[: args.limit]

    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    report = await run_batch(corpus, dry_run=args.dry_run)
    label = args.task or "all"
    print(
        f"[{stamp}] benign {label}: ran {report['ran']}, "
        f"skipped {report['skipped']} already complete"
    )
    for session_id, outcome in report["outcomes"]:
        print(f"    {session_id}  {outcome}")
    if report["stopped"]:
        print(f"\nSTOPPED on {report['stopped_on']}: subtype {report['subtype']!r}")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture the benign corpus.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", choices=TASK_TYPES, help="One task type, for example b1.")
    group.add_argument("--all", action="store_true", help="Every benign session in order.")
    parser.add_argument("--limit", type=int, default=None, help="Stop after this many.")
    parser.add_argument("--seed", type=int, default=CORPUS_SEED)
    parser.add_argument("--dry-run", action="store_true", help="List without any model call.")
    return asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
