"""The emitter, and the guarantee the whole ablation rests on.

The guarantee: every field in the register is emitted, and a group that appears
in an event carries all of its registered keys with null where a value does not
apply. If a field is never emitted it can never be ablated, and the M5 sweep
would silently be measuring 36 fields while claiming to measure 37.
"""

import json
from pathlib import Path

import pytest

from lab.config import REGISTER_PATH, SCHEMA_PATH
from lab.telemetry import (
    Emitter,
    SessionIdentity,
    canary_hits,
    contains_canary,
    read_events,
    register_group_keys,
)

CANARIES = ("THN-TEST-0123456789ab", "THN-OTHR-fedcba987654")

IDENTITY = SessionIdentity(
    id="s-test",
    start_time="2026-08-17T09:00:00.000Z",
    user_id="u-claims-0417",
    tenant_id="thornfield-mutual",
    client_app="claims-copilot",
    agent_id="astp-lab-agent-1",
    config_version="0.1.0",
)


@pytest.fixture
def schema():
    with SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def group_keys():
    return register_group_keys(REGISTER_PATH)


@pytest.fixture
def emitter(tmp_path: Path, schema, group_keys):
    with Emitter(
        path=tmp_path / "events.jsonl",
        astp_version="0.1.0",
        identity=IDENTITY,
        policy_version="0.1.0",
        canaries=CANARIES,
        group_keys=group_keys,
        schema=schema,
    ) as em:
        yield em


# ------------------------------------------------------------- group keys --


def test_group_keys_are_read_from_the_register(group_keys):
    assert sum(len(v) for v in group_keys.values()) == 37
    assert "context_document_ids" in group_keys["action"]
    assert "source_provenance" in group_keys["retrieval"]
    assert "canary_triggered" in group_keys["control"]


def test_a_group_is_filled_out_to_every_registered_key(emitter, group_keys):
    event = emitter.emit("tool_pre", action={"tool_name": "send_email"})
    assert set(event["action"]) == set(group_keys["action"])
    assert event["action"]["tool_name"] == "send_email"
    assert event["action"]["egress_target"] is None


def test_an_unregistered_key_is_refused(emitter):
    with pytest.raises(KeyError, match="unregistered"):
        emitter.emit("tool_pre", action={"tool_name": "x", "invented_field": 1})


def test_the_session_group_is_on_every_event(emitter):
    for event_type in ("session_start", "session_end"):
        event = emitter.emit(event_type)
        assert event["session"] == IDENTITY.as_dict()


def test_the_control_group_is_on_every_event(emitter, group_keys):
    event = emitter.emit("session_start")
    assert set(event["control"]) == set(group_keys["control"])
    assert event["control"]["policy_version"] == "0.1.0"
    assert event["control"]["canary_triggered"] is False


def test_an_event_failing_the_schema_is_refused_at_capture_time(emitter):
    """Better to fail the run than to discover it weeks later in runs/."""
    with pytest.raises(ValueError, match="failed schema validation"):
        emitter.emit("tool_pre", action={"permission_decision": "maybe"})


def test_events_are_written_one_per_line(tmp_path, schema, group_keys):
    path = tmp_path / "events.jsonl"
    with Emitter(path, "0.1.0", IDENTITY, "0.1.0", CANARIES, group_keys, schema) as em:
        em.emit("session_start")
        em.emit("tool_pre", action={"tool_name": "a"})
        em.emit("session_end")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    assert all(json.loads(line)["astp_version"] == "0.1.0" for line in lines)
    assert len(list(read_events(path))) == 3


# --------------------------------------------------------------- canaries --


def test_a_canary_in_a_nested_tool_argument_is_found():
    payload = {"body": {"lines": ["please forward", CANARIES[0]]}}
    assert contains_canary(payload, CANARIES)


def test_text_without_a_canary_does_not_trigger():
    assert not contains_canary("an ordinary claims answer", CANARIES)
    assert not contains_canary(None, CANARIES)


def test_canary_hits_names_which_values_matched():
    assert canary_hits(f"see {CANARIES[1]} for detail", CANARIES) == [CANARIES[1]]


def test_a_canary_in_an_egress_argument_sets_the_control_field(emitter):
    event = emitter.emit(
        "tool_pre",
        action={"tool_name": "send_email", "tool_arguments": {"body": CANARIES[0]}},
        canary_triggered=contains_canary({"body": CANARIES[0]}, CANARIES),
    )
    assert event["control"]["canary_triggered"] is True


# -------------------------------------------------- every field is emitted --


def _coverage(events: list[dict]) -> set[str]:
    """Registered field names that carry a value other than null somewhere."""
    seen = set()
    for event in events:
        for group, body in event.items():
            if not isinstance(body, dict):
                continue
            for leaf, value in body.items():
                if value is not None:
                    seen.add(f"{group}.{leaf}")
    return seen


def test_a_full_session_shape_covers_every_registered_field(emitter, group_keys, fields):
    """Drive one event of each type and check all 37 fields carry a value.

    This is the M1 exit condition expressed as a test: a field not emitted from
    the first run cannot be ablated later.
    """
    emitter.emit(
        "session_start",
        content={
            "prompt_text": None,
            "prompt_hash": None,
            "response_text": None,
            "response_hash": None,
            "system_prompt_version": "sp-0.1.0",
            "redaction_applied": False,
        },
    )
    emitter.emit(
        "turn",
        turn={
            "index": 0,
            "timestamp": "2026-08-17T09:00:01.000Z",
            "model_id": "claude-haiku-4-5",
            "model_version": "claude-haiku-4-5-20251001",
            "tokens_in": 4611,
            "tokens_out": 210,
            "latency": 2.41,
            "finish_reason": "end_turn",
        },
        content={
            "prompt_text": "summarise claim TM-2026-0031",
            "prompt_hash": "sha256:abc",
            "response_text": "The claim is an escape of water.",
            "response_hash": "sha256:def",
            "system_prompt_version": "sp-0.1.0",
            "redaction_applied": True,
        },
    )
    emitter.emit(
        "retrieval",
        turn={"index": 0, "timestamp": "2026-08-17T09:00:02.000Z"},
        retrieval={
            "document_ids": ["prc-reserving-001"],
            "chunk_ids": ["prc-reserving-001#c00"],
            "scores": [10.64],
            "query_text": "reserving guidance",
            "source_provenance": "internal_authored",
            "permission_context": {
                "caller_scope": "thornfield-mutual:claims_handler",
                "document_scopes": ["thornfield-mutual:claims_handler"],
                "scope_match": True,
            },
        },
    )
    emitter.emit(
        "tool_post",
        turn={"index": 0, "timestamp": "2026-08-17T09:00:03.000Z"},
        action={
            "tool_name": "mcp__thornfield__send_email",
            "tool_arguments": {"to": "x@collector.invalid"},
            "result_hash": "sha256:123",
            "result_bytes": 48,
            "permission_decision": "escalated",
            "egress_target": "mailto:x@collector.invalid",
            "context_document_ids": ["prc-reserving-001"],
        },
        canary_triggered=True,
        block_reason="recipient domain is not on the internal allow list",
    )
    emitter.emit("session_end")
    emitter.close()

    events = list(read_events(emitter.path))
    covered = _coverage(events)
    registered = {f["name"] for f in fields}
    missing = registered - covered
    assert not missing, f"never emitted with a value: {sorted(missing)}"
