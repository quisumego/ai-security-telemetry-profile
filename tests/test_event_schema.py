"""The event schema must stay in step with the field register.

A field that exists in the register but not the schema cannot be emitted, and a
field emitted but not registered has escaped the ablation. Both directions are
checked here so neither can drift.
"""

import jsonschema
import pytest
from jsonschema import Draft202012Validator

from conftest import GROUPS


def _leaf(schema: dict, dotted: str):
    group, _, leaf = dotted.partition(".")
    return schema["properties"][group]["properties"][leaf]


def test_schema_is_itself_a_valid_json_schema(event_schema):
    Draft202012Validator.check_schema(event_schema)


def test_schema_declares_the_six_groups(event_schema):
    declared = set(event_schema["properties"]) - {"astp_version", "event_type"}
    assert declared == set(GROUPS)


def test_every_registered_field_exists_in_the_schema(event_schema, fields):
    for field in fields:
        try:
            _leaf(event_schema, field["name"])
        except KeyError:
            pytest.fail(f"{field['name']} is in the register but not the schema")


def test_every_schema_property_exists_in_the_register(event_schema, fields):
    registered = {f["name"] for f in fields}
    for group in GROUPS:
        for leaf in event_schema["properties"][group]["properties"]:
            dotted = f"{group}.{leaf}"
            assert dotted in registered, f"{dotted} is in the schema but not the register"


def test_groups_reject_unknown_properties(event_schema):
    """An unregistered field must not slip through as extra JSON."""
    assert event_schema["additionalProperties"] is False
    for group in GROUPS:
        assert event_schema["properties"][group]["additionalProperties"] is False, group


def test_context_document_ids_is_an_array_of_strings(event_schema):
    prop = _leaf(event_schema, "action.context_document_ids")
    assert "array" in prop["type"]
    assert prop["items"] == {"type": "string"}


def test_permission_decision_enumerates_allowed_outcomes(event_schema):
    prop = _leaf(event_schema, "action.permission_decision")
    assert "allowed" in prop["enum"], "permitted calls must be recordable, not only denials"
    assert "denied" in prop["enum"]


# --------------------------------------------------------------- validation --

MINIMAL = {
    "astp_version": "0.1.0",
    "event_type": "session_start",
    "session": {"id": "s-001"},
}


def test_a_minimal_event_validates(event_schema):
    jsonschema.validate(MINIMAL, event_schema)


def test_a_full_tool_event_validates(event_schema):
    event = {
        "astp_version": "0.1.0",
        "event_type": "tool_pre",
        "session": {
            "id": "s-001",
            "start_time": "2026-08-12T10:00:00Z",
            "user_id": "u-77",
            "tenant_id": "thornfield-claims",
            "client_app": "internal-assistant",
            "agent_id": "agent-1",
            "config_version": "0.1.0",
        },
        "turn": {"index": 3, "timestamp": "2026-08-12T10:00:12Z", "tokens_in": 900},
        "action": {
            "tool_name": "send_email",
            "tool_arguments": {"to": "audit@example.invalid"},
            "permission_decision": "allowed",
            "egress_target": "example.invalid",
            "context_document_ids": ["doc-14", "doc-91"],
        },
        "control": {"canary_triggered": True, "block_reason": None},
    }
    jsonschema.validate(event, event_schema)


def test_an_event_without_a_session_is_rejected(event_schema):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"astp_version": "0.1.0", "event_type": "turn"}, event_schema)


def test_an_unknown_field_is_rejected(event_schema):
    bad = dict(MINIMAL, session={"id": "s-001", "not_a_registered_field": "x"})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, event_schema)


def test_an_unknown_event_type_is_rejected(event_schema):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dict(MINIMAL, event_type="something_else"), event_schema)


@pytest.mark.parametrize(
    "event_type,required_group",
    [("turn", "turn"), ("retrieval", "retrieval"), ("tool_pre", "action"), ("tool_post", "action")],
)
def test_event_types_require_their_group(event_schema, event_type, required_group):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dict(MINIMAL, event_type=event_type), event_schema)


def test_a_bad_permission_decision_is_rejected(event_schema):
    bad = dict(MINIMAL, event_type="tool_pre", action={"permission_decision": "maybe"})
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, event_schema)
