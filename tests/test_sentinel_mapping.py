"""The Sentinel mapping, held to the register and to the cited vendor constraints.

Nothing here reaches Azure. The constraints are constants in siem/sentinel.py,
each citing a numbered source in docs/sentinel-mapping.md, and these tests hold
the generated table, rule and queries to them. The files on disk and the doc's
generated blocks must be what the generator produces now.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest

from detect.detectors import A8_TOKENS_IN, A8_TOOL_CALLS, DETECTORS
from lab.config import REPO_ROOT
from siem import sentinel

DOC_TEXT = sentinel.DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cols() -> list[dict]:
    return sentinel.columns()


# ------------------------------------------------------------------ table --
def test_every_register_field_is_carried_exactly_once(cols, fields):
    carried = [c["field"] for c in cols if c["field"] and "." in c["field"]]
    expected = []
    for f in fields:
        if f["name"] == "retrieval.permission_context":
            keys = sentinel._permission_context_keys()
            expected += [f"{f['name']}.{k}" for k in keys]
        else:
            expected.append(f["name"])
    assert carried == expected


def test_permission_context_splits_into_its_three_schema_properties(cols):
    split = [c["field"] for c in cols if (c["field"] or "").startswith("retrieval.permission_context.")]
    assert split == [f"retrieval.permission_context.{k}" for k in ("caller_scope", "document_scopes", "scope_match")]


def test_column_names_follow_the_cited_rules(cols):
    names = [c["column"] for c in cols]
    assert len(names) == len(set(names))
    assert len(names) <= sentinel.MAX_COLUMNS
    for name in names:
        assert sentinel.COLUMN_NAME.match(name), name
        assert name not in sentinel.RESERVED_COLUMNS, name


def test_the_group_prefix_keeps_two_fields_off_reserved_names():
    assert sentinel.pascal("session.id") == "SessionId"
    assert sentinel.pascal("session.tenant_id") == "SessionTenantId"
    assert {"id", "TenantId"} <= sentinel.RESERVED_COLUMNS


def test_every_column_type_is_one_the_table_accepts(cols):
    assert {c["type"] for c in cols} <= sentinel.TABLE_TYPES


def test_timegenerated_is_ingestion_time(cols):
    first = cols[0]
    assert (first["column"], first["type"], first["expression"]) == ("TimeGenerated", "dateTime", "now()")


def test_the_table_is_a_custom_analytics_table_with_no_retention_set():
    table = sentinel.table_definition()["properties"]
    assert table["schema"]["name"].endswith("_CL")
    assert table["plan"] == "Analytics"
    assert not any("etention" in key for key in table)


def test_tiers_shown_are_the_registers(cols, fields):
    tiers = {f["name"]: f["tier"] for f in fields}
    for c in cols:
        if c["field"] and "." in c["field"]:
            name = c["field"] if c["field"] in tiers else c["field"].rsplit(".", 1)[0]
            assert c["tier"] == tiers[name]


# ---------------------------------------------------------------- the DCR --
def test_the_rule_is_direct_and_its_stream_names_follow_the_cited_forms():
    dcr = sentinel.dcr_definition()
    assert dcr["kind"] == "Direct"
    (stream,) = dcr["properties"]["streamDeclarations"]
    assert stream.startswith("Custom-")
    (flow,) = dcr["properties"]["dataFlows"]
    assert flow["streams"] == [stream]
    assert flow["outputStream"] == "Custom-" + sentinel.TABLE_NAME


def test_the_stream_declares_every_top_level_member_an_event_can_carry(event_schema):
    declared = {c["name"]: c["type"] for c in sentinel.stream_columns()}
    assert set(declared) == set(event_schema["properties"])
    assert set(declared.values()) <= sentinel.STREAM_TYPES


def test_the_transformation_stays_within_the_cited_length():
    assert len(sentinel.transform()) <= sentinel.MAX_TRANSFORM_CHARS


def test_the_transformation_calls_only_supported_functions():
    called = set(re.findall(r"\b([a-z_]+)\(", sentinel.transform()))
    assert called
    assert called <= sentinel.TRANSFORM_FUNCTIONS


def test_the_transformation_uses_only_extend_and_project():
    operators = re.findall(r"^\| (\S+)", sentinel.transform(), re.MULTILINE)
    assert operators == ["extend", "project"]


def test_the_transformation_projects_exactly_the_tables_columns(cols):
    projected = re.findall(r"^    (\w+) = ", sentinel.transform(), re.MULTILINE)
    assert projected == [c["column"] for c in cols]


# -------------------------------------------------------------- the rules --
def test_there_is_one_query_and_one_verdict_per_frozen_detector():
    ids = [d.id for d in DETECTORS]
    assert sorted(sentinel.rules()) == sorted(ids)
    assert sorted(sentinel.TRANSLATION) == sorted(ids)
    assert len(ids) == 7


def test_every_sigma_rule_has_exactly_one_rule_file():
    sigma = sorted(p.name[:3] for p in (REPO_ROOT / "detect" / "sigma").glob("a*.yml"))
    written = sorted("a" + p.stem[-2:] for p in sentinel.RULES_DIR.glob("*.kql"))
    assert sigma == written


def test_every_query_stays_within_the_cited_limits():
    for detector_id, query in sentinel.rules().items():
        assert len(query) <= sentinel.MAX_RULE_QUERY_CHARS, detector_id
        for forbidden in sentinel.FORBIDDEN_IN_RULES:
            assert forbidden not in query, detector_id


def test_every_watchlist_alias_is_a_valid_alias():
    aliases = set(re.findall(r"_GetWatchlist\('([^']+)'\)", "\n".join(sentinel.rules().values())))
    assert aliases
    for alias in aliases:
        assert sentinel.WATCHLIST_ALIAS.match(alias), alias


def test_the_consumption_rule_takes_the_frozen_thresholds():
    query = sentinel.rules()["d-a08"]
    assert f">= {A8_TOOL_CALLS}" in query
    assert f">= {A8_TOKENS_IN}" in query


def test_every_column_a_query_names_is_a_table_column(cols):
    names = {c["column"] for c in cols}
    derived = {"Domain", "Host", "Permitted", "Tool", "DocumentId", "FetchedHost",
               "ToolCalls", "MaxTokensIn", "LastSeen", "SearchKey"}
    for detector_id, query in sentinel.rules().items():
        referenced = set(re.findall(r"\b([A-Z][A-Za-z]+)\b", query)) - {sentinel.TABLE_NAME}
        assert referenced <= names | derived, (detector_id, referenced - names - derived)


# ------------------------------------------------------------ the output --
def test_the_files_on_disk_are_what_the_generator_produces():
    for path, text in sentinel.artefacts().items():
        assert (REPO_ROOT / path).read_text(encoding="utf-8") == text, path
    assert len(list(sentinel.RULES_DIR.glob("*.kql"))) == len(DETECTORS)


def test_the_doc_blocks_are_what_the_generator_produces():
    assert sentinel.render_doc(DOC_TEXT) == DOC_TEXT


def test_the_generated_json_parses():
    for path in (sentinel.TABLE_JSON, sentinel.DCR_JSON):
        json.loads(path.read_text(encoding="utf-8"))


def test_the_doc_says_nothing_is_deployed():
    assert "Documented, not deployed." in DOC_TEXT
    assert "no Azure spend was incurred" in DOC_TEXT


def test_every_cited_source_is_listed_with_a_retrieval_date_and_every_listed_source_is_cited():
    table = DOC_TEXT.split("## Sources")[1].split("## 1.")[0]
    rows = re.findall(r"^\| (\d+) \|.*\| ([^|]+) \|$", table, re.MULTILINE)
    listed = {int(n) for n, _ in rows}
    for _, retrieved in rows:
        assert re.fullmatch(r"\d{1,2} \w+ 2026", retrieved.strip()), retrieved
    body = DOC_TEXT.split("## 1.")[1]
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", body)}
    source = (REPO_ROOT / "siem" / "sentinel.py").read_text(encoding="utf-8")
    comments = " ".join(line.split("#", 1)[1] for line in source.splitlines() if "#" in line)
    cited_in_code = {int(n) for n in re.findall(r"\[(\d+)\]", comments)}
    assert cited_in_code
    assert cited == listed, (cited ^ listed)
    assert cited_in_code <= listed


def test_the_siem_package_loads_nothing_that_can_call_a_model_or_the_network():
    """Checked in a fresh interpreter, because this test process has already
    imported the lab agent through other tests."""
    probe = (
        "import sys, siem.sentinel\n"
        "roots = {m.split('.')[0] for m in sys.modules}\n"
        "bad = sorted(roots & {'anthropic', 'claude_agent_sdk', 'requests', 'httpx', 'urllib3',"
        " 'azure', 'socket', 'http'})\n"
        "bad += [m for m in sys.modules if m in ('lab.agent', 'lab.harness', 'lab.tools', 'lab.hooks')]\n"
        "print(','.join(bad))\n"
    )
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                         cwd=REPO_ROOT, check=True)
    assert out.stdout.strip() == ""
