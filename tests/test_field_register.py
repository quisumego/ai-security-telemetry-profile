"""The field register is the M0 deliverable, so it is tested like code.

These tests guard the properties the methodology depends on. In particular they
guard the pre-commitment. Until M5 that meant no tier could be set at all. From
M5 it means every tier is exactly what the tiering rule computes from the
recorded sweep, and the pre-registered prediction is unchanged since it was
registered. The guard got stronger, not removed.
"""

import hashlib
import json

from conftest import GROUPS, TIERS

from ablation import rulings
from ablation.matrix import tier_for

# SHA-256 over the sorted "name:predicted_tier" lines of the register as it was
# added at b533d6a, on 12 August 2026, before any capture existed.
PREDICTED_AT_REGISTRATION = "a585f6354b8e681191838f93c9faf8d13a575357ec9383674903a97b6678ccb1"

REQUIRED_KEYS = {
    "name",
    "group",
    "type",
    "otel",
    "security_only",
    "rationale",
    "bears_on",
    "predicted_tier",
    "tier",
}

ATTACK_CLASSES = {f"A{i}" for i in range(1, 11)}

# The seven fields the profile adds for detection with no equivalent in the
# OpenTelemetry GenAI conventions. These are the hypothesis under test, so the
# set is pinned here and a change to it has to be deliberate.
EXPECTED_SECURITY_ONLY = {
    "retrieval.source_provenance",
    "retrieval.permission_context",
    "action.permission_decision",
    "action.egress_target",
    "action.context_document_ids",
    "control.canary_triggered",
    "control.block_reason",
}


def test_register_declares_its_own_size(register, fields):
    assert register["field_count"] == len(fields)


def test_field_count_is_thirty_seven(fields):
    assert len(fields) == 37


def test_every_field_has_the_required_keys(fields):
    for field in fields:
        missing = REQUIRED_KEYS - set(field)
        assert not missing, f"{field.get('name')} is missing {sorted(missing)}"


def test_field_names_are_unique(fields):
    names = [f["name"] for f in fields]
    assert len(names) == len(set(names))


def test_field_name_prefix_matches_its_group(fields):
    for field in fields:
        prefix, _, leaf = field["name"].partition(".")
        assert prefix == field["group"], f"{field['name']} is in group {field['group']}"
        assert leaf, f"{field['name']} has no leaf name"


def test_all_six_groups_are_populated(fields):
    populated = {f["group"] for f in fields}
    assert populated == set(GROUPS)


def test_otel_mapping_value_is_valid(fields):
    for field in fields:
        assert field["otel"] in ("full", "partial", "none"), field["name"]


def test_a_full_or_partial_mapping_names_an_attribute_or_explains_itself(fields):
    for field in fields:
        if field["otel"] == "full":
            assert field.get("otel_attribute"), (
                f"{field['name']} claims a full mapping but names no attribute"
            )
        if field["otel"] == "none":
            assert not field.get("otel_attribute"), (
                f"{field['name']} claims no mapping but names an attribute"
            )


def test_security_only_set_is_exactly_the_hypothesis(fields):
    flagged = {f["name"] for f in fields if f["security_only"]}
    assert flagged == EXPECTED_SECURITY_ONLY


def test_security_only_fields_have_no_otel_equivalent(fields):
    for field in fields:
        if field["security_only"]:
            assert field["otel"] == "none", (
                f"{field['name']} is flagged security-only but maps to OpenTelemetry"
            )


def test_context_document_ids_is_present(fields):
    """Named in the plan as the single most important field in the schema."""
    names = {f["name"] for f in fields}
    assert "action.context_document_ids" in names


def test_every_field_states_a_rationale(fields):
    for field in fields:
        assert field["rationale"].strip(), f"{field['name']} has an empty rationale"


def test_bears_on_lists_only_real_attack_classes(fields):
    for field in fields:
        unknown = set(field["bears_on"]) - ATTACK_CLASSES
        assert not unknown, f"{field['name']} references {sorted(unknown)}"


def test_predicted_tier_is_a_valid_tier(fields):
    for field in fields:
        assert field["predicted_tier"] in TIERS, field["name"]


def test_every_tier_is_what_the_rule_computes_from_the_recorded_sweep(repo_root, fields):
    """Replaces the M0 guard that no tier was set before the ablation.

    Each tier is recomputed here from the cells in results/necessity.json and
    the ruled justification list, by the same rule, and must match what the
    register carries. A tier set by hand, or edited after the sweep, fails.
    """
    necessity = json.loads((repo_root / "results" / "necessity.json").read_text(encoding="utf-8"))
    for field in fields:
        name = field["name"]
        cells = [c["cell"] for c in necessity["single"][name]["cells"].values()]
        computed = tier_for(cells, name in rulings.STATED_JUSTIFICATION)
        assert field["tier"] == computed, f"{name} carries {field['tier']!r}, the rule gives {computed!r}"
        assert field["tier"] == necessity["tiers"][name]["tier"], name


def test_every_tier_names_the_cells_that_decided_it(repo_root, fields):
    necessity = json.loads((repo_root / "results" / "necessity.json").read_text(encoding="utf-8"))
    for field in fields:
        assert field["tier_cells"] == necessity["tiers"][field["name"]]["cells"], field["name"]
        if field["tier"] in ("required", "recommended"):
            assert field["tier_cells"], f"{field['name']} is {field['tier']} with no deciding cell"


def test_the_tiers_record_the_sweep_they_came_from(register, repo_root):
    necessity = json.loads((repo_root / "results" / "necessity.json").read_text(encoding="utf-8"))
    assert register["tiered_at"] == "M5"
    assert register["tier_sweep"]["artefact"] == "results/necessity.json"
    assert register["tier_sweep"]["commit"] == necessity["commit"]
    assert necessity["tree_clean"] is True


def test_every_tier_is_a_valid_tier(fields):
    for field in fields:
        assert field["tier"] in TIERS, field["name"]


def test_predicted_tiers_are_unchanged_since_registration(fields):
    """The pre-registered expectation is kept beside the result, never moved to
    fit it."""
    body = "\n".join(sorted(f"{f['name']}:{f['predicted_tier']}" for f in fields))
    assert hashlib.sha256(body.encode("utf-8")).hexdigest() == PREDICTED_AT_REGISTRATION


def test_the_prediction_includes_expected_failures(fields):
    """A register where every field is predicted required is not a test.

    The sweep has to be able to fail. At least one field must be predicted to
    carry no detection signal at all.
    """
    predicted_failures = [f["name"] for f in fields if f["predicted_tier"] == "not_required"]
    assert predicted_failures, "no field is predicted to fail the ablation"


def test_mapping_counts_match_the_mapping_document(repo_root, fields):
    """schema/otel-mapping.md publishes a summary table. Keep it honest."""
    counts = {"full": 0, "partial": 0, "none": 0}
    for field in fields:
        counts[field["otel"]] += 1

    text = (repo_root / "schema" / "otel-mapping.md").read_text(encoding="utf-8")
    for mapping, count in counts.items():
        assert f"| {mapping} | {count} |" in text, (
            f"otel-mapping.md summary says something other than {count} for {mapping}"
        )
