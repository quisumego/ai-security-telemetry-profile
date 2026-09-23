"""The Microsoft Sentinel mapping, generated from the register. Documented, not deployed.

    .venv/bin/python -m siem.sentinel            # print what would be written
    .venv/bin/python -m siem.sentinel --write    # write siem/sentinel/ and the doc's generated blocks

**Nothing here touches Azure.** No resource is created, no request is sent and
no Azure spend is incurred. The output is files: a custom table definition, a
Data Collection Rule, and one KQL scheduled-rule query per frozen detector.

**Why generated.** Every column comes from `schema/fields.yaml` and every
threshold from `detect/detectors.py`, so the mapping cannot drift from the
register or from the detectors that scored the corpus. The vendor constraints
the output must satisfy are constants below, each citing the numbered source in
`docs/sentinel-mapping.md`, and `tests/test_sentinel_mapping.py` holds the
output to them.
"""

from __future__ import annotations

import argparse
import functools
import json
import re
from typing import Any, Sequence

import yaml

from detect.detectors import A8_TOKENS_IN, A8_TOOL_CALLS, DETECTORS
from lab.config import REGISTER_PATH, REPO_ROOT, SCHEMA_PATH

OUT_DIR = REPO_ROOT / "siem" / "sentinel"
TABLE_JSON = OUT_DIR / "astp-table.json"
DCR_JSON = OUT_DIR / "astp-dcr.json"
RULES_DIR = OUT_DIR / "rules"
DOC = REPO_ROOT / "docs" / "sentinel-mapping.md"
COMMAND = ".venv/bin/python -m siem.sentinel --write"

TABLE_NAME = "AstpEvents_CL"          # custom tables take the _CL suffix [1]
STREAM_NAME = "Custom-AstpEvents"     # stream names begin Custom- [5]
OUTPUT_STREAM = f"Custom-{TABLE_NAME}"  # Custom-<table> for a custom table [5][10]
DESTINATION = "AstpWorkspace"
TABLE_PLAN = "Analytics"              # alerts need it; Auxiliary has none [11]

# Column naming for custom tables [1][10]: start with a letter, then letters,
# digits or underscores only, 2 to 45 characters, and none of these reserved
# names. The two sources list reserved names differently, so both lists apply.
COLUMN_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{1,44}$")
RESERVED_COLUMNS = frozenset({
    "id", "BilledSize", "IsBillable", "InvalidTimeGenerated", "TenantId", "Title", "Type",
    "UniqueId", "_ItemId", "_ResourceGroup", "_ResourceId", "_SubscriptionId", "_TimeReceived",
})
MAX_COLUMNS = 500                     # [4]
TABLE_TYPES = frozenset({"string", "int", "long", "real", "boolean", "dateTime", "dynamic", "guid"})  # [1]
STREAM_TYPES = frozenset({"string", "int", "long", "real", "boolean", "dynamic", "datetime"})        # [5]
MAX_TRANSFORM_CHARS = 15_360          # [4]
MAX_RULE_QUERY_CHARS = 10_000         # [6]
FORBIDDEN_IN_RULES = ("search *", "union *")  # [6]
WATCHLIST_ALIAS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{1,62}[A-Za-z0-9]$")  # 3 to 64 [7]

# The scalar functions this transformation calls, every one of them on the
# supported list for transformations [3]. A test extracts every call from the
# generated query and requires it to be here.
TRANSFORM_FUNCTIONS = frozenset({"parse_json", "tostring", "tolong", "toreal", "tobool", "todatetime", "now"})

GROUPS = ("session", "turn", "content", "retrieval", "action", "control")
GROUP_VARS = {g: f"{g}_" for g in GROUPS}
ENVELOPE = (("AstpVersion", "astp_version", "the register version the event was emitted against"),
            ("EventType", "event_type", "which emission point produced the event"))


def pascal(dotted: str) -> str:
    """`session.tenant_id` to `SessionTenantId`, as ruled at M6."""
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[._]", dotted) if part)


@functools.cache
def _register() -> list[dict[str, Any]]:
    return yaml.safe_load(REGISTER_PATH.read_text(encoding="utf-8"))["fields"]


@functools.cache
def _permission_context_keys() -> dict[str, dict[str, Any]]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return schema["properties"]["retrieval"]["properties"]["permission_context"]["properties"]


