"""The M1 exit condition, expressed as a test over the committed captures.

Two things have to hold of every session in `runs/`, and holding them by
inspection once is not the same as holding them on every future run:

1. Every emitted line validates against `schema/event.schema.json`.
2. Every field in the register is emitted, and carries a value somewhere.

The second is the one the whole ablation depends on. A field that was never
emitted from the first run cannot be nulled at M5, so the sweep would quietly
measure fewer fields than it claimed to.
"""

import json

import pytest
import yaml
from jsonschema import Draft202012Validator

from lab.config import REGISTER_PATH, REPO_ROOT, SCHEMA_PATH
from lab.telemetry import read_events

RUNS_DIR = REPO_ROOT / "runs"


def _session_files():
    return sorted(RUNS_DIR.glob("*/session-*.jsonl"))


@pytest.fixture(scope="module")
def captured_events():
    events = []
    for path in _session_files():
        events.extend(read_events(path))
    return events


@pytest.fixture(scope="module")
def registered_names():
    with REGISTER_PATH.open(encoding="utf-8") as fh:
        return {f["name"] for f in yaml.safe_load(fh)["fields"]}


@pytest.fixture(scope="module")
def validator():
    with SCHEMA_PATH.open(encoding="utf-8") as fh:
        return Draft202012Validator(json.load(fh))


def test_at_least_one_session_has_been_captured():
    assert _session_files(), "no capture exists in runs/"


def test_every_captured_line_validates_against_the_schema(validator):
    failures = []
    for path in _session_files():
        for line_no, event in enumerate(read_events(path), 1):
            for error in validator.iter_errors(event):
                failures.append(f"{path.name}:{line_no} {list(error.path)}: {error.message}")
    assert not failures, "\n".join(failures)


# The M7b local model pass, ruled by the owner on 23 September 2026 (ruling 14).
# Its captures sit in runs/ beside the frozen ones but ran on a local model by
# design, so the two tests below that pin the Claude model and the Claude
# transcript read-back leave them out by name. Every other manifest, including
# both frozen corpora, is still held to both. tests/test_crosscheck.py holds the
# M7b captures to their own pin.
LOCAL_PASS_PREFIX = "m7b-"


def _claude_manifests():
    return [p for p in sorted(RUNS_DIR.glob("*/manifest.json"))
            if not p.parent.name.startswith(LOCAL_PASS_PREFIX)]


def test_every_manifest_records_the_pinned_model_and_no_fallback():
    manifests = _claude_manifests()
    assert manifests, "no run manifest exists"
    for path in manifests:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        model = manifest["model"]
        assert model["requested"] == "claude-haiku-4-5", path
        assert model["fallback_model"] is None, f"{path} ran with a fallback configured"
        assert model["resolved"], f"{path} records no resolved model"
        for resolved in model["resolved"]:
            assert resolved.startswith("claude-haiku-4-5"), (
                f"{path} ran on {resolved}, which is not the pinned model"
            )


def test_every_manifest_records_token_counts_rather_than_only_a_cost_estimate():
    for path in sorted(RUNS_DIR.glob("*/manifest.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        tokens = manifest["tokens"]
        assert tokens["input_tokens"] > 0, path
        assert tokens["output_tokens"] > 0, path


def test_every_turn_figure_came_from_the_completed_record():
    """turns_unenriched rising means the transcript lookup stopped working and
    the capture is carrying nulls where token counts should be."""
    for path in _claude_manifests():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        assert manifest["session"]["turns_unenriched"] == 0, (
            f"{path} has turns whose token counts could not be read back"
        )


def test_every_registered_field_is_present_as_a_key(captured_events, registered_names):
    present = set()
    for event in captured_events:
        for group, body in event.items():
            if isinstance(body, dict):
                present.update(f"{group}.{leaf}" for leaf in body)
    missing = registered_names - present
    assert not missing, f"never emitted as a key: {sorted(missing)}"


def test_every_registered_field_carries_a_value_somewhere(captured_events, registered_names):
    """The M1 exit condition. A field emitted only ever as null has not been
    shown to work, and cannot be ablated meaningfully at M5."""
    valued = set()
    for event in captured_events:
        for group, body in event.items():
            if isinstance(body, dict):
                for leaf, value in body.items():
                    if value is not None:
                        valued.add(f"{group}.{leaf}")
    missing = registered_names - valued
    assert not missing, f"never carried a value in any capture: {sorted(missing)}"


def test_provenance_is_labelled_on_every_retrieval_event(captured_events):
    retrievals = [e for e in captured_events if e["event_type"] == "retrieval"]
    assert retrievals, "no retrieval event was captured"
    for event in retrievals:
        assert event["retrieval"]["source_provenance"], event


def test_a_permission_decision_is_recorded_on_every_tool_call(captured_events):
    """Including the permitted ones. Logging only denials hides the case that
    matters, which is the harmful action that was allowed."""
    calls = [e for e in captured_events if e["event_type"] in {"tool_pre", "tool_post"}]
    assert calls, "no tool call was captured"
    for event in calls:
        assert event["action"]["permission_decision"], event
    assert any(e["action"]["permission_decision"] == "allowed" for e in calls)


def test_context_document_ids_accumulate_within_a_session():
    """The field the profile leans on hardest. If it never grows, the link
    between retrieved content and the action it produced is not being made."""
    grew = False
    for path in _session_files():
        sizes = [
            len(e["action"]["context_document_ids"])
            for e in read_events(path)
            if e["event_type"] in {"tool_pre", "tool_post"}
        ]
        if sizes and max(sizes) > 0 and sizes[-1] >= sizes[0]:
            grew = True
    assert grew, "context_document_ids never accumulated in any capture"


def test_the_corpus_digest_covers_the_attack_overlays():
    from lab.harness import CORPUS_INPUTS, OVERLAYS_DIR

    assert OVERLAYS_DIR in CORPUS_INPUTS


def test_the_manifest_carries_a_scenario_block_and_the_freeze_tag():
    """Ad hoc runs record scenario as null; scored trials fill it."""
    from lab.agent import SessionResult
    from lab.harness import build_manifest

    result = SessionResult(
        session_id="s-test",
        events_path=REPO_ROOT / "runs" / "x" / "session-s-test.jsonl",
        events_written=0,
        tool_calls=0,
        turns=0,
    )
    plain = build_manifest(run_id="x", label="t", prompt="p", seed=0, result=result)
    assert plain["scenario"] is None
    assert "tag" in plain["corpus"]

    block = {"id": "a01", "trial": 1, "holdout": False, "overlay_digest": None}
    scored = build_manifest(
        run_id="x", label="t", prompt="p", seed=0, result=result, scenario=block
    )
    assert scored["scenario"] == block
