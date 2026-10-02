# Microsoft Sentinel mapping

> **Documented, not deployed.** No Azure resource was created, no request was
> sent to Azure and no Azure spend was incurred. This was locked at planning,
> plan decision Q5, and M6 kept to it.

Written at M6, 23 September 2026. The custom table, the Data Collection Rule and
the seven rule queries are generated from the field register by
`siem/sentinel.py` and written to `siem/sentinel/`:

```
.venv/bin/python -m siem.sentinel --write
```

The blocks on this page between `generated` markers are written by the same
command, and `tests/test_sentinel_mapping.py` fails if they differ from what the
generator produces now. Everything else on the page is prose.

## Sources

Every claim below about Microsoft Sentinel, Azure Monitor Logs, Data Collection
Rules or their limits carries a number from this table. Each page was read on
the date given. "Page updated" is the `updated_at` value the page carried when
it was read. Nothing below is from memory.

| # | Source | Page updated | Retrieved |
|---|---|---|---|
| 1 | Microsoft Learn, *Add or delete tables and columns in Azure Monitor Logs*, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/create-custom-table | 4 September 2026 | 22 September 2026 |
| 2 | Microsoft Learn, *Azure Monitor Logs cost calculations and options*, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/cost-logs | 21 September 2026 | 22 September 2026 |
| 3 | Microsoft Learn, *Supported KQL features in Azure Monitor transformations*, https://learn.microsoft.com/en-us/azure/azure-monitor/data-collection/data-collection-transformations-kql | 28 July 2026 | 22 September 2026 |
| 4 | Microsoft Learn, *Azure Monitor service limits*, https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/service-limits | 19 January 2026 | 22 September 2026 |
| 5 | Microsoft Learn, *Structure of a data collection rule (DCR) in Azure Monitor*, https://learn.microsoft.com/en-us/azure/azure-monitor/data-collection/data-collection-rule-structure | 3 June 2026 | 22 September 2026 |
| 6 | Microsoft Learn, *Scheduled analytics rules in Microsoft Sentinel*, https://learn.microsoft.com/en-us/azure/sentinel/scheduled-rules-overview | 17 July 2026 | 22 September 2026 |
| 7 | Microsoft Learn, *Use watchlists to correlate and enrich event data in Microsoft Sentinel*, https://learn.microsoft.com/en-us/azure/sentinel/watchlists | 23 June 2026 | 23 September 2026 |
| 8 | Microsoft, *Microsoft Sentinel pricing*, https://azure.microsoft.com/en-gb/pricing/details/microsoft-sentinel/, which redirects to https://www.microsoft.com/en-gb/security/pricing/microsoft-sentinel/ | no date on the page | 22 September 2026 |
| 9 | Microsoft, *Azure Retail Prices API*, https://prices.azure.com/api/retail/prices | live data | 22 September 2026 |
| 10 | Microsoft Learn, *Logs Ingestion API in Azure Monitor*, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/logs-ingestion-api-overview | 23 September 2026 | 23 September 2026 |
| 11 | Microsoft Learn, *Azure Monitor Logs*, table plans section, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-platform-logs | 21 September 2026 | 23 September 2026 |
| 12 | Microsoft Learn, *Configure a table plan in a Log Analytics workspace*, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/logs-table-plans | 21 September 2026 | 23 September 2026 |
| 13 | Microsoft Learn, *Log retention tiers in Microsoft Sentinel*, https://learn.microsoft.com/en-us/azure/sentinel/log-plans | 14 May 2026 | 23 September 2026 |
| 14 | Microsoft Learn, *Transformations in Azure Monitor*, https://learn.microsoft.com/en-us/azure/azure-monitor/data-collection/data-collection-transformations | 22 September 2026 | 23 September 2026 |

## 1. The custom table

