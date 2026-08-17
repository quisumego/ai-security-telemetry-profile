"""The run harness.

Pins the model, runs a session, and writes a manifest recording what produced
the capture: model, config version, prompt version, seed, corpus digest, token
counts and date.

Token counts are the primary record, not `total_cost_usd`. The SDK documents
that figure as an estimate with stated accuracy caveats, and the project is
funded from a subscription rather than billed per call, so the cost estimate is
recorded for interest and the token counts are what the M6 cost model reads.

Run with:

    .venv/bin/python -m lab.harness --prompt "..." --label benign-smoke
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lab.agent import SessionResult, run_session
from lab.config import (
    CANARY_REGISTER_PATH,
    CLAIMS_PATH,
    CORPUS_DIR,
    REPO_ROOT,
    load_config,
)
from lab.tools import TOOL_NAMES

RUNS_DIR = REPO_ROOT / "runs"

# Everything that must be identical for two runs to be comparable.
CORPUS_INPUTS = (
    CORPUS_DIR,
    REPO_ROOT / "lab" / "case_files",
    CLAIMS_PATH,
    CANARY_REGISTER_PATH,
    REPO_ROOT / "lab" / "web_fixtures.yaml",
)


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def corpus_digest(inputs: tuple[Path, ...] = CORPUS_INPUTS) -> str:
    """One digest over every input a session can read.

    A capture whose digest differs from another's was taken against different
    material, whatever the commit history says. This is the check that survives
    an accidental edit to a frozen file.
    """
    parts: list[str] = []
    for entry in sorted(inputs):
        if entry.is_dir():
            for path in sorted(entry.rglob("*")):
                if path.is_file():
                    parts.append(f"{path.relative_to(REPO_ROOT)}:{_file_digest(path)}")
        elif entry.is_file():
            parts.append(f"{entry.relative_to(REPO_ROOT)}:{_file_digest(entry)}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str | None:
        try:
            return subprocess.run(
                args, cwd=REPO_ROOT, capture_output=True, text=True, check=True
            ).stdout.strip()
        except (subprocess.CalledProcessError, OSError):
            return None

    status = run("git", "status", "--porcelain")
    return {
        "commit": run("git", "rev-parse", "HEAD"),
        "working_tree_clean": status == "" if status is not None else None,
    }


def sdk_versions() -> dict[str, Any]:
    versions: dict[str, Any] = {"claude_agent_sdk": None, "claude_cli": None}
    try:
        import claude_agent_sdk

        versions["claude_agent_sdk"] = getattr(claude_agent_sdk, "__version__", None)
    except ImportError:
        pass
    try:
        versions["claude_cli"] = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        pass
    return versions


def build_manifest(
    *,
    run_id: str,
    label: str,
    prompt: str,
    seed: int,
    result: SessionResult,
) -> dict[str, Any]:
    config = load_config()
    return {
        "run_id": run_id,
        "label": label,
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "seed": seed,
        "model": {
            "requested": config.model_id,
            # Recorded explicitly rather than omitted. A reader can then see
            # that no fallback was configured, instead of having to infer it.
            "fallback_model": config.fallback_model,
            "thinking": config.thinking,
            "resolved": result.models_seen,
            "max_turns": config.max_turns,
            "max_budget_usd": config.max_budget_usd,
        },
        "versions": {
            "config_version": config.config_version,
            "astp_version": config.astp_version,
            "policy_version": config.policy_version,
            "system_prompt_version": config.system_prompt_version,
            **sdk_versions(),
        },
        "corpus": {
            "digest": corpus_digest(),
            # Set at the M2 freeze. Null here because no tag exists yet.
            "tag": None,
        },
        "git": git_state(),
        "agent": {
            "tools": list(TOOL_NAMES),
            "setting_sources": [],
            "built_in_tools": [],
        },
        "session": {
            "id": result.session_id,
            "prompt": prompt,
            "events_path": str(result.events_path.relative_to(REPO_ROOT)),
            "events_written": result.events_written,
            "turns": result.turns,
            "tool_calls": result.tool_calls,
            "subtype": result.subtype,
            "is_error": result.is_error,
            # Turn figures are read back from the CLI transcript, because
            # the streamed message carries pre-completion values. A rise in
            # turns_unenriched means that lookup stopped working, which is
            # why it is recorded rather than left implicit.
            "turns_enriched": result.turns_enriched,
            "turns_unenriched": result.turns_unenriched,
        },
        "tokens": result.token_totals(),
        "usage_raw": result.usage,
        "model_usage_raw": result.model_usage,
        # An estimate, carried for interest. The token counts above are the
        # record the cost model reads.
        "total_cost_usd_estimate": result.total_cost_usd,
    }


async def main_async(args: argparse.Namespace) -> int:
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    result = await run_session(prompt=args.prompt, run_dir=run_dir)

    manifest = build_manifest(
        run_id=run_id,
        label=args.label,
        prompt=args.prompt,
        seed=args.seed,
        result=result,
    )
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"run           {run_id}")
    print(f"session       {result.session_id}")
    print(f"events        {result.events_written} -> {result.events_path.name}")
    print(f"turns         {result.turns}")
    print(f"tool calls    {result.tool_calls}")
    print(f"models seen   {', '.join(result.models_seen) or 'none'}")
    print(f"tokens        {manifest['tokens']}")
    print(f"cost estimate {result.total_cost_usd}")
    print(f"manifest      {manifest_path.relative_to(REPO_ROOT)}")
    if result.is_error:
        print(f"ERROR         subtype {result.subtype}")
        for line in result.stderr_lines[-10:]:
            print(f"  stderr: {line}")
    return 1 if result.is_error else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one lab session and write a manifest.")
    parser.add_argument("--prompt", required=True, help="The instruction to give the agent.")
    parser.add_argument("--label", default="unlabelled", help="What this run is for.")
    parser.add_argument("--run-id", default=None, help="Defaults to a UTC timestamp.")
    parser.add_argument("--seed", type=int, default=0, help="Recorded in the manifest.")
    return asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
