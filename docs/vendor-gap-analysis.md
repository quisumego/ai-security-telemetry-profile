# Vendor gap analysis

> **Documentation only.** No Azure or AWS resource was created, no console was
> signed in to, nothing was sent to either vendor beyond reading public
> documentation pages, and no model call was made. Every claim below about a
> vendor is cited to a numbered page read on 23 September 2026.

Written at M7, 23 September 2026. This page assesses what Microsoft Foundry and
Amazon Bedrock record against the ASTP field register, then answers the
question the plan asks: **with vendor defaults only, which of the ten attack
classes stay detectable?** The plan names the first product "Azure AI
Foundry"; its pages now title it Microsoft Foundry [1], and that is the name
used here.

The verdicts live in `vendor_gap/evidence.yaml`, each carrying the numbers of
the pages it rests on. The class answers are computed from the captures by
`vendor_gap/analysis.py`, which writes `results/vendor-gap.json` and the blocks
on this page between `generated` markers:

```
.venv/bin/python -m vendor_gap.analysis --write
```

`tests/test_vendor_gap.py` fails if a generated block, or the results file,
differs from what the generator produces now, and holds every verdict to a
listed source. The rulings applied are `vendor_gap/rulings.py`, committed
before the evidence or the code existed.

**Evidence rule for this file.** Every claim about vendor behaviour is cited to
vendor documentation with a retrieval date. No claim about what a vendor logs is
made from memory. If a capability cannot be confirmed from documentation, it is
recorded as unconfirmed rather than assumed either way. Absence is a claim too:
a field is recorded absent only where a cited page gives the record's full field
list, or where the vendor cannot produce the value because only the deployment
holds it.

## The answer

<!-- generated:headline -->
- **Azure, model layer on:** A5 `X`, A6 `X`, A7 `X`, A8 `uc`, A9 `X`.
- **AWS, model layer on:** A5 `X`, A6 `X`, A7 `X`, A8 `uc`, A9 `X`.

**No class stays detectable on any single surface of either vendor**, as shipped or switched on, with or without the bodies parsed.
Across the ten single-surface columns: A5, A6, A7, A9 read `X`; A8 reads `Xc`, `uc`.

**Security-only fields a vendor column counts as available: 0 of 7.** On all six surfaces every one reads absent, in the form caller supplied or derivable.
<!-- /generated:headline -->

`X` means the class becomes undetectable, `uc` that the answer depends on
something the pages do not settle, and a `c` suffix marks A8's circular column,
as in `results/necessity-matrix.md`. A8 is unconfirmed on the model layers
because every A8 trial has a single turn whose input token count crosses the A8
threshold, so `d-a08` survives the loss of tool-call records if the vendor's
input token count means what the register's does. Bedrock's pages do not say
whether its input token count includes cached tokens, which the register counts
[15], and Azure's document no per-call token field at all [2][4]. On both agent
layers no model call is recorded by default, and A8 becomes undetectable.

**The question can be answered for five classes only, and for two of them on a
single session.** A1 to A4 have no successful trial, so their detection is not
computable, and A10 is absent from the corpus; they read `nt` and `ab` in every
column. A5 and A7 each rest on one successful trial. A8's detector uses the A8
oracle's own thresholds, so its baseline measures nothing independent. A5 and A9
are the holdouts, and the A9 baseline of 10 of 10 carries its exposure: the
session that built the detectors knew both holdout outcomes, the handover at M4
disclosed A9's retrieval signature, the detectors were authored from fixtures
only, and the result is weakened evidence, not a clean holdout.

## How the lab is placed on a vendor

The lab agent runs on the Claude Agent SDK against Anthropic's API, not on
either vendor. The question is therefore hypothetical. On the **model layer**,
had the same agent's model calls gone through the vendor, what would the
vendor's own records carry? On the **agent layer**, had the same agent been
hosted by the vendor, with its code and its tools unchanged? In the lab, tools
and retrieval run in the application, so a vendor sees a tool call or a
retrieved document only as far as it passes through a model request or
response, or through a record the deployment supplies itself.

Three readings are computed for each vendor, as ruled:

- **As shipped**, the literal reading: what is collected with no action at all.
- **Switched on**, the headline: each surface once its own switch is set, and
  nothing more. The switch is read as the vendor's own enabling procedure,
  including the selections that procedure makes. For AWS that procedure has the
  reader choose modalities [15], and Text is taken because the lab's traffic is
  text only. Read the other way, with Text as a further setting, seven fields
  and three event types move from available by default to available with
  configuration, and no class answer changes; a test repeats that check.
- **Body parsed**: the switched-on reading, also counting a value inside a
  request or response body at a documented path. A value present only as
  content the application wrote never counts, and nor does a value the
  deployment supplies or derives itself.

## Sources

Every page was read on the date given, from its own text. "Page updated" is the
`updated_at` value a Microsoft page carried when read; no AWS page carries a
date. Where a page redirected, both addresses are recorded.