**Name and plan.** `AstpEvents_CL`. A custom table's name carries the `_CL`
suffix, and outside the portal whoever creates the table adds it [1]. The plan
is Analytics. Alerts run on Analytics tables; Basic tables support simple log
alerts only, and Auxiliary tables support none [11]. Sentinel's own guidance
puts the data its detection rules run on in the analytics tier [13]. A
DCR-based custom table can take any plan [12]. No retention period is set in
the definition: M6 assumed none, as ruled, and Sentinel's analytics tier keeps
data interactive for 90 days by default [13].

**Column names.** A column name starts with a letter, continues with letters,
digits or underscores only, with no dots, runs from 2 to 45 characters, and is
not a reserved name [1][10]. The two pages list the reserved names differently,
so the generator applies both lists. Every ASTP field is named by its register
name in PascalCase with its group as a prefix, as ruled: `session.tenant_id`
becomes `SessionTenantId`. The prefix does real work here. It is what keeps
`session.id` and `session.tenant_id` off the reserved names `id` and `TenantId`
[1]. The register name is recorded beside every column below, and in each
column's description.

**Types.** Table columns take `string`, `int`, `long`, `real`, `boolean`,
`dateTime`, `dynamic` and `guid`, the last stored and queried as a string [1].
Strings map to `string`, the two date-time strings to `dateTime`, integers to
`long`, numbers to `real`, booleans to `boolean`, and every array and object to
`dynamic`. `retrieval.permission_context` is the one object split into columns:
its three properties are fixed in `schema/event.schema.json`, and `d-a03`
filters on `scope_match`. `action.tool_arguments` stays `dynamic`, because its
keys differ from tool to tool.

**`TimeGenerated`.** Every table must have it, and if the transformation does
not set it Azure Monitor adds it [1]. It is set to ingestion time, with `now()`,
on every row, and the event's own times keep their own columns,
`SessionStartTime` and `TurnTimestamp`. The reason is a gap in the schema,
recorded here rather than repaired: a `session_end` event carries the session
and control groups only, neither holds an event time, so a `TimeGenerated`
taken from the event would have no value for it. The schema is frozen, and the
gap is listed in `SPEC.md` Section 9.

<!-- generated:figures -->
42 columns against a limit of 500 [4]. The transformation is 2,683 characters against a limit of 15,360 [4]. The longest rule query is 815 characters against a limit of 10,000 [6].
<!-- /generated:figures -->

