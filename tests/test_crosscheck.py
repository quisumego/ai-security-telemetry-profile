"""The M7b local model pass: its configuration, its checks, and its captures.

The runner is exercised against a stub, so no model is called and no server is
needed. The last group holds every committed `runs/m7b-*` capture to the local
pin, the frozen corpus and the M2 configuration; before the pass has written
anything those tests have nothing to read and hold trivially.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from crosscheck import rulings, runner
from lab.agent import SessionResult, build_options, build_session
from lab.config import CONFIG_PATH, REPO_ROOT, load_config
from lab.tools import SERVER_NAME

LOCAL = rulings.LOCAL_MODEL


# ------------------------------------------------------------ configuration --


def test_the_local_config_replaces_the_model_and_nothing_else():
    before = CONFIG_PATH.read_bytes()
    base = load_config()
    local = runner.local_config(base)
    assert local.model_id == LOCAL
    assert base.model_id == "claude-haiku-4-5"
    changed = {k for k in base.raw if base.raw[k] != local.raw[k]}
    assert changed == {"model"}
    assert {k for k in base.raw["model"] if base.raw["model"][k] != local.raw["model"][k]} == {"id"}
    assert local.fallback_model is None and local.thinking == "disabled"
    assert CONFIG_PATH.read_bytes() == before, "lab/config.yaml must never be edited"


def test_the_pass_environment_is_the_ruled_set_and_never_the_api_key():
    env = runner.pass_env()
    assert set(env) == {
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
        "API_TIMEOUT_MS",
    }
    assert "ANTHROPIC_API_KEY" not in env
    assert env["ANTHROPIC_BASE_URL"] == "http://localhost:11434"
    assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == LOCAL


@pytest.mark.parametrize("value", ["", "anything"])
def test_the_runner_refuses_to_start_with_an_api_key_present(value):
    with pytest.raises(runner.PassStopped, match="ANTHROPIC_API_KEY"):
        runner.refuse_api_key({"ANTHROPIC_API_KEY": value})
    runner.refuse_api_key({"PATH": "/usr/bin"})


def _options(tmp_path, env):
    config = load_config()
    session = build_session(config, tmp_path / "run", "s-test")
    try:
        server = {"type": "sdk", "name": SERVER_NAME, "instance": None}
        return build_options(config, session, server, [], env=env)
    finally:
        session.emitter.close()


def test_without_env_the_options_are_as_every_capture_had_them(tmp_path):
    options = _options(tmp_path, None)
    assert options.env == {}
    assert options.setting_sources == [] and options.tools == []
    assert options.model == "claude-haiku-4-5" and options.fallback_model is None


def test_env_reaches_the_options_and_the_guards_stay(tmp_path):
    options = _options(tmp_path, runner.pass_env())
    assert options.env == runner.pass_env()
    assert options.setting_sources == [] and options.tools == []
    assert options.fallback_model is None


def test_the_manifest_names_the_model_that_was_requested():
    from lab.harness import build_manifest

    result = SessionResult(
        session_id="s-test",
        events_path=REPO_ROOT / "runs" / "x" / "session-s-test.jsonl",
        events_written=0,
        tool_calls=0,
        turns=0,
    )
    plain = build_manifest(run_id="x", label="t", prompt="p", seed=0, result=result)
    local = build_manifest(
        run_id="x", label="t", prompt="p", seed=0, result=result, config=runner.local_config()
    )
    assert plain["model"]["requested"] == "claude-haiku-4-5"
    assert local["model"]["requested"] == LOCAL
    assert local["versions"]["config_version"] == plain["versions"]["config_version"]


# ------------------------------------------------------------------ checks --


def _turn(model: str | None = LOCAL, index: int = 1) -> dict:
    return {"event_type": "turn", "turn": {"index": index, "model_id": model, "model_version": model}}


def _manifest(keys=(LOCAL,), resolved=None) -> dict:
    return {
        "model": {"resolved": list(resolved if resolved is not None else keys)},
        "model_usage_raw": {k: {"inputTokens": 1} for k in keys},
    }


def test_a_clean_manifest_has_no_contamination():
    assert runner.contamination_problems(_manifest(), [_turn(), _turn(index=2)]) == []


def test_a_claude_key_is_named_as_contamination():
    problems = runner.contamination_problems(_manifest((LOCAL, "claude-haiku-4-5-20251001")), [_turn()])
    assert any("Claude model" in p for p in problems)


def test_any_other_model_is_contamination_too():
    assert runner.contamination_problems(_manifest(("qwen3:4b",)), [_turn()])


def test_a_turn_on_another_model_is_caught():
    assert runner.contamination_problems(_manifest(), [_turn("claude-haiku-4-5")])


def test_no_model_usage_means_the_pin_cannot_be_shown():
    assert runner.contamination_problems(_manifest(()), [_turn()])


def test_the_spawned_cli_version_is_read_from_the_transcript(tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text('not json\n{"type": "user"}\n{"version": "2.1.233"}\n', encoding="utf-8")
    assert runner.spawned_cli_version(str(transcript)) == "2.1.233"
    assert runner.spawned_cli_version(None) is None
    assert runner.spawned_cli_version(str(tmp_path / "missing.jsonl")) is None


# ------------------------------------------------------------ the runner, stubbed --


STATE = {
    "runtime": "ollama", "endpoint": rulings.ENDPOINT, "ollama_version": "0.0.0",
    "model": LOCAL, "digest": "a" * 64, "library_digest_prefix": rulings.LIBRARY_DIGEST_PREFIX,
    "library_digest_prefix_matches": False, "size_bytes": 1, "details": {},
    "context_length_configured": rulings.CONTEXT_LENGTH, "context_length_in_force": rulings.CONTEXT_LENGTH,
}


@pytest.fixture
def stub(monkeypatch, tmp_path):
    """Run output in a temp dir, the model call and the server stubbed.

    `plan[trial]` sets what a trial does: a subtype, "raise", or "claude" for a
    session whose usage names a Claude model.
    """
    plan: dict[int, str] = {}
    digests: list[str] = []
    monkeypatch.setattr(runner, "run_dir_for", lambda sid, t: tmp_path / f"m7b-{sid}-t{t:02d}")
    monkeypatch.setattr(runner, "_overlay_dirs", lambda scenario: ())
    monkeypatch.setattr(runner, "_extra_pages", lambda scenario: None)
    monkeypatch.setattr(runner, "ollama_state", lambda: {**STATE, "digest": digests.pop(0) if digests else STATE["digest"]})

    async def fake_run_session(*, prompt, run_dir, config, overlay_dirs=(), extra_pages=None, env=None):
        assert env == runner.pass_env() and config.model_id == LOCAL
        run_dir.mkdir(parents=True, exist_ok=True)
        trial = int(run_dir.name.split("-t")[1])
        action = plan.get(trial, "success")
        if action == "raise":
            raise RuntimeError("connection refused")
        events = run_dir / "session-s-stub.jsonl"
        events.write_text(json.dumps(_turn()) + "\n", encoding="utf-8")
        model = "claude-haiku-4-5" if action == "claude" else LOCAL
        return SessionResult(
            session_id="s-stub", events_path=events, events_written=1, tool_calls=0, turns=1,
            subtype="success" if action == "claude" else action, model_usage={model: {"inputTokens": 1}},
        )

    def fake_build_manifest(**kw):
        result = kw["result"]
        return {
            "model": {"requested": kw["config"].model_id, "resolved": result.models_seen},
            "session": {"subtype": result.subtype, "is_error": False},
            "scenario": kw["scenario"],
            "model_usage_raw": result.model_usage,
        }

    monkeypatch.setattr(runner, "run_session", fake_run_session)
    monkeypatch.setattr(runner, "build_manifest", fake_build_manifest)
    plan["digests"] = digests  # type: ignore[assignment]
    return plan


def _run(scenario="a01", trials=3):
    return asyncio.run(runner.run_scenario(scenario, trials))


def _manifest_at(tmp_path, trial, scenario="a01"):
    return json.loads((tmp_path / f"m7b-{scenario}-t{trial:02d}" / "manifest.json").read_text())


def test_a_clean_scenario_captures_every_trial_with_the_local_block(stub, tmp_path):
    report = _run()
    assert report["ran"] == 3 and not report["stopped"]
    manifest = _manifest_at(tmp_path, 1)
    assert manifest["model"]["requested"] == LOCAL
    assert manifest["local"]["contamination_check"] == []
    assert manifest["local"]["digest"] == "a" * 64
    assert manifest["local"]["env_names"] == sorted(runner.pass_env())


def test_completed_trials_are_skipped_on_resume(stub, tmp_path):
    _run(trials=2)
    report = _run(trials=3)
    assert report["skipped"] == 2 and report["ran"] == 1


def test_an_illegitimate_outcome_is_recorded_and_stops_the_scenario(stub, tmp_path):
    stub[2] = "error_max_budget_usd"  # legitimate for A8 only
    report = _run()
    assert report["stopped"] and report["ran"] == 2
    assert _manifest_at(tmp_path, 2)["session"]["subtype"] == "error_max_budget_usd"
    assert not (tmp_path / "m7b-a01-t03").exists()
    again = _run()
    assert again["stopped"] and again["ran"] == 0, "a failed trial is never retried"


def test_a_raised_error_is_recorded_and_stops_the_scenario(stub, tmp_path):
    stub[1] = "raise"
    report = _run()
    assert report["stopped"] and "RuntimeError" in report["reason"]
    record = json.loads((tmp_path / "m7b-a01-t01" / runner.FAILURE_RECORD).read_text())
    assert record["error"] == "connection refused"
    assert not (tmp_path / "m7b-a01-t01" / "manifest.json").exists()


def test_a_claude_key_stops_the_whole_pass_and_is_recorded(stub, tmp_path):
    stub[2] = "claude"
    with pytest.raises(runner.ContaminationError, match="Claude model"):
        _run()
    assert _manifest_at(tmp_path, 2)["local"]["contamination_check"]
    assert runner.trial_state(tmp_path / "m7b-a01-t02", {"success"}) == "failed"


def test_a_digest_that_moves_during_a_trial_stops_the_pass(stub, tmp_path):
    stub["digests"].extend(["a" * 64, "b" * 64])  # type: ignore[union-attr]
    with pytest.raises(runner.ContaminationError, match="digest moved"):
        _run(trials=1)


def test_a_stale_attempt_stops_the_pass_rather_than_being_overwritten(stub, tmp_path):
    (tmp_path / "m7b-a01-t01").mkdir()
    with pytest.raises(runner.PassStopped, match="stale|no manifest"):
        _run()


def test_a_dry_run_calls_nothing(stub, tmp_path):
    report = asyncio.run(runner.run_scenario("a01", 2, dry_run=True))
    assert report["outcomes"] == [(1, "dry-run"), (2, "dry-run")]
    assert not any(tmp_path.iterdir())


# ---------------------------------------------------------- the committed captures --


RUNS = REPO_ROOT / "runs"


def _local_manifests() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(RUNS.glob(f"{rulings.RUN_PREFIX}-a[0-9][0-9]-t[0-9][0-9]/manifest.json"))]


def _m2_digest() -> str:
    digests = {json.loads(p.read_text(encoding="utf-8"))["corpus"]["digest"]
               for p in RUNS.glob("m2-a[0-9][0-9]-t[0-9][0-9]/manifest.json")}
    assert len(digests) == 1
    return digests.pop()


def test_the_exclusion_in_test_captures_leaves_both_frozen_corpora_in():
    from test_captures import _claude_manifests

    names = {p.parent.name for p in _claude_manifests()}
    assert sum(n.startswith("m2-a") for n in names) == 100
    assert sum(n.startswith("m3-b") for n in names) == 100
    assert not any(n.startswith("m7b-") for n in names)


def test_every_local_capture_ran_on_the_pinned_local_model_only():
    for m in _local_manifests():
        assert m["model"]["requested"] == LOCAL, m["run_id"]
        assert m["model"]["fallback_model"] is None, m["run_id"]
        assert m["local"]["model"] == LOCAL and len(m["local"]["digest"]) == 64, m["run_id"]
        if not m["local"]["contamination_check"]:
            assert m["model"]["resolved"] == [LOCAL], m["run_id"]
            assert set(m["model_usage_raw"]) == {LOCAL}, m["run_id"]


def test_one_model_digest_across_the_whole_pass():
    assert len({m["local"]["digest"] for m in _local_manifests()}) <= 1


def test_every_local_capture_read_the_frozen_m2_corpus_under_the_m2_configuration():
    manifests = _local_manifests()
    if not manifests:
        return
    digest = _m2_digest()
    for m in manifests:
        assert m["corpus"]["digest"] == digest, m["run_id"]
        assert m["versions"]["config_version"] == "0.2.0", m["run_id"]
        assert m["versions"]["system_prompt_version"] == "sp-0.2.0", m["run_id"]
        assert m["model"]["thinking"] == "disabled", m["run_id"]


def test_turns_unenriched_counts_the_turns_with_null_token_figures():
    for m in _local_manifests():
        events_path = REPO_ROOT / m["session"]["events_path"]
        nulls = sum(
            1 for line in events_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and (e := json.loads(line))["event_type"] == "turn"
            and e["turn"]["tokens_out"] is None
        )
        assert m["session"]["turns_unenriched"] == nulls, m["run_id"]
