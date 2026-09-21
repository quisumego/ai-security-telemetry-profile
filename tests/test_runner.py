"""The runner is exercised end to end against a stub, so no allowance is spent.

The stub stands in for run_session and writes nothing to the model. It lets the
resume behaviour and the stop-on-illegitimate-outcome behaviour be tested
deterministically.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from attacks import runner
from attacks.oracles import load_scenario
from lab import harness
from lab.agent import SessionResult


def _fake_result(subtype: str, run_dir: Path) -> SessionResult:
    return SessionResult(
        session_id="s-stub",
        events_path=run_dir / "session-s-stub.jsonl",
        events_written=0,
        tool_calls=0,
        turns=0,
        subtype=subtype,
    )


@pytest.fixture
def stub(monkeypatch, tmp_path):
    """Point the runner's run output at a temp dir and stub the model call."""
    monkeypatch.setattr(runner, "RUNS_DIR", tmp_path)
    monkeypatch.setattr(runner, "run_dir_for", lambda sid, t: tmp_path / f"m2-{sid}-t{t:02d}")

    subtypes: dict[int, str] = {}

    async def fake_run_session(*, prompt, run_dir, config, overlay_dirs=(), extra_pages=None, **kw):
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "session-s-stub.jsonl").write_text("", encoding="utf-8")
        trial = int(run_dir.name.split("-t")[1])
        return _fake_result(subtypes.get(trial, "success"), run_dir)

    # The runner's overlay lookup reads scenario paths off disk; these tests
    # exercise control flow, not overlay loading, so it is neutralised here.
    monkeypatch.setattr(runner, "_overlay_dirs", lambda scenario: ())
    monkeypatch.setattr(runner, "_extra_pages", lambda scenario: None)
    monkeypatch.setattr(runner, "run_session", fake_run_session)
    monkeypatch.setattr(runner, "build_manifest", lambda **kw: {
        "session": {"subtype": kw["result"].subtype, "is_error": False},
        "scenario": kw["scenario"],
    })
    return subtypes


def test_a_clean_run_captures_every_trial(stub, tmp_path):
    report = asyncio.run(runner.run_scenario("a01", 3))
    assert report["ran"] == 3
    assert report["skipped"] == 0
    assert not report["stopped"]
    for t in (1, 2, 3):
        assert (tmp_path / f"m2-a01-t{t:02d}" / "manifest.json").is_file()


def test_completed_trials_are_skipped_on_a_second_pass(stub, tmp_path):
    asyncio.run(runner.run_scenario("a01", 3))
    report = asyncio.run(runner.run_scenario("a01", 3))
    assert report["ran"] == 0
    assert report["skipped"] == 3


def test_an_illegitimate_subtype_stops_the_run(stub, tmp_path):
    stub[2] = "error_during_execution"
    report = asyncio.run(runner.run_scenario("a01", 3))
    assert report["stopped"]
    assert report["ran"] == 2
    assert not (tmp_path / "m2-a01-t03" / "manifest.json").is_file()


def test_the_budget_subtype_is_legitimate_for_a08_only(stub, tmp_path):
    stub[1] = "error_max_budget_usd"
    a08 = asyncio.run(runner.run_scenario("a08", 1))
    assert not a08["stopped"]

    a01 = asyncio.run(runner.run_scenario("a01", 1))
    assert a01["stopped"]


def test_a_success_with_is_error_is_not_complete(stub, tmp_path, monkeypatch):
    run_dir = tmp_path / "m2-a01-t01"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps({"session": {"subtype": "success", "is_error": True}}), encoding="utf-8"
    )
    assert runner.trial_is_complete(run_dir, {"success"}) is False


# The overlay digest. It was a stub returning None until the A2 capture of
# 21 September 2026 showed every manifest carrying a null where the overlay
# identity should be. These tests exist so it cannot silently become a stub
# again.


def test_overlay_digest_is_recorded_for_every_scenario_that_serves_one():
    for scenario_id in ("a02", "a05", "a06", "a08", "a10"):
        scenario = load_scenario(scenario_id)
        digest = runner._overlay_digest(scenario)
        assert digest is not None, f"{scenario_id} serves an overlay and must record its digest"
        assert len(digest) == 64


def test_overlay_digest_is_null_only_when_a_scenario_serves_no_overlay():
    for scenario_id in ("a01", "a03", "a04", "a07", "a09"):
        scenario = load_scenario(scenario_id)
        assert runner._overlay_digest(scenario) is None


def test_each_overlay_scenario_has_a_digest_of_its_own():
    digests = {
        scenario_id: runner._overlay_digest(load_scenario(scenario_id))
        for scenario_id in ("a02", "a05", "a06", "a08", "a10")
    }
    assert len(set(digests.values())) == len(digests), digests


def test_the_overlay_digest_follows_the_overlay_bytes(tmp_path, monkeypatch):
    overlay = tmp_path / "corpus"
    overlay.mkdir()
    document = overlay / "doc.md"
    document.write_text("one", encoding="utf-8")
    # corpus_digest resolves paths against lab.harness.REPO_ROOT, so both have
    # to move for a temporary overlay to be digestible at all.
    monkeypatch.setattr(runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(harness, "REPO_ROOT", tmp_path)

    scenario = {"overlay": {"corpus": "corpus", "web_fixtures": None}}
    before = runner._overlay_digest(scenario)
    document.write_text("two", encoding="utf-8")
    after = runner._overlay_digest(scenario)

    assert before != after


def test_the_manifest_carries_the_overlay_digest(stub, tmp_path):
    asyncio.run(runner.run_scenario("a02", 1))
    manifest = json.loads((tmp_path / "m2-a02-t01" / "manifest.json").read_text())
    assert manifest["scenario"]["overlay_digest"] == runner._overlay_digest(load_scenario("a02"))