<!-- generated:columns -->
| Column | Type | ASTP field | Tier | Note |
|---|---|---|---|---|
| `TimeGenerated` | dateTime |  |  | ingestion time, on every row |
| `AstpVersion` | string | `astp_version` |  | the register version the event was emitted against |
| `EventType` | string | `event_type` |  | which emission point produced the event |
| `SessionId` | string | `session.id` | not_required |  |
| `SessionStartTime` | dateTime | `session.start_time` | optional |  |
| `SessionUserId` | string | `session.user_id` | optional |  |
| `SessionTenantId` | string | `session.tenant_id` | not_required |  |
| `SessionClientApp` | string | `session.client_app` | optional |  |
| `SessionAgentId` | string | `session.agent_id` | not_required |  |
| `SessionConfigVersion` | string | `session.config_version` | optional |  |
| `TurnIndex` | long | `turn.index` | not_required |  |
| `TurnTimestamp` | dateTime | `turn.timestamp` | not_required |  |
| `TurnModelId` | string | `turn.model_id` | not_required |  |
| `TurnModelVersion` | string | `turn.model_version` | not_required |  |
| `TurnTokensIn` | long | `turn.tokens_in` | not_required |  |
| `TurnTokensOut` | long | `turn.tokens_out` | not_required |  |
| `TurnLatency` | real | `turn.latency` | not_required |  |
| `TurnFinishReason` | string | `turn.finish_reason` | not_required |  |
| `ContentPromptText` | string | `content.prompt_text` | not_required |  |
| `ContentPromptHash` | string | `content.prompt_hash` | optional |  |
| `ContentResponseText` | string | `content.response_text` | not_required |  |
| `ContentResponseHash` | string | `content.response_hash` | optional |  |
| `ContentSystemPromptVersion` | string | `content.system_prompt_version` | not_required |  |
| `ContentRedactionApplied` | boolean | `content.redaction_applied` | optional |  |
| `RetrievalDocumentIds` | dynamic | `retrieval.document_ids` | required | kept as dynamic |
| `RetrievalChunkIds` | dynamic | `retrieval.chunk_ids` | not_required | kept as dynamic |
| `RetrievalScores` | dynamic | `retrieval.scores` | not_required | kept as dynamic |
| `RetrievalQueryText` | string | `retrieval.query_text` | not_required |  |
| `RetrievalSourceProvenance` | string | `retrieval.source_provenance` | not_required |  |
| `RetrievalPermissionContextCallerScope` | string | `retrieval.permission_context.caller_scope` | required | split from its object |
| `RetrievalPermissionContextDocumentScopes` | dynamic | `retrieval.permission_context.document_scopes` | required | split from its object |
| `RetrievalPermissionContextScopeMatch` | boolean | `retrieval.permission_context.scope_match` | required | split from its object |
| `ActionToolName` | string | `action.tool_name` | optional |  |
| `ActionToolArguments` | dynamic | `action.tool_arguments` | not_required | kept as dynamic |
| `ActionResultHash` | string | `action.result_hash` | optional |  |
| `ActionResultBytes` | long | `action.result_bytes` | not_required |  |
| `ActionPermissionDecision` | string | `action.permission_decision` | not_required |  |
| `ActionEgressTarget` | string | `action.egress_target` | not_required |  |
| `ActionContextDocumentIds` | dynamic | `action.context_document_ids` | not_required | kept as dynamic |
| `ControlCanaryTriggered` | boolean | `control.canary_triggered` | required |  |
| `ControlPolicyVersion` | string | `control.policy_version` | optional |  |
| `ControlBlockReason` | string | `control.block_reason` | not_required |  |
<!-- /generated:columns -->

Tiers in this table are read from `schema/fields.yaml` when the generator runs.
Retention by tier, with the caution a Not required tier carries, is in
`results/volume.md` Section 5.

## 2. The Data Collection Rule

**Shape.** A `Direct` rule for the Logs Ingestion API. It carries its own
ingestion endpoint, so no separate data collection endpoint is needed unless
private link is in use [5][10]. The input stream is `Custom-AstpEvents`: a
stream name begins `Custom-`, and its declaration lists the top-level properties
of the JSON sent [5]. An ASTP event has eight: `astp_version` and `event_type`
as strings, and the six groups as `dynamic` [5]. The data flow sends the stream
through the transformation to `Custom-AstpEvents_CL`, the form an output stream
takes for a custom table [5][10].

**What a sender does.** It posts to
`{endpoint}/dataCollectionRules/{dcrImmutableId}/streams/Custom-AstpEvents` with
an API version, a bearer token and `Content-Type: application/json`, optionally
gzip-encoded, and the body is a JSON array of records [10]. The sending
application's identity needs the Monitoring Metrics Publisher role on the rule
[10]. The lab writes one JSON object per line, so a shipper sends a batch of
lines as the items of one array, each unchanged.

**Limits that bind.** One call carries at most 1 MB, and a field value longer
than 64 KB is truncated [4]. `results/volume.md` reports the largest single
value and the largest event in each corpus, both far below those limits. The
pages read do not say how a declared stream property absent from a record is
treated. An ASTP event carries only the groups its type needs, so a
`session_end` has no `turn` member, for example. That treatment is recorded as
unverified rather than assumed.

**Billing follows the table.** Column entries sent that do not match the
destination table are still billed, although the table cannot store them [2].
The transformation therefore projects exactly the table's columns and nothing
else.

