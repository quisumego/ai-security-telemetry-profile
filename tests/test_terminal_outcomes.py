"""A CLI cap has to reach the manifest, and nothing else may pose as one.

The SDK raises a bare Exception carrying the CLI's text when a session ends on
max_turns or the budget guard, rather than yielding a ResultMessage with a
subtype. max_turns is on legitimate_outcomes for every scenario in the attack
corpus, and ruling 13 makes the budget guard part of the A8 measurement, so
both have to be recorded rather than crash the runner. A8 trial 1 was lost that
way on 21 September 2026.

The property these tests protect is the second half: an error the table does
not recognise must be re-raised, never recorded as a legitimate outcome. A
silent mislabel would put a failed session into a scored corpus.
"""

from __future__ import annotations

import pytest

from lab.agent import _TERMINAL_CONDITIONS, _terminal_subtype


def test_the_observed_max_turns_wording_maps_to_its_subtype():
    # The exact text seen from the CLI on 21 September 2026.
    assert _terminal_subtype("Reached maximum number of turns (12)") == "error_max_turns"


def test_the_max_turns_match_is_not_sensitive_to_case_or_surrounding_text():
    assert (
        _terminal_subtype("Claude Code returned an error result: Reached Maximum Number Of Turns (12)")
        == "error_max_turns"
    )


def test_a_budget_cap_maps_to_its_subtype():
    assert _terminal_subtype("Session stopped: budget limit of $0.50 reached") == "error_max_budget_usd"


@pytest.mark.parametrize(
    "message",
    [
        "Connection reset by peer",
        "Invalid API key",
        "Overloaded",
        "",
        "Tool mcp__thornfield__fetch_url failed",
        "rate limit exceeded",
    ],
)
def test_an_unrecognised_error_is_not_a_terminal_condition(message):
    """The safety property. None means the caller re-raises and the run stops."""
    assert _terminal_subtype(message) is None


def test_a_usage_window_error_is_not_silently_recorded_as_a_cap():
    """A usage limit stops the capture; it is not an outcome to score.

    This is the failure most likely to arrive mid-capture on a subscription allowance, so it is
    named explicitly rather than left to the parametrised list.
    """
    assert _terminal_subtype("Claude usage limit reached. Your limit will reset at 9pm.") is None


def test_every_table_entry_is_lowercase_so_the_match_works():
    """_terminal_subtype lowercases the message, so a capitalised needle
    could never match and would fail open, returning None for a real cap."""
    for needle, _subtype in _TERMINAL_CONDITIONS:
        assert needle == needle.lower(), needle


def test_the_table_maps_only_to_subtypes_a_scenario_can_declare():
    """Every subtype the table can produce must be one a scenario file is
    allowed to list in legitimate_outcomes, or a cap would be recorded and
    then stop the run anyway."""
    declared = {"error_max_turns", "error_max_budget_usd"}
    assert {subtype for _needle, subtype in _TERMINAL_CONDITIONS} == declared


# The two branches end to end. query is replaced with a stub that raises the
# way the SDK does, so no model call is made and no allowance is spent.


def _raising_query(message: str):
    async def fake_query(*_args, **_kwargs):
        raise Exception(message)
        yield  # pragma: no cover, makes this an async generator

    return fake_query


def test_a_cap_is_recorded_rather_than_raised(tmp_path, monkeypatch):
    import asyncio

    from lab import agent

    monkeypatch.setattr(
        agent, "query", _raising_query("Claude Code returned an error result: Reached maximum number of turns (12)")
    )
    run_dir = tmp_path / "m2-stub-t01"
    run_dir.mkdir(parents=True)

    result = asyncio.run(agent.run_session(prompt="anything", run_dir=run_dir))

    assert result.subtype == "error_max_turns"
    assert result.is_error is True
    assert "maximum number of turns" in (result.error_text or "").lower()


def test_an_unrecognised_error_still_stops_the_run(tmp_path, monkeypatch):
    import asyncio

    from lab import agent

    monkeypatch.setattr(agent, "query", _raising_query("Overloaded"))
    run_dir = tmp_path / "m2-stub-t02"
    run_dir.mkdir(parents=True)

    with pytest.raises(Exception, match="Overloaded"):
        asyncio.run(agent.run_session(prompt="anything", run_dir=run_dir))


def test_the_session_is_closed_out_even_when_the_run_stops(tmp_path, monkeypatch):
    """The finally block still emits session_end and closes the emitter, so a
    stopped run leaves a readable event stream rather than a truncated one."""
    import asyncio
    import json

    from lab import agent

    monkeypatch.setattr(agent, "query", _raising_query("Overloaded"))
    run_dir = tmp_path / "m2-stub-t03"
    run_dir.mkdir(parents=True)

    with pytest.raises(Exception, match="Overloaded"):
        asyncio.run(agent.run_session(prompt="anything", run_dir=run_dir))

    written = sorted(run_dir.glob("session-*.jsonl"))
    assert written, "the run left no event stream"
    events = [json.loads(line) for line in written[0].read_text().splitlines() if line.strip()]
    assert events[0]["event_type"] == "session_start"
    assert events[-1]["event_type"] == "session_end"