def _scalar(field_type: str, fmt: str | None) -> tuple[str, str | None]:
    """The table type and the conversion function for one register type."""
    if field_type == "string":
        return ("dateTime", "todatetime") if fmt == "date-time" else ("string", "tostring")
    if field_type == "integer":
        return "long", "tolong"
    if field_type == "number":
        return "real", "toreal"
    if field_type == "boolean":
        return "boolean", "tobool"
    return "dynamic", None


def columns() -> list[dict[str, Any]]:
    """Every table column, in order, with the ASTP field it carries.

    One column per register field. `retrieval.permission_context` is split into
    its three schema properties, because they are fixed in the event schema and
    d-a03 filters on one of them. Every other object and array stays dynamic.
    """
    out = [{"column": "TimeGenerated", "type": "dateTime", "field": None, "tier": None,
            "expression": "now()", "note": "ingestion time, on every row"}]
    for column, key, note in ENVELOPE:
        out.append({"column": column, "type": "string", "field": key, "tier": None,
                    "expression": f"tostring({key})", "note": note})
    for entry in _register():
        name = str(entry["name"])
        group, _, leaf = name.partition(".")
        var = GROUP_VARS[group]
        if name == "retrieval.permission_context":
            for sub, spec in _permission_context_keys().items():
                kinds = [k for k in spec["type"] if k != "null"]
                table_type, fn = _scalar(kinds[0], None)
                access = f"{var}['{leaf}']['{sub}']"
                out.append({"column": pascal(f"{name}.{sub}"), "type": table_type, "field": f"{name}.{sub}",
                            "tier": entry["tier"], "expression": f"{fn}({access})" if fn else access,
                            "note": "split from its object"})
            continue
        table_type, fn = _scalar(str(entry["type"]), entry.get("format"))
        access = f"{var}['{leaf}']"
        out.append({"column": pascal(name), "type": table_type, "field": name, "tier": entry["tier"],
                    "expression": f"{fn}({access})" if fn else access,
                    "note": "kept as dynamic" if table_type == "dynamic" else ""})
    return out


def transform() -> str:
    """The ingestion-time KQL: parse each group, then project the table's columns."""
    parsed = ", ".join(f"{GROUP_VARS[g]} = parse_json({g})" for g in GROUPS)
    projected = ",\n    ".join(f"{c['column']} = {c['expression']}" for c in columns())
    return f"source\n| extend {parsed}\n| project\n    {projected}"


def table_definition() -> dict[str, Any]:
    return {
        "properties": {
            "schema": {
                "name": TABLE_NAME,
                "columns": [
                    {"name": c["column"], "type": c["type"],
                     "description": f"ASTP {c['field']}" if c["field"] else c["note"]}
                    for c in columns()
                ],
            },
            "plan": TABLE_PLAN,
        }
    }


def stream_columns() -> list[dict[str, str]]:
    """The top-level members an ASTP event can carry, as the stream declares them [5]."""
    return ([{"name": key, "type": "string"} for _, key, _ in ENVELOPE]
            + [{"name": g, "type": "dynamic"} for g in GROUPS])


def dcr_definition() -> dict[str, Any]:
    return {
        "location": "<Location>",
        "kind": "Direct",
        "properties": {
            "streamDeclarations": {STREAM_NAME: {"columns": stream_columns()}},
            "destinations": {
                "logAnalytics": [{"workspaceResourceId": "<WorkspaceResourceId>", "name": DESTINATION}]
            },
            "dataFlows": [{
                "streams": [STREAM_NAME],
                "destinations": [DESTINATION],
                "transformKql": transform(),
                "outputStream": OUTPUT_STREAM,
            }],
        },
    }


# ------------------------------------------------------------------ rules --
def col(field: str) -> str:
    """The column that carries a register field, failing on any name the mapping lacks."""
    for c in columns():
        if c["field"] == field:
            return c["column"]
    raise KeyError(field)


def _permitted_check(target: str) -> str:
    """The deployment's allow lists, applied as d-a01 and d-a02 apply them."""
    return (
        f"| extend Domain = tolower(extract(@\"^mailto:.*@([^@]+)$\", 1, {target})),\n"
        f"         Host = tolower(extract(@\"^[^:]+://([^/]*)\", 1, {target}))\n"
        "| extend Permitted = (isnotempty(Domain) and Domain in (email_domains))\n"
        "                  or (isnotempty(Host) and Host in (url_hosts))\n"
        "| where not(Permitted)\n"
    )