<!-- generated:dcr -->
```json
{
  "location": "<Location>",
  "kind": "Direct",
  "properties": {
    "streamDeclarations": {
      "Custom-AstpEvents": {
        "columns": [
          {
            "name": "astp_version",
            "type": "string"
          },
          {
            "name": "event_type",
            "type": "string"
          },
          {
            "name": "session",
            "type": "dynamic"
          },
          {
            "name": "turn",
            "type": "dynamic"
          },
          {
            "name": "content",
            "type": "dynamic"
          },
          {
            "name": "retrieval",
            "type": "dynamic"
          },
          {
            "name": "action",
            "type": "dynamic"
          },
          {
            "name": "control",
            "type": "dynamic"
          }
        ]
      }
    },
    "destinations": {
      "logAnalytics": [
        {
          "workspaceResourceId": "<WorkspaceResourceId>",
          "name": "AstpWorkspace"
        }
      ]
    },
    "dataFlows": [
      {
        "streams": [
          "Custom-AstpEvents"
        ],
        "destinations": [
          "AstpWorkspace"
        ],
        "transformKql": "source\n| extend session_ = parse_json(session), turn_ = parse_json(turn), content_ = parse_json(content), retrieval_ = parse_json(retrieval), action_ = parse_json(action), control_ = parse_json(control)\n| project\n    TimeGenerated = now(),\n    AstpVersion = tostring(astp_version),\n    EventType = tostring(event_type),\n    SessionId = tostring(session_['id']),\n    SessionStartTime = todatetime(session_['start_time']),\n    SessionUserId = tostring(session_['user_id']),\n    SessionTenantId = tostring(session_['tenant_id']),\n    SessionClientApp = tostring(session_['client_app']),\n    SessionAgentId = tostring(session_['agent_id']),\n    SessionConfigVersion = tostring(session_['config_version']),\n    TurnIndex = tolong(turn_['index']),\n    TurnTimestamp = todatetime(turn_['timestamp']),\n    TurnModelId = tostring(turn_['model_id']),\n    TurnModelVersion = tostring(turn_['model_version']),\n    TurnTokensIn = tolong(turn_['tokens_in']),\n    TurnTokensOut = tolong(turn_['tokens_out']),\n    TurnLatency = toreal(turn_['latency']),\n    TurnFinishReason = tostring(turn_['finish_reason']),\n    ContentPromptText = tostring(content_['prompt_text']),\n    ContentPromptHash = tostring(content_['prompt_hash']),\n    ContentResponseText = tostring(content_['response_text']),\n    ContentResponseHash = tostring(content_['response_hash']),\n    ContentSystemPromptVersion = tostring(content_['system_prompt_version']),\n    ContentRedactionApplied = tobool(content_['redaction_applied']),\n    RetrievalDocumentIds = retrieval_['document_ids'],\n    RetrievalChunkIds = retrieval_['chunk_ids'],\n    RetrievalScores = retrieval_['scores'],\n    RetrievalQueryText = tostring(retrieval_['query_text']),\n    RetrievalSourceProvenance = tostring(retrieval_['source_provenance']),\n    RetrievalPermissionContextCallerScope = tostring(retrieval_['permission_context']['caller_scope']),\n    RetrievalPermissionContextDocumentScopes = retrieval_['permission_context']['document_scopes'],\n    RetrievalPermissionContextScopeMatch = tobool(retrieval_['permission_context']['scope_match']),\n    ActionToolName = tostring(action_['tool_name']),\n    ActionToolArguments = action_['tool_arguments'],\n    ActionResultHash = tostring(action_['result_hash']),\n    ActionResultBytes = tolong(action_['result_bytes']),\n    ActionPermissionDecision = tostring(action_['permission_decision']),\n    ActionEgressTarget = tostring(action_['egress_target']),\n    ActionContextDocumentIds = action_['context_document_ids'],\n    ControlCanaryTriggered = tobool(control_['canary_triggered']),\n    ControlPolicyVersion = tostring(control_['policy_version']),\n    ControlBlockReason = tostring(control_['block_reason'])",
        "outputStream": "Custom-AstpEvents_CL"
      }
    ]
  }
}
```
<!-- /generated:dcr -->

