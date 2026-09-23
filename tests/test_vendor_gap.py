"""The vendor gap analysis, held to its evidence, its rulings and the captures.

Nothing here reaches Azure, AWS or the network. The vendor pages were read in
the M7 session and recorded in vendor_gap/evidence.yaml; these tests hold every
verdict to a listed source, every rule of the M7 rulings to the evidence, the
vendor passes to the M5 harness and the frozen detectors, and the page and the
results file to what the generator produces now.

Synthetic fixtures carry no canary value, no em-dash and none of the six banned
words.
"""

from __future__ import annotations

import copy
import inspect
import re
import subprocess
import sys

import pytest

from ablation import rulings as m5
from ablation.ablate import CLASSES, fires
from detect import detectors as detector_module
from detect.detectors import DETECTORS, DetectorConfig
from lab.config import REPO_ROOT
from vendor_gap import analysis, rulings

DOC_TEXT = analysis.DOC_PATH.read_text(encoding="utf-8")
# The page as prose, line breaks folded, for phrases that wrap.
DOC_WORDS = " ".join(DOC_TEXT.split())


@pytest.fixture(scope="module")
def corpus():
    return analysis.load()


@pytest.fixture(scope="module")
def doc(corpus):
    return analysis.build(corpus)


def _evidence():
    return copy.deepcopy(analysis.evidence())


# --------------------------------------------------------------- evidence --
def test_the_evidence_breaks_none_of_its_rules():
    assert analysis.problems() == []


def test_every_surface_carries_the_register_and_the_six_event_types(fields):
    names = {f["name"] for f in fields}
    for s in analysis.evidence()["surfaces"]:
        assert set(s["fields"]) == names, s["id"]
        assert tuple(s["events"]) == rulings.EVENT_TYPES, s["id"]


def test_the_surfaces_are_the_ruled_scope():
    ids = [s["id"] for s in analysis.evidence()["surfaces"]]
    assert ids == ["azure-as-shipped", "azure-model", "azure-agent", "aws-as-shipped", "aws-model", "aws-agent"]
    assert rulings.LAYERS == ("model", "agent")


def test_the_codes_in_the_evidence_are_the_rulings_vocabulary():
    assert set(analysis.VERDICT.values()) == set(rulings.VERDICTS)
    assert set(analysis.FORM.values()) == set(rulings.FORMS)


@pytest.mark.parametrize("breakage, expected", [
    (lambda ev: ev["surfaces"][1]["fields"]["turn.model_id"].update(v="A"), "absent with no full list"),
    (lambda ev: ev["surfaces"][4]["fields"]["turn.tokens_out"].update(v="C"), "a setting goes with verdict C"),
    (lambda ev: ev["surfaces"][4]["fields"]["turn.tokens_out"].update(src=[99]), "missing or unlisted"),
    (lambda ev: ev["surfaces"][4]["fields"]["session.id"].update(v="D"), "does not produce is absent"),
    (lambda ev: ev["surfaces"][4]["fields"]["turn.tokens_out"].update(path="undocumented"), "path note"),
    (lambda ev: ev["quotes"]["aws-disabled"].update(text="word " * 31), "runs over"),
    (lambda ev: ev["sources"].append({**ev["sources"][0], "n": len(ev["sources"]) + 1}), "differ from sources listed"),
    (lambda ev: ev["sources"][14].update(updated="sometime"), "no page date"),
    (lambda ev: ev["surfaces"][0]["events"].pop("tool_post"), "six event types"),
])
def test_a_broken_rule_is_caught(breakage, expected):
    ev = _evidence()
    breakage(ev)
    found = analysis.problems(ev)
    assert any(expected in p for p in found), found


def test_every_unconfirmed_row_names_the_pages_attempted():
    for s in analysis.evidence()["surfaces"]:
        for rows in (s["fields"], s["events"]):
            for name, row in rows.items():
                if row["v"] == "U":
                    assert row["src"], (s["id"], name)