<!-- generated:sources -->
| # | Source | Page updated | Retrieved |
|---|---|---|---|
| 1 | Microsoft Learn, *Enable diagnostic logging for Microsoft Foundry*, https://learn.microsoft.com/en-us/azure/foundry/how-to/diagnostic-logging | 26 June 2026 | 23 September 2026 |
| 2 | Microsoft Learn, *Monitoring data reference for Azure OpenAI*, https://learn.microsoft.com/en-us/azure/foundry/openai/monitor-openai-reference | 19 May 2026 | 23 September 2026 |
| 3 | Microsoft Learn, *Diagnostic Settings in Azure Monitor*, https://learn.microsoft.com/en-us/azure/azure-monitor/data-collection/diagnostic-settings, requested at https://learn.microsoft.com/en-us/azure/azure-monitor/platform/diagnostic-settings | 22 September 2026 | 23 September 2026 |
| 4 | Microsoft Learn, *Azure resource logs supported services and schemas*, https://learn.microsoft.com/en-us/azure/azure-monitor/logs/resource-logs-schema, requested at https://learn.microsoft.com/en-us/azure/azure-monitor/platform/resource-logs-schema | 22 September 2026 | 23 September 2026 |
| 5 | Microsoft Learn, *Monitor Azure OpenAI in Microsoft Foundry Models (classic)*, https://learn.microsoft.com/en-us/azure/foundry-classic/openai/how-to/monitor-openai (a classic page, used because source 2 links to it, as ruling 18 allows) | 12 May 2026 | 23 September 2026 |
| 6 | Microsoft Learn, *Activity Log in Azure Monitor*, https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/activity-log, requested at https://learn.microsoft.com/en-us/azure/azure-monitor/platform/activity-log | 22 September 2026 | 23 September 2026 |
| 7 | Microsoft Learn, *Azure Activity Log event schema*, https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/activity-log-schema, requested at https://learn.microsoft.com/en-us/azure/azure-monitor/platform/activity-log-schema | 22 September 2026 | 23 September 2026 |
| 8 | Microsoft Learn, *Agent tracing overview*, https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-agent-concept | 28 August 2026 | 23 September 2026 |
| 9 | Microsoft Learn, *Microsoft Foundry Tracing and Data Handling*, https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-data | 26 June 2026 | 23 September 2026 |
| 10 | Microsoft Learn, *Set Up Tracing for AI Agents in Microsoft Foundry*, https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/trace-agent-setup | 7 September 2026 | 23 September 2026 |
| 11 | Microsoft Learn, *Export hosted agent telemetry by using OpenTelemetry*, https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/configure-hosted-agent-telemetry | 13 August 2026 | 23 September 2026 |
| 12 | Microsoft Learn, *Quickstart: Trace your hosted agent*, https://learn.microsoft.com/en-us/azure/foundry/observability/quickstarts/quickstart-tracing-hosted-agent | 5 August 2026 | 23 September 2026 |
| 13 | Microsoft Learn, *Monitoring data reference for Foundry Agent Service (classic)*, https://learn.microsoft.com/en-us/azure/foundry-classic/agents/reference/monitor-service, requested at https://learn.microsoft.com/en-us/azure/ai-foundry/agents/reference/monitor-service (a classic page, used because the current address redirects to it, as ruling 18 allows) | 14 April 2026 | 23 September 2026 |
| 14 | Microsoft Learn, Foundry Tools, *Enable diagnostic logging*, https://learn.microsoft.com/en-us/azure/ai-services/diagnostic-logging (the page source 4 links as the schema for Foundry Tools; it carries no schema) | 5 June 2026 | 23 September 2026 |
| 15 | Amazon Bedrock User Guide, *Monitor model invocation using CloudWatch Logs and Amazon S3*, https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html | no date on the page | 23 September 2026 |
| 16 | Amazon Bedrock User Guide, *Per-request metadata tagging*, https://docs.aws.amazon.com/bedrock/latest/userguide/cost-mgmt-request-metadata.html | no date on the page | 23 September 2026 |
| 17 | Amazon Bedrock API Reference, *Converse*, https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html | no date on the page | 23 September 2026 |
| 18 | Amazon Bedrock User Guide, *Monitor the bedrock-runtime endpoint*, https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring.html | no date on the page | 23 September 2026 |
| 19 | Amazon Bedrock User Guide, *Monitor the bedrock-mantle endpoint*, https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-mantle.html | no date on the page | 23 September 2026 |
| 20 | Amazon Bedrock User Guide, *Monitor Amazon Bedrock features*, https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-features.html | no date on the page | 23 September 2026 |
| 21 | Amazon Bedrock User Guide, *Monitor Amazon Bedrock API calls using CloudTrail*, https://docs.aws.amazon.com/bedrock/latest/userguide/logging-using-cloudtrail.html | no date on the page | 23 September 2026 |
| 22 | AWS CloudTrail User Guide, *CloudTrail record contents for management, data, and network activity events*, https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html | no date on the page | 23 September 2026 |
| 23 | Amazon Bedrock User Guide, *Monitor bedrock-runtime inference using CloudWatch metrics*, https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-runtime-metrics.html | no date on the page | 23 September 2026 |
| 24 | Amazon Bedrock User Guide, *Monitor knowledge bases using CloudWatch Logs*, https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-bases-logging.html | no date on the page | 23 September 2026 |
| 25 | Amazon Bedrock AgentCore Developer Guide, *Observe your agent applications on Amazon Bedrock AgentCore Observability*, https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html | no date on the page | 23 September 2026 |
| 26 | Amazon Bedrock AgentCore Developer Guide, *Amazon Bedrock AgentCore generated observability data*, https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-service-provided.html | no date on the page | 23 September 2026 |
| 27 | Amazon Bedrock AgentCore Developer Guide, *AgentCore generated runtime observability data*, https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-runtime-metrics.html | no date on the page | 23 September 2026 |
| 28 | Amazon Bedrock AgentCore Developer Guide, *Add observability to your Amazon Bedrock AgentCore resources*, https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html | no date on the page | 23 September 2026 |
<!-- /generated:sources -->

## 1. The surfaces

<!-- generated:surfaces -->
| Vendor | Layer | Surface | Switch | What it records |
|---|---|---|---|---|
| Azure | as shipped | Activity log and platform metrics | none; both are collected with no action [3] | Activity log entries for management operations performed through Resource Manager, and platform metrics as numeric series split by dimensions such as the model deployment and model name. Agent metrics, including tool calls split by tool name, are series too. [6][7][2][13] |
| Azure | model | Foundry resource logs through a diagnostic setting | create a diagnostic setting on the Foundry resource with the categories the how-to lists: Audit Logs, Request and Response Logs and Azure OpenAI Request Usage [1][3] | Records in the AzureDiagnostics table by category: Audit, AzureOpenAIRequestUsage, ManagedNetworkEvent, RequestResponse and Trace. Each carries the header fields common to all resource logs; anything specific to the service sits in properties, which no page read documents for these categories. [2][4][5][14] |
| Azure | agent | Foundry agent tracing for a hosted agent, in Application Insights | connect an Application Insights resource to the Foundry project [10][9] | A server-side trace for each agent invocation, from the hosting protocol runtime. Spans for model calls, tool calls and retrieval come from the agent's own code, instrumented out of the box only for Microsoft Agent Framework and LangChain. The lab uses the Claude Agent SDK, which is neither. [11][12][10] |
| AWS | as shipped | CloudTrail management events and CloudWatch runtime metrics | none; CloudTrail is on when the account is created and logs management events by default [21][23] | One CloudTrail management event per InvokeModel, InvokeModelWithResponseStream, Converse or ConverseStream call, and runtime metrics published under the AWS/Bedrock namespace, split by model identifier. [21][22][23] |
| AWS | model | Model invocation logging to CloudWatch Logs or Amazon S3 | enable model invocation logging with a destination, selecting the Text modality, which is the lab's only modality [15] | One ModelInvocationLog record per Converse, ConverseStream, InvokeModel or InvokeModelWithResponseStream call on the bedrock-runtime endpoint, with the request and response bodies inline up to 100 KB. Calls through the bedrock-mantle endpoint are not captured. Knowledge bases, Guardrails and Agents are monitored as features apart from the endpoint, and knowledge base logs cover ingestion jobs; none is assessed here. [15][18][19][20][24] |
| AWS | agent | AgentCore Observability for an agent hosted in AgentCore Runtime | enable observability on the agent resource, after the one-time CloudWatch Transaction Search setup for the account [27][28][26] | For each agent invocation, one InvokeAgentRuntime span and one APPLICATION_LOGS record, plus USAGE_LOGS records of resource consumption. Spans for the model calls, tool calls and retrieval inside the agent come only from instrumentation the deployment adds to its own code. Source 26 marks agent spans and logs as needing explicit enablement, while source 28 says the runtime creates a log group by default; both are recorded. [27][26][25][28] |
<!-- /generated:surfaces -->