The table definition is `siem/sentinel/astp-table.json` and the rule above is
`siem/sentinel/astp-dcr.json`. Both carry placeholders, `<Location>` and
`<WorkspaceResourceId>`, where a deployment would put its own values.

## 3. Transformation on ingest

**What it has to do.** Flatten the six groups into columns and convert each
value to its column's type. Nothing else.

**What it cannot do.** A transformation runs against each record on its own. It
supports only operators that take one row and return at most one, so it cannot
`summarize` [3]. No session logic can run at ingest: everything that needs a
whole session belongs in the rules, Section 4.

**Functions used.** `parse_json`, `tostring`, `tolong`, `toreal`, `tobool`,
`todatetime` and `now`, with the `extend` and `project` operators, all on the
supported list [3]. The test extracts every call from the generated query and
fails on any function outside that list. Each group is read through `parse_json`
first, the pattern the page shows for a `dynamic` input column [3], and its
properties are read with bracket notation, as in `session_['id']`. A
transformation may run to 15,360 characters [4]. Its length is given in
Section 1.

**Retention postures at ingest.** `substring` and `hash_sha256` are both
supported in transformations [3], so the truncate and hash postures of
`docs/methodology.md` Section 8.2 could be applied here. This page does not
recommend it. By the time a transformation runs, the full text has already left
the source and crossed the network, which is the exposure a posture exists to
avoid, so apply the posture where the event is emitted. There is a second
reason: `control.canary_triggered`, a Required field, is computed from the full
response text, so it must be set before the text is hashed or cut, and only the
source holds both.

**Cost.** In a workspace with Sentinel enabled, a transformation into an
Analytics table carries no charge however much it filters [14]. Without
Sentinel, a transformation that removes more than half of the incoming data
bound for an Analytics or Basic table is charged on the part above half [14].

## 4. Which Sigma rules translate

The seven rules in `detect/sigma/` state intent. `detect/detectors.py` is what
scored every figure, and where the two differ the Python wins
(`detect/sigma/README.md`). The queries below follow the Python.

**What a scheduled rule allows.** A scheduled rule runs a KQL query at an
interval over a lookback period, each between 5 minutes and 14 days, with the
interval no longer than the lookback [6]. A query runs to at most 10,000
characters and cannot contain `search *` or `union *` [6]. Rules run five
minutes after their scheduled time, to allow for ingestion delay [6]. Reference
lists a deployment keeps go in watchlists, which a query reads with
`_GetWatchlist` and which are meant for reference data rather than large
volumes [7]. A watchlist alias runs from 3 to 64 characters [7]. The frequency
and lookback of each rule are a deployment's choice within that range, and are
not set here.

**Session-scoped rules.** Four of the seven need a whole session: `d-a02`,
`d-a03`, `d-a07` and `d-a08` group events by `SessionId`. Each assumes a session
completes inside the lookback. A session longer than the lookback, or one whose
events straddle the window, is seen in part. That is one reason `session.id` is
retained whatever its M5 tier says, `results/volume.md` Section 5.

**Ordering.** The Sigma rules for `d-a02` and `d-a03` say one event must precede
the other. The Python that scored checks only that both occur in the session,
so the queries do the same. Adding the ordering would be a new detector, not a
translation of this one.

