"""The M7b pass: the attack corpus against a local model through Ollama.

    .venv/bin/python -m crosscheck.runner --scenario a01 --trials 1
    .venv/bin/python -m crosscheck.runner --all
    .venv/bin/python -m crosscheck.runner --all --dry-run

**The agent is the lab agent, unchanged.** Same SDK, same bundled CLI, same
hooks, the same six tools, system prompt sp-0.2.0, and every guard:
`setting_sources=[]`, `tools=[]`, `fallback_model` null, `max_turns` 12,
`max_budget_usd` 0.50, thinking disabled. Two things differ, and both are
recorded: the model name, replaced in memory in a copy of the configuration so
`lab/config.yaml` is never edited, and the endpoint, reached through the SDK's
`env` option for this process's sessions only. Nothing is exported in the
shell and no settings file is written.

**No request carries the owner's login.** `ANTHROPIC_AUTH_TOKEN` holds Ollama's
documented placeholder and outranks the subscription login in Claude Code's
authentication order, so the login is never the active credential.
`ANTHROPIC_API_KEY` is never set, and the runner refuses to start if it is
present in its own environment.

**Every manifest is checked as it is written.** The `model_usage` keys,
`model.resolved`, and the model on every turn event must name the pinned local
model and nothing else. The first Claude key, or any other model, stops the
whole pass (ruling 13). The runtime's model digest is read before and after
every trial and must not move.

**Resumable, and never retried.** A trial is complete when its manifest shows
an outcome on its scenario's legitimate list and a clean contamination check.
A trial that ends on any other outcome, or raises, is recorded with its error
text, its scenario stops, and the pass moves to the next scenario. A run
directory with neither a manifest nor a failure record is a stale attempt, and
the runner stops rather than write over it or read it as a result.

Run directories are `runs/m7b-aNN-tNN`, beside the frozen captures, which are
never read for writing. Rulings are in `crosscheck/rulings.py`.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from attacks.oracles import load_scenario
from attacks.runner import SCENARIO_IDS, _extra_pages, _overlay_dirs, _overlay_digest
from crosscheck import rulings
from lab.agent import run_session
from lab.config import LabConfig, load_config
from lab.harness import RUNS_DIR, build_manifest
from lab.telemetry import read_events

FAILURE_RECORD = "failure.json"


class ContaminationError(RuntimeError):
    """A manifest named a model other than the pinned local one."""


class PassStopped(RuntimeError):
    """The pass cannot continue honestly, and stopped."""


# -------------------------------------------------------------- configuration --


def local_config(base: LabConfig | None = None) -> LabConfig:
    """The lab configuration with the model replaced, in memory only."""
    base = base or load_config()
    raw = copy.deepcopy(base.raw)
    raw["model"]["id"] = rulings.LOCAL_MODEL
    return LabConfig(raw=raw, path=base.path)


def pass_env() -> dict[str, str]:
    """The variables the CLI receives for this pass, and nothing else.

    Each is documented: the endpoint and placeholder credential by Ollama's
    Anthropic compatibility page, the rest by Claude Code's environment
    variable reference. None is a secret.
    """
    return {
        "ANTHROPIC_BASE_URL": rulings.ENDPOINT,
        "ANTHROPIC_AUTH_TOKEN": rulings.AUTH_TOKEN_PLACEHOLDER,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": rulings.LOCAL_MODEL,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "API_TIMEOUT_MS": str(rulings.API_TIMEOUT_MS),
    }


def refuse_api_key(environ: dict[str, str] | os._Environ = os.environ) -> None:
    """Ruling 5: the key is never set, so its presence means something is wrong."""
    if rulings.REFUSE_IF_API_KEY_PRESENT and "ANTHROPIC_API_KEY" in environ:
        raise PassStopped(
            "ANTHROPIC_API_KEY is present in this environment. It is never set "
            "for this project; unset it before running the pass."
        )


# ------------------------------------------------------------------- runtime --


def _get_json(endpoint: str, path: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{endpoint}{path}", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def ollama_state(endpoint: str = rulings.ENDPOINT) -> dict[str, Any]:
    """What the local runtime reports about itself and the pinned model.

    Read from the documented `/api/version`, `/api/tags` and `/api/ps`. The
    context length is the one in force for the loaded model, null when the
    model is not loaded at the moment of reading.
    """
    version = _get_json(endpoint, "/api/version").get("version")
    models = _get_json(endpoint, "/api/tags").get("models") or []
    entry = next((m for m in models if m.get("name") == rulings.LOCAL_MODEL), None)
    if entry is None:
        raise PassStopped(f"{rulings.LOCAL_MODEL} is not present on the local server")
    running = _get_json(endpoint, "/api/ps").get("models") or []
    loaded = next((m for m in running if m.get("name") == rulings.LOCAL_MODEL), None)
    digest = str(entry.get("digest") or "")
    return {
        "runtime": "ollama",
        "endpoint": endpoint,
        "ollama_version": version,
        "model": rulings.LOCAL_MODEL,
        "digest": digest,
        "library_digest_prefix": rulings.LIBRARY_DIGEST_PREFIX,
        "library_digest_prefix_matches": digest.startswith(rulings.LIBRARY_DIGEST_PREFIX),
        "size_bytes": entry.get("size"),
        "details": entry.get("details"),
        "context_length_configured": rulings.CONTEXT_LENGTH,
        "context_length_in_force": loaded.get("context_length") if loaded else None,
    }


def spawned_cli_version(transcript_path: str | None) -> str | None:
    """The CLI version the transcript records, which is the CLI that ran.

    `versions.claude_cli` in the manifest reads the CLI on PATH, which the SDK
    does not spawn while it carries a bundled one (ruling 22).
    """
    if not transcript_path:
        return None
    path = Path(transcript_path)
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("version"):
            return str(record["version"])
    return None


# ------------------------------------------------------------- the checks --


def contamination_problems(manifest: dict[str, Any], events: list[dict[str, Any]]) -> list[str]:
    """Every place a model other than the pinned local one appears.

    Empty means clean. A missing `model_usage` is a problem too, because the
    pin cannot then be shown.
    """
    pinned = rulings.LOCAL_MODEL
    problems: list[str] = []
    usage_keys = set((manifest.get("model_usage_raw") or {}).keys())
    if not usage_keys:
        problems.append("model_usage records no model, so the pin cannot be shown")
    for key in sorted(usage_keys | set(manifest["model"].get("resolved") or [])):
        if key != pinned:
            kind = "a Claude model" if key.lower().startswith("claude") else "another model"
            problems.append(f"{key} is {kind}, not {pinned}")
    for event in events:
        if event.get("event_type") != "turn":
            continue
        turn = event["turn"]
        for name in ("model_id", "model_version"):
            if turn.get(name) != pinned:
                problems.append(f"turn {turn.get('index')} {name} is {turn.get(name)!r}")
    return problems


def _legitimate(manifest: dict[str, Any], legitimate: set[str]) -> bool:
    session = manifest.get("session", {})
    if session.get("subtype") == "success" and session.get("is_error"):
        return False
    return session.get("subtype") in legitimate


def trial_state(run_dir: Path, legitimate: set[str]) -> str:
    """One of complete, failed, stale or absent."""
    if not run_dir.exists():
        return "absent"
    manifest_path = run_dir / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        clean = not (manifest.get("local") or {}).get("contamination_check", ["unchecked"])
        return "complete" if clean and _legitimate(manifest, legitimate) else "failed"
    if (run_dir / FAILURE_RECORD).is_file():
        return "failed"
    return "stale"


def run_dir_for(scenario_id: str, trial: int) -> Path:
    return RUNS_DIR / f"{rulings.RUN_PREFIX}-{scenario_id}-t{trial:02d}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# --------------------------------------------------------------- the pass --


async def run_scenario(scenario_id: str, trials: int, *, dry_run: bool = False) -> dict[str, Any]:
    """Run the incomplete trials of one scenario. Returns a small report.

    Raises ContaminationError or PassStopped when the whole pass must stop.
    """
    scenario = load_scenario(scenario_id)
    legitimate = set(scenario["legitimate_outcomes"])
    prompt = scenario["prompt"]
    overlay_dirs = _overlay_dirs(scenario)
    extra_pages = _extra_pages(scenario)
    config = local_config()
    env = pass_env()
    report: dict[str, Any] = {
        "scenario": scenario_id, "ran": 0, "skipped": 0, "outcomes": [], "stopped": False,
    }

    for trial in range(1, trials + 1):
        run_dir = run_dir_for(scenario_id, trial)
        state = trial_state(run_dir, legitimate)
        if state == "complete":
            report["skipped"] += 1
            continue
        if state == "failed":
            report.update(stopped=True, reason=f"trial {trial} is recorded as failed; not retried")
            return report
        if state == "stale":
            raise PassStopped(
                f"{run_dir.name} holds an attempt with no manifest and no failure "
                "record. Move it out of runs/ before resuming; it is not overwritten."
            )
        if dry_run:
            report["outcomes"].append((trial, "dry-run"))
            continue

        before = ollama_state()
        try:
            result = await run_session(
                prompt=prompt,
                run_dir=run_dir,
                config=config,
                overlay_dirs=overlay_dirs,
                extra_pages=extra_pages,
                env=env,
            )
        except Exception as exc:  # recorded, never retried (ruling 13)
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / FAILURE_RECORD).write_text(json.dumps({
                "run_id": run_dir.name,
                "scenario": scenario_id,
                "trial": trial,
                "date": _now(),
                "error_type": type(exc).__name__,
                "error": str(exc)[:4000],
            }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            report["ran"] += 1
            report["outcomes"].append((trial, f"raised {type(exc).__name__}"))
            report.update(stopped=True, reason=f"trial {trial} raised {type(exc).__name__}: {str(exc)[:300]}")
            return report

        after = ollama_state()
        manifest = build_manifest(
            run_id=run_dir.name,
            label=f"m7b {scenario_id} trial {trial}",
            prompt=prompt,
            seed=trial,
            result=result,
            scenario={
                "id": scenario_id,
                "trial": trial,
                "holdout": bool(scenario["holdout"]),
                "overlay_digest": _overlay_digest(scenario),
            },
            config=config,
        )
        events = list(read_events(Path(result.events_path)))
        problems = contamination_problems(manifest, events)
        if before["digest"] != after["digest"]:
            problems.append(f"model digest moved during the trial: {before['digest']} to {after['digest']}")
        manifest["local"] = {
            **after,
            "context_length_in_force": after["context_length_in_force"] or before["context_length_in_force"],
            "cli_spawned_version": spawned_cli_version(result.transcript_path),
            "env_names": sorted(env),
            "contamination_check": problems,
        }
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        report["ran"] += 1
        report["outcomes"].append((trial, result.subtype))

        if problems:
            raise ContaminationError(f"{run_dir.name}: " + "; ".join(problems))
        if not _legitimate(manifest, legitimate):
            report.update(stopped=True, reason=f"trial {trial} ended {result.subtype!r}, not on the legitimate list")
            return report

    return report


async def main_async(args: argparse.Namespace) -> int:
    refuse_api_key()
    ids = SCENARIO_IDS if args.all else [args.scenario]
    pinned_digest: str | None = None
    for scenario_id in ids:
        if not args.dry_run:
            digest = ollama_state()["digest"]
            if pinned_digest is not None and digest != pinned_digest:
                print(f"STOPPED: model digest moved between scenarios, {pinned_digest} to {digest}")
                return 2
            pinned_digest = digest
        try:
            report = await run_scenario(scenario_id, args.trials, dry_run=args.dry_run)
        except (ContaminationError, PassStopped) as exc:
            print(f"[{_now()}] {scenario_id}: PASS STOPPED: {exc}")
            return 2
        print(f"[{_now()}] {report['scenario']}: ran {report['ran']}, skipped {report['skipped']} already complete")
        for trial, subtype in report["outcomes"]:
            print(f"    trial {trial:>2}  {subtype}")
        if report["stopped"]:
            print(f"    SCENARIO STOPPED: {report['reason']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="The M7b local model pass.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scenario", help="A scenario id, for example a01.")
    group.add_argument("--all", action="store_true", help="Every scenario in order.")
    parser.add_argument("--trials", type=int, default=rulings.TRIALS_PER_SCENARIO)
    parser.add_argument("--dry-run", action="store_true", help="List what would run; no model call.")
    return asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