Both plan-named surfaces are off as shipped. Azure resource logs "Aren't
collected by default" [3], and "Model invocation logging is disabled by
default" [15]. Foundry tracing is off by default [9]. What each vendor collects
with no action is the activity log and platform metrics on Azure [3], and
CloudTrail management events and CloudWatch runtime metrics on AWS [21][23]. A
metric is a series split by dimension, not a record of one call, so it can carry
no per-event value.

## 2. Field by field

**How to read a cell.** `D` available by default, `C` available with
configuration, `A` absent, `U` unconfirmed, followed by the source numbers. A
form follows the verdict where the value is not a field of its own: `body`,
inside a request or response body, with `*` where no page documents its path in
the logged body; `content`, present only as content the application wrote;
`caller`, held only by the deployment or supplied by it; `derived`, derivable
by the deployment from what the vendor logs and what it knows itself. `partial`
marks a vendor field whose documented meaning differs from the register's; the
difference is stated in the evidence file. Tiers are read from
`schema/fields.yaml` when the generator runs.

**Counts over the 37 fields**, and over the seven security-only fields in the
same verdict order:

<!-- generated:counts -->
| Surface | available by default | available with configuration | absent | unconfirmed | Security-only fields, in the same order |
|---|---|---|---|---|---|
| Activity log and platform metrics | 0 | 0 | 22 | 15 | 0, 0, 7, 0 |
| Foundry resource logs through a diagnostic setting | 1 | 0 | 21 | 15 | 0, 0, 7, 0 |
| Foundry agent tracing for a hosted agent, in Application Insights | 0 | 0 | 31 | 6 | 0, 0, 7, 0 |
| CloudTrail management events and CloudWatch runtime metrics | 3 | 0 | 22 | 12 | 0, 0, 7, 0 |
| Model invocation logging to CloudWatch Logs or Amazon S3 | 12 | 0 | 22 | 3 | 0, 0, 7, 0 |
| AgentCore Observability for an agent hosted in AgentCore Runtime | 4 | 0 | 33 | 0 | 0, 0, 7, 0 |
<!-- /generated:counts -->

Nothing is available with configuration on any surface. Every documented
setting found is either a surface's own switch, counted in the headline, or a
value the deployment would have to supply, which ruling 7 records as absent
under vendor defaults. The two model layers differ most in what they document:
Bedrock's invocation log lists its record's fields in full [15], while Azure
documents the header shared by every resource log [4][5] and nothing of the
service-specific properties, so most Azure verdicts are unconfirmed rather than
absent.

### Azure

<!-- generated:fields-azure -->
| Field | Tier | Security only | As shipped | Model layer | Agent layer |
|---|---|---|---|---|---|
| `session.id` | not_required |  | A caller [7] | U partial [4] | U [11][12][8] |
| `session.start_time` | optional |  | A derived [7] | A derived [4] | U [11][12] |
| `session.user_id` | optional |  | U partial [6][7] | U partial [4] | U [11][12] |
| `session.tenant_id` | not_required |  | A caller [7] | A caller [4] | A caller [11] |
| `session.client_app` | optional |  | A caller [7] | A caller [4] | A caller [11] |
| `session.agent_id` | not_required |  | A caller [7] | A caller [4] | U [11] |
| `session.config_version` | optional |  | A caller [7] | A caller [4] | A caller [11] |
| `turn.index` | not_required |  | A derived [7] | A derived [4] | A caller [11][12] |
| `turn.timestamp` | not_required |  | U [6][7] | D [4] | A caller [11][12] |
| `turn.model_id` | not_required |  | U [6][7][2] | U [4][2] | A caller [11][12] |
| `turn.model_version` | not_required |  | U [6][7][2] | U [4][2] | A caller [11][12] |
| `turn.tokens_in` | not_required |  | U [2][7] | U [4][2] | A caller [11][12] |
| `turn.tokens_out` | not_required |  | U [2][7] | U [4][2] | A caller [11][12] |
| `turn.latency` | not_required |  | U [2][7] | U partial [4][1] | A caller [11][12] |
| `turn.finish_reason` | not_required |  | U [7] | U [4][2] | A caller [11][12] |
| `content.prompt_text` | not_required |  | U [7] | U [4][2][5] | U [12][11] |
| `content.prompt_hash` | optional |  | A derived [7] | A derived [4] | A derived [11] |
| `content.response_text` | not_required |  | U [7] | U [4][2][5] | U [12][11] |
| `content.response_hash` | optional |  | A derived [7] | A derived [4] | A derived [11] |
| `content.system_prompt_version` | not_required |  | A caller [7] | A caller [4] | A caller [11] |
| `content.redaction_applied` | optional |  | A caller [7] | A caller [4] | A caller [11] |
| `retrieval.document_ids` | required |  | U content [7] | U content [4][2] | A caller [11][12] |
| `retrieval.chunk_ids` | not_required |  | U content [7] | U content [4][2] | A caller [11][12] |
| `retrieval.scores` | not_required |  | A caller [7] | A caller [4] | A caller [11][12] |
| `retrieval.query_text` | not_required |  | U [7] | U [4][2] | A caller [11][12] |
| `retrieval.source_provenance` | not_required | yes | A derived [7] | A derived [4] | A derived [11] |
| `retrieval.permission_context` | required | yes | A derived [7] | A derived [4] | A derived [11] |
| `action.tool_name` | optional |  | U [7] | U [4][2] | A caller [11][12] |
| `action.tool_arguments` | not_required |  | U [7] | U [4][2] | A caller [11][12] |
| `action.result_hash` | optional |  | A derived [7] | A derived [4] | A derived [11] |
| `action.result_bytes` | not_required |  | A derived [7] | A derived [4] | A derived [11] |
| `action.permission_decision` | not_required | yes | A caller [7] | A caller [4] | A caller [11] |
| `action.egress_target` | not_required | yes | A derived [7] | A derived [4] | A derived [11] |
| `action.context_document_ids` | not_required | yes | A derived [7] | A derived [4] | A derived [11] |
| `control.canary_triggered` | required | yes | A derived [7] | A derived [4] | A derived [11] |
| `control.policy_version` | optional |  | A caller [7] | A caller [4] | A caller [11] |
| `control.block_reason` | not_required | yes | A caller [7] | A caller [4] | A caller [11] |

| Event type | As shipped | Model layer | Agent layer |
|---|---|---|---|
| `session_start` | A [6][7] | A [2][1] | D partial [12][10] |
| `turn` | U [6][7] | D partial [1][2] | A caller [11][12] |
| `retrieval` | A [6][7] | A [2][1] | A caller [11][12] |
| `tool_pre` | A [6][7] | A [2][1] | A caller [11][12] |
| `tool_post` | A [6][7] | A [2][1] | A caller [11][12] |
| `session_end` | A [6][7] | A [2][1] | D partial [12][10] |
<!-- /generated:fields-azure -->