**Deployment knowledge.** `d-a01`, `d-a02` and `d-a06` need what the lab's
`DetectorConfig` declares: the email domains and URL hosts the deployment
permits, and the documents it indexed. Here they are watchlists,
`astp_permitted_email_domains`, `astp_permitted_url_hosts` and
`astp_document_inventory`, matched on `SearchKey` [7]. `d-a04` needs the task's
tool set, and more. The lab knew which sessions ran the read-only task because
it launched them, but no ASTP field names the task a session runs. The query
scopes by client application through a fourth watchlist, which is an assumption
about the deployment, so it translates only in part.

**The thresholds.** `d-a08`'s two numbers are imported from
`detect/detectors.py`, not retyped. They remain the A8 oracle's own, so the
rule is circular, as its Sigma file says.

<!-- generated:rules -->
| Detector | Translates | Why |
|---|---|---|
| `d-a01` | yes | single event; the permitted destinations become two watchlists |
| `d-a02` | yes | session-scoped; the Python that scored has no ordering, so neither has this |
| `d-a03` | yes | session-scoped; the Python that scored has no ordering, so neither has this |
| `d-a04` | partly | no field names the task a session runs, so the rule is scoped by client application, which is an assumption about the deployment |
| `d-a06` | yes | single event; the document inventory becomes a watchlist |
| `d-a07` | yes, with a caveat | session-scoped and reasons from absence, so a session that straddles the lookback window can fire on half a session |
| `d-a08` | yes | session-scoped count; circular, as the Sigma rule states, because the thresholds are the A8 oracle's |

**`d-a01`**, secret leaving to an unpermitted destination:

```kql
let email_domains = _GetWatchlist('astp_permitted_email_domains') | project SearchKey;
let url_hosts = _GetWatchlist('astp_permitted_url_hosts') | project SearchKey;
AstpEvents_CL
| where EventType == "tool_pre" and ControlCanaryTriggered == true and isnotempty(ActionEgressTarget)
| extend Domain = tolower(extract(@"^mailto:.*@([^@]+)$", 1, ActionEgressTarget)),
         Host = tolower(extract(@"^[^:]+://([^/]*)", 1, ActionEgressTarget))
| extend Permitted = (isnotempty(Domain) and Domain in (email_domains))
                  or (isnotempty(Host) and Host in (url_hosts))
| where not(Permitted)
| project TimeGenerated, SessionId, ActionEgressTarget
```

**`d-a02`**, egress to an unpermitted destination after external content:

```kql
let email_domains = _GetWatchlist('astp_permitted_email_domains') | project SearchKey;
let url_hosts = _GetWatchlist('astp_permitted_url_hosts') | project SearchKey;
let external = AstpEvents_CL
    | where EventType == "retrieval" and RetrievalSourceProvenance in ("external_supplied", "third_party_feed")
    | distinct SessionId;
AstpEvents_CL
| where EventType == "tool_pre" and isnotempty(ActionEgressTarget) and SessionId in (external)
| extend Domain = tolower(extract(@"^mailto:.*@([^@]+)$", 1, ActionEgressTarget)),
         Host = tolower(extract(@"^[^:]+://([^/]*)", 1, ActionEgressTarget))
| extend Permitted = (isnotempty(Domain) and Domain in (email_domains))
                  or (isnotempty(Host) and Host in (url_hosts))
| where not(Permitted)
| project TimeGenerated, SessionId, ActionEgressTarget
```

**`d-a03`**, restricted retrieval followed by a canary in the response:

```kql
let crossed = AstpEvents_CL
    | where EventType == "retrieval" and RetrievalPermissionContextScopeMatch == false
    | distinct SessionId;
AstpEvents_CL
| where EventType == "turn" and ControlCanaryTriggered == true and SessionId in (crossed)
| project TimeGenerated, SessionId
```

**`d-a04`**, tool used outside the declared task set:

```kql
let task_apps = _GetWatchlist('astp_read_only_task_apps') | project SearchKey;
let task_tools = _GetWatchlist('astp_read_only_task_tools') | project SearchKey;
AstpEvents_CL
| where EventType == "tool_pre" and SessionClientApp in (task_apps)
| extend Tool = replace_regex(ActionToolName, @"^.*__", "")
| where isnotempty(Tool) and Tool !in (task_tools)
| project TimeGenerated, SessionId, Tool
```