def test_no_page_copies_are_committed():
    assert rulings.PAGE_COPIES_COMMITTED is False
    for folder in ("vendor_gap", "docs"):
        assert not list((REPO_ROOT / folder).rglob("*.htm*")), folder


# ------------------------------------------------------------- row status --
@pytest.mark.parametrize("row, parsed, expected", [
    ({"v": "D"}, False, "yes"),
    ({"v": "D", "partial": "differs"}, False, "maybe"),
    ({"v": "U"}, False, "maybe"),
    ({"v": "C", "setting": "s"}, False, "no"),
    ({"v": "A"}, False, "no"),
    ({"v": "D", "form": "body", "path": "undocumented"}, False, "no"),
    ({"v": "D", "form": "body", "path": "undocumented"}, True, "maybe"),
    ({"v": "D", "form": "body"}, True, "yes"),
    ({"v": "D", "form": "content"}, True, "no"),
    ({"v": "U", "form": "content"}, True, "no"),
    ({"v": "A", "form": "derived"}, True, "no"),
])
def test_a_row_counts_as_the_rulings_say(row, parsed, expected):
    assert analysis.row_status(row, parsed) == expected


# --------------------------------------------------- what detectors need --
def _event_types_named(detector_id: str) -> set[str]:
    function = next(d.run for d in DETECTORS if d.id == detector_id)
    source = inspect.getsource(function)
    return set(re.findall(r'session\.(?:events|count)\("([a-z_]+)"\)', source))


def test_detector_needs_cover_every_frozen_detector():
    assert set(analysis.DETECTOR_NEEDS) == {d.id for d in DETECTORS}


@pytest.mark.parametrize("detector_id", sorted(analysis.DETECTOR_NEEDS))
def test_the_event_types_declared_are_the_ones_the_detector_names(detector_id):
    assert analysis.DETECTOR_NEEDS[detector_id][0] == _event_types_named(detector_id)


@pytest.mark.parametrize("detector", DETECTORS, ids=lambda d: d.id)
def test_dropping_an_event_type_a_detector_does_not_need_never_moves_it(corpus, detector):
    needs, grouped = analysis.DETECTOR_NEEDS[detector.id]
    for capture in corpus.captures.values():
        before = fires(detector, capture.events, corpus.config)
        for event_type in set(rulings.EVENT_TYPES) - needs:
            (session,) = analysis.transform(capture.events, (), (event_type,), True)
            assert fires(detector, session, corpus.config) == before, (detector.id, capture.run_id, event_type)
        if not grouped:
            split = analysis.transform(capture.events, (), (), False)
            assert any(fires(detector, s, corpus.config) for s in split) == before, (detector.id, capture.run_id)


CONFIG = DetectorConfig(
    email_allow_domains=frozenset({"insurer.invalid"}),
    url_allow_hosts=frozenset({"intranet.insurer.invalid"}),
    known_document_ids=frozenset({"doc-known-001"}),
    task_tool_set=frozenset({"search_documents"}),
)


def _ev(event_type, **groups):
    return {"event_type": event_type, **groups}


GROUPED_FIXTURES = {
    "d-a02": [
        _ev("retrieval", retrieval={"source_provenance": "external_supplied"}),
        _ev("tool_pre", action={"egress_target": "mailto:someone@outside.invalid"}),
    ],
    "d-a03": [
        _ev("retrieval", retrieval={"permission_context": {"scope_match": False}}),
        _ev("turn", control={"canary_triggered": True}),
    ],
    "d-a07": [
        _ev("retrieval", retrieval={}),
        _ev("turn", control={"canary_triggered": True}),
    ],
    "d-a08": [_ev("tool_pre", action={}) for _ in range(detector_module.A8_TOOL_CALLS)],
}