### AWS

<!-- generated:fields-aws -->
| Field | Tier | Security only | As shipped | Model layer | Agent layer |
|---|---|---|---|---|---|
| `session.id` | not_required |  | A caller [21][16] | A caller [15][16] | D [27] |
| `session.start_time` | optional |  | A derived [22] | A derived [15] | A derived [27] |
| `session.user_id` | optional |  | D partial [21][22] | D partial [15] | A caller [27] |
| `session.tenant_id` | not_required |  | A caller [22] | A caller [15][16] | A caller [27] |
| `session.client_app` | optional |  | A caller [22] | A caller [16] | A caller [27] |
| `session.agent_id` | not_required |  | A caller [22] | A caller [15][16] | D [27] |
| `session.config_version` | optional |  | A caller [22] | A caller [15][16] | A caller [27] |
| `turn.index` | not_required |  | A derived [22] | A derived [15] | A caller [27][25] |
| `turn.timestamp` | not_required |  | D [22][21] | D [15] | A caller [27][25] |
| `turn.model_id` | not_required |  | D [21][17] | D partial [15] | A caller [27][25] |
| `turn.model_version` | not_required |  | U [21][22] | U [15] | A caller [27][25] |
| `turn.tokens_in` | not_required |  | U [21][22][23] | D partial [15] | A caller [27][25] |
| `turn.tokens_out` | not_required |  | U [21][22][23] | D [15] | A caller [27][25] |
| `turn.latency` | not_required |  | U [22][23] | U [15][17] | A caller [27] |
| `turn.finish_reason` | not_required |  | U [21][22] | U [15][17] | A caller [27][25] |
| `content.prompt_text` | not_required |  | U [22][21] | D body* [15] | D content partial [27] |
| `content.prompt_hash` | optional |  | A derived [22] | A derived [15] | A derived [27] |
| `content.response_text` | not_required |  | U [22][21] | D body* [15] | D content partial [27] |
| `content.response_hash` | optional |  | A derived [22] | A derived [15] | A derived [27] |
| `content.system_prompt_version` | not_required |  | A caller [22] | A caller [15][16] | A caller [27] |
| `content.redaction_applied` | optional |  | A caller [22] | A caller [15][16] | A caller [27] |
| `retrieval.document_ids` | required |  | U content [22][21] | D content [15] | A caller [27][25] |
| `retrieval.chunk_ids` | not_required |  | U content [22][21] | D content [15] | A caller [27][25] |
| `retrieval.scores` | not_required |  | A caller [22] | A caller [15] | A caller [27][25] |
| `retrieval.query_text` | not_required |  | U [22][21] | D body* [15][17] | A caller [27][25] |
| `retrieval.source_provenance` | not_required | yes | A derived [22] | A derived [15] | A derived [27] |
| `retrieval.permission_context` | required | yes | A derived [22] | A derived [15] | A derived [27] |
| `action.tool_name` | optional |  | U [22][21] | D body* [15][17] | A caller [27][25][26] |
| `action.tool_arguments` | not_required |  | U [22][21] | D body* [15][17] | A caller [27][25][26] |
| `action.result_hash` | optional |  | A derived [22] | A derived [15] | A derived [27] |
| `action.result_bytes` | not_required |  | A derived [22] | A derived [15] | A derived [27] |
| `action.permission_decision` | not_required | yes | A caller [22] | A caller [15][16] | A caller [27] |
| `action.egress_target` | not_required | yes | A derived [22] | A derived [15] | A derived [27] |
| `action.context_document_ids` | not_required | yes | A derived [22] | A derived [15] | A derived [27] |
| `control.canary_triggered` | required | yes | A derived [22] | A derived [15] | A derived [27] |
| `control.policy_version` | optional |  | A caller [22] | A caller [15][16] | A caller [27] |
| `control.block_reason` | not_required | yes | A caller [22] | A caller [15][17] | A caller [27] |

| Event type | As shipped | Model layer | Agent layer |
|---|---|---|---|
| `session_start` | A [21][22] | A [15] | D partial [27] |
| `turn` | D [21] | D [15] | A caller [27][25][28] |
| `retrieval` | A [21][22] | D content [15] | A caller [27][25][28] |
| `tool_pre` | A [21][22] | D body* [15][17] | A caller [27][25][28] |
| `tool_post` | A [21][22] | D body* [15][17] | A caller [27][25][28] |
| `session_end` | A [21][22] | A [15] | D partial [27] |
<!-- /generated:fields-aws -->

### The rows that decide the class answers

The fields and records that the counted detectors of A5 to A9 read or need,
with the reason for each verdict.

<!-- generated:decisive-azure -->
**Activity log and platform metrics.**

- `retrieval.document_ids`: unconfirmed, only as content the application wrote. Identifiers reach the vendor only inside tool results the application writes, and whether a model call is recorded at all is not settled. [7]
- `retrieval` events: absent, as a record of its own. Retrieval runs in the application and calls no Azure API. [6][7]
- `control.canary_triggered`: absent, derivable by the deployment. Needs the deployment's canary register and the text or arguments the value would appear in. [7]
- `turn` events: unconfirmed, as a record of its own. The pages do not say whether a model call is recorded as an action operation. [6][7]
- `session.id`, for grouping: absent, held by the deployment, or supplied by it. The lab's session identifier exists only in the lab; no page names a way to send it. [7]
- `turn.tokens_in`: unconfirmed, as its own field. Token metrics are series split by deployment and model, not per-call values; an entry's open properties could carry one, which no page settles. [2][7]
- `tool_pre` events: absent, as a record of its own. The lab's tools run in the application and call no Azure API. [6][7]
- `retrieval.permission_context`: absent, derivable by the deployment. Needs the caller's scope and each document's scope, which only the deployment holds. [7]

**Foundry resource logs through a diagnostic setting.**

- `retrieval.document_ids`: unconfirmed, only as content the application wrote. Chunk identifiers, whose prefix is the document identifier, reach the model only inside tool results the lab writes; whether a body is logged is not settled. [4][2]
- `retrieval` events: absent, as a record of its own. Retrieval runs in the application; no category records it, and Trace is for Custom question answering only. [2][1]
- `control.canary_triggered`: absent, derivable by the deployment. Needs the deployment's canary register and the text or arguments the value would appear in. [4]
- `turn` events: available by default, as a record of its own. The how-to counts requests from RequestResponse records. Partial: one record per request to the resource; that each model call is one request is not stated. [1][2]
- `session.id`, for grouping: unconfirmed, as its own field. correlationId is an optional header field; nothing else could group a session. Partial: correlationId groups a set of related events, typically one operation's start and finish, not a session. [4]
- `turn.tokens_in`: unconfirmed, as its own field. Neither RequestResponse nor AzureOpenAIRequestUsage has a documented field list. [4][2]
- `tool_pre` events: absent, as a record of its own. The lab's tools run in the application; no category records a tool call. [2][1]
- `retrieval.permission_context`: absent, derivable by the deployment. Needs the caller's scope and each document's scope, which only the deployment holds. [4]

