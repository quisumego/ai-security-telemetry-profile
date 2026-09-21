"""The Section 8.7 post-capture checks, as assertions rather than claims.

These run over the scored M2 corpus only: the hundred `m2-a*` trials. The two
M1 benign runs and the M2 smoke session are deliberately excluded. They predate
the freeze, carry `corpus.tag` null, and are not part of any scored rate.

Each check exists because a capture that failed it would be unusable in a way
no later stage could repair: a corpus taken against drifting material, a
session that silently ran on another model, or turn figures that stopped being
read back from the transcript.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab.config import REPO_ROOT

SCORED_GLOB = "runs/m2-a[0-9][0-9]-t[0-9][0-9]/manifest.json"
EXPECTED_TRIALS = 100
SCENARIO_IDS = tuple(f"a{i:02d}" for i in range(1, 11))


def _scored_manifests() -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(REPO_ROOT.glob(SCORED_GLOB))
    ]


@pytest.fixture(scope="module")
def manifests() -> list[dict]:
    found = _scored_manifests()
    assert found, "no scored captures found"
    return found


def test_the_corpus_is_one_hundred_trials(manifests):
    assert len(manifests) == EXPECTED_TRIALS


def test_every_scenario_contributed_ten_trials(manifests):
    counts: dict[str, int] = {}
    for manifest in manifests:
        counts[manifest["scenario"]["id"]] = counts.get(manifest["scenario"]["id"], 0) + 1
    assert counts == {scenario_id: 10 for scenario_id in SCENARIO_IDS}


def test_turns_unenriched_is_zero_everywhere(manifests):
    """A rise means lab/transcript.py stopped reading the CLI transcript, so
    the per-turn figures would be null rather than wrong, and silently so."""
    offenders = [
        m["run_id"] for m in manifests if m["session"]["turns_unenriched"] != 0
    ]
    assert not offenders, offenders


def test_only_the_pinned_model_resolved(manifests):
    seen = {model for m in manifests for model in m["model"]["resolved"]}
    assert seen == {"claude-haiku-4-5", "claude-haiku-4-5-20251001"}, seen


def test_no_fallback_model_was_ever_set(manifests):
    assert {m["model"]["fallback_model"] for m in manifests} == {None}


def test_the_corpus_digest_is_identical_throughout(manifests):
    """Different digests mean different material, whatever git says."""
    digests = {m["corpus"]["digest"] for m in manifests}
    assert len(digests) == 1, digests


def test_the_corpus_tag_is_the_freeze_tag_throughout(manifests):
    assert {m["corpus"]["tag"] for m in manifests} == {"freeze-m2"}


def test_thinking_was_disabled_throughout(manifests):
    assert {m["model"]["thinking"] for m in manifests} == {"disabled"}


def test_the_configuration_did_not_move_during_the_capture(manifests):
    assert {m["versions"]["config_version"] for m in manifests} == {"0.2.0"}
    assert {m["versions"]["system_prompt_version"] for m in manifests} == {"sp-0.2.0"}


def test_overlay_digest_is_present_exactly_where_a_scenario_serves_one(manifests):
    """Null for a prompt-delivered scenario, a digest for an overlay one, and
    one digest per scenario rather than one per trial."""
    from attacks.delivery import serves_an_overlay
    from attacks.oracles import load_scenario

    by_scenario: dict[str, set] = {}
    for manifest in manifests:
        scenario_id = manifest["scenario"]["id"]
        by_scenario.setdefault(scenario_id, set()).add(manifest["scenario"]["overlay_digest"])

    for scenario_id, digests in by_scenario.items():
        assert len(digests) == 1, f"{scenario_id} varied: {digests}"
        digest = digests.pop()
        if serves_an_overlay(load_scenario(scenario_id)):
            assert digest is not None and len(digest) == 64, f"{scenario_id}: {digest}"
        else:
            assert digest is None, f"{scenario_id}: {digest}"


def test_the_holdouts_are_flagged_in_their_manifests(manifests):
    """A5 and A9 were committed as holdouts before any scenario file existed."""
    holdouts = {
        m["scenario"]["id"] for m in manifests if m["scenario"]["holdout"]
    }
    assert holdouts == {"a05", "a09"}


def test_no_scenario_file_carries_a_canary_value():
    """An attack prompt containing the string it is meant to exfiltrate would
    score itself. tests/test_corpus.py enforces this over the whole tree; it is
    restated here because Section 8.7 lists it as a post-capture check."""
    import yaml

    register = yaml.safe_load((REPO_ROOT / "lab" / "canary_register.yaml").read_text())
    values = {entry["value"] for entry in register["canaries"]}
    for path in sorted((REPO_ROOT / "attacks" / "scenarios").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        for value in values:
            assert value not in text, f"{path.name} carries a canary value"


def test_every_trial_ended_on_an_outcome_its_scenario_allows(manifests):
    from attacks.oracles import load_scenario

    for manifest in manifests:
        scenario = load_scenario(manifest["scenario"]["id"])
        allowed = set(scenario["legitimate_outcomes"])
        subtype = manifest["session"]["subtype"]
        assert subtype in allowed, f"{manifest['run_id']}: {subtype} not in {allowed}"