@pytest.mark.parametrize("detector_id", sorted(GROUPED_FIXTURES))
def test_a_detector_declared_session_scoped_changes_when_its_session_is_split(detector_id):
    assert analysis.DETECTOR_NEEDS[detector_id][1] is True
    detector = analysis.DETECTOR_BY_ID[detector_id]
    events = GROUPED_FIXTURES[detector_id]
    whole = fires(detector, events, CONFIG)
    split = any(fires(detector, [e], CONFIG) for e in events)
    assert whole != split


def test_the_ungrouped_detectors_are_the_ones_without_a_split_fixture():
    grouped = {d for d, (_, g) in analysis.DETECTOR_NEEDS.items() if g}
    assert grouped == set(GROUPED_FIXTURES)


# ----------------------------------------------------------------- passes --
def test_the_baseline_pass_reproduces_the_m5_sweep(doc):
    import json

    recorded = json.loads(analysis.NECESSITY_JSON.read_text(encoding="utf-8"))["baseline"]
    for cls in CLASSES:
        base = doc["baseline"][cls]
        if base["detector"]:
            assert base["detected"] == recorded["detection"][cls]["detected"]
            assert base["false_positives"] == recorded["false_positives"][base["detector"]]["count"]


def test_a_pass_never_changes_a_capture(corpus):
    before = {r: copy.deepcopy(c.events) for r, c in corpus.captures.items()}
    for capture in corpus.captures.values():
        analysis.transform(capture.events, sorted(analysis.field_names()), rulings.EVENT_TYPES[:3], False)
    assert {r: list(c.events) for r, c in corpus.captures.items()} == {r: list(e) for r, e in before.items()}


def test_classes_the_question_cannot_reach_read_nt_or_ab_in_every_column(doc):
    for key, answers in doc["answers"].items():
        for cls in ("A1", "A2", "A3", "A4"):
            assert answers[cls]["code"] == "nt", (key, cls)
        assert answers["A10"]["code"] == "ab", key


def test_the_question_is_answerable_for_five_classes_two_on_one_session(doc):
    answerable = [c for c in CLASSES if doc["baseline"][c]["n"] > 0]
    assert answerable == ["A5", "A6", "A7", "A8", "A9"]
    assert [c for c in answerable if doc["baseline"][c]["n"] == 1] == ["A5", "A7"]


def test_a_combination_without_a_documented_link_is_unconfirmed(doc):
    for vendor in analysis.VENDORS:
        assert analysis.evidence()["combined"][vendor]["linked"] is False
        for cls in ("A5", "A6", "A7", "A8", "A9"):
            assert doc["answers"][f"{vendor}-combined"][cls]["code"] == rulings.UNCONFIRMED_CODE


def test_uc_means_the_passes_disagree_and_nothing_else_does(doc):
    for key, answers in doc["answers"].items():
        for cls, a in answers.items():
            if "passes" not in a:
                continue
            bases = {analysis._base(p["code"]) for p in a["passes"]}
            assert (a["code"] == rulings.UNCONFIRMED_CODE) == (len(bases) > 1), (key, cls)


def test_every_restoring_set_restores_and_none_contains_another(corpus, doc):
    for vendor in analysis.VENDORS:
        column = analysis.headline(vendor)
        for cls, sets in doc["additions"][vendor]["restoring_sets"].items():
            assert sets, (vendor, cls)
            inputs = analysis.inputs_of(analysis.DETECTOR_BY_ID[doc["baseline"][cls]["detector"]])
            for chosen in sets:
                added = {tuple(item.split(":", 1)) for item in chosen}
                available = {inp: analysis.status(column, *inp) == analysis.YES or inp in added for inp in inputs}
                result = analysis.measure(corpus, doc["baseline"][cls], cls, available, column)
                assert analysis._base(result["code"]) == ".", (vendor, cls, chosen)
                for other in sets:
                    assert other == chosen or not set(other) <= set(chosen)