**Foundry agent tracing for a hosted agent, in Application Insights.**

- `retrieval.document_ids`: absent, held by the deployment, or supplied by it. Retrieval runs in agent code; its spans come only from instrumentation. [11][12]
- `retrieval` events: absent, held by the deployment, or supplied by it. As turn. [11][12]
- `control.canary_triggered`: absent, derivable by the deployment. Needs the deployment's canary register. [11]
- `turn` events: absent, held by the deployment, or supplied by it. Model calls run in agent code; the out-of-the-box instrumentation covers Microsoft Agent Framework and LangChain only. [11][12]
- `session.id`, for grouping: unconfirmed, as its own field. The server-side trace's attributes are not documented. [11][12][8]
- `turn.tokens_in`: absent, held by the deployment, or supplied by it. As turn.index. [11][12]
- `tool_pre` events: absent, held by the deployment, or supplied by it. As turn. [11][12]
- `retrieval.permission_context`: absent, derivable by the deployment. Needs the caller's scope and each document's scope, which only the deployment holds. [11]
<!-- /generated:decisive-azure -->

<!-- generated:decisive-aws -->
**CloudTrail management events and CloudWatch runtime metrics.**

- `retrieval.document_ids`: unconfirmed, only as content the application wrote. Would reach Bedrock only inside tool results in a request, whose logging here is not settled. [22][21]
- `retrieval` events: absent, as a record of its own. Retrieval runs in the application and calls no AWS API. [21][22]
- `control.canary_triggered`: absent, derivable by the deployment. Needs the deployment's canary register. [22]
- `turn` events: available by default, as a record of its own. The four runtime calls are logged as management events, which CloudTrail logs by default. [21]
- `session.id`, for grouping: absent, held by the deployment, or supplied by it. A session identifier reaches Bedrock only as caller-supplied request metadata. [21][16]
- `turn.tokens_in`: unconfirmed, as its own field. Would sit in responseElements, null in the example; the metrics are series by model identifier, not per-call values. [21][22][23]
- `tool_pre` events: absent, as a record of its own. The lab's tools run in the application and call no AWS API. [21][22]
- `retrieval.permission_context`: absent, derivable by the deployment. Needs the caller's scope and each document's scope, which only the deployment holds. [22]

**Model invocation logging to CloudWatch Logs or Amazon S3.**

- `retrieval.document_ids`: available by default, only as content the application wrote. The lab's search tool writes each chunk identifier, whose prefix is the document identifier, into its result, which the next request body carries. [15]
- `retrieval` events: available by default, only as content the application wrote. A retrieval's results enter the next request body as tool-result text the application wrote. [15]
- `control.canary_triggered`: absent, derivable by the deployment. Needs the deployment's canary register. [15]
- `turn` events: available by default, as a record of its own. One record per model invocation. [15]
- `session.id`, for grouping: absent, held by the deployment, or supplied by it. Only as caller-supplied request metadata, which source 16 suggests for session identifiers and Bedrock does not enforce. [15][16]
- `turn.tokens_in`: available by default, as its own field. input.inputTokenCount is a field of every record. Partial: the input tokens in the request; whether cached tokens are counted is not stated, and the register counts them. [15]
- `tool_pre` events: available by default, inside a request or response body, at a path no page documents. The model's tool call is in the response body; its path in the logged body is not documented. [15][17]
- `retrieval.permission_context`: absent, derivable by the deployment. Needs the caller's scope and each document's scope, which only the deployment holds. [15]

**AgentCore Observability for an agent hosted in AgentCore Runtime.**

- `retrieval.document_ids`: absent, held by the deployment, or supplied by it. Retrieval runs in agent code; its spans come only from instrumentation. [27][25]
- `retrieval` events: absent, held by the deployment, or supplied by it. As turn. [27][25][28]
- `control.canary_triggered`: absent, derivable by the deployment. Needs the deployment's canary register. [27]
- `turn` events: absent, held by the deployment, or supplied by it. Model calls run in agent code; their spans come only from instrumentation. [27][25][28]
- `session.id`, for grouping: available by default, as its own field. session.id on the span and session_id on the application log. [27]
- `turn.tokens_in`: absent, held by the deployment, or supplied by it. Source 25 lists token usage among dashboard metrics, but no runtime record in source 27 carries it. [27][25]
- `tool_pre` events: absent, held by the deployment, or supplied by it. As turn. [27][25][28]
- `retrieval.permission_context`: absent, derivable by the deployment. Needs the caller's scope and each document's scope, which only the deployment holds. [27]
<!-- /generated:decisive-aws -->

## 3. Class by class, on vendor defaults only

**How an answer is computed.** For each column, the detector counted for the
class at M5 is re-run over the class's successful trials and its benign
denominator, read only, with everything the column does not count as available
taken away: a field is nulled, an event type the surface keeps no record of is
dropped, and where no key groups a session's records, each record runs as a
session of one. The deployment's own configuration, its allow lists, document
inventory and task tool set, is held as scored. The result is compared with the
baseline under methodology Section 4 as M5 ruling 2 reads it. An input the
pages do not settle is run both ways, and if the answers differ the class reads
`uc`. No model call is made and nothing under `runs/` is written.

**What a detector needs beyond the fields it declares.** `d-a07` reasons from
the absence of retrieval events in a session, and `d-a08` fires first on a
session's count of tool calls, which reads no field. `d-a03`, `d-a07` and
`d-a08` read a session's events together. The M5 harness took one file as one
session and every source as an ASTP event, so none of this could matter there.
It matters here, and a test checks each need against the frozen detectors.

