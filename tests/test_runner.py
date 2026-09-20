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