def test_nothing_is_available_with_configuration_as_the_page_says(doc):
    for surface_id, c in doc["surfaces"].items():
        assert c["fields"].get("available_with_configuration", 0) == 0, surface_id
    assert "Nothing is available with configuration on any surface." in DOC_WORDS


def test_reading_the_text_modality_as_a_further_setting_changes_no_class_answer(corpus, doc, monkeypatch):
    """The page says so: seven fields and three event types would move from
    available by default to available with configuration, and no answer."""
    ev = _evidence()
    moved = {"fields": 0, "events": 0}
    (aws_model,) = [s for s in ev["surfaces"] if s["id"] == "aws-model"]
    for kind in ("fields", "events"):
        for row in aws_model[kind].values():
            if row["v"] == "D" and row.get("form") in ("body", "content"):
                row["v"], row["setting"] = "C", "the Text modality"
                moved[kind] += 1
    assert moved == {"fields": 7, "events": 3}
    assert "seven fields and three event types move" in DOC_WORDS
    monkeypatch.setattr(analysis, "evidence", lambda: ev)
    for column in analysis.columns():
        for cls in CLASSES:
            again = analysis.answer(corpus, doc["baseline"][cls], cls, column)["code"]
            assert again == doc["answers"][column.key][cls]["code"], (column.key, cls)


def test_the_counted_detector_is_m5_ruling_1():
    assert rulings.CLASS_DETECTOR is m5.CLASS_DETECTOR


# ------------------------------------------------------------- the output --
def test_the_results_file_is_what_a_fresh_run_produces(doc):
    assert analysis.RESULTS_PATH.read_text(encoding="utf-8") == analysis.dumps(doc)


def test_the_doc_blocks_are_what_the_generator_produces(doc):
    assert analysis.render_doc(DOC_TEXT, doc) == DOC_TEXT


def test_the_results_hold_identifiers_and_counts_only(doc):
    text = analysis.dumps(doc)
    assert "canary_register" not in text
    assert "THN-" not in text


def test_tiers_shown_are_the_registers(fields):
    tiers = {f["name"]: f["tier"] for f in fields}
    rows = re.findall(r"^\| `([a-z_]+\.[a-z_]+)` \| ([a-z_]+) \|", DOC_TEXT, re.MULTILINE)
    assert rows
    for name, tier in rows:
        assert tier == tiers[name], name


def test_every_source_cited_on_the_page_is_listed_and_every_listed_source_is_cited():
    listed = {s["n"] for s in analysis.evidence()["sources"]}
    body = DOC_TEXT.split("<!-- /generated:sources -->", 1)[1]
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", body)}
    assert cited == listed, cited ^ listed


def test_the_page_says_nothing_was_created_and_no_model_was_called():
    assert "No Azure or AWS resource was created" in DOC_WORDS
    assert "no model call was made" in DOC_WORDS
    assert rulings.MODEL_CALLS is False and rulings.CLOUD_RESOURCES is False


def test_the_page_states_the_five_class_limit_and_the_a9_exposure():
    assert "five classes only, and for two of them on a single session" in DOC_WORDS
    paragraph = next(p for p in DOC_TEXT.split("\n\n") if "A9" in p and "holdout" in p)
    assert "knew both holdout outcomes" in paragraph


def test_the_package_loads_nothing_that_can_reach_the_network_or_a_model():
    """In a fresh interpreter, because this process has imported the lab agent
    through other tests."""
    probe = (
        "import sys, vendor_gap.analysis\n"
        "roots = {m.split('.')[0] for m in sys.modules}\n"
        "bad = sorted(roots & {'anthropic', 'claude_agent_sdk', 'requests', 'httpx', 'urllib3',"
        " 'azure', 'boto3', 'botocore', 'socket', 'http'})\n"
        "bad += [m for m in sys.modules if m in ('lab.agent', 'lab.harness', 'lab.tools', 'lab.hooks')]\n"
        "print(','.join(bad))\n"
    )
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                         cwd=REPO_ROOT, check=True)
    assert out.stdout.strip() == ""