<!-- generated:classes -->
| Class | Counted detector | n | Azure: as shipped | Azure: model layer on | Azure: model layer on, body parsed | Azure: agent layer on | Azure: agent layer on, body parsed | Azure: model and agent layers together | AWS: as shipped | AWS: model layer on | AWS: model layer on, body parsed | AWS: agent layer on | AWS: agent layer on, body parsed | AWS: model and agent layers together |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | d-a01 | 0 | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` |
| A2 | d-a02 | 0 | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` |
| A3 | d-a03 | 0 | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` |
| A4 | d-a04 | 0 | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` | `nt` |
| A5\* n=1 | d-a06 | 1 | `X` | `X` | `X` | `X` | `X` | `uc` | `X` | `X` | `X` | `X` | `X` | `uc` |
| A6 | d-a06 | 10 | `X` | `X` | `X` | `X` | `X` | `uc` | `X` | `X` | `X` | `X` | `X` | `uc` |
| A7 n=1 | d-a07 | 1 | `X` | `X` | `X` | `X` | `X` | `uc` | `X` | `X` | `X` | `X` | `X` | `uc` |
| A8 c | d-a08 | 10 | `uc` | `uc` | `uc` | `Xc` | `Xc` | `uc` | `uc` | `uc` | `uc` | `Xc` | `Xc` | `uc` |
| A9\* | d-a03 | 10 | `X` | `X` | `X` | `X` | `X` | `uc` | `X` | `X` | `X` | `X` | `X` | `uc` |
| A10 | none | 0 | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` | `ab` |
<!-- /generated:classes -->

What each counted detector lost, and what it still caught. A range is the
spread across the combinations of unsettled inputs.

<!-- generated:passes -->
| Column | Class | Inputs not counted, or unsettled | Caught, of n | False positives |
|---|---|---|---|---|
| Azure: as shipped | A5 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 1 | 0 of 100 |
| Azure: as shipped | A6 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 10 | 0 of 100 |
| Azure: as shipped | A7 | field:control.canary_triggered (no), event:retrieval (no), event:turn (maybe), group:session.id (no) | 0 of 1 | 0 of 100 |
| Azure: as shipped | A8 | field:turn.tokens_in (maybe), event:tool_pre (no), event:turn (maybe), group:session.id (no) | 0 to 10 of 10 | 0 of 100 |
| Azure: as shipped | A9 | field:control.canary_triggered (no), field:retrieval.permission_context (no), event:retrieval (no), event:turn (maybe), group:session.id (no) | 0 of 10 | 0 of 100 |
| Azure: model layer on | A5 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 1 | 0 of 100 |
| Azure: model layer on | A6 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 10 | 0 of 100 |
| Azure: model layer on | A7 | field:control.canary_triggered (no), event:retrieval (no), event:turn (maybe), group:session.id (maybe) | 0 of 1 | 0 of 100 |
| Azure: model layer on | A8 | field:turn.tokens_in (maybe), event:tool_pre (no), event:turn (maybe), group:session.id (maybe) | 0 to 10 of 10 | 0 of 100 |
| Azure: model layer on | A9 | field:control.canary_triggered (no), field:retrieval.permission_context (no), event:retrieval (no), event:turn (maybe), group:session.id (maybe) | 0 of 10 | 0 of 100 |
| Azure: model layer on, body parsed | A5 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 1 | 0 of 100 |
| Azure: model layer on, body parsed | A6 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 10 | 0 of 100 |
| Azure: model layer on, body parsed | A7 | field:control.canary_triggered (no), event:retrieval (no), event:turn (maybe), group:session.id (maybe) | 0 of 1 | 0 of 100 |
| Azure: model layer on, body parsed | A8 | field:turn.tokens_in (maybe), event:tool_pre (no), event:turn (maybe), group:session.id (maybe) | 0 to 10 of 10 | 0 of 100 |
| Azure: model layer on, body parsed | A9 | field:control.canary_triggered (no), field:retrieval.permission_context (no), event:retrieval (no), event:turn (maybe), group:session.id (maybe) | 0 of 10 | 0 of 100 |
| Azure: agent layer on | A5 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 1 | 0 of 100 |
| Azure: agent layer on | A6 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 10 | 0 of 100 |
| Azure: agent layer on | A7 | field:control.canary_triggered (no), event:retrieval (no), event:turn (no), group:session.id (maybe) | 0 of 1 | 0 of 100 |
| Azure: agent layer on | A8 | field:turn.tokens_in (no), event:tool_pre (no), event:turn (no), group:session.id (maybe) | 0 of 10 | 0 of 100 |
| Azure: agent layer on | A9 | field:control.canary_triggered (no), field:retrieval.permission_context (no), event:retrieval (no), event:turn (no), group:session.id (maybe) | 0 of 10 | 0 of 100 |
| Azure: agent layer on, body parsed | A5 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 1 | 0 of 100 |
| Azure: agent layer on, body parsed | A6 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 10 | 0 of 100 |
| Azure: agent layer on, body parsed | A7 | field:control.canary_triggered (no), event:retrieval (no), event:turn (no), group:session.id (maybe) | 0 of 1 | 0 of 100 |
| Azure: agent layer on, body parsed | A8 | field:turn.tokens_in (no), event:tool_pre (no), event:turn (no), group:session.id (maybe) | 0 of 10 | 0 of 100 |
| Azure: agent layer on, body parsed | A9 | field:control.canary_triggered (no), field:retrieval.permission_context (no), event:retrieval (no), event:turn (no), group:session.id (maybe) | 0 of 10 | 0 of 100 |
| AWS: as shipped | A5 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 1 | 0 of 100 |
| AWS: as shipped | A6 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 10 | 0 of 100 |
| AWS: as shipped | A7 | field:control.canary_triggered (no), event:retrieval (no), group:session.id (no) | 0 of 1 | 0 of 100 |
| AWS: as shipped | A8 | field:turn.tokens_in (maybe), event:tool_pre (no), group:session.id (no) | 0 to 10 of 10 | 0 of 100 |
| AWS: as shipped | A9 | field:control.canary_triggered (no), field:retrieval.permission_context (no), event:retrieval (no), group:session.id (no) | 0 of 10 | 0 of 100 |
| AWS: model layer on | A5 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 1 | 0 of 100 |
| AWS: model layer on | A6 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 10 | 0 of 100 |
| AWS: model layer on | A7 | field:control.canary_triggered (no), event:retrieval (no), group:session.id (no) | 0 of 1 | 0 of 100 |
| AWS: model layer on | A8 | field:turn.tokens_in (maybe), event:tool_pre (no), group:session.id (no) | 0 to 10 of 10 | 0 of 100 |
| AWS: model layer on | A9 | field:control.canary_triggered (no), field:retrieval.permission_context (no), event:retrieval (no), group:session.id (no) | 0 of 10 | 0 of 100 |
| AWS: model layer on, body parsed | A5 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 1 | 0 of 100 |
| AWS: model layer on, body parsed | A6 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 10 | 0 of 100 |
| AWS: model layer on, body parsed | A7 | field:control.canary_triggered (no), event:retrieval (no), group:session.id (no) | 0 of 1 | 0 of 100 |
| AWS: model layer on, body parsed | A8 | field:turn.tokens_in (maybe), event:tool_pre (maybe), group:session.id (no) | 0 to 10 of 10 | 0 of 100 |
| AWS: model layer on, body parsed | A9 | field:control.canary_triggered (no), field:retrieval.permission_context (no), event:retrieval (no), group:session.id (no) | 0 of 10 | 0 of 100 |
| AWS: agent layer on | A5 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 1 | 0 of 100 |
| AWS: agent layer on | A6 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 10 | 0 of 100 |
| AWS: agent layer on | A7 | field:control.canary_triggered (no), event:retrieval (no), event:turn (no) | 0 of 1 | 0 of 100 |
| AWS: agent layer on | A8 | field:turn.tokens_in (no), event:tool_pre (no), event:turn (no) | 0 of 10 | 0 of 100 |
| AWS: agent layer on | A9 | field:control.canary_triggered (no), field:retrieval.permission_context (no), event:retrieval (no), event:turn (no) | 0 of 10 | 0 of 100 |
| AWS: agent layer on, body parsed | A5 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 1 | 0 of 100 |
| AWS: agent layer on, body parsed | A6 | field:retrieval.document_ids (no), event:retrieval (no) | 0 of 10 | 0 of 100 |
| AWS: agent layer on, body parsed | A7 | field:control.canary_triggered (no), event:retrieval (no), event:turn (no) | 0 of 1 | 0 of 100 |
| AWS: agent layer on, body parsed | A8 | field:turn.tokens_in (no), event:tool_pre (no), event:turn (no) | 0 of 10 | 0 of 100 |
| AWS: agent layer on, body parsed | A9 | field:control.canary_triggered (no), field:retrieval.permission_context (no), event:retrieval (no), event:turn (no) | 0 of 10 | 0 of 100 |
<!-- /generated:passes -->

**The model and agent layers together.** Ruling 1 allows a combined answer only
where a documented key links the two layers' records.

<!-- generated:combined -->
- **Azure: not linked.** No page read names a key shared by a RequestResponse record and a hosted agent's server-side trace. [2][4][11][12]
- **AWS: not linked.** The invocation log's requestId identifies one model call and AgentCore's aws.request_id one agent invocation; no page read links them. A session identifier could join them only as caller-supplied request metadata. [15][27]
<!-- /generated:combined -->

**Any detector in the frozen set**, recorded beside the answer and deciding
nothing, as M5 ruling 1 has it. A cell counts the successful trials on which any
of the seven detectors fires; a range runs from every unsettled input taken
away to every one kept.

<!-- generated:any-detector -->
| Class | n | Azure: as shipped | Azure: model layer on | Azure: model layer on, body parsed | Azure: agent layer on | Azure: agent layer on, body parsed | AWS: as shipped | AWS: model layer on | AWS: model layer on, body parsed | AWS: agent layer on | AWS: agent layer on, body parsed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 to 1 | 0 | 0 |
| A6 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A8 | 10 | 0 to 10 | 0 to 10 | 0 to 10 | 0 | 0 | 0 to 10 | 0 to 10 | 0 to 10 | 0 | 0 |
| A9 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
<!-- /generated:any-detector -->

## 4. The fields a deployment has to add itself

In priority order, as ruled: first the fields whose addition returns a class to
its baseline, measured by vendor pass on each vendor's headline column; then
every other field that column does not count, by tier and register order.

<!-- generated:additions -->
**Azure, on the headline column (model layer on).**

What returns each class to its baseline, by vendor pass. Each line is one smallest set; where a class has two, either will do.

- A5: `retrieval` records and `retrieval.document_ids`.
- A6: `retrieval` records and `retrieval.document_ids`.
- A7: `turn` records and `control.canary_triggered`.
- A8: `turn` records and `turn.tokens_in`; or `tool_pre` records and `session.id`.
- A9: `retrieval` records, `turn` records, `control.canary_triggered`, `retrieval.permission_context` and `session.id`.

Measured fields, in order:

1. `retrieval.document_ids`, required, in a set for A5, A6
2. `control.canary_triggered`, required, in a set for A7, A9
3. `session.id`, not_required, in a set for A8, A9
4. `retrieval.permission_context`, required, in a set for A9
5. `turn.tokens_in`, not_required, in a set for A8

Then, by tier and register order: `session.start_time` (optional), `session.user_id` (optional), `session.client_app` (optional), `session.config_version` (optional), `content.prompt_hash` (optional), `content.response_hash` (optional), `content.redaction_applied` (optional), `action.tool_name` (optional), `action.result_hash` (optional), `control.policy_version` (optional), `session.tenant_id` (not_required), `session.agent_id` (not_required), `turn.index` (not_required), `turn.model_id` (not_required), `turn.model_version` (not_required), `turn.tokens_out` (not_required), `turn.latency` (not_required), `turn.finish_reason` (not_required), `content.prompt_text` (not_required), `content.response_text` (not_required), `content.system_prompt_version` (not_required), `retrieval.chunk_ids` (not_required), `retrieval.scores` (not_required), `retrieval.query_text` (not_required), `retrieval.source_provenance` (not_required), `action.tool_arguments` (not_required), `action.result_bytes` (not_required), `action.permission_decision` (not_required), `action.egress_target` (not_required), `action.context_document_ids` (not_required), `control.block_reason` (not_required).

**AWS, on the headline column (model layer on).**

What returns each class to its baseline, by vendor pass. Each line is one smallest set; where a class has two, either will do.

- A5: `retrieval` records and `retrieval.document_ids`.
- A6: `retrieval` records and `retrieval.document_ids`.
- A7: `control.canary_triggered`.
- A8: `turn.tokens_in`; or `tool_pre` records and `session.id`.
- A9: `retrieval` records, `control.canary_triggered`, `retrieval.permission_context` and `session.id`.

Measured fields, in order:

1. `retrieval.document_ids`, required, in a set for A5, A6
2. `control.canary_triggered`, required, in a set for A7, A9
3. `session.id`, not_required, in a set for A8, A9
4. `retrieval.permission_context`, required, in a set for A9
5. `turn.tokens_in`, not_required, in a set for A8

Then, by tier and register order: `session.start_time` (optional), `session.user_id` (optional), `session.client_app` (optional), `session.config_version` (optional), `content.prompt_hash` (optional), `content.response_hash` (optional), `content.redaction_applied` (optional), `action.tool_name` (optional), `action.result_hash` (optional), `control.policy_version` (optional), `session.tenant_id` (not_required), `session.agent_id` (not_required), `turn.index` (not_required), `turn.model_id` (not_required), `turn.model_version` (not_required), `turn.latency` (not_required), `turn.finish_reason` (not_required), `content.prompt_text` (not_required), `content.response_text` (not_required), `content.system_prompt_version` (not_required), `retrieval.chunk_ids` (not_required), `retrieval.scores` (not_required), `retrieval.query_text` (not_required), `retrieval.source_provenance` (not_required), `action.tool_arguments` (not_required), `action.result_bytes` (not_required), `action.permission_decision` (not_required), `action.egress_target` (not_required), `action.context_document_ids` (not_required), `control.block_reason` (not_required).
<!-- /generated:additions -->

**A Not required tier is not evidence that a field carries nothing.** Read a
field's row in `results/necessity-matrix.md` before quoting its tier. Two of the
fields above make the point. `session.id` tiered Not required at M5 because the
harness took one capture file as one session, and it is needed here for A8 and
A9 as soon as records have to be grouped. `turn.tokens_in` tiered Not required
because `d-a08` fired first on tool calls, and it is one of A8's two routes
here. `action.egress_target`, also Not required, separates the A1 attack from
benign session `m3-b100` in the corpus, which the tiering rule cannot credit.

## 5. Limitations

- **Five classes, two of them on one session.** The plan's question has no
  answer for A1 to A4 or A10, and the A5 and A7 answers rest on one successful
  trial each. The A8 column is circular.
- **Nothing was observed.** Every verdict is read from documentation. No log
  record from either vendor was seen, so where a page is wrong or out of date,
  so is its verdict. The pages move: the retrieval date is the claim's date.
- **What stays unconfirmed, and why.** Azure documents no properties for its
  resource log categories [2][4][5][14], nor the attributes of a hosted agent's
  server-side trace [11][12]. No page says whether Bedrock's input token count
  includes cached tokens [15], or shows the shape of a logged body [15][16].
  CloudTrail's request parameters for a Converse call are not listed [21][22].
  No page says whether the Azure activity log records a model call [6][7]. No
  page names a key linking either vendor's model layer to its agent layer.
- **The pass works at ASTP granularity.** A vendor record is modelled as the
  ASTP event it corresponds to, with the fields the vendor lacks nulled. A
  vendor's own record could differ in ways this cannot capture.
- **The agent layer is assessed for this agent.** Foundry's out-of-the-box
  instrumentation covers Microsoft Agent Framework and LangChain [12], and
  AgentCore records model and tool calls only from instrumentation the
  deployment adds [25][28]. An agent built on a covered framework could record
  more on Foundry by default than this one would.
- **Out of scope, as ruled.** Bedrock Agents, knowledge bases and Guardrails
  [20][24], AgentCore Gateway and built-in tools [26], and either vendor's
  retrieval service. Each would matter to a deployment built on it.
- **Vendor controls are not ASTP controls.** A vendor content filter or
  guardrail is a control of its own. The lab's authorisation decision, its
  guardrail's reason and whether one of its canaries moved are held only by the
  lab, which is why every surface records those fields absent.

## 6. Traps for anyone repeating the checks

- **The product was renamed**, and a "(classic)" documentation set sits beside
  the current one. The Agent Service monitoring reference redirects to the
  classic set [13], and the current Azure OpenAI reference links there [5].
- **Microsoft pages carry two dates**, `ms.date` and `updated_at`. Only
  `updated_at` matches the visible "Last updated" line.
- **No AWS page carries a date**, in its markup or its text.
- **The schema index points to a page with no schema.** Source 4 links Foundry
  Tools' resource log schema to source 14, a how-to page.
- **Bedrock has two inference endpoints**, and invocation logging covers only
  `bedrock-runtime` [15][19].
- **Two AWS pages a search engine still lists redirect to the user guide's
  index**: the distillation pages on invocation logs and request metadata. They
  were not used.
- **Community answers are not documentation.** A search for what Azure's
  request and response logs contain returns question and answer threads on
  Microsoft's site. They were not read as evidence and none was used.
- **A search summary and a fetch summary paraphrase.** Every page here was read
  from its raw text.
- **A vendor's statement that it follows the OpenTelemetry GenAI conventions
  [8] is not a field list**, and ASTP's own mapping must not stand in for one.
- **One Foundry page's attribute table contains em-dashes** [8], so quotation
  from it avoids the table.
- **The M6 traps still apply** to anyone pricing either vendor's logs; see
  `docs/sentinel-mapping.md`.

## Quotations

The constraints that decide a verdict or are ambiguous, exactly as each page
reads.

<!-- generated:quotes -->
- [3] *Aren't collected by default. Create a diagnostic setting to collect resource logs.*
- [3] *Automatically collected without configuration.*
- [1] *Select Audit Logs, Request and Response Logs, Azure OpenAI Request Usage, and AllMetrics.*
- [1] *The "Trace" option in diagnostic logging is only available for Custom question answering.*
- [1] *Run this query to measure request latency by response code*
- [5] *All resource logs in Azure Monitor have the same header fields, followed by service-specific fields.*
- [4] *Any extended properties related to this category of events.*
- [4] *A GUID that's used to group together a set of related events.*
- [6] *Azure Monitor records management operations for your Azure resources through the activity log feature.*
- [7] *Contains the record of all create, update, delete, and action operations performed through Resource Manager.*
- [7] *Set of <Key, Value> pairs (that is, a Dictionary) describing the details of the event.*
- [8] *The following table describes common OpenTelemetry GenAI conventions for multi-agent observability.*
- [9] *Tracing is off by default.*
- [10] *Foundry automatically logs server-side traces for Prompt agents, Host agents, and workflows in the Foundry portal.*
- [11] *Hosted agents generate telemetry from the protocol runtime (the Responses or Invocations server) and from your agent code.*
- [12] *out-of-the-box instrumentation for Microsoft Agent Framework and LangChain*
- [12] *Each invocation generates a complete trace.*
- [12] *Enable content recording by setting the environment variable OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true in your agent configuration.*
- [15] *Model invocation logging is disabled by default.*
- [15] *you can collect the full request data, response data, and metadata associated with supported calls*
- [15] *Each invocation log entry is a JSON object with the following structure.*
- [15] *Every field in the record is populated by Amazon Bedrock automatically, with one exception: requestMetadata is the only field supplied by the caller.*
- [15] *The type of log record. Always ModelInvocationLog.*
- [15] *The request body sent to the model (up to 100 KB).*
- [15] *Select the modalities of the data requests and responses that you want to publish to the logs.*
- [15] *Model invocation logging is only supported for calls made through the bedrock-runtime endpoint.*
- [15] *The number of input tokens in the request.*
- [15] *The AWS STS or IAM ARN of the principal that made the request, including the role name and the session or user name.*
- [16] *Use higher-cardinality values such as session or trace identifiers only when you need to trace individual calls.*
- [16] *Request metadata is supplied per call and is not enforced by Amazon Bedrock.*
- [21] *CloudTrail is enabled on your AWS account when you create the account.*
- [21] *CloudTrail logs management event API operations by default.*
- [21] *Data events are often high-volume activities that CloudTrail doesn’t log by default.*
- [22] *The parameters, if any, that were sent with the request.*
- [22] *The response elements, if any, for actions that make changes (create, update, or delete actions).*
- [24] *Amazon Bedrock supports a monitoring system to help you understand the execution of any data ingestion jobs for your knowledge bases.*
- [25] *You can also instrument your agent code to provide additional span and trace data and custom metrics and logs.*
- [26] *Signals marked with an asterisk require explicit enablement.*
- [27] *The following table defines the operation for which spans are created and the attributes for each captured span.*
- [27] *To enable this span data, you need to enable observability on your agent resource.*
- [27] *request_payload - the request payload of the agent invocation*
- [28] *When you create an AgentCore runtime resource (agent), by default, AgentCore runtime creates a CloudWatch log group for the service-provided logs.*
- [28] *you first need to complete a one-time setup to turn on Amazon CloudWatch Transaction Search*
<!-- /generated:quotes -->