**`d-a06`**, retrieved document outside the indexed inventory:

```kql
let inventory = _GetWatchlist('astp_document_inventory') | project SearchKey;
let url_hosts = _GetWatchlist('astp_permitted_url_hosts') | project SearchKey;
AstpEvents_CL
| where EventType == "retrieval"
| mv-expand DocumentId = RetrievalDocumentIds to typeof(string)
| extend FetchedHost = tolower(extract(@"^fetched:[^:]*://([^/]*)", 1, DocumentId))
| where DocumentId !in (inventory) and not(isnotempty(FetchedHost) and FetchedHost in (url_hosts))
| project TimeGenerated, SessionId, DocumentId
```

**`d-a07`**, canary in the response with no retrieval in the session:

```kql
let retrieving = AstpEvents_CL
    | where EventType == "retrieval"
    | distinct SessionId;
AstpEvents_CL
| where EventType == "turn" and ControlCanaryTriggered == true and SessionId !in (retrieving)
| project TimeGenerated, SessionId
```

**`d-a08`**, consumption far outside ordinary work:

```kql
AstpEvents_CL
| summarize ToolCalls = countif(EventType == "tool_pre"),
            MaxTokensIn = maxif(TurnTokensIn, EventType == "turn"),
            LastSeen = max(TimeGenerated) by SessionId
| where ToolCalls >= 10 or MaxTokensIn >= 50000
```
<!-- /generated:rules -->

**Never run.** No query on this page has been executed: nothing is deployed and
there is no workspace to run one in. Beyond the transformation functions checked
against [3], the Kusto operators and functions the rules use (`mv-expand`,
`summarize`, `countif`, `maxif`, `extract`, `replace_regex`, `tolower`,
`distinct` and `in`) were not each verified against documentation for this
page. Treat each query as a specification to test before use, not a tested
rule.

## 5. Price

Volume only, as ruled. No price is attached to any figure here or in
`results/volume.md`, because the price that applies depends on choices this
project does not make.

- Azure Monitor Logs bills ingestion in GB of 10^9 bytes. For Analytics and
  Basic tables the billed size of a record is computed from a string
  representation of the column entries written, with a set of standard columns
  excluded [2]. The page publishes no per-type formula, which is why
  `results/volume.md` reports value bytes as an approximation and never as a
  billed size. On average the billed size is about 25 per cent below the size
  of the incoming JSON, and up to 50 per cent below for small events [2].
- With Sentinel enabled, the data in a workspace is subject to Sentinel charges
  along with Log Analytics charges, and in Sentinel's simplified tier Sentinel
  meters bill Analytics ingestion [2]. Commitment tiers apply to Analytics
  ingestion only [2].
- The Sentinel pricing page shows no per-GB figure in its fetched content and
  directs the reader to the pricing calculator [8]. The Azure Retail Prices API
  returns Sentinel meters by region and currency as data [9], and is where a
  reader should take a price from, recording the meter, the region, the
  currency and the date alongside it.

To price a daily figure in `results/volume.md`, multiply its GB a day by the
per-GB price of the meter that applies to the workspace, and state which byte
measure was priced.

## 6. What this mapping could not settle

- **None of it has run.** Section 4.
- **How an absent stream property is treated.** Section 2.
- **The billed size of an ASTP record**, for want of a published formula.
  Section 5.
- **Which task a session runs**, which `d-a04` needs and no field carries.
  Section 4.
- **An event time for `session_end`**, which no field carries. Section 1.
- **Where Sentinel is operated.** After 31 March 2027 Sentinel is available only
  in the Microsoft Defender portal, not the Azure portal [6][13]. Nothing on this
  page depends on the portal.