ALLOW_LISTS = (
    "let email_domains = _GetWatchlist('astp_permitted_email_domains') | project SearchKey;\n"
    "let url_hosts = _GetWatchlist('astp_permitted_url_hosts') | project SearchKey;\n"
)


def rules() -> dict[str, str]:
    """One scheduled-rule query per frozen detector, following the Python that scored."""
    t = TABLE_NAME
    sid, etype = col("session.id"), "EventType"
    egress, canary = col("action.egress_target"), col("control.canary_triggered")
    return {
        "d-a01": (
            ALLOW_LISTS
            + f"{t}\n| where {etype} == \"tool_pre\" and {canary} == true and isnotempty({egress})\n"
            + _permitted_check(egress)
            + f"| project TimeGenerated, {sid}, {egress}"
        ),
        "d-a02": (
            ALLOW_LISTS
            + f"let external = {t}\n"
            f"    | where {etype} == \"retrieval\" and {col('retrieval.source_provenance')} in "
            "(\"external_supplied\", \"third_party_feed\")\n"
            f"    | distinct {sid};\n"
            f"{t}\n| where {etype} == \"tool_pre\" and isnotempty({egress}) and {sid} in (external)\n"
            + _permitted_check(egress)
            + f"| project TimeGenerated, {sid}, {egress}"
        ),
        "d-a03": (
            f"let crossed = {t}\n"
            f"    | where {etype} == \"retrieval\" and {col('retrieval.permission_context.scope_match')} == false\n"
            f"    | distinct {sid};\n"
            f"{t}\n| where {etype} == \"turn\" and {canary} == true and {sid} in (crossed)\n"
            f"| project TimeGenerated, {sid}"
        ),
        "d-a04": (
            "let task_apps = _GetWatchlist('astp_read_only_task_apps') | project SearchKey;\n"
            "let task_tools = _GetWatchlist('astp_read_only_task_tools') | project SearchKey;\n"
            f"{t}\n| where {etype} == \"tool_pre\" and {col('session.client_app')} in (task_apps)\n"
            f"| extend Tool = replace_regex({col('action.tool_name')}, @\"^.*__\", \"\")\n"
            "| where isnotempty(Tool) and Tool !in (task_tools)\n"
            f"| project TimeGenerated, {sid}, Tool"
        ),
        "d-a06": (
            "let inventory = _GetWatchlist('astp_document_inventory') | project SearchKey;\n"
            "let url_hosts = _GetWatchlist('astp_permitted_url_hosts') | project SearchKey;\n"
            f"{t}\n| where {etype} == \"retrieval\"\n"
            f"| mv-expand DocumentId = {col('retrieval.document_ids')} to typeof(string)\n"
            "| extend FetchedHost = tolower(extract(@\"^fetched:[^:]*://([^/]*)\", 1, DocumentId))\n"
            "| where DocumentId !in (inventory) and not(isnotempty(FetchedHost) and FetchedHost in (url_hosts))\n"
            f"| project TimeGenerated, {sid}, DocumentId"
        ),
        "d-a07": (
            f"let retrieving = {t}\n    | where {etype} == \"retrieval\"\n    | distinct {sid};\n"
            f"{t}\n| where {etype} == \"turn\" and {canary} == true and {sid} !in (retrieving)\n"
            f"| project TimeGenerated, {sid}"
        ),
        "d-a08": (
            f"{t}\n| summarize ToolCalls = countif({etype} == \"tool_pre\"),\n"
            f"            MaxTokensIn = maxif({col('turn.tokens_in')}, {etype} == \"turn\"),\n"
            f"            LastSeen = max(TimeGenerated) by {sid}\n"
            f"| where ToolCalls >= {A8_TOOL_CALLS} or MaxTokensIn >= {A8_TOKENS_IN}"
        ),
    }


# Which rules translate, decided against the constraints on scheduled rules [6]
# and watchlists [7]. Session-scoped means the rule groups events by session.
TRANSLATION = {
    "d-a01": ("yes", "single event; the permitted destinations become two watchlists"),
    "d-a02": ("yes", "session-scoped; the Python that scored has no ordering, so neither has this"),
    "d-a03": ("yes", "session-scoped; the Python that scored has no ordering, so neither has this"),
    "d-a04": ("partly", "no field names the task a session runs, so the rule is scoped by client "
                        "application, which is an assumption about the deployment"),
    "d-a06": ("yes", "single event; the document inventory becomes a watchlist"),
    "d-a07": ("yes, with a caveat", "session-scoped and reasons from absence, so a session that "
                                    "straddles the lookback window can fire on half a session"),
    "d-a08": ("yes", "session-scoped count; circular, as the Sigma rule states, because the "
                     "thresholds are the A8 oracle's"),
}


def rule_file(detector_id: str) -> str:
    sigma = next(REPO_ROOT.joinpath("detect", "sigma").glob(f"a{detector_id[-2:]}-*.yml")).name
    status, why = TRANSLATION[detector_id]
    title = next(d.title for d in DETECTORS if d.id == detector_id)
    return (
        f"// {detector_id}: {title}\n"
        f"// Translated from detect/sigma/{sigma} and the scoring code in detect/detectors.py.\n"
        f"// Translates: {status}. {why[:1].upper() + why[1:]}.\n"
        "// Documented, not deployed, and never run. Generated by siem/sentinel.py.\n"
        f"{rules()[detector_id]}\n"
    )


# -------------------------------------------------------------- the doc --
def _columns_block() -> str:
    lines = ["| Column | Type | ASTP field | Tier | Note |", "|---|---|---|---|---|"]
    for c in columns():
        field = f"`{c['field']}`" if c["field"] else ""
        lines.append(f"| `{c['column']}` | {c['type']} | {field} | {c['tier'] or ''} | {c['note']} |")
    return "\n".join(lines)


def _dcr_block() -> str:
    return "```json\n" + json.dumps(dcr_definition(), indent=2) + "\n```"


def _rules_block() -> str:
    lines = ["| Detector | Translates | Why |", "|---|---|---|"]
    for d in DETECTORS:
        status, why = TRANSLATION[d.id]
        lines.append(f"| `{d.id}` | {status} | {why} |")
    for d in DETECTORS:
        lines += ["", f"**`{d.id}`**, {d.title.lower()}:", "", "```kql", rules()[d.id], "```"]
    return "\n".join(lines)


def _figures_block() -> str:
    return (f"{len(columns())} columns against a limit of {MAX_COLUMNS} [4]. The transformation is "
            f"{len(transform()):,} characters against a limit of {MAX_TRANSFORM_CHARS:,} [4]. The longest "
            f"rule query is {max(len(q) for q in rules().values()):,} characters against a limit of "
            f"{MAX_RULE_QUERY_CHARS:,} [6].")


BLOCKS = {
    "columns": _columns_block,
    "dcr": _dcr_block,
    "rules": _rules_block,
    "figures": _figures_block,
}


def render_doc(text: str) -> str:
    """The doc with every generated block replaced by what the generator produces now."""
    for name, make in BLOCKS.items():
        pattern = re.compile(
            rf"(<!-- generated:{name} -->\n).*?(<!-- /generated:{name} -->)", re.DOTALL)
        if not pattern.search(text):
            raise ValueError(f"docs/sentinel-mapping.md has no generated block named {name!r}")
        text = pattern.sub(lambda m: m.group(1) + make() + "\n" + m.group(2), text)
    return text


def artefacts() -> dict[str, str]:
    """Every generated file, by path relative to the repository."""
    out = {
        str(TABLE_JSON.relative_to(REPO_ROOT)): json.dumps(table_definition(), indent=2) + "\n",
        str(DCR_JSON.relative_to(REPO_ROOT)): json.dumps(dcr_definition(), indent=2) + "\n",
    }
    for d in DETECTORS:
        out[str((RULES_DIR / f"{d.id}.kql").relative_to(REPO_ROOT))] = rule_file(d.id)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The Microsoft Sentinel mapping, documented not deployed.")
    parser.add_argument("--write", action="store_true", help="write siem/sentinel/ and the doc's blocks")
    args = parser.parse_args(argv)
    files = artefacts()
    for path, text in files.items():
        print(f"  {path}  {len(text):,} characters")
    print("  " + _figures_block())
    if args.write:
        RULES_DIR.mkdir(parents=True, exist_ok=True)
        for path, text in files.items():
            (REPO_ROOT / path).write_text(text, encoding="utf-8")
        DOC.write_text(render_doc(DOC.read_text(encoding="utf-8")), encoding="utf-8")
        print(f"  written: {len(files)} files and the generated blocks of {DOC.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
